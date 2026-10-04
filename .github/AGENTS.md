# CI/CD (owner: Marc): GitHub Actions.
- Every PR runs backend, frontend and infra checks; main deploys to dev, a tag deploys to prod.
- AWS access only through OIDC roles; no long-lived keys in secrets.
- Actions pinned to a major version; Dependabot updates them and every dependency weekly.
