from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.master_data import clean_capabilities


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
    home_room_id: int | None = None
    home_room_policy: str = Field("hard", pattern="^(hard|soft|disabled)$")


class TermCohortsCreate(BaseModel):
    academic_year_id: int
    department_id: int
    default_strength: int = Field(60, gt=0, le=300)


class CourseOfferingCreate(BaseModel):
    semester_offering_id: int
    code: str
    name: str
    kind: str = Field(pattern="^(theory|lab|elective)$")
    sessions_per_week: int = Field(ge=1, le=10)
    theory_sessions_per_week: int = Field(0, ge=0, le=10)
    lecture_sessions_per_week: int = Field(0, ge=0, le=10)
    duration_periods: int = Field(ge=1, le=4)
    enrollment: int = Field(gt=0, le=500)
    faculty_ids: list[int] = Field(min_length=1)
    theory_faculty_ids: list[int] = []
    lecture_faculty_ids: list[int] = []
    eligible_room_ids: list[int] = []
    required_features: list[str] = []
    participant_group: str | None = None
    elective_group: str | None = None
    parallel_elective: bool = False
    fixed_day: str | None = None
    fixed_period: int | None = Field(None, ge=0, le=7)
    fixed_room_id: int | None = None

    @field_validator("required_features")
    @classmethod
    def normalize_required_features(cls, values: list[str]) -> list[str]:
        return clean_capabilities(values)

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind == "lab" and self.duration_periods != 2:
            raise ValueError("Laboratories must occupy exactly two consecutive periods")
        if self.kind != "lab":
            if self.theory_sessions_per_week == 0 and self.lecture_sessions_per_week == 0:
                self.theory_sessions_per_week = self.sessions_per_week
                self.theory_faculty_ids = list(self.faculty_ids)
            if self.theory_sessions_per_week and not self.theory_faculty_ids:
                raise ValueError("Select faculty for the theory classes")
            if self.lecture_sessions_per_week and not self.lecture_faculty_ids:
                raise ValueError("Select faculty for the lecture/tutorial classes")
            self.sessions_per_week = self.theory_sessions_per_week + self.lecture_sessions_per_week
            self.faculty_ids = list(dict.fromkeys(self.theory_faculty_ids + self.lecture_faculty_ids))
            if self.sessions_per_week < 1 or self.sessions_per_week > 10:
                raise ValueError("The total theory and lecture/tutorial classes must be between 1 and 10")
        if self.parallel_elective and not self.elective_group:
            raise ValueError("Parallel electives require an elective group")
        return self


class LabBatchAllocationCreate(BaseModel):
    participant_group: str = Field(min_length=1, max_length=80)
    faculty_ids: list[int] = Field(min_length=1)
    room_id: int | None = None


class LabOfferingBatchCreate(BaseModel):
    semester_offering_id: int
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    sessions_per_week: int = Field(ge=1, le=10)
    total_enrollment: int = Field(gt=0, le=500)
    required_features: list[str] = []
    elective_lab: bool = False
    batches: list[LabBatchAllocationCreate] = Field(min_length=1, max_length=10)

    @field_validator("required_features")
    @classmethod
    def normalize_required_features(cls, values: list[str]) -> list[str]:
        return clean_capabilities(values)

    @model_validator(mode="after")
    def validate_batches(self):
        expected = 2 if self.elective_lab else 4
        if len(self.batches) != expected:
            label = "elective lab" if self.elective_lab else "regular lab"
            raise ValueError(f"A {label} must define exactly {expected} batches")
        names = [" ".join(batch.participant_group.strip().split()).casefold() for batch in self.batches]
        if len(set(names)) != len(names):
            raise ValueError("Every lab batch must have a unique name")
        return self

