"""Mechanical normalization using explicit, reviewed JSON-pointer mappings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from records_audit import EvidenceError, FIELDS, bound_path, pointer, read_json, sha


def prepare(raw_root: Path, mapping_path: Path, output: Path) -> None:
    mapping = read_json(mapping_path)
    if output.resolve().is_relative_to(raw_root.resolve()):
        raise EvidenceError("output must be outside the original archive")
    cache = {}
    raw_bytes = {}
    for name, expected in mapping["source_files"].items():
        if name in ("intake.json", "normalized.jsonl"):
            raise EvidenceError("original source collides with a reserved output name; retain it under a raw/ prefix")
        data = bound_path(raw_root, name).read_bytes()
        if sha(data) != expected:
            raise EvidenceError(f"mapping source hash differs: {name}")
        cache[name] = read_json(bound_path(raw_root, name))
        raw_bytes[name] = data
    rows = []
    for collection in mapping["record_collections"]:
        name = collection["file"]
        parent = collection["collection_pointer"]
        records = pointer(cache[name], parent)
        if not isinstance(records, list):
            raise EvidenceError("record collection must be an array; JSONL root is an array")
        fields = collection["field_pointers"]
        context = collection.get("context_bindings", {})
        if set(fields) & set(context) or set(fields) | set(context) != set(FIELDS):
            raise EvidenceError("every field needs exactly one source binding")
        for index, _ in enumerate(records):
            bindings = dict(context)
            for field, relative in fields.items():
                if relative != "" and not relative.startswith("/"):
                    raise EvidenceError("relative field pointer invalid")
                bindings[field] = {"file": name, "pointer": f"{parent}/{index}{relative}"}
            values = {field: pointer(cache[binding["file"]], binding["pointer"])
                      for field, binding in bindings.items()}
            rows.append({"values": values, "bindings": bindings})
    intake = {"study": mapping["study"], "source_files": mapping["source_files"],
              "bindings": mapping["bindings"]}
    # Build in memory before exclusively creating output. Preserve raw inputs.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in raw_bytes.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
    (output / "intake.json").write_text(json.dumps(intake, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "normalized.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.raw_root, args.mapping, args.output)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        raise SystemExit(f"UNEXECUTED/FAILED NORMALIZATION: {error}") from error
    print("COPIED AND BOUND SOURCE FIELDS; frozen provenance requires separate review")


if __name__ == "__main__":
    main()
