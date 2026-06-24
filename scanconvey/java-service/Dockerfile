FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app

# Install Maven
RUN apk add --no-cache maven

# Copy proto first (needed by protobuf-maven-plugin)
COPY proto /proto
COPY java-service/pom.xml .
COPY java-service/src ./src

RUN mvn -q package -DskipTests

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app

RUN mkdir -p /app/audit

COPY --from=builder /app/target/java-service-1.0.0.jar app.jar

EXPOSE 8080 9090
ENTRYPOINT ["java", "-XX:+UseVirtualThreads", "-jar", "app.jar"]
