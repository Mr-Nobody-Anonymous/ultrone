# PostgreSQL Infrastructure

Database infrastructure for ULTRONE.

## Components

- **Schema migrations** — Alembic-based schema management
- **Connection pooling** — asyncpg / SQLAlchemy async
- **ORM models** — SQLAlchemy 2.0 mapped classes

## Tables (planned)

| Table | Purpose |
|-------|--------|
| `entities` | Canonical entity store |
| `events` | Event audit log |
| `observations` | Observation history |
| `decisions` | Decision audit trail with provenance |
| `users` | User accounts |
| `roles` | RBAC roles |
| `sessions` | Active sessions |
| `simulations` | Simulation configurations and results |
| `experiments` | Research experiment metadata |

## Quick Start

```bash
# Start PostgreSQL
docker compose up -d postgres

# Run migrations
alembic upgrade head
```
