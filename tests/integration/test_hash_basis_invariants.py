"""Reproducibility invariants for the SHA-256 freeze hash basis.

These tests are offline and deterministic. They guard the checkout policy defined
in ``docs/hash_basis_policy.md``:

* the canonical text representation of tracked files is LF;
* ``.gitattributes`` forces LF working-tree materialization on every platform;
* freezes attest raw working-tree bytes, so a clean checkout must materialize
  bytes identical to the committed blobs;
* validation must not be weakened to hash-time normalization or blob-only hashing.

They assert nothing about experimental results, metrics, or benchmark semantics.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GITATTRIBUTES = PROJECT_ROOT / ".gitattributes"
POLICY_LINE = "* text=auto eol=lf"

CRLF = b"\r\n"
LF = b"\n"

# Working-tree files whose bytes are bound by a recorded SHA-256 freeze, or that a
# validator hashes at runtime. These are the files a non-canonical checkout breaks.
HASH_BOUND_PATHS: tuple[str, ...] = (
    "docs/phaseD_instrument_qualification_plan.md",
    "docs/preregistration_coverage_extension_v1.md",
    "docs/preregistration_coverage_extension_v3.md",
    "benchmark/pilot-v5/manifest.json",
    "benchmark/pilot-v6/manifest.json",
    "benchmark/pilot-v6.1/manifest.json",
    "benchmark/pilot-v6/freeze-record.json",
    "benchmark/pilot-v6.1/freeze-record.json",
)

# Digests recorded on the canonical LF basis. These must keep matching.
RECORDED_LF_BASIS_HASHES: dict[str, str] = {
    "docs/phaseD_instrument_qualification_plan.md": (
        "2896f0e0263a36ab8eb240ccfbeb2ace35057cec16e3f0fe943ed13adf5fcc2a"
    ),
    "benchmark/pilot-v5/manifest.json": (
        "9b21b0c9e0e85e2e81cbefd5f4fb99d6c16f4a5c18a276019bf302295ab82966"
    ),
}

# Modules that must keep hashing raw working-tree bytes.
WORKING_TREE_HASHING_MODULES: tuple[str, ...] = (
    "src/iqa_soa/benchmark/pilot.py",
    "src/iqa_soa/metrics/pilot.py",
    "src/iqa_soa/metrics/statistics.py",
    "scripts/analyze_phaseD_qualification.py",
)

_GIT = shutil.which("git")
requires_git = pytest.mark.skipif(_GIT is None, reason="git executable not available")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> bytes:
    assert _GIT is not None
    completed = subprocess.run(
        [_GIT, *args], cwd=PROJECT_ROOT, capture_output=True, check=True
    )
    return completed.stdout


def _blob_bytes(path: str) -> bytes:
    return _git("cat-file", "blob", "HEAD:" + path)


def _stale_checkout_hint(path: str) -> str:
    return (
        path + " does not match its committed blob byte-for-byte.\n"
        "If the only difference is CRLF vs LF, this working tree was materialized "
        "before the .gitattributes checkout policy and is stale. Re-materialize it "
        "with 'git rm --cached -r . && git reset --hard'. See "
        "docs/hash_basis_policy.md section 7. Committed content is unaffected."
    )


# --- checkout policy -------------------------------------------------------


def test_gitattributes_exists_and_declares_lf_policy() -> None:
    assert GITATTRIBUTES.is_file(), ".gitattributes is missing from the repo root"
    raw = GITATTRIBUTES.read_bytes()
    assert CRLF not in raw, ".gitattributes must itself be LF"
    lines = [line.strip() for line in raw.decode("utf-8").splitlines() if line.strip()]
    assert POLICY_LINE in lines, ".gitattributes must contain: " + POLICY_LINE


@requires_git
@pytest.mark.parametrize("path", HASH_BOUND_PATHS)
def test_hash_bound_text_artifacts_resolve_to_eol_lf(path: str) -> None:
    raw = _git("check-attr", "text", "eol", "--", path).decode("utf-8")
    attrs: dict[str, str] = {}
    for line in raw.splitlines():
        if not line:
            continue
        _, name, value = line.rsplit(": ", 2)
        attrs[name] = value
    assert attrs.get("eol") == "lf", path + " does not resolve to eol=lf: " + raw
    assert attrs.get("text") == "auto", path + " does not resolve to text=auto: " + raw


# --- canonical basis is well defined ---------------------------------------


@requires_git
@pytest.mark.parametrize("path", HASH_BOUND_PATHS)
def test_committed_blobs_are_lf_only(path: str) -> None:
    """The canonical basis is unambiguous only if the blobs carry no CRLF."""
    assert CRLF not in _blob_bytes(path), path + " blob contains CRLF"


@requires_git
@pytest.mark.parametrize("path", HASH_BOUND_PATHS)
def test_working_tree_bytes_match_committed_blob(path: str) -> None:
    """In a clean canonical checkout, what we hash is what was committed."""
    worktree = (PROJECT_ROOT / path).read_bytes()
    assert worktree == _blob_bytes(path), _stale_checkout_hint(path)


@requires_git
@pytest.mark.parametrize(("path", "expected"), sorted(RECORDED_LF_BASIS_HASHES.items()))
def test_recorded_lf_basis_hashes_still_match(path: str, expected: str) -> None:
    """Existing LF-basis freezes must survive the checkout policy unchanged."""
    assert _sha256(_blob_bytes(path)) == expected, (
        path + " committed blob no longer hashes to its recorded LF-basis digest"
    )
    assert _sha256((PROJECT_ROOT / path).read_bytes()) == expected, (
        _stale_checkout_hint(path)
    )


# --- tamper detection is preserved -----------------------------------------


@requires_git
def test_single_byte_mutation_is_detected_by_working_tree_hashing(
    tmp_path: Path,
) -> None:
    """A one-byte edit must change the digest. This is the property being protected."""
    path = "benchmark/pilot-v5/manifest.json"
    original = _blob_bytes(path)
    baseline = _sha256(original)

    scratch = tmp_path / "manifest.json"
    scratch.write_bytes(original)
    assert _sha256(scratch.read_bytes()) == baseline

    # Flip one bit of one byte, then restore, exercising real file I/O.
    mutated = bytearray(original)
    index = original.index(b"pilot-v5") + 6
    mutated[index] = original[index] ^ 0x01
    assert len(mutated) == len(original), "mutation must be byte-length neutral"
    scratch.write_bytes(bytes(mutated))

    assert _sha256(scratch.read_bytes()) != baseline, (
        "working-tree hashing failed to detect a single-byte mutation"
    )

    scratch.write_bytes(original)
    assert _sha256(scratch.read_bytes()) == baseline, "restore did not return to basis"


@requires_git
def test_injected_carriage_return_is_not_absorbed_by_hashing(tmp_path: Path) -> None:
    """An injected CR must be visible to the validator, not normalized away."""
    path = "benchmark/pilot-v5/manifest.json"
    original = _blob_bytes(path)
    scratch = tmp_path / "manifest.json"
    scratch.write_bytes(original.replace(LF, CRLF, 1))
    assert _sha256(scratch.read_bytes()) != _sha256(original), (
        "hashing absorbed an injected CR; tamper detection has been weakened"
    )


# --- anti-weakening --------------------------------------------------------


def _sha256_call_arguments(module: str) -> list[str]:
    """Source text of the first argument of every ``hashlib.sha256(...)`` call."""
    source = (PROJECT_ROOT / module).read_text(encoding="utf-8")
    tree = ast.parse(source)
    arguments: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "sha256":
            segment = ast.get_source_segment(source, node.args[0])
            arguments.append(segment if segment is not None else "")
    return arguments


@pytest.mark.parametrize("module", WORKING_TREE_HASHING_MODULES)
def test_validators_still_hash_raw_working_tree_bytes(module: str) -> None:
    """Every digest in these modules must be taken over unmodified file bytes."""
    arguments = _sha256_call_arguments(module)
    assert arguments, module + " has no hashlib.sha256 call sites to check"

    # Normalizing or re-encoding the bytes before hashing would make a benign EOL
    # difference and an injected CR indistinguishable.
    forbidden = ("replace", "read_text", "splitlines", "decode", "encode", "translate")
    for argument in arguments:
        assert "read_bytes()" in argument or argument.endswith("_bytes"), (
            module + " hashes something other than raw file bytes: " + argument
        )
        for token in forbidden:
            assert token not in argument, (
                module + " normalizes bytes before hashing (found "
                + token + " in " + argument + "); see docs/hash_basis_policy.md "
                "section 2"
            )


@pytest.mark.parametrize("module", WORKING_TREE_HASHING_MODULES)
def test_validators_do_not_hash_git_blob_bytes(module: str) -> None:
    """The Git object store attests what was committed, not what the run read."""
    source = (PROJECT_ROOT / module).read_text(encoding="utf-8")
    for token in ("cat-file", "hash-object", "rev-parse", "GitPython", "pygit2"):
        assert token not in source, (
            module + " appears to hash Git object bytes rather than working-tree "
            "bytes (found " + token + "); see docs/hash_basis_policy.md section 2"
        )


# --- archival EOL reconstruction -------------------------------------------


def _reconstruct_from_eol_mask(canonical: bytes, bare_lf_indices: list[int]) -> bytes:
    """Apply an ``eol-mask-v1`` mask to a canonical LF byte stream.

    Enumerates the LF terminators of ``canonical`` in stream order. Ordinals listed
    in ``bare_lf_indices`` stay a bare LF; every other LF becomes CRLF. No other
    byte is altered.
    """
    bare = set(bare_lf_indices)
    out = bytearray()
    ordinal = 0
    for byte in canonical:
        if byte == 0x0A:
            if ordinal not in bare:
                out += b"\r"
            out += b"\n"
            ordinal += 1
        else:
            out.append(byte)
    return bytes(out)


@requires_git
def test_historical_mixed_eol_materialization_is_reconstructible() -> None:
    """The lost mixed-EOL byte sequence must stay derivable from committed bytes.

    This reads only the committed blob and the recorded mask, never the working
    tree, so it holds from any fresh canonical checkout.
    """
    sidecar = PROJECT_ROOT / "docs" / "hash_basis_amendment_v1.json"
    record = json.loads(sidecar.read_text(encoding="utf-8"))

    entries = [
        entry
        for entry in record["amended_artifacts"]
        if "historical_eol_reconstruction" in entry
    ]
    assert entries, "no artifact carries an historical_eol_reconstruction mask"

    for entry in entries:
        mask = entry["historical_eol_reconstruction"]
        assert mask["convention"] == "eol-mask-v1"
        assert mask["index_basis"] == (
            "0-based LF-terminator ordinal in canonical LF byte stream"
        )
        assert mask["all_other_lf_terminators_are_crlf"] is True
        assert mask["capture_verified_against_original_worktree"] is True

        canonical = _blob_bytes(mask["canonical_source"])
        assert _sha256(canonical) == mask["canonical_source_sha256"], (
            "canonical source blob no longer matches the recorded mask basis"
        )
        assert len(canonical) == mask["canonical_source_bytes"]

        # The mask is only durable if its recorded anchor commit still resolves to
        # the same canonical source bytes. That anchor is a real, reachable commit,
        # not the working-tree materialization, which was never a Git blob.
        anchor = mask["capture_canonical_source_commit"]
        anchored = _git(
            "cat-file", "blob", anchor + ":" + mask["canonical_source"]
        )
        assert _sha256(anchored) == mask["canonical_source_sha256"], (
            "canonical source at anchor commit " + anchor + " does not hash to the "
            "recorded canonical_source_sha256"
        )
        assert anchored == canonical, (
            "canonical source drifted between anchor commit " + anchor + " and HEAD"
        )
        assert canonical.count(LF) == mask["total_lf_terminators"]
        # A lossless mask requires the canonical stream to carry no CR of its own.
        assert b"\r" not in canonical

        indices = mask["bare_lf_terminator_indices"]
        assert len(indices) == mask["bare_lf_terminator_count"]
        assert len(set(indices)) == len(indices), "mask indices contain duplicates"
        assert indices == sorted(indices), "mask indices are not in stream order"
        assert all(0 <= i < mask["total_lf_terminators"] for i in indices), (
            "mask indices fall outside the canonical LF terminator range"
        )

        rebuilt = _reconstruct_from_eol_mask(canonical, indices)

        assert len(rebuilt) == mask["reconstructed_byte_length"]
        assert rebuilt.count(CRLF) == mask["reconstructed_crlf_count"]
        assert rebuilt.count(LF) - rebuilt.count(CRLF) == (
            mask["reconstructed_bare_lf_count"]
        )
        assert _sha256(rebuilt) == mask["reconstructed_sha256"]
        assert _sha256(rebuilt) == entry["historical_recorded_sha256"], (
            "reconstruction does not reproduce the historical recorded digest for "
            + entry["artifact"]
        )
        assert rebuilt.replace(CRLF, LF) == canonical, (
            "normalizing the reconstruction does not return the canonical blob"
        )


@requires_git
def test_preregistration_v3_mask_reproduces_d9d5_exactly() -> None:
    """Pin the archived values for the primary subject artifact."""
    sidecar = PROJECT_ROOT / "docs" / "hash_basis_amendment_v1.json"
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    entry = next(
        item
        for item in record["amended_artifacts"]
        if item["artifact"] == "docs/preregistration_coverage_extension_v3.md"
    )
    mask = entry["historical_eol_reconstruction"]

    canonical = _blob_bytes("docs/preregistration_coverage_extension_v3.md")
    rebuilt = _reconstruct_from_eol_mask(canonical, mask["bare_lf_terminator_indices"])

    assert len(rebuilt) == 34016
    assert rebuilt.count(CRLF) == 518
    assert rebuilt.count(LF) - rebuilt.count(CRLF) == 50
    assert _sha256(rebuilt) == (
        "d9d5f6aad993b9b106d22f06e9e9a347f74c4f5b571449f48ab512bf0c2589a1"
    )
    assert rebuilt.replace(CRLF, LF) == canonical
    assert _sha256(canonical) == (
        "6b7a33501f4610a73f35770314368ecc2aee4eadeab1f5f51b6e09c847409efe"
    )


# --- amendment record integrity --------------------------------------------


@requires_git
def test_amendment_sidecar_claims_hold_against_committed_bytes() -> None:
    """Every canonical LF digest asserted by the amendment must be reproducible."""
    sidecar = PROJECT_ROOT / "docs" / "hash_basis_amendment_v1.json"
    record = json.loads(sidecar.read_text(encoding="utf-8"))

    assert record["additive_only"] is True
    assert record["historical_records_modified"] is False
    assert record["canonical_basis"]["hash_time_normalization"] is False
    assert record["canonical_basis"]["blob_only_hashing"] is False

    for entry in record["amended_artifacts"]:
        path = entry["artifact"]
        blob = _blob_bytes(path)
        assert _sha256(blob) == entry["canonical_lf"]["sha256"], (
            "amendment records a stale canonical LF digest for " + path
        )
        assert len(blob) == entry["canonical_lf"]["bytes"]
        assert entry["historical_recorded_sha256"] != entry["canonical_lf"]["sha256"]
        assert entry["content_difference_beyond_line_endings"] is False, (
            "amendment claims " + path + " differs beyond line endings"
        )


@requires_git
def test_amendment_does_not_rewrite_historical_records() -> None:
    """The historical digests must still be present, verbatim, where they were."""
    sidecar = PROJECT_ROOT / "docs" / "hash_basis_amendment_v1.json"
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    historical = {e["historical_recorded_sha256"] for e in record["amended_artifacts"]}

    corpus = "\n".join(
        _blob_bytes(path).decode("utf-8", errors="replace")
        for path in record["historical_record_locations_left_unchanged"]
    )
    still_present = {digest for digest in historical if digest in corpus}
    assert still_present == historical, (
        "historical digests were removed from their records: "
        + ", ".join(sorted(historical - still_present))
    )
