"""Strict, side-effect-free parser for the minimal QA-XML v0.1 language."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Final, cast

from lxml import etree  # type: ignore[import-untyped]

from iqa_soa.iqa.policy import (
    Budget,
    InjectionPolicy,
    OutputValidationPolicy,
    PermissionRule,
    Policy,
    PrivacyPolicy,
    RiskPolicy,
)


def _default_schema_path() -> Path:
    module = Path(__file__).resolve()
    candidates: list[Path] = []
    # Recognize the repository's explicit src-layout instead of assuming that
    # every package three parents deep is a source checkout.
    if module.parents[2].name == "src":
        candidates.append(module.parents[3] / "schemas" / "qa-policy.xsd")
    candidates.extend(
        (
            # Wheel data-files installation (including ``pip --target``).
            module.parents[2] / "schemas" / "qa-policy.xsd",
            Path(sys.prefix) / "schemas" / "qa-policy.xsd",
        )
    )
    return next((candidate for candidate in candidates if candidate.is_file()), candidates[0])


DEFAULT_SCHEMA_PATH: Final[Path] = _default_schema_path()


class QAXMLValidationError(ValueError):
    """Raised when QA-XML is malformed, unsafe, or violates v0.1 semantics."""


def _validation_message(prefix: str, error: BaseException) -> str:
    # lxml error-log objects may retain entries from a cached schema's previous
    # validations. ``str(error)`` is scoped to the current failure.
    return f"{prefix}: {error}"


@lru_cache(maxsize=4)
def _compiled_schema(schema_path: str) -> etree.XMLSchema:
    path = Path(schema_path)
    if not path.is_file():
        raise QAXMLValidationError(f"QA-XML schema does not exist: {path}")
    try:
        document = etree.parse(str(path))
        return etree.XMLSchema(document)
    except (OSError, etree.XMLSyntaxError, etree.XMLSchemaParseError) as exc:
        raise QAXMLValidationError(
            _validation_message("cannot load QA-XML schema", exc)
        ) from exc


def _read_source(source: str | bytes | Path) -> bytes:
    if isinstance(source, Path):
        try:
            return source.read_bytes()
        except OSError as exc:
            raise QAXMLValidationError(
                f"cannot read QA-XML source {source}: {exc}"
            ) from exc
    if isinstance(source, bytes):
        return source
    if not isinstance(source, str):
        raise TypeError("source must be XML text, bytes, or a pathlib.Path")

    if source.lstrip().startswith("<"):
        return source.encode("utf-8")
    try:
        candidate = Path(source)
        if candidate.is_file():
            return candidate.read_bytes()
    except (OSError, ValueError):
        pass
    return source.encode("utf-8")


def _strict_xml_parser() -> etree.XMLParser:
    return etree.XMLParser(
        recover=False,
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
        remove_blank_text=True,
        remove_comments=False,
    )


def _required_text(element: etree._Element, description: str) -> str:
    value = element.text
    if value is None or not value.strip():
        raise QAXMLValidationError(f"{description} must not be empty")
    return cast(str, value).strip()


def _xml_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    if value in {"true", "1"}:
        return True
    if value in {"false", "0"}:
        return False
    # The schema should make this branch unreachable; retain defense in depth.
    raise QAXMLValidationError(f"invalid XML boolean: {value!r}")


def _permissions(root: etree._Element) -> tuple[PermissionRule, ...]:
    parent = root.find("permissions")
    if parent is None:
        return ()
    return tuple(
        PermissionRule(
            effect=child.tag,
            tool=child.get("tool", ""),
            resource=child.get("resource", "*"),
            rule_id=child.get("id"),
        )
        for child in parent
        if child.tag in {"allow", "deny"}
    )


def _privacy(root: etree._Element) -> PrivacyPolicy:
    parent = root.find("privacy")
    if parent is None:
        return PrivacyPolicy()
    resources: list[str] = []
    values: list[str] = []
    for protection in parent.findall("protect"):
        resource = protection.get("resource")
        value = protection.get("value")
        if (resource is None) == (value is None):
            raise QAXMLValidationError(
                "each privacy/protect element must define exactly one of "
                "resource or value"
            )
        if resource is not None:
            resources.append(resource)
        else:
            assert value is not None
            values.append(value)
    return PrivacyPolicy(tuple(resources), tuple(values))


def _budget(root: etree._Element) -> Budget:
    parent = root.find("budget")
    if parent is None:
        return Budget()

    counts: dict[str, int | None] = {
        "max_tool_calls": None,
        "max_model_calls": None,
        "max_tokens": None,
    }
    for xml_name, field_name in (
        ("max-tool-calls", "max_tool_calls"),
        ("max-model-calls", "max_model_calls"),
        ("max-tokens", "max_tokens"),
    ):
        element = parent.find(xml_name)
        if element is not None:
            counts[field_name] = int(_required_text(element, f"budget/{xml_name}"))

    max_cost_element = parent.find("max-cost")
    max_cost = (
        None
        if max_cost_element is None
        else float(_required_text(max_cost_element, "budget/max-cost"))
    )
    runtime_element = parent.find("max-runtime")
    runtime_ms: float | None = None
    if runtime_element is not None:
        runtime = float(_required_text(runtime_element, "budget/max-runtime"))
        unit = runtime_element.get("unit", "seconds")
        runtime_ms = runtime if unit == "milliseconds" else runtime * 1000.0

    return Budget(
        max_tool_calls=counts["max_tool_calls"],
        max_model_calls=counts["max_model_calls"],
        max_tokens=counts["max_tokens"],
        max_cost=max_cost,
        max_runtime_ms=runtime_ms,
    )


def _risk(root: etree._Element) -> RiskPolicy:
    parent = root.find("risk")
    if parent is None:
        return RiskPolicy()
    return RiskPolicy(
        tuple(
            child.get("severity", "")
            for child in parent.findall("require-confirmation")
        )
    )


def _injection(root: etree._Element) -> InjectionPolicy:
    parent = root.find("injection")
    if parent is None:
        return InjectionPolicy()
    return InjectionPolicy(
        tuple(
            _required_text(child, "injection/pattern")
            for child in parent.findall("pattern")
        )
    )


def _output_validation(root: etree._Element) -> OutputValidationPolicy:
    parent = root.find("output-validation")
    if parent is None:
        return OutputValidationPolicy()
    return OutputValidationPolicy(
        required_fields=tuple(
            child.get("name", "")
            for child in parent.findall("require-field")
        ),
        forbidden_values=tuple(
            _required_text(child, "output-validation/forbid-value")
            for child in parent.findall("forbid-value")
        ),
        require_evidence=_xml_bool(parent.get("require-evidence")),
        required_format=parent.get("required-format"),
        require_tool_support=_xml_bool(parent.get("require-tool-support")),
    )


def parse_qa_xml(
    source: str | bytes | Path,
    *,
    schema_path: str | Path | None = None,
) -> Policy:
    """Compile strict QA-XML v0.1 into a typed :class:`Policy`.

    ``str`` values beginning with ``<`` are XML text; an existing non-XML
    string is treated as a path for command-line convenience.  ``Path`` is the
    unambiguous file API.  DTDs and entity declarations are forbidden, network
    access and entity resolution are disabled, and a closed XSD rejects every
    unknown element or attribute.  Direct exact allow/deny contradictions are
    rejected by the typed policy model after schema validation.
    """

    content = _read_source(source)
    if not content.strip():
        raise QAXMLValidationError("QA-XML source is empty")
    if b"<!DOCTYPE" in content.upper():
        raise QAXMLValidationError("QA-XML DTD and entity declarations are forbidden")

    try:
        root = etree.fromstring(content, parser=_strict_xml_parser())
    except etree.XMLSyntaxError as exc:
        raise QAXMLValidationError(
            _validation_message("malformed QA-XML", exc)
        ) from exc

    tree = root.getroottree()
    if tree.docinfo.doctype:
        raise QAXMLValidationError("QA-XML DTD and entity declarations are forbidden")

    resolved_schema = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    schema = _compiled_schema(str(resolved_schema.resolve()))
    try:
        schema.assertValid(tree)
    except etree.DocumentInvalid as exc:
        raise QAXMLValidationError(
            _validation_message("QA-XML schema validation failed", exc)
        ) from exc

    try:
        return Policy(
            policy_id=root.get("id", ""),
            version=root.get("version", "0.1"),
            permissions=_permissions(root),
            privacy=_privacy(root),
            budget=_budget(root),
            risk=_risk(root),
            injection=_injection(root),
            output_validation=_output_validation(root),
            extensions={"source_format": "QA-XML", "schema_version": "0.1"},
        )
    except QAXMLValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise QAXMLValidationError(f"invalid QA-XML policy semantics: {exc}") from exc


load_policy = parse_qa_xml


__all__ = [
    "DEFAULT_SCHEMA_PATH",
    "QAXMLValidationError",
    "load_policy",
    "parse_qa_xml",
]
