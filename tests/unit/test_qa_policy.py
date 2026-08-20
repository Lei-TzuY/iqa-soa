from __future__ import annotations

from dataclasses import replace

import pytest

from iqa_soa.iqa.policy import (
    Budget,
    InjectionPolicy,
    OutputValidationPolicy,
    PermissionRule,
    Policy,
    PolicyConflictError,
    PrivacyPolicy,
    RiskPolicy,
    merge_case_constraints,
)


def test_permission_matching_is_glob_based_case_sensitive_and_deny_first() -> None:
    policy = Policy(
        "permissions",
        permissions=(
            PermissionRule("allow", "file.*", "workspace/*", "workspace"),
            PermissionRule("deny", "file.read", "workspace/private/*", "private"),
        ),
    )

    assert policy.permission_for("file.read", "workspace/report.txt") == "allow"
    assert policy.permission_for("file.read", "workspace\\private\\secret.txt") == "deny"
    assert policy.permission_for("File.Read", "workspace/report.txt") is None
    assert policy.allow_rules[0].rule_id == "workspace"
    assert policy.deny_rules[0].rule_id == "private"


def test_policy_rejects_direct_exact_allow_deny_contradiction() -> None:
    with pytest.raises(PolicyConflictError) as raised:
        Policy(
            "conflict",
            permissions=(
                PermissionRule("allow", "file.read", "private/*"),
                PermissionRule("deny", "file.read", "private/*"),
            ),
        )

    assert raised.value.conflicts == (("file.read", "private/*"),)


def test_wildcard_overlap_is_not_a_direct_contradiction() -> None:
    policy = Policy(
        "overlap",
        permissions=(
            PermissionRule("allow", "file.read", "*"),
            PermissionRule("deny", "file.read", "private/*"),
        ),
    )

    assert policy.permission_for("file.read", "private/record.txt") == "deny"


def test_case_merge_replaces_broad_allow_and_narrows_every_constraint() -> None:
    base = Policy(
        "base",
        permissions=(PermissionRule("allow", "*", "*"),),
        privacy=PrivacyPolicy(("base/private/*",), ("BASE_SECRET",)),
        budget=Budget(max_tool_calls=10, max_cost=0.5),
        risk=RiskPolicy(("high",)),
        injection=InjectionPolicy((r"ignore\s+prior",)),
        output_validation=OutputValidationPolicy(
            required_fields=("status",), require_evidence=True
        ),
        extensions={"compiler": "v0"},
    )

    merged = merge_case_constraints(
        base,
        allowed_actions=("file.read:*",),
        forbidden_actions=({"tool": "file.read", "resource": "workspace/tmp/*"},),
        allowed_resources=("workspace/*",),
        forbidden_resources=("workspace/private/*",),
        protected_resources=("workspace/patient.txt",),
        protected_values=("CASE_SECRET",),
        budget={"max_tool_calls": 3, "max_runtime": 2},
        injection_patterns=(r"reveal\s+secret",),
        output_required_fields=("evidence_id",),
        output_forbidden_values=("CASE_SECRET",),
        output_require_evidence=False,
    )

    assert merged.permission_for("file.read", "workspace/report.txt") == "allow"
    assert merged.permission_for("message.send", "workspace/report.txt") is None
    assert merged.permission_for("file.read", "workspace/private/a.txt") == "deny"
    assert merged.permission_for("file.read", "workspace/tmp/a.txt") == "deny"
    assert merged.privacy.protected_resources == (
        "base/private/*",
        "workspace/patient.txt",
    )
    assert merged.privacy.protected_values == ("BASE_SECRET", "CASE_SECRET")
    assert merged.budget.max_tool_calls == 3
    assert merged.budget.max_cost == 0.5
    assert merged.budget.max_runtime_ms == 2000.0
    assert merged.budget.max_runtime == 2.0
    assert merged.injection.patterns == (
        r"ignore\s+prior",
        r"reveal\s+secret",
    )
    assert merged.output_validation.required_fields == ("status", "evidence_id")
    assert merged.output_validation.forbidden_values == ("CASE_SECRET",)
    # A case overlay may add a hard requirement but cannot switch one off.
    assert merged.output_validation.require_evidence is True
    assert merged.extensions == {"compiler": "v0"}
    assert base.permission_for("message.send", "external") == "allow"


def test_case_merge_accepts_budget_like_object_and_action_rule() -> None:
    class ActionRule:
        tool = "database.query"
        resource = "public/*"

    class CaseBudget:
        max_tool_calls = 4
        max_model_calls = None
        max_tokens = None
        max_cost = None
        max_runtime_ms = 1250.0

    merged = Policy("case").with_case_constraints(
        allowed_actions=(ActionRule(),), budget=CaseBudget()
    )

    assert merged.permissions == (
        PermissionRule("allow", "database.query", "public/*"),
    )
    assert merged.budget.max_tool_calls == 4
    assert merged.budget.max_runtime_ms == 1250.0


def test_case_merge_skips_provably_disjoint_action_resource_pairs() -> None:
    merged = Policy("paired-allowlists").with_case_constraints(
        allowed_actions=(
            {"tool": "file.read", "resource": "retrieval/*"},
            {"tool": "api.call", "resource": "production-status"},
        ),
        allowed_resources=("retrieval/*", "production-status"),
    )

    assert merged.permissions == (
        PermissionRule("allow", "file.read", "retrieval/*"),
        PermissionRule("allow", "api.call", "production-status"),
    )


def test_budget_normalization_rejects_ambiguous_or_invalid_limits() -> None:
    with pytest.raises(ValueError, match="both max_runtime"):
        Budget.from_constraints({"max_runtime": 1, "max_runtime_ms": 1000})
    with pytest.raises(ValueError, match="unknown budget"):
        Budget.from_constraints({"currency": "USD"})
    with pytest.raises(TypeError, match="integer"):
        Budget(max_tool_calls=True)
    with pytest.raises(ValueError, match="non-negative"):
        Budget(max_cost=-0.01)


def test_typed_subpolicies_validate_at_construction() -> None:
    with pytest.raises(ValueError, match="unknown risk"):
        RiskPolicy(("extreme",))
    with pytest.raises(ValueError, match="invalid injection pattern"):
        InjectionPolicy(("[",))
    with pytest.raises(ValueError, match="required_format"):
        OutputValidationPolicy(required_format="yaml")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="effect"):
        PermissionRule("permit", "file.read")  # type: ignore[arg-type]


def test_frozen_policy_supports_explicit_dataclass_replace() -> None:
    original = Policy("original")
    replaced = replace(original, policy_id="copy", budget=Budget(max_tool_calls=1))

    assert original.policy_id == "original"
    assert replaced.policy_id == "copy"
    assert replaced.budget.max_tool_calls == 1


def test_policy_serialization_redacts_protected_values_by_default() -> None:
    policy = Policy("privacy", privacy=PrivacyPolicy((), ("SECRET",)))

    assert "protected_values" not in policy.to_dict()["privacy"]
    assert policy.to_dict()["privacy"]["protected_value_count"] == 1
    assert policy.to_dict(include_protected_values=True)["privacy"][
        "protected_values"
    ] == ["SECRET"]
