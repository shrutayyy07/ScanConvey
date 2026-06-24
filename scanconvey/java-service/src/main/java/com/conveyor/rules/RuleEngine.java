package com.conveyor.rules;

import com.conveyor.audit.AuditLogger;
import com.conveyor.grpc.proto.DetectedObject;
import com.conveyor.grpc.proto.FrameTelemetry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Week 6 - Intelligent rule engine for defect classification.
 *
 * Consumes the raw YOLO prediction arrays forwarded by the gRPC service,
 * computes per-defect frequency metrics over a rolling window, and flags
 * an "Emergency Line Halt" when multi-axis tolerances are breached.
 *
 * Tolerance bounds (configurable via application.properties):
 *   - crack_rate_threshold       : max cracks per 100 frames (default 5)
 *   - misalignment_rate_threshold: max misalignments per 100 frames (default 3)
 *   - missing_component_threshold: max missing-component events per 100 frames (default 2)
 *   - confidence_floor           : discard predictions below this score (default 0.45)
 */
@Component
public class RuleEngine {

    private static final Logger log = LoggerFactory.getLogger(RuleEngine.class);

    // Rolling window size in frames
    private static final int WINDOW = 100;

    // Tolerance bounds
    private static final int    CRACK_THRESHOLD       = 5;
    private static final int    MISALIGN_THRESHOLD    = 3;
    private static final int    MISSING_THRESHOLD     = 2;
    private static final double CONFIDENCE_FLOOR      = 0.45;
    // If any single defect type exceeds this confidence on a single frame, halt immediately
    private static final double INSTANT_HALT_CONF     = 0.92;

    // Defect counters within the rolling window
    private final Map<DefectType, AtomicInteger> windowCounts = new EnumMap<>(DefectType.class);
    private final AtomicLong framesSeen = new AtomicLong(0);

    private final AuditLogger auditLogger;

    public RuleEngine(AuditLogger auditLogger) {
        this.auditLogger = auditLogger;
        for (DefectType t : DefectType.values()) {
            windowCounts.put(t, new AtomicInteger(0));
        }
    }

    public enum DefectType {
        CRACK, MISALIGNMENT, MISSING_COMPONENT, UNKNOWN
    }

    public record RuleResult(boolean isHalt, String reason) {
        public static RuleResult ok() { return new RuleResult(false, ""); }
        public static RuleResult halt(String reason) { return new RuleResult(true, reason); }
    }

    /**
     * Evaluate a single frame's telemetry against the tolerance rules.
     * Thread-safe: called concurrently from the gRPC handler.
     */
    public RuleResult evaluate(FrameTelemetry frame) {
        long seq = framesSeen.incrementAndGet();

        // Reset window counts every WINDOW frames
        if (seq % WINDOW == 0) {
            windowCounts.values().forEach(c -> c.set(0));
            log.debug("Rule engine window reset at frame {}", seq);
        }

        List<DetectedObject> objects = frame.getObjectsList();

        for (DetectedObject obj : objects) {
            if (obj.getConfidence() < CONFIDENCE_FLOOR) continue;

            DefectType type = parseDefectType(obj.getDefectType());
            if (type == DefectType.UNKNOWN) continue;

            int count = windowCounts.get(type).incrementAndGet();

            // Instant halt on extremely high-confidence single detection
            if (obj.getConfidence() >= INSTANT_HALT_CONF) {
                String reason = String.format(
                    "High-confidence %s detected (conf=%.2f, frame=%d)",
                    type, obj.getConfidence(), frame.getFrameIndex());
                auditLogger.logHalt(reason, frame);
                return RuleResult.halt(reason);
            }

            // Rolling-window frequency check
            RuleResult check = checkThreshold(type, count, frame);
            if (check.isHalt()) return check;
        }

        return RuleResult.ok();
    }

    private RuleResult checkThreshold(DefectType type, int count, FrameTelemetry frame) {
        int threshold = switch (type) {
            case CRACK             -> CRACK_THRESHOLD;
            case MISALIGNMENT      -> MISALIGN_THRESHOLD;
            case MISSING_COMPONENT -> MISSING_THRESHOLD;
            default                -> Integer.MAX_VALUE;
        };

        if (count > threshold) {
            String reason = String.format(
                "EMERGENCY LINE HALT: %s frequency %d exceeded tolerance %d in last %d frames (frame=%d)",
                type, count, threshold, WINDOW, frame.getFrameIndex());
            log.error(reason);
            auditLogger.logHalt(reason, frame);
            return RuleResult.halt(reason);
        }
        return RuleResult.ok();
    }

    private DefectType parseDefectType(String raw) {
        return switch (raw.toLowerCase()) {
            case "crack"              -> DefectType.CRACK;
            case "misalignment"       -> DefectType.MISALIGNMENT;
            case "missing_component"  -> DefectType.MISSING_COMPONENT;
            default                   -> DefectType.UNKNOWN;
        };
    }
}
