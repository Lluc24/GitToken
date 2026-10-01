# Domain: commits, agent attribution, LoC → token estimation, tiers. The heart of the product.
- No I/O and no framework imports (fastapi, pydantic, httpx, asyncpg, boto3). Clock and randomness are passed in.
- Value objects are frozen dataclasses whose constructors enforce invariants (GithubLogin, LinesChanged ≥ 0).
- Estimator coefficients come from an EstimatorVersion value, never from module constants.
- Agent signatures (trailers, bot logins, branch prefixes, config files) are data loaded at the boundary, not code.
- Fully unit-tested with plain pytest; no mocks are needed here.
