# -*- coding: utf-8 -*-
"""ui_translation_tool — ekstrak/terapkan terjemahan UI (.datu8/.spm) + PNG.

Implementasi: ``src/nexas/ui_translation_tool.py``. Wrapper kompatibilitas root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nexas.ui_translation_tool import *  # noqa: F401,F403
from src.nexas.ui_translation_tool import main  # noqa: F401

if __name__ == '__main__':
    main()
