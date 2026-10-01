# Integrations (owner: Marc): adapters to GitHub (GraphQL, REST, search) and SQS.
- Every external response is parsed with Pydantic, converted to domain types, then the model is dropped.
- All GitHub calls go through the token broker. Read X-RateLimit-* and GraphQL rateLimit on every call.
- Out of quota: requeue the message with a delay until reset. Never sleep, never busy-wait.
- API only, never `git clone`. Every client sets explicit timeouts.
