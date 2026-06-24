package com.conveyor.controller;

import com.conveyor.service.TelemetryQueueService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * Week 1 - High-throughput reactive telemetry ingestion gateway.
 *
 * Built with Spring WebFlux so network threads are never blocked.
 * Each POST /telemetry call drops an immediate acknowledgement and
 * enqueues the payload for async downstream processing.
 *
 * GET /telemetry/stream is a Server-Sent Events channel that pushes
 * live rule-engine alerts to any subscribed consumer (e.g. a monitoring
 * dashboard or the Python vision engine).
 */
@RestController
@RequestMapping("/telemetry")
public class TelemetryController {

    private static final Logger log = LoggerFactory.getLogger(TelemetryController.class);

    private final TelemetryQueueService queue;

    public TelemetryController(TelemetryQueueService queue) {
        this.queue = queue;
    }

    /**
     * Non-blocking ingest endpoint.
     * Returns 202 Accepted immediately; processing is asynchronous.
     */
    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE,
                 produces = MediaType.APPLICATION_JSON_VALUE)
    public Mono<Map<String, Object>> ingest(@RequestBody Map<String, Object> payload) {
        return Mono.fromCallable(() -> {
            queue.enqueue(payload);
            log.debug("Telemetry enqueued: frame={}", payload.get("frame_index"));
            return Map.<String, Object>of("accepted", true, "queued", queue.size());
        });
    }

    /**
     * SSE stream of rule-engine events (alerts, halts, stats).
     * Clients connect once and receive a continuous stream.
     */
    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<Map<String, Object>> stream() {
        return queue.eventFlux();
    }

    @GetMapping("/health")
    public Mono<Map<String, Object>> health() {
        return Mono.just(Map.of("status", "ok", "queue_size", queue.size()));
    }
}
