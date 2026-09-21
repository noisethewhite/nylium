"""Transaction atomicity: only the outermost session commits.

A nested commit_after_this shares the owner's session and must
NOT commit — if the outer operation raises mid-way, the nested write
rolls back with it instead of leaking a half-written object.
"""
from uuid import uuid4

import sqlalchemy as sqla

from nylium.database import Database
from nylium.table_rows.objects import Instance, Type


class _Boom(Exception):
    pass


def test_nested_write_rolls_back_on_outer_error():
    tuuid = uuid4()

    @Database.commit_after_this
    def make_type():
        Database.session.add(
            Type(uuid=tuuid, name="ProbeType")
        )

    make_type()

    @Database.commit_after_this
    def outer():
        @Database.commit_after_this
        def register():
            Database.session.add(Instance(uuid=uuid4(), type_uuid=tuuid, name="n", plural_name="ns"))

        register()
        raise _Boom()

    try:
        outer()
    except _Boom:
        pass

    @Database.use_same_session
    def count_instances():
        return Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(Instance)
        ) or 0

    assert count_instances() == 0, "nested write leaked past the outer rollback"


def test_outer_commit_persists_nested_write():
    tuuid = uuid4()

    @Database.commit_after_this
    def make_type():
        Database.session.add(
            Type(uuid=tuuid, name="ProbeType2")
        )

    make_type()

    @Database.commit_after_this
    def outer():
        @Database.commit_after_this
        def register():
            Database.session.add(Instance(uuid=uuid4(), type_uuid=tuuid, name="n", plural_name="ns"))

        register()

    outer()

    @Database.use_same_session
    def count_instances():
        return Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(Instance)
        ) or 0

    assert count_instances() == 1, "outer commit did not persist the nested write"
