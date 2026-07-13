"""Spec extraction helpers for PC parts listings."""

from __future__ import annotations

import re
from typing import Any

_GPU_RE = re.compile(
    r"(?P<brand>NVIDIA|AMD)?\s*(?:GeForce|Radeon)?\s*(?P<family>RTX|GTX|RX)\s*(?P<model>\d{3,4})(?:\s*(?P<suffix>Ti|SUPER|XT|XTX|GRE))?",
    re.IGNORECASE,
)
_CPU_RE = re.compile(
    r"\b(?P<brand>Intel|AMD)\s+(?P<model>(?:Core\s+i\d[-\s]*)?\d{3,5}[A-Z0-9-]*|Ryzen\s+\d\s+\d{4,5}[A-Z0-9-]*)",
    re.IGNORECASE,
)
_RAM_RE = re.compile(r"(?P<size>\d{1,3})\s?GB\s*(?P<kind>DDR[3-5])?", re.IGNORECASE)
_STORAGE_RE = re.compile(r"(?P<size>\d{2,5})\s?(?P<unit>TB|GB)\b", re.IGNORECASE)
_CLOCK_RE = re.compile(
    r"(?P<clock>\d{3,4}(?:\.\d+)?)\s?MHz|(?P<clock_ghz>\d(?:\.\d+)?)\s?GHz", re.IGNORECASE
)


def extract_specs(title: str, category: str | None = None) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", title).strip()
    specs: dict[str, Any] = {"title_normalized": text}

    gpu = _GPU_RE.search(text)
    if gpu:
        specs["gpu_vendor"] = (gpu.group("brand") or "").upper() or None
        specs["gpu_family"] = gpu.group("family").upper()
        specs["gpu_model"] = f"{gpu.group('family').upper()} {gpu.group('model')}"
        if gpu.group("suffix"):
            specs["gpu_suffix"] = gpu.group("suffix").upper()
        specs.setdefault("category", category or "gpu")

    cpu = _CPU_RE.search(text)
    if cpu:
        specs["cpu_vendor"] = (cpu.group("brand") or "").upper() or None
        specs["cpu_model"] = re.sub(r"\s+", " ", cpu.group("model")).strip()
        specs.setdefault("category", category or "cpu")

    ram = _RAM_RE.search(text)
    if ram:
        specs["ram_gb"] = int(ram.group("size"))
        if ram.group("kind"):
            specs["ram_type"] = ram.group("kind").upper()
        specs.setdefault("category", category or "ram")

    storage = _STORAGE_RE.search(text)
    if storage:
        specs["storage_size"] = int(storage.group("size"))
        specs["storage_unit"] = storage.group("unit").upper()
        specs.setdefault("category", category or "storage")

    clock = _CLOCK_RE.search(text)
    if clock:
        if clock.group("clock"):
            specs["clock_mhz"] = float(clock.group("clock"))
        elif clock.group("clock_ghz"):
            specs["clock_ghz"] = float(clock.group("clock_ghz"))

    return specs
