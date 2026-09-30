# -*- coding: utf-8 -*-
"""exefs_patch_tool — patcher pesan info UI di ExeFS (file `main`).

Implementasi: ``src/nexas/exefs_patch_tool.py``. Wrapper kompatibilitas root
agar perintah lama (``python exefs_patch_tool.py scan|apply|discover``) tetap jalan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nexas.exefs_patch_tool import *  # noqa: F401,F403
from src.nexas.exefs_patch_tool import main  # noqa: F401

if __name__ == '__main__':
    main()
