from pydantic import BaseModel, EmailStr, Field, field_validator


def clean_capabilities(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = " ".join(value.strip().split())
        key = label.casefold()
        if label and key not in seen:
            cleaned.append(label)
            seen.add(key)
    return cleaned


class FacultyCreate(BaseModel):
    faculty_code: str = Field(min_length=1, max_length=30)
    name: str
    email: EmailStr
    home_department_id: int
    weekly_limit: int = Field(18, ge=1, le=40)
    daily_limit: int = Field(6, ge=1, le=8)
    max_consecutive: int = Field(3, ge=1, le=8)
    active: bool = True

    @field_validator("email")
    @classmethod
    def require_institute_email(cls, value: EmailStr) -> EmailStr:
        if not str(value).lower().endswith("@sgsits.ac.in"):
            raise ValueError("Faculty email must use the @sgsits.ac.in domain")
        return value


class RoomCreate(BaseModel):
    code: str
    name: str
    department_id: int | None = None
    capacity: int = Field(gt=0)
    room_type: str = Field(pattern="^(theory|lab)$")
    features: list[str] = []
    concurrent_capacity: int = Field(1, ge=1, le=10)

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        return clean_capabilities(values)


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
    note: str = Field("", max_length=300)


class RoomAvailabilitySlot(BaseModel):
    day: str
    period_index: int = Field(ge=0, le=11)
    available: bool = True
    note: str = Field("", max_length=300)

