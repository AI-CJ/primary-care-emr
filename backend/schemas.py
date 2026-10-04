from datetime import date
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


SexAtBirth = Literal[
    "female",
    "male",
    "intersex",
    "unknown",
    "prefer_not_to_answer",
]

Pronouns = Literal[
    "he/him",
    "she/her",
    "they/them",
    "other",
    "prefer_not_to_answer",
]


class PatientBase(BaseModel):
    first_name: str = Field(max_length=100)
    preferred_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(max_length=100)
    suffix: str | None = Field(default=None, max_length=20)

    date_of_birth: date
    sex_at_birth: SexAtBirth

    pronouns: Pronouns | None = None
    custom_pronouns: str | None = Field(default=None, max_length=100)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_names_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value

    @field_validator(
        "preferred_name",
        "middle_name",
        "suffix",
        "custom_pronouns",
    )
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("date_of_birth")
    @classmethod
    def date_of_birth_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future")

        return value

    @model_validator(mode="after")
    def validate_custom_pronouns(self):
        if self.pronouns == "other" and not self.custom_pronouns:
            raise ValueError(
                "Custom pronouns are required when pronouns is 'other'"
            )

        if self.pronouns != "other":
            self.custom_pronouns = None

        return self


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)