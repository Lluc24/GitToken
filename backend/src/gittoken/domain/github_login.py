import re
from dataclasses import dataclass

_LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")


class InvalidGithubLoginError(ValueError):
    pass


@dataclass(frozen=True)
class GithubLogin:
    value: str

    def __post_init__(self) -> None:
        if _LOGIN.fullmatch(self.value) is None:
            raise InvalidGithubLoginError(
                f"expected 1 to 39 letters, digits or hyphens, not starting with a hyphen, got {self.value!r}"
            )
