#!/usr/bin/env python3
"""Compile locale/*/LC_MESSAGES/django.po to django.mo (no gettext CLI required)."""

from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent

for po_path in ROOT.glob("locale/*/LC_MESSAGES/django.po"):
    mo_path = po_path.with_suffix(".mo")
    polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
    print(f"Compiled {mo_path.relative_to(ROOT)}")
