#!/usr/bin/env python3
"""Export VisionForge Pydantic contracts to a deterministic JSON Schema snapshot."""

from __future__ import annotations

import argparse
import copy
import difflib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

import visionforge_core.contracts as contracts
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "schema" / "contracts" / "visionforge-contracts.schema.json"


def public_contract_models() -> list[type[BaseModel]]:
    """Return public Pydantic BaseModel contracts from visionforge_core.contracts.__all__."""
    models: list[type[BaseModel]] = []
    seen: set[type[BaseModel]] = set()
    for name in contracts.__all__:
        value = getattr(contracts, name)
        if (
            inspect.isclass(value)
            and issubclass(value, BaseModel)
            and value is not BaseModel
            and value not in seen
        ):
            models.append(value)
            seen.add(value)
    return sorted(models, key=lambda model: model.__name__)


def build_schema() -> dict[str, Any]:
    root_models = public_contract_models()
    root_model_names = {model.__name__ for model in root_models}
    models = [(model, "validation") for model in root_models]
    _, schema = models_json_schema(
        models,
        title="VisionForge Contracts",
        ref_template="#/$defs/{model}",
    )
    schema = inline_non_root_defs(schema, root_model_names)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "VisionForge Contracts"
    schema["x-schema-version"] = contracts.SCHEMA_VERSION
    return schema


def inline_non_root_defs(schema: dict[str, Any], root_model_names: set[str]) -> dict[str, Any]:
    """Inline enum and nested helper definitions that are not public root models."""
    schema = copy.deepcopy(schema)
    defs = schema.get("$defs", {})
    inline_names = set(defs) - root_model_names

    def resolve(node: Any, seen: frozenset[str] = frozenset()) -> Any:
        if isinstance(node, list):
            return [resolve(item, seen) for item in node]
        if not isinstance(node, dict):
            return node

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            ref_name = ref.removeprefix("#/$defs/")
            if ref_name in inline_names:
                if ref_name in seen:
                    raise ValueError(f"循環的 inline schema ref：{ref_name}")
                replacement = copy.deepcopy(defs[ref_name])
                return resolve(replacement, seen | {ref_name})

        return {key: resolve(value, seen) for key, value in node.items()}

    schema = resolve(schema)
    schema["$defs"] = {
        name: value for name, value in schema.get("$defs", {}).items() if name in root_model_names
    }
    return schema


def render_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_schema(content: str) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")


def check_schema(content: str) -> int:
    existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if existing == content:
        return 0

    diff = difflib.unified_diff(
        existing.splitlines(keepends=True),
        content.splitlines(keepends=True),
        fromfile=str(OUTPUT_PATH),
        tofile=f"{OUTPUT_PATH} (generated)",
    )
    sys.stderr.writelines(diff)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the schema snapshot changed")
    args = parser.parse_args()

    content = render_schema(build_schema())
    if args.check:
        return check_schema(content)

    write_schema(content)
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
