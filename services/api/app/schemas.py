from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    total_questions: int = Field(ge=1, le=100)
    options: list[str] = Field(default_factory=lambda: ["A", "B", "C", "D"])
    correct_marks: float = Field(default=1.0, gt=0, le=100)
    incorrect_marks: float = Field(default=0.0, ge=-100, le=100)
    blank_marks: float = Field(default=0.0, ge=-100, le=100)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str]) -> list[str]:
        normalized = [item.strip().upper() for item in value]
        if not 2 <= len(normalized) <= 4:
            raise ValueError("OMR templates support between 2 and 4 options")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Option labels must be unique")
        if any(not item or len(item) > 3 for item in normalized):
            raise ValueError("Option labels must contain 1 to 3 characters")
        return normalized


class AnswerKeyInput(BaseModel):
    answers: dict[str, str]


class ReviewInput(BaseModel):
    answers: dict[str, str | None]


class ExamOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    total_questions: int
    options_json: list[str]
    correct_marks: float
    incorrect_marks: float
    blank_marks: float
    answer_key_json: dict[str, str] | None
    created_at: str | None = None
