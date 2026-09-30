# -*- coding: utf-8 -*-
"""build_release_packages — bangun 3 paket ZIP rilis multi-platform.

Implementasi: ``src/nexas/build_release_packages.py``. Wrapper kompatibilitas root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nexas.build_release_packages import *  # noqa: F401,F403
from src.nexas.build_release_packages import main  # noqa: F401

if __name__ == '__main__':
    main()
