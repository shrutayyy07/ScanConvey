package com.conveyor.grpc;

import com.conveyor.grpc.proto.ConveyorTelemetryGrpc;
import com.conveyor.grpc.proto.FrameTelemetry;
import com.conveyor.grpc.proto.TelemetryAck;
import com.conveyor.rules.RuleEngine;
import com.conveyor.service.TelemetryQueueService;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.server.service.GrpcService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * Week 3 - gRPC server endpoint.
 *
 * Python sends a bidirectional stream of FrameTelemetry messages.
 * For each frame this service:
 *   1. Converts the proto to a plain Map and feeds it to TelemetryQueueService (Week 1).
 *   2. Runs the RuleEngine (Week 6) to check defect tolerances.
 *   3. Streams back a TelemetryAck, including an emergency halt flag if triggered.
 */
@GrpcService
public class ConveyorTelemetryService
        extends ConveyorTelemetryGrpc.ConveyorTelemetryImplBase {

    private static final Logger log = LoggerFactory.getLogger(ConveyorTelemetryService.class);

    private final TelemetryQueueService queue;
    private final RuleEngine            rules;

    public ConveyorTelemetryService(TelemetryQueueService queue, RuleEngine rules) {
        this.queue = queue;
        this.rules = rules;
    }

    @Override
    public StreamObserver<FrameTelemetry> streamTelemetry(
            StreamObserver<TelemetryAck> responseObserver) {

        return new StreamObserver<>() {

            @Override
            public void onNext(FrameTelemetry frame) {
                log.debug("gRPC frame received: index={} objects={}",
                        frame.getFrameIndex(), frame.getObjectsCount());

                // Convert proto -> map for the reactive queue (Week 1 bridge)
                Map<String, Object> payload = protoToMap(frame);
                queue.enqueue(payload);

                // Week 6: evaluate rule engine
                RuleEngine.RuleResult result = rules.evaluate(frame);

                TelemetryAck.Builder ack = TelemetryAck.newBuilder().setAccepted(true);
                if (result.isHalt()) {
                    ack.setAccepted(false).setHaltReason(result.reason());
                    log.warn("EMERGENCY LINE HALT triggered: {}", result.reason());
                }
                responseObserver.onNext(ack.build());
            }

            @Override
            public void onError(Throwable t) {
                log.error("gRPC stream error: {}", t.getMessage());
                responseObserver.onError(t);
            }

            @Override
            public void onCompleted() {
                log.info("gRPC telemetry stream completed");
                responseObserver.onCompleted();
            }
        };
    }

    private Map<String, Object> protoToMap(FrameTelemetry f) {
        Map<String, Object> m = new HashMap<>();
        m.put("frame_index",  f.getFrameIndex());
        m.put("total_frames", f.getTotalFrames());
        m.put("box_count",    f.getBoxCount());
        m.put("packet_count", f.getPacketCount());
        m.put("parcel_count", f.getParcelCount());
        m.put("timestamp_ms", f.getTimestampMs());
        m.put("object_count", f.getObjectsCount());
        return m;
    }
}
