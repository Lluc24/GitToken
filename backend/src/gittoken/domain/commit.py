from dataclasses import dataclass


@dataclass(frozen=True)
class Commit:
    # None: the commit email is not linked to a GitHub account.
    author_login: str | None
    author_email: str
    message: str
    lines_added: int
