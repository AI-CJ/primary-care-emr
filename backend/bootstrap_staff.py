"""Create a synthetic staff login interactively for local development."""

import argparse
from getpass import getpass

from sqlalchemy.orm import Session

from backend.account_auth import create_user_account
from backend.database import engine


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create a local synthetic staff account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=("clinician", "admin"), default="clinician")
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
                account_type="staff",
                staff_role=options.role,
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            parser.error(str(exc))
    print("Synthetic staff account created.")


if __name__ == "__main__":
    main()
