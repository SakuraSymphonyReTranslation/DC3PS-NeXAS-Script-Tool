"""
Headless Runner NSP Mod Maker (Da Capo III Plus Story - Indo Patch)
=======================================================================
Melanjutkan sesi Antigravity yang terputus: memanggil pipeline build
NspMakerGui._run_direct dari build_modded_nsp_gui.pyc (Python 3.14)
TANPA membuka jendela GUI, sehingga update_patch.bat dapat membuat
1 file NSP standalone secara otomatis.

Pemakaian:
    py -3.14 build_nsp_headless.py            # build penuh
    py -3.14 build_nsp_headless.py --dry-run  # validasi config saja
"""
import sys
import os
import types
import queue
import logging
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = Path(__file__).resolve().parent.parent  # root repo (file ini di src/)
EXTRACTED = BASE / 'NSPModMaker.exe_extracted'
PYC = EXTRACTED / 'build_modded_nsp_gui.pyc'

# ---------------------------------------------------------------- stub customtkinter
# Modul asli hanya digunakan oleh class GUI; pipeline build tidak menyentuhnya.
ctk = types.ModuleType('customtkinter')
ctk.__getattr__ = lambda name: type(name, (), {
    '__init__': lambda self, *a, **k: None,
    '__getattr__': lambda self, item: lambda *a, **k: None,
})  # type: ignore[attr-defined]
sys.modules['customtkinter'] = ctk

# ---------------------------------------------------------------- load pyc
sys._MEIPASS = str(EXTRACTED)          # membuat modul menganggap diri "compiled"
import marshal
import importlib.util

spec = importlib.util.spec_from_file_location('nspmod', PYC)
mod = importlib.util.module_from_spec(spec)
sys.modules['nspmod'] = mod          # wajib: resolusi dataclass butuh modul terdaftar
spec.loader.exec_module(mod)
print('[+] Modul build_modded_nsp_gui.pyc dimuat (headless)')

# ---------------------------------------------------------------- config
config_path = Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming'))) / 'NSPModMaker' / 'config.json'
import json
cfg = json.loads(config_path.read_text(encoding='utf-8'))

base_nsp = Path(cfg['base'])
layeredfs = Path(cfg['layeredfs'])
output = Path(cfg['output'])
keyset = Path(cfg['keyset']) if cfg.get('keyset') else None
title_id = cfg.get('title_id') or '010041601B544000'
name = cfg.get('product_name') or 'Da Capo III Plus Story Indo Mod'

# Validasi awal (mirror check_requirements build_patch_nsp.py)
if not base_nsp.exists():
    print(f'[!] Base NSP tidak ditemukan: {base_nsp}'); sys.exit(2)
if not layeredfs.exists():
    print(f'[!] Folder LayeredFS tidak ditemukan: {layeredfs}'); sys.exit(2)
if keyset and not keyset.exists():
    print(f'[!] Keyset tidak ditemukan: {keyset}'); sys.exit(2)

# GUI selalu mengirim Base NSP juga sebagai "update" (Update title ID sama,
# urutan pipeline tetap valid). Pipeline menoleransi hal ini.
config = mod.BuildConfig(
    base=base_nsp,
    update=base_nsp,           # tanpa update NSP terpisah; GUI default
    layeredfs=layeredfs,
    mod_exefs=None,
    title_id=title_id,
    name=name,
    output=output,
    force=True,
    keep_workdir=False,
    workdir=mod.short_workdir_for(output, base_nsp),
    log_path=mod.APP_DIR / 'logs' / 'build_modded_nsp.log',
    keyset=keyset,
)

print(f'    Base      : {config.base}')
print(f'    LayeredFS : {config.layeredfs}')
print(f'    Output    : {config.output}')
print(f'    Workdir   : {config.workdir}')
print(f'    Keyset    : {config.keyset}')

if '--dry-run' in sys.argv:
    mod.validate_config(config)
    print('[OK] Config valid (dry-run). Tidak ada build dijalankan.')
    sys.exit(0)

# ---------------------------------------------------------------- build headless
class _Runner:
    """Menggantikan self pada NspMakerGui._run_direct (hanya butuh output_queue)."""
    output_queue = queue.Queue()

runner = _Runner()
root_logger = logging.getLogger()
before = list(root_logger.handlers)

print('[*] Build NSP dimulai (ekstraksi 7 GB base, merge mod, rebuild RomFS, repack NSP)...')
print('    Proses ini bisa memakan waktu puluhan menit. Pantau log:')
print(f'    {config.log_path}')

try:
    mod.NspMakerGui._run_direct(runner, config)
finally:
    # _run_direct memasang _QueueLogHandler ke root logger; bersihkan sisa handler
    for h in list(root_logger.handlers):
        if h not in before:
            root_logger.removeHandler(h)

# hasil dikirim lewat queue: '__OK__' / '__FAIL__' / pesan error string
msgs = []
while True:
    try:
        msgs.append(runner.output_queue.get_nowait())
    except queue.Empty:
        break
print('-' * 70)
for m in msgs:
    print('  ', m)
print('-' * 70)

if msgs and msgs[-1] == '__OK__':
    size_gb = output.stat().st_size / (1024 ** 3)
    print(f'[SUKSES] NSP dibuat: {output} ({size_gb:.2f} GB)')
    sys.exit(0)
print('[GAGAL] Build tidak selesai. Lihat log di atas / berkas log.')
sys.exit(1)
