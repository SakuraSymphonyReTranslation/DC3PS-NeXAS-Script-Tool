"""
Script Pembantu Pembuatan NSP Patch untuk Da Capo III Plus Story
Sakura Symphony ReTranslation
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Memastikan output console mendukung UTF-8 (untuk karakter Jepang pada path)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent  # root repo (file ini di src/)

# Lokasi default penting
DEFAULT_BASE_NSP = Path(r"H:\Games\DC3PS\Da Capo III Plus Story [010041601B544000][v0][Base].nsp")
DEFAULT_KEYS = Path(os.path.expandvars(r"%APPDATA%\eden\keys\prod.keys"))
LAYEREDFS_DIR = BASE_DIR / "DC3PS_Indo_Patch" / "romfs"
OUTPUT_NSP = BASE_DIR / "Da Capo III Plus Story [010041601B544000][v0][Indo_Mod].nsp"
NSP_TOOL = BASE_DIR / "nsp_mod_maker_tool" / "NSPModMaker.exe"

def check_requirements():
    print("=" * 70)
    print("      PEMERIKSAAN KEBUTUHAN PEMBUATAN NSP (STANDALONE 1-FILE)")
    print("=" * 70)
    
    # 1. Cek folder patch
    if not LAYEREDFS_DIR.exists():
        print(f"[!] ERROR: Folder mod tidak ditemukan di:\n    {LAYEREDFS_DIR}")
        print("    Jalankan insert skrip atau update_patch.bat terlebih dahulu.")
        return False
    print(f"[+] Folder Mod RomFS ditemukan:\n    {LAYEREDFS_DIR}")

    # 2. Cek Keys
    keys_path = DEFAULT_KEYS
    if not keys_path.exists():
        local_keys = BASE_DIR / "prod.keys"
        if local_keys.exists():
            keys_path = local_keys
        else:
            print(f"[!] PERINGATAN: prod.keys tidak ditemukan di:\n    {DEFAULT_KEYS}")
            print("    Pastikan prod.keys tersedia untuk proses enkripsi/dekripsi NSP.")
    else:
        print(f"[+] Keyset prod.keys ditemukan:\n    {keys_path}")

    # 3. Cek Base NSP
    base_nsp = DEFAULT_BASE_NSP
    if not base_nsp.exists():
        print(f"[!] PERINGATAN: Base Game NSP tidak ditemukan di lokasi default:\n    {DEFAULT_BASE_NSP}")
        print("    Anda dapat memilih file Base Game NSP secara manual di NSP Mod Maker.")
    else:
        size_gb = base_nsp.stat().st_size / (1024**3)
        print(f"[+] Base Game NSP ditemukan:\n    {base_nsp} ({size_gb:.2f} GB)")

    # 4. Cek Tool
    if not NSP_TOOL.exists():
        print(f"[!] ERROR: NSPModMaker.exe tidak ditemukan di:\n    {NSP_TOOL}")
        return False
    print(f"[+] NSPModMaker Tool siap:\n    {NSP_TOOL}")
    
    return True

def setup_nspmodmaker_config():
    config_dir = Path(os.path.expandvars(r"%APPDATA%\NSPModMaker"))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    
    keys_path = DEFAULT_KEYS if DEFAULT_KEYS.exists() else (BASE_DIR / "prod.keys")
    base_path = DEFAULT_BASE_NSP if DEFAULT_BASE_NSP.exists() else ""
    
    cfg = {
        "base": str(base_path),
        "update": "",
        "layeredfs": str(LAYEREDFS_DIR),
        "mod_exefs": "",
        "title_id": "010041601B544000",
        "product_name": "Da Capo III Plus Story Indo Mod",
        "output": str(OUTPUT_NSP),
        "keyset": str(keys_path) if keys_path.exists() else "",
        "lang": "en"
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"[+] Konfigurasi otomatis disimpan ke:\n    {config_path}")
        return True
    except Exception as e:
        print(f"[!] Gagal menyimpan config.json: {e}")
        return False

def launch_tool():
    print("\n[*] Menjalankan NSP Mod Maker...")
    print("    Semua kolom path (Base NSP, Mod RomFS, Keyset, Output) telah terisi otomatis.")
    print("    Silakan klik tombol 'Generate NSP' pada aplikasi yang terbuka.\n")
    try:
        subprocess.Popen([str(NSP_TOOL)], cwd=str(NSP_TOOL.parent))
        return True
    except Exception as e:
        print(f"[!] Gagal membuka NSP Mod Maker: {e}")
        return False

if __name__ == "__main__":
    if check_requirements():
        setup_nspmodmaker_config()
        if len(sys.argv) > 1 and sys.argv[1] == "--check":
            print("\n[OK] Semua kebutuhan NSP Mod Maker valid dan konfigurasi siap.")
            sys.exit(0)
        elif len(sys.argv) > 1 and sys.argv[1] == "--launch":
            launch_tool()
        else:
            print("\nTekan Enter untuk meluncurkan NSP Mod Maker atau Ctrl+C untuk keluar...")
            try:
                input()
                launch_tool()
            except KeyboardInterrupt:
                print("\nDibatalkan.")
