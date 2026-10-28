from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import create_db_engine, get_db


def test_foreign_keys_are_switched_on():
    engine = create_db_engine("sqlite://")
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_in_memory_database_is_shared_between_connections():
    engine = create_db_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE demo (id INTEGER)"))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM demo")).scalar() == 0


def test_get_db_yields_a_session_and_cleans_up():
    generator = get_db()
    assert isinstance(next(generator), Session)
    generator.close()
