# CI/CD (owner: Mark): GitHub Actions.
- Every PR runs backend, frontend and infra checks; main deploys to dev, a tag deploys to prod.
- AWS access only through OIDC roles; no long-lived keys in secrets.
- Pin third-party actions by commit SHA.
