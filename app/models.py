"""Validación compartida por las operaciones de la API."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CourtInput(InputModel):
    name: str = Field(min_length=3, max_length=70)
    venue: str = Field(min_length=3, max_length=70)
    sport: Literal["Fútbol", "Vóley", "Básquet"]
    capacity: int = Field(ge=2, le=100)
    hourly_rate: int = Field(ge=100, le=100000)


class UserInput(InputModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=120)


class ScheduleInput(InputModel):
    weekday: int = Field(ge=0, le=6)
    opens: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    closes: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class RentalInput(InputModel):
    court_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    date: date
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration: int = Field(ge=30, le=240, multiple_of=30)
    event: str = Field(min_length=3, max_length=120)


class ConfirmationInput(InputModel):
    payment: Literal["Pendiente", "Pagado"] = "Pendiente"
