# V0.4.1 Architecture

HerbWise-AI is a FastAPI modular monolith: `core`/`common` provide configuration and shared contracts; `modules` own business data and APIs; `integrations` isolate LLM, vision and RAGFlow providers; `workflows` execute the traceable LangGraph flow. MySQL persists identities, learning data, tasks, traces, retrievals, evidence, replay and reports; Redis is runtime infrastructure. Production URLs use `mysql+asyncmy://...` and `redis://...`; filesystem records remain relative to controlled `/data` paths.

The runtime supports mock, replay, real and hybrid modes. Real providers are never called unless their explicit configuration flags and credentials are supplied. RAGFlow is accessed through one adapter using `RAGFLOW_BASE_URL`; Mock/Fake and replay remain usable without it. The service produces learning resources and a lightweight standard-library `zipfile`/XML DOCX demonstration export.

The project frontend target is Soybean Admin (Vue 3 is an underlying technology only). The repository does not currently include official Soybean Admin frontend source: Soybean Admin frontend is pending integration while backend APIs and handoff materials are frozen.
