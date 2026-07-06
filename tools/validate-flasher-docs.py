#!/usr/bin/env python3
"""Validate docs packs and ESP Web Tools manifests before publishing Pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PACKS = DOCS / "packs"
ESP_IMAGE_MAGIC = b"\xe9"
ESP_IMAGE_OFFSETS = {0, 0x1000, 0x10000}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

failed = False


def error(path: Path, message: str) -> None:
    global failed
    failed = True
    rel = path.relative_to(ROOT) if path.is_absolute() else path
    print(f"::error file={rel}::{message}")


def ok(message: str) -> None:
    print(f"ok: {message}")


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        error(path, f"invalid JSON: {exc}")
        return None


def parse_offset(path: Path, value: Any, context: str) -> int | None:
    try:
        if isinstance(value, str):
            return int(value, 0)
        return int(value)
    except (TypeError, ValueError):
        error(path, f"{context} has invalid offset {value!r}")
        return None


def docs_path(path_value: str) -> Path:
    return DOCS / path_value


def first_byte(path: Path) -> bytes:
    try:
        with path.open("rb") as file:
            return file.read(1)
    except OSError:
        return b""


def validate_manifest(manifest_path: Path) -> set[str]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        error(manifest_path, "manifest root must be an object")
        return set()

    builds = manifest.get("builds")
    if not isinstance(builds, list) or not builds:
        error(manifest_path, "manifest must contain at least one build")
        return set()

    chip_families: set[str] = set()
    for build_index, build in enumerate(builds):
        if not isinstance(build, dict):
            error(manifest_path, f"build #{build_index + 1} must be an object")
            continue

        chip_family = build.get("chipFamily")
        if not isinstance(chip_family, str) or not chip_family:
            error(manifest_path, f"build #{build_index + 1} is missing chipFamily")
        else:
            chip_families.add(chip_family)

        parts = build.get("parts")
        if not isinstance(parts, list) or not parts:
            error(manifest_path, f"build #{build_index + 1} must contain parts")
            continue

        parsed_parts: list[tuple[int, str, Path]] = []
        for part_index, part in enumerate(parts):
            if not isinstance(part, dict):
                error(manifest_path, f"build #{build_index + 1} part #{part_index + 1} must be an object")
                continue

            part_path_value = part.get("path")
            if not isinstance(part_path_value, str) or not part_path_value:
                error(manifest_path, f"build #{build_index + 1} part #{part_index + 1} is missing path")
                continue

            offset = parse_offset(manifest_path, part.get("offset"), f"build #{build_index + 1} part '{part_path_value}'")
            if offset is None:
                continue

            part_path = docs_path(part_path_value)
            if not part_path.is_file():
                error(manifest_path, f"references missing part '{part_path_value}'")
                continue

            parsed_parts.append((offset, part_path_value, part_path))

        if not parsed_parts:
            continue

        first_offset, first_part_value, first_part_path = min(parsed_parts, key=lambda item: item[0])
        required_magic_parts = {(first_offset, first_part_value, first_part_path)}
        required_magic_parts.update(part for part in parsed_parts if part[0] in ESP_IMAGE_OFFSETS)

        for offset, part_path_value, part_path in sorted(required_magic_parts):
            magic = first_byte(part_path)
            if magic != ESP_IMAGE_MAGIC:
                got = magic.hex() if magic else "empty"
                error(
                    manifest_path,
                    f"offset 0x{offset:x} part '{part_path_value}' starts 0x{got}; expected ESP image magic 0xe9",
                )

    return chip_families


def validate_preview(pack_path: Path, pack: dict[str, Any]) -> None:
    preview = pack.get("preview")
    preview_dir = pack.get("previewDir")
    states = pack.get("states")

    if preview is not None:
        if not isinstance(preview, str) or not preview:
            error(pack_path, "preview must be a non-empty path")
        elif not docs_path(preview).is_file():
            error(pack_path, f"preview file '{preview}' is missing")

    if (preview_dir is None) != (states is None):
        error(pack_path, "previewDir and states must be declared together")
        return

    if preview_dir is None and states is None:
        return

    if not isinstance(preview_dir, str):
        error(pack_path, "previewDir must be a string")
        return

    if not isinstance(states, list) or not states:
        error(pack_path, "states must be a non-empty array")
        return

    for state in states:
        if not isinstance(state, str) or not state:
            error(pack_path, f"invalid state {state!r}")
            continue
        gif_path = DOCS / "preview" / "gifs" / preview_dir / f"{state}.gif"
        if not gif_path.is_file():
            error(pack_path, f"state '{state}' is missing preview GIF '{gif_path.relative_to(DOCS)}'")


def validate_pack(
    pack_path: Path,
    pack: dict[str, Any],
    seen_pack_ids: dict[str, Path],
    manifest_chips: dict[str, set[str]],
) -> None:
    pack_id = pack.get("id")
    if not isinstance(pack_id, str) or not pack_id:
        error(pack_path, "pack must have a non-empty id")
    elif pack_id != pack_path.stem:
        error(pack_path, f"pack id '{pack_id}' must match file name '{pack_path.stem}'")
    elif pack_id in seen_pack_ids:
        error(pack_path, f"duplicate pack id '{pack_id}' also appears in {seen_pack_ids[pack_id].relative_to(ROOT)}")
    else:
        seen_pack_ids[pack_id] = pack_path

    kind = pack.get("kind")
    if kind not in {"firmware", "pet"}:
        error(pack_path, "kind must be either 'firmware' or 'pet'")

    tag = pack.get("tag")
    if not isinstance(tag, str) or not tag:
        error(pack_path, "pack must have a non-empty tag")

    manifest_value = pack.get("manifest")
    if not isinstance(manifest_value, str) or not manifest_value:
        error(pack_path, "pack must reference a manifest")
    else:
        manifest_path = docs_path(manifest_value)
        if not manifest_path.is_file():
            error(pack_path, f"manifest '{manifest_value}' is missing")
        elif isinstance(tag, str) and tag:
            chips = manifest_chips.get(manifest_value, set())
            if chips and tag not in chips:
                error(pack_path, f"tag '{tag}' does not match manifest chipFamily {sorted(chips)}")

    validate_preview(pack_path, pack)

    if kind == "pet":
        if tag != "ESP32-S3":
            error(pack_path, "pet packs must target tag 'ESP32-S3' for the JC3248W535 flasher")
        for required in ("preview", "previewDir", "states"):
            if required not in pack:
                error(pack_path, f"pet pack is missing required '{required}'")

    updated = pack.get("updated")
    if updated is not None and (not isinstance(updated, str) or not ISO_DATE.fullmatch(updated)):
        error(pack_path, "updated must use YYYY-MM-DD")


def main() -> int:
    if not DOCS.is_dir() or not PACKS.is_dir():
        error(ROOT, "docs/ and docs/packs/ must exist")
        return 1

    manifest_chips = {
        manifest_path.name: validate_manifest(manifest_path)
        for manifest_path in sorted(DOCS.glob("manifest-*.json"))
    }
    if not manifest_chips:
        error(DOCS, "no manifest-*.json files found")

    seen_pack_ids: dict[str, Path] = {}
    pack_paths = sorted(PACKS.glob("*.json"))
    if not pack_paths:
        error(PACKS, "no pack JSON files found")

    for pack_path in pack_paths:
        pack = load_json(pack_path)
        if isinstance(pack, dict):
            validate_pack(pack_path, pack, seen_pack_ids, manifest_chips)
        else:
            error(pack_path, "pack root must be an object")

    if failed:
        print("flasher docs validation failed")
        return 1

    ok(f"validated {len(pack_paths)} packs and {len(manifest_chips)} manifests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
