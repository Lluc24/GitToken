# Entrypoints: api/ (FastAPI), worker/ (SQS consumer), cli/ (calibrate). Each is a composition root.
- Build settings and adapters at startup, inject them into use cases.
- Handlers are thin: parse input → call one use case → map result or domain error to the response.
- Request and response schemas are Pydantic models here. They are the OpenAPI contract the frontend client is generated from.
- Public routes live under /v1; a breaking change needs a new version.
