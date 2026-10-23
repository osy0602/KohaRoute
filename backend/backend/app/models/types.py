"""Shared column types."""

import enum

from sqlalchemy import Enum


def string_enum(enum_class: type[enum.Enum], name: str) -> Enum:
    """Build a column type that stores an enum's *values* as short text with a CHECK rule.

    Storing text (``"pending"``) instead of a native enum keeps the SQLite file readable, and
    the CHECK constraint makes the database itself refuse any value outside the enum.

    Args:
        enum_class: The Python enum whose values are allowed.
        name: Name of the CHECK constraint in the database.

    Returns:
        A SQLAlchemy column type for use in ``mapped_column``.
    """
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=16,
        values_callable=lambda members: [member.value for member in members],
    )
