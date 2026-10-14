from typing import Literal
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    expected_revision: int = Field(ge=0, strict=True)
    expected_work_date: date
    action: Literal['START_REMOTE', 'CHECK_OUT']
    reason: str | None = None

    @model_validator(mode='after')
    def validate_reason(self):
        if self.reason is not None:
            self.reason = self.reason.strip()
            if not 1 <= len(self.reason) <= 1000:
                raise ValueError('Invalid reason')
        if self.action == 'START_REMOTE' and self.reason is None:
            raise ValueError('Remote requires reason')
        return self
