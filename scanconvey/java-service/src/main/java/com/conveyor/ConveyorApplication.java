package com.conveyor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.embedded.netty.NettyReactiveWebServerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class ConveyorApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConveyorApplication.class, args);
    }

    /**
     * Week 1: configure Netty with virtual-thread executor for
     * non-blocking telemetry ingestion at high throughput.
     */
    @Bean
    public NettyReactiveWebServerFactory nettyFactory() {
        NettyReactiveWebServerFactory factory = new NettyReactiveWebServerFactory();
        factory.addServerCustomizers(httpServer ->
            httpServer.runOn(reactor.netty.resources.LoopResources.create(
                "conveyor-loop", 1,
                Runtime.getRuntime().availableProcessors(), true))
        );
        return factory;
    }
}
