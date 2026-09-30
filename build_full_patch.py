# -*- coding: utf-8 -*-
"""build_full_patch — builder patch lengkap (scenario + UI + video + ExeFS).

Implementasi: ``src/nexas/build_full_patch.py``. Wrapper kompatibilitas root
agar ``python build_full_patch.py ...`` dan update_patch.bat tetap berfungsi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nexas.build_full_patch import *  # noqa: F401,F403
from src.nexas.build_full_patch import main  # noqa: F401

if __name__ == '__main__':
    main()
