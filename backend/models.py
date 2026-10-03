from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date

class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    middle_name: Mapped[str | None] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column()
    suffix: Mapped[str | None] = mapped_column(nullable=True)
    date_of_birth: Mapped[date] = mapped_column()
    pronouns: Mapped[str | None] = mapped_column(nullable=True)
    sex_at_birth: Mapped[str | None] = mapped_column(nullable=True)