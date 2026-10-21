from typing import Literal
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

OFFICE_ACTIONS = ('START_OFFICE', 'CANCEL_LEAVE_START_OFFICE', 'SWITCH_OFFICE')
REASON_ACTIONS = ('START_REMOTE', 'CANCEL_LEAVE_START_REMOTE', 'SWITCH_REMOTE', 'MORNING_LEAVE', 'FULL_DAY_LEAVE')


class ActionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    expected_revision: int = Field(ge=0, strict=True)
    expected_work_date: date
    action: Literal['START_REMOTE', 'START_OFFICE', 'CHECK_OUT', 'START_LUNCH',
                    'MORNING_LEAVE', 'FULL_DAY_LEAVE',
                    'CANCEL_LEAVE_START_OFFICE', 'CANCEL_LEAVE_START_REMOTE',
                    'SWITCH_OFFICE', 'SWITCH_REMOTE']
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
        if self.action in REASON_ACTIONS and self.reason is None:
            raise ValueError('This action requires reason')
        gps={'latitude','longitude','accuracy_m'}
        if self.action in OFFICE_ACTIONS:
            if any(getattr(self,key) is None for key in gps) or self.reason is not None:
                raise ValueError('Office requires GPS and no reason')
        elif gps & self.model_fields_set:
            raise ValueError('GPS is forbidden for this action')
        return self
