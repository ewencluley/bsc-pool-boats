from dataclasses import dataclass
from datetime import date
@dataclass(frozen=True)
class Session:
    name: str
    date: date