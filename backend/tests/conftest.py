import os

# gittoken.api builds its app from the environment on import; tests never reach these services.
os.environ |= {
    "GITHUB_TOKEN": "github-token",
    "SUPABASE_URL": "https://supabase.test",
    "SUPABASE_SECRET_KEY": "supabase-key",
    "SENTRY_DSN": "",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "",
}
