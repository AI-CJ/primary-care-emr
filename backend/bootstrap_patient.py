"""Create a patient login linked to an existing synthetic chart."""

import argparse
from getpass import getpass

from sqlalchemy.orm import Session

from backend.account_auth import create_user_account
from backend.database import engine


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create a local synthetic patient account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--patient-id", required=True, type=int)
    options = parser.parse_args(argv)

    password = getpass("New password (12-128 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("Passwords do not match")

    with Session(engine) as session:
        try:
            create_user_account(
                session,
                username=options.username,
                password=password,
                account_type="patient",
                patient_id=options.patient_id,
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            parser.error(str(exc))
    print("Synthetic patient account created.")


if __name__ == "__main__":
    main()
