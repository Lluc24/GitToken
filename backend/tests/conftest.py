import os
import tempfile
from pathlib import Path

# gittoken.api builds its app from the environment on import; tests never reach these services.
os.environ |= {
    "GITHUB_TOKEN": "github-token",
    "SUPABASE_URL": "https://supabase.test",
    "SUPABASE_SECRET_KEY": "supabase-key",
    "SENTRY_DSN": "",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "",
}


def pytest_sessionstart() -> None:
    """The app mounts frontend/dist relative to the working directory, and CI runs the backend
    tests without building the frontend."""
    working_directory = Path(tempfile.mkdtemp(prefix="gittoken-tests-"))
    (working_directory / "frontend" / "dist").mkdir(parents=True)
    os.chdir(working_directory)
