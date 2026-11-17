"""SQLite connection handling and database bootstrap."""

import os
import sqlite3

from flask import current_app, g


def get_db():
    """Return the request-scoped SQLite connection."""
    if "db" not in g:
        os.makedirs(os.path.dirname(current_app.config["DATABASE"]), exist_ok=True)
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(exception=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    """Create tables when missing and load the sample catalogue once."""
    connection = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        connection.executescript(schema_file.read().decode("utf-8"))
    connection.commit()

    from .seed import seed_if_empty

    seed_if_empty(connection)


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
