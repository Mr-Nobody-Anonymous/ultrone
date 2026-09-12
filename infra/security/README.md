# Security Infrastructure

Authentication, authorization, and security for ULTRONE.

## Components

- **Authentication** — OAuth 2.0 / JWT token management
- **Authorization** — Role-Based Access Control (RBAC)
- **API Security** — Rate limiting, input validation, CORS
- **Audit Logging** — Security event audit trail
- **Secrets Management** — Environment-based secret management

## Roles (planned)

| Role | Description |
|------|-------------|
| `admin` | Full system access |
| `operator` | Operational console access |
| `analyst` | Read-only analysis access |
| `researcher` | Research platform access |
| `viewer` | View-only access |

## Integration

- `apps/backend/auth/` — Authentication middleware
- `apps/backend/security/` — Security controls
- `packages/safety/policy/` — Policy enforcement
- `packages/safety/constraints/` — Constraint definitions
