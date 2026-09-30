# -*- coding: utf-8 -*-
"""NeXAS Script Tool — engine inti ekstraksi, injeksi, parsing opcode & word wrap.

Implementasi: ``src/nexas/nexas_tool.py``.
File ini hanya wrapper kompatibilitas agar ``python nexas_tool.py ...`` di root
tetap berfungsi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nexas.nexas_tool import *  # noqa: F401,F403
from src.nexas.nexas_tool import main  # noqa: F401

if __name__ == '__main__':
    main()
