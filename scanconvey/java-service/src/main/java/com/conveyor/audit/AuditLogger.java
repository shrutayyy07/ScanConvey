package com.conveyor.audit;

import com.conveyor.grpc.proto.FrameTelemetry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Week 7 - Database-free transactional audit logger.
 *
 * Writes factory incident and telemetry compliance summaries to local
 * Markdown flat-files using Java NIO FileChannel for high-throughput I/O.
 *
 * A ReentrantLock guards every write so concurrent virtual threads from
 * the gRPC handler and the rule engine cannot interleave partial lines.
 *
 * Two log files are maintained:
 *   - audit/incidents.md  : halt events and rule violations
 *   - audit/telemetry.md  : frame-by-frame compliance summaries
 */
@Component
public class AuditLogger {

    private static final Logger log = LoggerFactory.getLogger(AuditLogger.class);
    private static final DateTimeFormatter FMT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'").withZone(ZoneOffset.UTC);

    private final Path incidentFile;
    private final Path telemetryFile;

    private final ReentrantLock incidentLock  = new ReentrantLock();
    private final ReentrantLock telemetryLock = new ReentrantLock();

    public AuditLogger(@Value("${audit.log-dir:audit}") String logDir) {
        Path dir = Path.of(logDir);
        try {
            Files.createDirectories(dir);
        } catch (IOException e) {
            throw new IllegalStateException("Cannot create audit log directory: " + dir, e);
        }
        this.incidentFile  = dir.resolve("incidents.md");
        this.telemetryFile = dir.resolve("telemetry.md");
        initFile(incidentFile,  "# Conveyor Counter - Incident Log\n\n");
        initFile(telemetryFile, "# Conveyor Counter - Telemetry Compliance Log\n\n");
    }

    /**
     * Write an emergency-halt incident entry.
     * Called from the rule engine, potentially on a virtual thread.
     */
    public void logHalt(String reason, FrameTelemetry frame) {
        String entry = String.format(
            "## HALT EVENT — %s\n" +
            "- **Reason:** %s\n" +
            "- **Frame:** %d / %d\n" +
            "- **Boxes:** %d | **Packets:** %d | **Parcels:** %d\n" +
            "- **Objects in frame:** %d\n\n",
            now(),
            reason,
            frame.getFrameIndex(), frame.getTotalFrames(),
            frame.getBoxCount(), frame.getPacketCount(), frame.getParcelCount(),
            frame.getObjectsCount()
        );
        writeNio(incidentFile, incidentLock, entry);
        log.warn("Audit halt logged: {}", reason);
    }

    /**
     * Write a frame compliance summary (called every N frames).
     */
    public void logTelemetry(FrameTelemetry frame, boolean passed) {
        String status = passed ? "PASS" : "WARN";
        String entry = String.format(
            "| %s | %d | %d | %d | %d | %d | %s |\n",
            now(),
            frame.getFrameIndex(),
            frame.getBoxCount(),
            frame.getPacketCount(),
            frame.getParcelCount(),
            frame.getObjectsCount(),
            status
        );

        // Write table header lazily on first row
        telemetryLock.lock();
        try {
            if (Files.size(telemetryFile) < 100) {
                writeNio(telemetryFile, telemetryLock,
                    "| Timestamp | Frame | Boxes | Packets | Parcels | Objects | Status |\n" +
                    "|-----------|-------|-------|---------|---------|---------|--------|\n");
            }
        } catch (IOException ignored) {
        } finally {
            telemetryLock.unlock();
        }

        writeNio(telemetryFile, telemetryLock, entry);
    }

    // ── private ──────────────────────────────────────────────────────────────

    private void initFile(Path file, String header) {
        if (!Files.exists(file)) {
            writeNio(file, new ReentrantLock(), header);
        }
    }

    /**
     * Thread-safe NIO write using FileChannel + ReentrantLock.
     * Opens with APPEND so concurrent processes also remain safe.
     */
    private void writeNio(Path file, ReentrantLock lock, String content) {
        lock.lock();
        try (FileChannel channel = FileChannel.open(
                file,
                StandardOpenOption.CREATE,
                StandardOpenOption.WRITE,
                StandardOpenOption.APPEND)) {
            byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
            ByteBuffer buf = ByteBuffer.wrap(bytes);
            while (buf.hasRemaining()) {
                channel.write(buf);
            }
        } catch (IOException e) {
            log.error("Audit write failed for {}: {}", file, e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    private String now() {
        return FMT.format(Instant.now());
    }
}
