# Vision fusion rules

Local and Qwen results are normalized against `medicine_items` and
`medicine_aliases` before comparison. Agreement selects the higher-confidence
candidate and adds `FUSION_AGREEMENT_BONUS` (capped by
`FUSION_CONFIDENCE_CAP`). Conflict retains the local candidate, subtracts
`FUSION_CONFLICT_PENALTY`, and requires manual review. A single valid provider
is retained as a marked fallback; no provider result produces no candidate.
