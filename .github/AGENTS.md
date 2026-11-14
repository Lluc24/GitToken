# CI/CD: GitHub Actions.
- Every PR runs the backend and frontend checks; a push to main that changes supabase/migrations applies them to the database.
- preview.yml calls each PR's Vercel preview and fails unless the page, the API and a profile lookup answer 200.
- smoke.yml calls the production site after every production promotion; it fails when the app cannot start or a profile lookup fails.
- Actions pinned to a major version; Dependabot updates them and the Python dependencies weekly.
