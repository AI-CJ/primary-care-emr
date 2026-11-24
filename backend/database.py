import os
import sys

from sqlalchemy import create_engine, text

from backend.settings import build_database_url

if sys.platform == "emscripten":
    # Only the browser's WebAssembly runtime can select this disposable database.
    from backend.browser_demo import create_browser_engine

    engine = create_browser_engine()
    database_url = engine.url
else:
    from dotenv import load_dotenv

    load_dotenv()
    database_url = build_database_url(os.environ)
    engine = create_engine(database_url, pool_pre_ping=True)


def check_database_connection():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
