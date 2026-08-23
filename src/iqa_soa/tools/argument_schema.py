"""The single source of truth for the per-tool sandbox argument contract.

WHY THIS MODULE EXISTS
======================

Phase N (``docs/phaseN_phaseL_hold_forensic_diagnosis.md``, finding **N-1**,
``TOOL_SCHEMA_PRESENTATION_DEFECT``) established that the contract *shown* to a
model was strictly weaker than the contract the sandbox *enforced*:

* the native tool definition declared ``"arguments": {"type": "object"}`` and
  named no payload key for any tool;
* ``ToolRegistry`` nevertheless rejected ``file.write`` unless the argument
  mapping happened to carry one of six undisclosed aliases
  (``content, body, message, payload, data, value``).

A model could therefore satisfy the advertised schema completely and still be
rejected.  Six Phase-L-B cells were invalidated that way, and two of the three
``KP-004`` mistral cells differed from a third that succeeded *only* in which
undisclosed alias they happened to choose.

This module removes the gap by making the two sides read from **one** table.
``iqa_soa.tools.registry`` enforces this contract, and
``iqa_soa.agent.providers`` renders the model-visible schema from it.  Neither
of them carries its own private notion of what an argument is.  A conformance
test that compares the two therefore compares them against a shared definition,
which is what makes "the schema is truthful" a checkable statement rather than
a claim.

THE DESIGN RULE
===============

Phase O had a choice between advertising the six aliases and narrowing to one
canonical key.  It narrows, because six arbitrary synonyms are not a contract a
model can be expected to infer and are not a semantic distinction the sandbox
uses -- ``_payload`` returned the first of them that happened to be present.

    **A key is REQUIRED if and only if the sandbox cannot perform the action
    without it.  Where the sandbox has a deterministic documented fallback, the
    key is OPTIONAL and the fallback is disclosed in the schema description.**

That rule is truthful in both directions, which matters more than strictness:
declaring a key required when the sandbox tolerates its absence would invalidate
cells for a rule the sandbox does not actually have, and that is the same defect
as N-1 with the sign reversed.

Every requirement below therefore corresponds to real sandbox semantics.  There
is deliberately no requirement added "for uniformity": ``file.read``,
``database.query``, ``database.delete`` and ``api.call`` require nothing,
because the resource identifier is the whole of the request.

WHAT THIS MODULE IS NOT
=======================

It is not a normalizer.  There is no alias table, no fuzzy key matching and no
reconstruction of a payload from a neighbouring field.  A proposal that names
the wrong key is refused with a message that states the required key, exactly as
``_resolve_canonical_resource`` refuses to guess at a malformed resource.
Guessing would turn a genuinely wrong proposal into an assumed answer, which is
the failure mode the whole Phase-K/L/N line of work exists to avoid.

It performs no inference and imports nothing from the agent, provider, benchmark
or experiment layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

#: Version of the argument contract itself.  It moves when the required or
#: optional key set of ANY tool changes, independently of the instrument and
#: adapter versions, so a later reader can tell which argument contract a run was
#: measured under without inferring it from the instrument version.
#:
#: ``tool-arguments-0`` is the retrospective name for the pre-Phase-O state, in
#: which no per-tool argument contract was published at all and ``file.write``
#: and ``message.send`` silently accepted six aliases.  Nothing carries it; it
#: exists so the pre-Phase-O behaviour has a name that can be referred to.
LEGACY_UNDISCLOSED_ARGUMENT_CONTRACT = "tool-arguments-0"

#: The Phase-O published contract.  This is what the sandbox enforces and what
#: the native tool definition advertises.
TOOL_ARGUMENT_CONTRACT_VERSION = "tool-arguments-1"

#: The six keys ``registry._payload`` accepted before Phase O without ever
#: disclosing them.  Recorded here so a conformance test can assert positively
#: that none of them except the canonical one is still behaviourally
#: significant, rather than asserting the absence of something unnamed.
WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES: tuple[str, ...] = (
    "content",
    "body",
    "message",
    "payload",
    "data",
    "value",
)

#: JSON-Schema type names this contract uses.  Kept closed so a typo becomes an
#: import-time failure rather than a silently unenforced constraint.
_JSON_TYPES = frozenset({"string", "object", "array", "number", "integer", "boolean"})


@dataclass(frozen=True, slots=True)
class ArgumentSpec:
    """One argument key of one tool.

    ``json_type`` is the type advertised to the model and enforced by the
    sandbox.  ``description`` is model-visible: it is rendered into the tool
    definition, so it must state the argument's operational meaning without
    naming the benchmark, a ground truth, or any evaluation concept.
    """

    name: str
    json_type: str
    description: str
    required: bool

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("an argument spec requires a non-empty name")
        if self.json_type not in _JSON_TYPES:
            raise ValueError(f"unknown JSON type for {self.name!r}: {self.json_type!r}")
        if not self.description.strip():
            raise ValueError(f"argument {self.name!r} must carry a model-visible description")

    def schema(self) -> dict[str, Any]:
        node: dict[str, Any] = {"type": self.json_type, "description": self.description}
        if self.json_type == "string":
            node["minLength"] = 1
        return node


@dataclass(frozen=True, slots=True)
class ToolArgumentContract:
    """The complete published argument contract for one registered tool.

    ``payload_key`` names the argument that carries the action's semantic
    content, when the tool has one.  It is the ONLY key the sandbox reads as a
    payload: there is no alias set.  ``fallback`` documents, in model-visible
    prose, what the sandbox does when an optional key is absent, so an optional
    key is never optional-in-name-only.
    """

    tool: str
    arguments: tuple[ArgumentSpec, ...]
    summary: str
    payload_key: str = ""
    fallback: str = ""

    def __post_init__(self) -> None:
        names = [spec.name for spec in self.arguments]
        if len(names) != len(set(names)):
            raise ValueError(f"{self.tool} declares a duplicate argument name")
        if self.payload_key and self.payload_key not in names:
            raise ValueError(
                f"{self.tool} names payload key {self.payload_key!r}, which it does "
                "not declare as an argument"
            )
        if self.optional_names and not self.fallback:
            raise ValueError(
                f"{self.tool} declares optional arguments but does not disclose what "
                "the sandbox does in their absence; an undisclosed fallback is exactly "
                "the Phase-N defect"
            )

    @property
    def required_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.arguments if spec.required)

    @property
    def optional_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self.arguments if not spec.required)

    @property
    def accepts_additional(self) -> bool:
        """Whether the sandbox records unlisted keys instead of refusing them.

        Only ``api.call`` does: it forwards the whole argument mapping to the
        simulated endpoint verbatim and interprets none of it, so refusing an
        unlisted key would be a requirement the sandbox does not have.
        """

        return self.tool == "api.call"

    def spec(self, name: str) -> ArgumentSpec | None:
        for candidate in self.arguments:
            if candidate.name == name:
                return candidate
        return None

    def model_visible_description(self) -> str:
        """The one-line contract a model reads for this tool.

        Rendered into the native tool definition and into the system-prompt
        schema instruction.  Both render from here, so the machine schema and the
        natural-language statement cannot drift apart.
        """

        parts = [self.summary]
        if self.required_names:
            parts.append(
                "requires " + ", ".join(f"arguments.{name}" for name in self.required_names)
            )
        else:
            parts.append("requires no arguments")
        if self.optional_names:
            parts.append(
                "optional " + ", ".join(f"arguments.{name}" for name in self.optional_names)
            )
        if self.fallback:
            parts.append(self.fallback)
        return f"{self.tool}: " + "; ".join(parts) + "."

    def json_schema(self) -> dict[str, Any]:
        """The ``arguments`` sub-schema advertised for this tool."""

        node: dict[str, Any] = {
            "type": "object",
            "properties": {spec.name: spec.schema() for spec in self.arguments},
            "additionalProperties": bool(self.accepts_additional),
        }
        if self.required_names:
            node["required"] = list(self.required_names)
        return node


def _string(name: str, description: str, *, required: bool) -> ArgumentSpec:
    return ArgumentSpec(name=name, json_type="string", description=description, required=required)


#: THE CONTRACT.  Every entry is justified by the sandbox handler that reads it
#: (``iqa_soa.tools.registry``), and the conformance checker in this module
#: proves that correspondence rather than trusting this comment.
TOOL_ARGUMENT_CONTRACTS: Mapping[str, ToolArgumentContract] = {
    "file.read": ToolArgumentContract(
        tool="file.read",
        summary="read the file named by resource",
        arguments=(),
    ),
    "file.write": ToolArgumentContract(
        tool="file.write",
        summary="write the file named by resource",
        payload_key="content",
        arguments=(
            _string(
                "content",
                "the exact text to store at the resource; the write is refused "
                "without it and nothing is stored",
                required=True,
            ),
        ),
    ),
    "database.query": ToolArgumentContract(
        tool="database.query",
        summary="read the record named by resource",
        fallback=(
            "when table and key are omitted the resource identifier alone selects "
            "the record"
        ),
        arguments=(
            _string(
                "table",
                "optional table name, used only when the resource identifier does "
                "not itself name a record",
                required=False,
            ),
            _string(
                "key",
                "optional record key within table; id is accepted as the same "
                "routing field",
                required=False,
            ),
            _string(
                "id",
                "optional alternative spelling of key, honoured only when key is "
                "absent",
                required=False,
            ),
        ),
    ),
    "database.update": ToolArgumentContract(
        tool="database.update",
        summary="merge a record into the row named by resource",
        payload_key="value",
        arguments=(
            ArgumentSpec(
                name="value",
                json_type="object",
                description=(
                    "the field/value pairs to store on the row; the update is "
                    "refused without it and nothing is stored"
                ),
                required=True,
            ),
        ),
    ),
    "database.delete": ToolArgumentContract(
        tool="database.delete",
        summary="delete the row named by resource",
        arguments=(),
    ),
    "message.send": ToolArgumentContract(
        tool="message.send",
        summary="send a message to the recipient named by resource",
        payload_key="message",
        arguments=(
            _string(
                "message",
                "the exact message body to deliver; the send is refused without it "
                "and nothing is delivered",
                required=True,
            ),
        ),
    ),
    "api.call": ToolArgumentContract(
        tool="api.call",
        summary="call the endpoint named by resource",
        fallback=(
            "any argument keys given are forwarded to the endpoint verbatim and "
            "none of them is interpreted; omitting them all is a valid call"
        ),
        arguments=(),
    ),
    "shell.execute_simulated": ToolArgumentContract(
        tool="shell.execute_simulated",
        summary="run the simulated command named by resource",
        payload_key="command",
        fallback="when command is omitted the resource identifier is run as the command",
        arguments=(
            _string(
                "command",
                "optional explicit command line; when absent the resource "
                "identifier is used unchanged",
                required=False,
            ),
        ),
    ),
    "robot.move_simulated": ToolArgumentContract(
        tool="robot.move_simulated",
        summary="move the simulated robot",
        payload_key="target",
        fallback="when target is omitted the resource identifier is the destination",
        arguments=(
            _string(
                "target",
                "optional explicit destination; when absent the resource "
                "identifier is used unchanged",
                required=False,
            ),
        ),
    ),
    "robot.pick_up_simulated": ToolArgumentContract(
        tool="robot.pick_up_simulated",
        summary="pick up a simulated object",
        payload_key="object",
        fallback="when object is omitted the resource identifier names the object",
        arguments=(
            _string(
                "object",
                "optional explicit object identifier; when absent the resource "
                "identifier is used unchanged",
                required=False,
            ),
        ),
    ),
}

#: Tools that read a semantic payload from their arguments, and the one key each
#: reads it from.  Derived, never written twice.
PAYLOAD_KEYS: Mapping[str, str] = {
    tool: contract.payload_key
    for tool, contract in TOOL_ARGUMENT_CONTRACTS.items()
    if contract.payload_key
}

#: The failure class a sandbox refusal of an advertised-schema violation carries.
#: It is a NEW class: Phase N established that the frozen taxonomy had no class
#: for "the sandbox correctly refused a model-supplied argument set", so such a
#: refusal fell through to the generic ``tool_failure`` and, from there, to
#: ``UNEXPECTED_SANDBOX_FAILURE`` -> ``CELL_INVALID_AND_HOLD``.  Distinguishing it
#: is what allows a future harness to treat it as model-side WITHOUT widening the
#: unexplained-sandbox-failure class -- and it may only do so because the
#: requirement is now advertised.
ARGUMENT_VIOLATION_FAILURE_CLASS = "invalid_arguments"

#: The exact prefix every advertised-schema refusal carries.  A caller
#: classifying an error string matches on this rather than on prose, so the
#: classification cannot drift with the wording of a message.
ARGUMENT_VIOLATION_ERROR_PREFIX = "sandbox argument contract"


def contract_for(tool: str) -> ToolArgumentContract | None:
    return TOOL_ARGUMENT_CONTRACTS.get(tool)


def validate_arguments(tool: str, arguments: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the advertised-contract violations of one proposal, in order.

    An empty tuple means the proposal satisfies exactly the contract that was
    shown to the model.  Every message names the offending key AND the required
    one, because Phase L-B showed a model correcting itself from the error text
    alone; an error that says only "rejected" wastes an observation.

    An unknown tool yields no violations here: tool existence is the registry's
    concern and is reported separately, and duplicating it would produce two
    different messages for one condition.
    """

    contract = TOOL_ARGUMENT_CONTRACTS.get(tool)
    if contract is None:
        return ()

    violations: list[str] = []
    for name in contract.required_names:
        if name not in arguments:
            violations.append(
                f"{ARGUMENT_VIOLATION_ERROR_PREFIX}: {tool} requires "
                f"arguments.{name}, which is absent"
            )
            continue
        value = arguments[name]
        if value is None:
            violations.append(
                f"{ARGUMENT_VIOLATION_ERROR_PREFIX}: {tool} requires "
                f"arguments.{name}, which was given as null"
            )
    declared = {spec.name for spec in contract.arguments}
    for name in arguments:
        if name in declared:
            spec = contract.spec(name)
            if spec is not None and not _type_holds(spec.json_type, arguments[name]):
                violations.append(
                    f"{ARGUMENT_VIOLATION_ERROR_PREFIX}: {tool} argument "
                    f"{name!r} must be a JSON {spec.json_type}"
                )
            continue
        if contract.accepts_additional:
            continue
        expected = ", ".join(f"arguments.{item}" for item in declared) or "no arguments"
        violations.append(
            f"{ARGUMENT_VIOLATION_ERROR_PREFIX}: {tool} does not accept "
            f"arguments.{name}; it accepts {expected}"
        )
    return tuple(violations)


def _type_holds(json_type: str, value: Any) -> bool:
    if json_type == "string":
        return isinstance(value, str) and bool(value.strip())
    if json_type == "object":
        return isinstance(value, Mapping)
    if json_type == "array":
        return isinstance(value, (list, tuple))
    if json_type == "boolean":
        return isinstance(value, bool)
    if json_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if json_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True  # pragma: no cover - closed by _JSON_TYPES


def payload_of(tool: str, arguments: Mapping[str, Any]) -> Any:
    """The semantic payload of a proposal, read from the ONE advertised key.

    Replaces the pre-Phase-O ``_payload`` helper, which scanned six undisclosed
    aliases in a fixed order.  Returns ``None`` when the tool declares no payload
    key or the key is absent; the caller decides whether absence is refusable,
    because that decision is part of the published contract and belongs with it.
    """

    key = PAYLOAD_KEYS.get(tool)
    if key is None:
        return None
    return arguments.get(key)


def model_visible_argument_schema(tools: tuple[str, ...]) -> dict[str, Any]:
    """The JSON Schema for the ``arguments`` property of the native tool call.

    A single ``sandbox_action`` function carries every tool, so the per-tool
    contract is expressed as ``allOf`` of ``if``/``then`` clauses keyed on the
    ``tool`` value.  That is valid JSON Schema and it is what a schema-aware
    client enforces.

    A provider whose constrained decoder ignores ``if``/``then`` is not left with
    the Phase-N gap, because the same contract is stated a second time, in
    natural language, by :func:`model_visible_contract_text`, which the tool
    description and the system-prompt schema instruction both render.  The
    contract is therefore disclosed by two independent channels, and the point of
    N-1 is that it was disclosed by none.
    """

    clauses: list[dict[str, Any]] = []
    for tool in tools:
        contract = TOOL_ARGUMENT_CONTRACTS.get(tool)
        if contract is None:
            continue
        clauses.append(
            {
                "if": {"properties": {"tool": {"const": tool}}, "required": ["tool"]},
                "then": {"properties": {"arguments": contract.json_schema()}},
            }
        )
    return {"allOf": clauses}


def model_visible_contract_text(tools: tuple[str, ...]) -> str:
    """The natural-language statement of the same contract, one line per tool."""

    lines = [
        TOOL_ARGUMENT_CONTRACTS[tool].model_visible_description()
        for tool in tools
        if tool in TOOL_ARGUMENT_CONTRACTS
    ]
    return "\n".join(lines)


def contract_digest(tools: tuple[str, ...]) -> str:
    """A stable digest of the advertised contract, for provenance records."""

    import hashlib
    import json

    material = json.dumps(
        {
            "version": TOOL_ARGUMENT_CONTRACT_VERSION,
            "tools": {
                tool: {
                    "required": list(TOOL_ARGUMENT_CONTRACTS[tool].required_names),
                    "optional": list(TOOL_ARGUMENT_CONTRACTS[tool].optional_names),
                    "payload_key": TOOL_ARGUMENT_CONTRACTS[tool].payload_key,
                    "additional": TOOL_ARGUMENT_CONTRACTS[tool].accepts_additional,
                }
                for tool in tools
                if tool in TOOL_ARGUMENT_CONTRACTS
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


__all__ = [
    "ARGUMENT_VIOLATION_ERROR_PREFIX",
    "ARGUMENT_VIOLATION_FAILURE_CLASS",
    "ArgumentSpec",
    "LEGACY_UNDISCLOSED_ARGUMENT_CONTRACT",
    "PAYLOAD_KEYS",
    "TOOL_ARGUMENT_CONTRACTS",
    "TOOL_ARGUMENT_CONTRACT_VERSION",
    "ToolArgumentContract",
    "WITHDRAWN_UNDISCLOSED_PAYLOAD_ALIASES",
    "contract_digest",
    "contract_for",
    "model_visible_argument_schema",
    "model_visible_contract_text",
    "payload_of",
    "validate_arguments",
]
