# Model security

The system accepts JPEG, PNG, and WebP uploads only, reads their server-managed
paths, and uses a data URL only for the outbound vision request. Base64 content
is not retained in workflow state or observability records. Provider failures
are converted to bounded application error codes and do not expose raw vendor
tracebacks.
