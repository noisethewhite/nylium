"""Transaction atomicity: only the outermost databasemethod commits.

A nested databasemethod(commit=True) shares the owner's session and must
NOT commit — if the outer operation raises mid-way, the nested write
rolls back with it instead of leaking a half-written object.
"""
from uuid import uuid4

import sqlalchemy as sqla

from nylium.database import Database, databasemethod
from nylium.tables import TABLE_Instances
from nylium.tables.objects.types import TABLE_Types


class _Boom(Exception):
    pass


def test_nested_write_rolls_back_on_outer_error():
    tuuid = uuid4()

    @databasemethod(commit=True)
    def make_type():
        Database.session.add(
            TABLE_Types(uuid=tuuid, name="ProbeType", plural_name="P", icon="x", color="#000000")
        )

    make_type()

    @databasemethod(commit=True)
    def outer():
        @databasemethod(commit=True)
        def register():
            Database.session.add(TABLE_Instances(uuid=uuid4(), type_uuid=tuuid, name="n", plural_name="ns"))

        register()
        raise _Boom()

    try:
        outer()
    except _Boom:
        pass

    @databasemethod(commit=False)
    def count_instances():
        return Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(TABLE_Instances)
        ) or 0

    assert count_instances() == 0, "nested write leaked past the outer rollback"


def test_outer_commit_persists_nested_write():
    tuuid = uuid4()

    @databasemethod(commit=True)
    def make_type():
        Database.session.add(
            TABLE_Types(uuid=tuuid, name="ProbeType2", plural_name="P2", icon="x", color="#000000")
        )

    make_type()

    @databasemethod(commit=True)
    def outer():
        @databasemethod(commit=True)
        def register():
            Database.session.add(TABLE_Instances(uuid=uuid4(), type_uuid=tuuid, name="n", plural_name="ns"))

        register()

    outer()

    @databasemethod(commit=False)
    def count_instances():
        return Database.session.scalar(
            sqla.select(sqla.func.count()).select_from(TABLE_Instances)
        ) or 0

    assert count_instances() == 1, "outer commit did not persist the nested write"
