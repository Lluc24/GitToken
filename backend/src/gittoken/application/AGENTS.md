# Application: use cases (ScoutProfile, CrawlRepo, RecomputeStats, GetProfileStats) orchestrating domain and ports.
- Ports are typing.Protocol classes defined here; persistence/ and integrations/ implement them.
- One use case per module with one public async `execute`. Inputs and outputs are domain types.
- No SQL, HTTP, SQS or framework code. Transactions are expressed through a unit-of-work port.
