# Authentication and RBAC

V0.2 uses Argon2 password hashes and JWT bearer access tokens. Refresh tokens are persisted as hashes, rotated on refresh, and revoked on logout. Roles seeded for the demo are `admin`, `student`, `teacher`, `clinical_pharmacist`, and `quality_inspector`; only the first two are intended for normal V0.2 use.

Test accounts: `admin` / `HerbWise@2026` and `student` / `HerbWise@2026`.
