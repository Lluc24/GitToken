# Infra (owner: Marc): AWS CDK in Python. Same Python tooling rules as backend/.
Stacks in stacks/: network, queues (SQS + DLQ), api_service and worker_service (ECS Fargate, same image), web (S3 + CloudFront), observability.
- Everything as code; no console changes. Put the `cdk diff` output in the PR.
- One stack per concern. Cross-stack values pass as typed constructor props, not string exports.
- Least-privilege IAM per task role. Secrets in Secrets Manager, injected at task start; never in code or images.
- Every queue has a DLQ and an age alarm. Every service has health checks, log retention and autoscaling.
- dev and prod come from the same code and differ only in a typed config object.
