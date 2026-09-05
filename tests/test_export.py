"""Markdown export: an object renders to a flat, human-readable document
with link targets as `[label](object:<uuid>)`. Api-level; the HTTP shape
(download headers) lives in test_http.py."""

from decimal import Decimal
from uuid import uuid4

from nylium.api import Api


def org_type():
    return Api.create_type("Org", {"name": "String", "city": "String"}, "Orgs")


def invoice_type():
    return Api.create_type(
        "Invoice",
        {"name": "String", "total": "Numeric", "customer": "Org"},
        "Invoices",
    )


def test_export_markdown_scalar_and_link():
    _ = org_type()
    _ = invoice_type()
    org = Api.create_object("Org", {"name": "Acme", "city": "Barcelona"})
    invoice = Api.create_object(
        "Invoice", {"name": "i1", "total": Decimal("10.5"), "customer": org.uuid}
    )

    result = Api.export_markdown(invoice.uuid)
    assert result is not None
    filename, content = result

    assert filename == "i1.md"
    assert content.startswith("# Invoice: i1\n")
    assert "- **name**: i1" in content
    assert "- **total**: 10.5" in content
    assert f"- **customer**: [Acme](object:{org.uuid})" in content


def test_export_markdown_array_of_links():
    _ = org_type()
    _ = Api.create_type(
        "Report",
        {"name": "String", "orgs": "Array<Org>"},
        "Reports",
    )
    one = Api.create_object("Org", {"name": "Acme"})
    two = Api.create_object("Org", {"name": "Globex"})
    report = Api.create_object("Report", {"name": "r1", "orgs": [one.uuid, two.uuid]})

    result = Api.export_markdown(report.uuid)
    assert result is not None
    _, content = result

    assert "- **orgs**:" in content
    assert f"  - [Acme](object:{one.uuid})" in content
    assert f"  - [Globex](object:{two.uuid})" in content


def test_export_markdown_missing_object_is_none():
    assert Api.export_markdown(uuid4()) is None
