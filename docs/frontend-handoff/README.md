# Frontend handoff

Swagger is `http://localhost:8000/docs`. Log in through `/api/auth/login`, persist both access and refresh tokens, and send the bearer access token. Student calls are restricted to the user’s `learner_id`; administrators can inspect all learners. Display source labels, loading/empty/error states and `manual_review_required` for every recognition/evidence result.

See the companion files for page mapping, auth, upload, SSE, recognition, evidence, trace, report and replay contracts.
