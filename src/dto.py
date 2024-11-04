import datetime
import enum
from dataclasses import dataclass

from pydantic import BaseModel, Field


class CallsStatRequest(BaseModel):
    correlation_id: int
    phones: list[int]


@dataclass(frozen=True)
class DurationStat:
    sec_10: int
    sec_10_30: int
    sec_30: int


@dataclass(frozen=True)
class PhoneStats:
    phone: int
    cnt_all_attempts: int
    cnt_att_dur: DurationStat
    min_price_att: float
    max_price_att: float
    avg_dur_att: float
    sum_price_att_over_15: float


class ResponseStatus(enum.StrEnum):
    complete = "Complete"


class CallsStatsResponse(BaseModel):
    correlation_id: int
    status: ResponseStatus
    task_received: datetime.datetime
    from_: str = Field(serialization_alias="from")
    to: str
    data: list[PhoneStats]
    total_duration: float
