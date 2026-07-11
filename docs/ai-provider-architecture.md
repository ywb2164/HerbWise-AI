# AI provider architecture

V0.3A keeps `RAG_MODE=mock` and routes all external model calls through the
provider contracts in `backend/app/integrations`. `OpenAICompatibleLLMProvider`
uses an async OpenAI-compatible `/chat/completions` client; Qwen-VL is a vision
adapter on top of that client. Providers return internal Pydantic schemas only.

`MODEL_API_KEY` is read through an `env:MODEL_API_KEY` reference. API responses,
model-call records, and logs never contain the secret, authorization header,
full prompt, provider raw response, or image base64.
