# CI/CD: GitHub Actions.
- Every PR runs the backend and frontend checks; a push to main that changes supabase/migrations applies them to the database.
- Actions pinned to a major version; Dependabot updates them and the Python dependencies weekly.
