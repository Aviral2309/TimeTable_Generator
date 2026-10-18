from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: str | None = Field(None, pattern="^(admin|faculty|student)$")


class BootstrapAdminRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    faculty_id: int | None = None
    student_group_id: str | None = None
    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(admin|faculty|student)$")
    faculty_id: int | None = None
    student_group_id: str | None = Field(None, max_length=80)
    active: bool = True

    @field_validator("email")
    @classmethod
    def require_institute_email(cls, value: EmailStr) -> EmailStr:
        if not str(value).lower().endswith("@sgsits.ac.in"):
            raise ValueError("Login email must use the @sgsits.ac.in domain")
        return value

    @model_validator(mode="after")
    def validate_role_link(self):
        if self.role == "faculty" and not self.faculty_id:
            raise ValueError("Faculty login must be linked to a faculty record")
        if self.role == "student" and not self.student_group_id:
            raise ValueError("Student login must be linked to a semester or batch group")
        return self


class UserUpdate(UserCreate):
    password: str | None = Field(None, min_length=8, max_length=128)

