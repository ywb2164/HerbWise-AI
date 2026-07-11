# V0.2 enums

Resource types: `lecture`, `guide`, `quiz`, `comparison_card`, `review_report`, `learning_report`.

Resource statuses: `generating`, `generated`, `reviewing`, `approved`, `needs_revision`, `rejected`, `archived`.

Profile dimensions: `basic_knowledge`, `character_identification`, `similar_medicine`, `pharmacopoeia_rules`, `clinical_quality_control`, `practical_review`.
# V0.3A additions

- `VISION_MODE`: `mock`, `qwen`, `local`, `hybrid`
- `LLM_MODE`: `mock`, `real`
- Fusion agreement: `agree`, `conflict`, `local_only`, `qwen_only`, `no_result`, `mock`
- Provider error codes: `configuration_error`, `authentication_error`, `rate_limit_error`, `timeout_error`, `network_error`, `invalid_response`, `schema_validation_error`, `provider_unavailable`, `local_model_unavailable`, `unsupported_file`, `unknown_error`
