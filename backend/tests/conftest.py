import os

# gittoken.api builds its app from the environment on import.
os.environ |= {
    "GITHUB_TOKEN": "github-token",
    "SUPABASE_URL": "https://supabase.test",
    "SUPABASE_SECRET_KEY": "supabase-key",
}
