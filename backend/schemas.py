from datetime import date
from typing import Literal

from pydantic import BaseModel


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


class PatientCreate(BaseModel):
    first_name: str
    preferred_name: str | None = None
    middle_name: str | None = None
    last_name: str
    suffix: str | None = None
    date_of_birth: date

    sex_at_birth: SexAtBirth

    pronouns: Pronouns | None = None
    custom_pronouns: str | None = None