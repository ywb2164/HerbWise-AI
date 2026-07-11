# Real AI configuration

Defaults remain `VISION_MODE=mock`, `LLM_MODE=mock`, and `RAG_MODE=mock`.
Set `MODEL_API_BASE_URL`, `MODEL_API_KEY`, `QWEN_VL_MODEL`,
`GENERATION_MODEL`, and `REVIEW_MODEL` only in environment configuration.
Model configuration rows store only `credential_reference` such as
`env:MODEL_API_KEY`, never the key itself. Model weights and uploaded images do
not belong in Git.
