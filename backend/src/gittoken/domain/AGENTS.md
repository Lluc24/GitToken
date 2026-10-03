# Domain: commits, agent attribution, LoC → token estimation, tiers. The heart of the product.
- No I/O and no framework imports (fastapi, pydantic, httpx, asyncpg, boto3). Clock and randomness are passed in.
- Value objects are frozen dataclasses whose constructors enforce invariants (GithubLogin, LinesChanged ≥ 0).
- Estimator v0 is one hardcoded constant in estimator.py; a versioned pattern comes later.
- Agent signatures (trailers, bot logins, branch prefixes, config files) are data loaded at the boundary, not code.
