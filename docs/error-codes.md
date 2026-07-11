# Error codes

`1401` unauthenticated; `1403` forbidden; `1404` not found; `1409` business conflict; `1500` internal error; `1503` external dependency unavailable.
# V0.3A provider errors

Model configuration and provider failures are returned through the existing
application error envelope. Provider details are reduced to safe error codes;
raw upstream tracebacks, credentials, request headers, image base64, and full
prompts are never included.
# V0.4 operational errors

Configuration diagnostics are intentionally redacted. `configuration_error`, `provider_unavailable`, `authentication_error`, `timeout_error`, and `local_model_unavailable` never expose credentials or raw upstream responses.
