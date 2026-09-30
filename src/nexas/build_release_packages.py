"""
Membangun paket distribusi multi-platform dari DC3PS_Indo_Patch/romfs.

Paket yang dihasilkan:
1. DC3PS_Indo_Patch_Atmosphere_Switch.zip  -> atmosphere/contents/<TID>/romfs
   Untuk Nintendo Switch asli (Atmosphere): ekstrak ke root SD card.
   Juga kompatibel Ryujinx: ekstrak ke folder mods/.
2. DC3PS_Indo_Patch_Emulators.zip          -> load/<TID>/<ModName>/romfs
   Untuk Eden/Citron/Yuzu/Sudachi di Windows dan Android:
   ekstrak ke folder load/ milik emulator (struktur folder Android identik).
3. DC3PS_Indo_Patch_Ryujinx.zip            -> mods/contents/<TID>/romfs
   Untuk Ryujinx desktop.

Paket ZIP emulator juga menyertakan installer.bat di dalam ZIP (hanya untuk
pengguna Windows) yang mendeteksi emulator terpasang dan menyalin otomatis.
"""
import os
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = Path(__file__).resolve().parent.parent.parent  # root repo (file ini di src/nexas/)
TID = "010041601B544000"
MOD_NAME = "Da Capo III Plus Story Patch"
SOURCE = BASE / "DC3PS_Indo_Patch" / "romfs"
FONT = BASE / "romfs" / "Custom Config" / "system.datu8"
INSTALLER = BASE / "installer.bat"

if not SOURCE.exists():
    print(f"[!] Sumber patch tidak ditemukan: {SOURCE}")
    sys.exit(1)


def collect_files() -> list[tuple[Path, Path]]:
    """Kembalikan daftar (file, path relatif dalam romfs)."""
    items = []
    for root, _dirs, files in os.walk(SOURCE):
        for name in files:
            src = Path(root) / name
            rel = src.relative_to(SOURCE)
            items.append((src, rel))
    # sertakan font kustom bila belum ada di patch
    if FONT.exists() and not any(rel.as_posix().startswith("Config/") for _s, rel in items):
        items.append((FONT, Path("Config") / "system.datu8"))
    return items


def build_zip(zip_path: Path, prefix: str, items: list[tuple[Path, Path]], extra_files: dict[str, Path] | None = None) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for src, rel in items:
            arc = f"{prefix}/{rel.as_posix()}" if prefix else rel.as_posix()
            z.write(src, arc)
        for arc, src in (extra_files or {}).items():
            z.write(src, arc)
    mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[+] {zip_path.name} ({mb:.2f} MB) — prefix: {prefix or '(root)'}")


def main() -> None:
    items = collect_files()
    print(f"Sumber: {len(items)} file dari {SOURCE}\n")

    # 1. Atmosphere / Switch real device (ekstrak ke root SD)
    build_zip(BASE / "DC3PS_Indo_Patch_Atmosphere_Switch.zip", f"atmosphere/contents/{TID}/romfs", items)

    # 2. Emulator universal desktop & Android (Eden/Citron/Yuzu/Sudachi)
    extra = {"installer.bat": INSTALLER} if INSTALLER.exists() else None
    build_zip(BASE / "DC3PS_Indo_Patch_Emulators.zip", f"load/{TID}/{MOD_NAME}/romfs", items, extra)

    # 3. Ryujinx desktop
    build_zip(BASE / "DC3PS_Indo_Patch_Ryujinx.zip", f"mods/contents/{TID}/romfs", items)

    print("\nSelesai. 3 paket siap distribusi.")


if __name__ == "__main__":
    main()
