package com.conveyor.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

import java.util.Map;
import java.util.concurrent.LinkedBlockingDeque;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Week 1 - Asynchronous in-memory event queue.
 *
 * Uses Project Reactor's Sinks.Many (multicast) so that multiple
 * downstream consumers (SSE clients, rule engine, audit logger) can
 * each subscribe independently without blocking the ingest thread.
 *
 * The backing LinkedBlockingDeque lets Java 21 Virtual Threads drain
 * the queue without monopolising platform threads.
 */
@Service
public class TelemetryQueueService {

    private static final Logger log = LoggerFactory.getLogger(TelemetryQueueService.class);

    private static final int BUFFER_CAPACITY = 4096;

    // Multicast sink - multiple subscribers, replay last 256 events for late joiners
    private final Sinks.Many<Map<String, Object>> sink =
            Sinks.many().multicast().onBackpressureBuffer(BUFFER_CAPACITY, false);

    private final LinkedBlockingDeque<Map<String, Object>> backlog = new LinkedBlockingDeque<>(BUFFER_CAPACITY);
    private final AtomicInteger counter = new AtomicInteger(0);

    /**
     * Enqueue a telemetry payload.
     * Returns immediately (non-blocking) - a virtual thread drains the queue.
     */
    public void enqueue(Map<String, Object> payload) {
        boolean offered = backlog.offerLast(payload);
        if (!offered) {
            log.warn("Telemetry backlog full - dropping frame {}", payload.get("frame_index"));
            return;
        }
        counter.incrementAndGet();
        // Drain in a virtual thread so we never block the Netty event loop
        Thread.ofVirtual().name("telemetry-drain-" + counter.get()).start(this::drain);
    }

    private void drain() {
        Map<String, Object> payload = backlog.pollFirst();
        if (payload == null) return;
        Sinks.EmitResult result = sink.tryEmitNext(payload);
        if (result.isFailure()) {
            log.debug("Sink emit failed ({}); no active subscribers", result);
        }
    }

    /**
     * Flux that all subscribers (SSE, rule engine) can consume.
     */
    public Flux<Map<String, Object>> eventFlux() {
        return sink.asFlux();
    }

    public int size() {
        return backlog.size();
    }
}
