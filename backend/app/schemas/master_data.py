from pydantic import BaseModel, EmailStr, Field


class FacultyCreate(BaseModel):
    faculty_code: str = Field(min_length=1, max_length=30)
    name: str
    email: EmailStr
    home_department_id: int
    weekly_limit: int = Field(18, ge=1, le=40)
    daily_limit: int = Field(6, ge=1, le=8)
    max_consecutive: int = Field(3, ge=1, le=8)


class RoomCreate(BaseModel):
    code: str
    name: str
    department_id: int | None = None
    capacity: int = Field(gt=0)
    room_type: str = Field(pattern="^(theory|lab)$")
    features: list[str] = []


class ReservationCreate(BaseModel):
    academic_year_id: int
    day: str
    start_period: int = Field(ge=0, le=7)
    duration_periods: int = Field(1, ge=1, le=8)
    room_id: int | None = None
    faculty_id: int | None = None
    participant_group_id: str | None = None
    description: str


class FacultyAvailabilitySlot(BaseModel):
    day: str
    period_index: int = Field(ge=0, le=11)
    available: bool = True
    preference: int = Field(0, ge=-5, le=5)

