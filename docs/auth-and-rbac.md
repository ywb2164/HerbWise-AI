# Authentication and RBAC

V0.2 uses Argon2 password hashes and JWT bearer access tokens. Refresh tokens are persisted as hashes, rotated on refresh, and revoked on logout. Roles seeded for the demo are `admin`, `student`, `teacher`, `clinical_pharmacist`, and `quality_inspector`; only the first two are intended for normal V0.2 use.

Test accounts: `admin` / `HerbWise@2026` and `student` / `HerbWise@2026`.

Student requests are also scoped to the `learner_id` bound to the account: profile,
assessment, learning-path, resource, and agent-task data for another learner return
HTTP 403. Structured medicine knowledge remains readable to authenticated users, but
its create, update, and delete operations require `admin`, `teacher`,
`clinical_pharmacist`, or `quality_inspector`.
