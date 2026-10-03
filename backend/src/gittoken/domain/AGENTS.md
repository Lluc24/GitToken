# Domain: commits, agent attribution, LoC → token estimation, tiers. The heart of the product.
- No I/O and no framework imports (fastapi, pydantic, httpx, asyncpg, boto3). Clock and randomness are passed in.
- Value objects are frozen dataclasses whose constructors enforce invariants (GithubLogin).
- Estimator v0 is one hardcoded constant in estimator.py; a versioned pattern comes later.
- Agent signatures are one hardcoded email table in attribution.py; loading them as data comes later.
