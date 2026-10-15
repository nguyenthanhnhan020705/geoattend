from typing import Literal
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    expected_revision: int = Field(ge=0, strict=True)
    expected_work_date: date
    action: Literal['START_REMOTE', 'START_OFFICE', 'CHECK_OUT']
    reason: str | None = None
    latitude: float | None = Field(default=None,ge=-90,le=90,allow_inf_nan=False,strict=True)
    longitude: float | None = Field(default=None,ge=-180,le=180,allow_inf_nan=False,strict=True)
    accuracy_m: float | None = Field(default=None,ge=0,allow_inf_nan=False,strict=True)

    @model_validator(mode='after')
    def validate_reason(self):
        if self.reason is not None:
            self.reason = self.reason.strip()
            if not 1 <= len(self.reason) <= 1000:
                raise ValueError('Invalid reason')
        if self.action == 'START_REMOTE' and self.reason is None:
            raise ValueError('Remote requires reason')
        gps={'latitude','longitude','accuracy_m'}
        if self.action=='START_OFFICE':
            if any(getattr(self,key) is None for key in gps) or self.reason is not None:
                raise ValueError('Office requires GPS and no reason')
        elif gps & self.model_fields_set:
            raise ValueError('GPS is forbidden for this action')
        return self
