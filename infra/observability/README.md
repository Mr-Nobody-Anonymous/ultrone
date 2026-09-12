# Observability Infrastructure

Monitoring, tracing, and logging stack for ULTRONE.

## Components

| Component | Purpose | Port |
|-----------|---------|------|
| Prometheus | Metrics collection | 9090 |
| Grafana | Dashboards | 3000 |
| Jaeger | Distributed tracing | 16686 |
| OpenTelemetry Collector | Telemetry pipeline | 4317 |

## Integration Points

- `packages/observability/tracing/` — OpenTelemetry SDK integration
- `packages/observability/metrics/` — Prometheus client
- `packages/observability/logging/` — Structured JSON logging
- `packages/observability/events/` — Event bus monitoring

## Quick Start

```bash
docker compose -f infra/observability/docker-compose.observability.yml up -d
```
