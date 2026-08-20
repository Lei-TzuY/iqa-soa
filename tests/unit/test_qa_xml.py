from __future__ import annotations

from pathlib import Path

import pytest

from iqa_soa.iqa.policy import PermissionRule
from iqa_soa.iqa.qa_xml import (
    DEFAULT_SCHEMA_PATH,
    QAXMLValidationError,
    load_policy,
    parse_qa_xml,
)


FULL_POLICY = r"""<?xml version="1.0" encoding="UTF-8"?>
<qa-policy id="case-policy" version="0.1">
  <permissions>
    <allow id="public-read" tool="file.read" resource="workspace/*"/>
    <deny id="private-read" tool="file.read" resource="workspace/private/*"/>
    <deny tool="message.send" resource="external"/>
  </permissions>
  <privacy>
    <protect resource="workspace/patient.txt"/>
    <protect value="PATIENT_SECRET_001"/>
  </privacy>
  <budget>
    <max-tool-calls>5</max-tool-calls>
    <max-model-calls>2</max-model-calls>
    <max-tokens>1000</max-tokens>
    <max-cost>0.10</max-cost>
    <max-runtime unit="seconds">1.5</max-runtime>
  </budget>
  <risk>
    <require-confirmation severity="high"/>
  </risk>
  <injection>
    <pattern>(?i)ignore\s+previous</pattern>
  </injection>
  <output-validation require-evidence="true"
                     required-format="object"
                     require-tool-support="true">
    <require-field name="status"/>
    <require-field name="evidence_id"/>
    <forbid-value>PATIENT_SECRET_001</forbid-value>
  </output-validation>
</qa-policy>
"""


def test_parse_complete_minimal_qa_xml_into_typed_policy() -> None:
    policy = parse_qa_xml(FULL_POLICY)

    assert policy.policy_id == "case-policy"
    assert policy.version == "0.1"
    assert policy.permissions[0] == PermissionRule(
        "allow", "file.read", "workspace/*", "public-read"
    )
    assert policy.permission_for("file.read", "workspace/private/a.txt") == "deny"
    assert policy.privacy.protected_resources == ("workspace/patient.txt",)
    assert policy.privacy.protected_values == ("PATIENT_SECRET_001",)
    assert policy.budget.max_tool_calls == 5
    assert policy.budget.max_model_calls == 2
    assert policy.budget.max_tokens == 1000
    assert policy.budget.max_cost == 0.1
    assert policy.budget.max_runtime_ms == 1500.0
    assert policy.risk.require_confirmation == ("high",)
    assert policy.injection.patterns == (r"(?i)ignore\s+previous",)
    assert policy.output_validation.required_fields == ("status", "evidence_id")
    assert policy.output_validation.forbidden_values == ("PATIENT_SECRET_001",)
    assert policy.output_validation.require_evidence is True
    assert policy.output_validation.required_format == "object"
    assert policy.output_validation.require_tool_support is True
    assert policy.extensions["source_format"] == "QA-XML"


def test_load_policy_accepts_path_and_runtime_milliseconds(tmp_path: Path) -> None:
    source = tmp_path / "milliseconds.xml"
    source.write_text(
        """<qa-policy id="ms"><budget>
        <max-runtime unit="milliseconds">250</max-runtime>
        </budget></qa-policy>""",
        encoding="utf-8",
    )

    policy = load_policy(source)

    assert policy.budget.max_runtime_ms == 250.0
    assert policy.budget.max_runtime == 0.25


def test_repository_default_policy_is_schema_valid() -> None:
    assert DEFAULT_SCHEMA_PATH.is_file()
    policy_path = DEFAULT_SCHEMA_PATH.parents[1] / "configs" / "policies" / "default.xml"

    policy = load_policy(policy_path)

    assert policy.policy_id == "fse-full-base"
    assert policy.permission_for("file.read", "workspace/report.txt") == "allow"
    assert policy.risk.require_confirmation == ("critical",)
    assert policy.output_validation.require_evidence is False


def test_schema_valid_comments_inside_sections_do_not_become_policy_nodes() -> None:
    policy = parse_qa_xml(
        """<qa-policy id="comments"><permissions><!-- rationale -->
        <allow tool="file.read" resource="public/*"/></permissions>
        <risk><!-- deployment note -->
        <require-confirmation severity="high"/></risk>
        <injection><!-- benchmark note --><pattern>ignore</pattern></injection>
        </qa-policy>"""
    )
    assert policy.permission_for("file.read", "public/a") == "allow"
    assert policy.risk.require_confirmation == ("high",)
    assert policy.injection.patterns == ("ignore",)


@pytest.mark.parametrize(
    "xml",
    [
        '<qa-policy id="unknown"><surprise/></qa-policy>',
        '<qa-policy id="attribute" unsafe="true"/>',
        '<qa-policy id="rule"><permissions><allow tool="file.read" nope="x"/></permissions></qa-policy>',
        '<qa-policy id="order"><budget/><permissions/></qa-policy>',
        '<qa-policy id="version" version="1.0"/>',
        '<wrong-root id="wrong"/>',
    ],
)
def test_closed_schema_rejects_unknown_or_misordered_xml(xml: str) -> None:
    with pytest.raises(QAXMLValidationError, match="schema validation failed"):
        parse_qa_xml(xml)


@pytest.mark.parametrize(
    "xml",
    [
        "<qa-policy>",
        '<qa-policy id="missing-close">',
        "not XML at all",
        "",
    ],
)
def test_rejects_malformed_or_empty_xml(xml: str) -> None:
    with pytest.raises(QAXMLValidationError):
        parse_qa_xml(xml)


def test_rejects_dtd_and_entity_declarations_before_validation() -> None:
    xml = """<!DOCTYPE qa-policy [
      <!ENTITY secret SYSTEM "file:///definitely-not-readable-by-qa-xml">
    ]>
    <qa-policy id="xxe"><privacy><protect value="&secret;"/></privacy></qa-policy>
    """

    with pytest.raises(QAXMLValidationError, match="DTD.*forbidden"):
        parse_qa_xml(xml)


def test_rejects_direct_contradictory_duplicate_permission() -> None:
    xml = """<qa-policy id="conflict"><permissions>
      <allow tool="file.read" resource="private/*"/>
      <deny tool="file.read" resource="private/*"/>
    </permissions></qa-policy>"""

    with pytest.raises(QAXMLValidationError, match="contradictory exact"):
        parse_qa_xml(xml)


def test_allows_nonidentical_overlap_because_runtime_deny_wins() -> None:
    xml = """<qa-policy id="deny-wins"><permissions>
      <allow tool="file.read" resource="*"/>
      <deny tool="file.read" resource="private/*"/>
    </permissions></qa-policy>"""

    policy = parse_qa_xml(xml)

    assert policy.permission_for("file.read", "private/secret.txt") == "deny"


@pytest.mark.parametrize(
    "protect",
    [
        "<protect/>",
        '<protect resource="private/*" value="SECRET"/>',
    ],
)
def test_privacy_protect_requires_exactly_one_typed_target(protect: str) -> None:
    xml = f'<qa-policy id="privacy"><privacy>{protect}</privacy></qa-policy>'

    with pytest.raises(QAXMLValidationError, match="exactly one"):
        parse_qa_xml(xml)


def test_rejects_semantically_invalid_injection_regex() -> None:
    xml = """<qa-policy id="regex"><injection>
      <pattern>[</pattern>
    </injection></qa-policy>"""

    with pytest.raises(QAXMLValidationError, match="invalid injection pattern"):
        parse_qa_xml(xml)


@pytest.mark.parametrize(
    "budget_element",
    [
        "<max-tool-calls>-1</max-tool-calls>",
        "<max-cost>-0.1</max-cost>",
        '<max-runtime unit="minutes">1</max-runtime>',
        "<max-tool-calls>1.5</max-tool-calls>",
    ],
)
def test_schema_rejects_invalid_budget_values(budget_element: str) -> None:
    xml = (
        f'<qa-policy id="budget"><budget>{budget_element}</budget></qa-policy>'
    )

    with pytest.raises(QAXMLValidationError, match="schema validation failed"):
        parse_qa_xml(xml)
