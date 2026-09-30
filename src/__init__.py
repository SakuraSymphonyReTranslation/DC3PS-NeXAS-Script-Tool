# -*- coding: utf-8 -*-
"""Paket sumber proyek DC3PS-NeXAS-Script-Tool.

Semua implementasi modul ada di sini; file .py di root repo hanyalah
wrapper kompatibilitas tipis agar perintah lama (python nexas_tool.py ...)
tetap berfungsi tanpa mengubah dokumentasi & script .bat.
"""
import os
import sys

# Pastikan root repo selalu ada di sys.path (agar import modul root-wrapper
# dan akses folder data seperti scratch/, romfs/ tetap konsisten).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
