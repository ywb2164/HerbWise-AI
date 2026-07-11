# RAGFlow deployment

Deploy RAGFlow independently from HerbWise-AI. Pin a specific upstream image version; do not use `latest`, commit RAGFlow source, data volumes, API keys, or copyrighted pharmacopoeia text. The HTTP paths used by HerbWise-AI are isolated in `backend/app/integrations/rag/ragflow.py` and require real-environment confirmation before production use.
