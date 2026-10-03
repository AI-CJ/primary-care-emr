import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = (
    f"postgresql+psycopg://"
    f"{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@"
    f"localhost:5432/"
    f"{os.environ['POSTGRES_DB']}"
)

engine = create_engine(database_url)


def check_database_connection():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))