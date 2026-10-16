from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

Status = Literal['NOT_STARTED','WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK','MORNING_LEAVE','FULL_DAY_LEAVE','CHECKED_OUT']
STATUSES = ('NOT_STARTED','WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK','MORNING_LEAVE','FULL_DAY_LEAVE','CHECKED_OUT')


class OpenSession(BaseModel):
    id: UUID
    work_mode: Literal['OFFICE','REMOTE']
    start_time: datetime
    start_reason: str | None


class Employee(BaseModel):
    id: UUID
    username: str
    full_name: str
    is_active: bool
    status: Status
    open_session: OpenSession | None


class Dashboard(BaseModel):
    as_of: datetime
    work_date: date
    total_users: int
    counts: dict[Status,int]
    items: list[Employee]
    onsite: list[Employee]
