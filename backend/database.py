import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from backend.settings import build_database_url

load_dotenv()

database_url = build_database_url(os.environ)

engine = create_engine(database_url, pool_pre_ping=True)


def check_database_connection():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))