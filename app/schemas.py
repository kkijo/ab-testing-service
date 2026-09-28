from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    
class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime

    model_config = {'from_attributes': True}

class VariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    is_control: bool = Field(default=False)


class VariantResponse(BaseModel):
    id: int
    experiment_id: int
    name: str
    weight: float
    is_control: bool

    model_config = {'from_attributes': True}


class AssignRequest(BaseModel):
    experiment_id: int
    user_id: str = Field(..., min_length=1, max_length=100)


class AssignResponse(BaseModel):
    experiment_id: int
    user_id: str
    variant_id: int
    variant_name: str


class EventCreate(BaseModel):
    experiment_id: int
    user_id: str = Field(..., min_length=1, max_length=100)
    event_type: str = Field(..., min_length=1, max_length=50)


class EventResponse(BaseModel):
    id: int
    experiment_id: int
    variant_id: int
    user_id: str
    event_type: str
    created_at: datetime   

    model_config = {"from_attributes": True}



class VariantStats(BaseModel):
    variant_id: int
    variant_name: str
    users_count: int
    conversions: int
    conversion_rate: float


class StatsResponse(BaseModel):
    experiment_id: int
    variants: list[VariantStats]
    z_statistic: float | None = None
    p_value: float | None = None
    is_significant: bool | None = None
    lift: float | None = None