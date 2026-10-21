from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class Account:
    id: UUID
    username: str
    full_name: str
    role: Literal['USER','ADMIN']
    is_active: bool

    @classmethod
    def from_row(cls, row):
        return cls(**{key: row[key] for key in cls.__dataclass_fields__})


@dataclass(frozen=True)
class AuthContext:
    account: Account
    session_id: UUID
    csrf_token: str
