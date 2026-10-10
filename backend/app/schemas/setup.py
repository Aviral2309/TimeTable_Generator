from pydantic import BaseModel, Field, model_validator


class InstituteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=2, max_length=150)


class AcademicYearCreate(BaseModel):
    name: str = Field(min_length=4, max_length=30)
    term_type: str = Field("odd", pattern="^(odd|even)$")


class DemoDataCreate(BaseModel):
    term_type: str = Field("odd", pattern="^(odd|even)$")


class WorkingWeekCreate(BaseModel):
    days: list[str] = Field(min_length=1, max_length=7)
    start_hour: int = Field(9, ge=0, le=22)
    periods_per_day: int = Field(8, ge=2, le=12)
    lunch_after_period: int = Field(3, ge=0, le=11)


class SemesterCreate(BaseModel):
    academic_year_id: int
    department_id: int
    semester_number: int = Field(ge=1, le=8)
    strength: int = Field(gt=0, le=300)
    home_room_id: int
    home_room_policy: str = Field("hard", pattern="^(hard|soft|disabled)$")


class CourseOfferingCreate(BaseModel):
    semester_offering_id: int
    code: str
    name: str
    kind: str = Field(pattern="^(theory|lab|elective)$")
    sessions_per_week: int = Field(ge=1, le=10)
    duration_periods: int = Field(ge=1, le=4)
    enrollment: int = Field(gt=0, le=500)
    faculty_ids: list[int] = Field(min_length=1)
    eligible_room_ids: list[int] = Field(min_length=1)
    required_features: list[str] = []
    participant_group: str | None = None
    elective_group: str | None = None
    parallel_elective: bool = False
    fixed_day: str | None = None
    fixed_period: int | None = Field(None, ge=0, le=7)
    fixed_room_id: int | None = None

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind == "lab" and self.duration_periods != 2:
            raise ValueError("Laboratories must occupy exactly two consecutive periods")
        if self.parallel_elective and not self.elective_group:
            raise ValueError("Parallel electives require an elective group")
        return self

