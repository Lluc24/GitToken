from dataclasses import dataclass
from datetime import datetime


class NegativeLinesChangedError(ValueError):
    pass


@dataclass(frozen=True)
class LinesChanged:
    added: int
    deleted: int

    def __post_init__(self) -> None:
        if self.added < 0 or self.deleted < 0:
            raise NegativeLinesChangedError(
                f"expected added >= 0 and deleted >= 0, got added={self.added} deleted={self.deleted}"
            )


@dataclass(frozen=True)
class Commit:
    sha: str
    committed_at: datetime
    # None: the commit email is not linked to a GitHub account.
    author_login: str | None
    author_email: str
    message: str
    lines: LinesChanged
