"""Object-layer mechanics: closed type world, validation, links,
arrays, cascades. Classes are defined inside tests on purpose —
class definition materializes into the DB, and the schema only
exists after the conftest fixture ran (collection imports happen
before fixtures)."""
import pytest
import sqlalchemy as sqla
from sqlalchemy.orm import Session

from nylium.database import Database
from nylium.database.tables import Instances
from nylium.objects import WInteger, WObject, WString


def instance_count() -> int:
    with Session(Database.engine) as session:
        count = session.scalar(sqla.select(sqla.func.count()).select_from(Instances))
        assert count is not None
        return count


def person_class() -> type[WObject]:
    class Person(WObject):
        name: WString
        age: WInteger
        friend: "Person"
        tags: list[WString]

    return Person


def test_plain_annotation_rejected():
    with pytest.raises(TypeError):
        class Bad(WObject):
            name: str


def test_round_trip():
    Person = person_class()
    oleg = Person(name="Oleg", age=30)
    oleg.friend = Person(name="Max", age=26)
    oleg.tags = ["admin", "owner"]

    back = Person.get(oleg.uuid)
    assert back is not None
    assert back.name == "Oleg" and back.age == 30
    assert back.friend is not None and back.friend.name == "Max"
    assert back.tags == ["admin", "owner"]


def test_scalar_validation():
    person = person_class()(name="Max", age=26)
    with pytest.raises(TypeError):
        person.age = "thirty"
    with pytest.raises(TypeError):
        person.age = True  # bool is not int, exact-type check


def test_link_type_check():
    Person = person_class()

    class Order(WObject):
        title: WString

    person = Person(name="Max", age=26)
    with pytest.raises(TypeError):
        person.friend = Order(title="candles")


def test_array_element_check():
    person = person_class()(name="Max", age=26)
    with pytest.raises(TypeError):
        person.tags = ["ok", 42]


def test_nested_arrays_round_trip_and_rewrite():
    class Matrix(WObject):
        rows: list[list[WInteger]]

    matrix = Matrix(rows=[[1, 2], [3]])
    assert matrix.rows == [[1, 2], [3]]
    matrix.rows = [[9]]
    assert matrix.rows == [[9]]


def test_get_type_check():
    Person = person_class()

    class Order(WObject):
        title: WString

    order = Order(title="candles")
    with pytest.raises(TypeError):
        Person.get(order.uuid)


def test_array_box_cascade_on_rewrite_and_delete():
    Person = person_class()
    oleg = Person(name="Oleg", age=30)
    oleg.friend = Person(name="Max", age=26)
    oleg.tags = ["admin", "owner"]

    before = instance_count()  # oleg, maxim, 2 tag boxes
    oleg.tags = ["solo"]
    assert instance_count() == before - 1
    oleg.delete()
    assert instance_count() == before - 4


def test_modified_at_moves():
    person = person_class()(name="Max", age=26)
    with Session(Database.engine) as session:
        row = session.get(Instances, person.uuid)
        assert row is not None
        first = row.modified_at
    person.name = "Maxim"
    with Session(Database.engine) as session:
        row = session.get(Instances, person.uuid)
        assert row is not None
        assert row.modified_at > first
