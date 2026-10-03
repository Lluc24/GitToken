from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Repository:
    owner: str
    name: str
    pushed_at: datetime
