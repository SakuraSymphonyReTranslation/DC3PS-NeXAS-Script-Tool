"""
build_full_patch.py — Builder Patch Lengkap Da Capo III Plus Story Bahasa Indonesia (satu perintah).

Menggabungkan SEMUA komponen terjemahan ke satu folder patch LayeredFS
(default: DC3PS_Indo_Patch/romfs) supaya tidak membingungkan:

  1. Naskah scenario  : romfs/Script_Mod/*.binu8            -> romfs/Script/
  2. Font kustom      : romfs/Custom Config/system.datu8    -> romfs/Config/
  3. UI Config        : CSV terjemahan -> Config/*.datu8    (ui_translation_tool)
  4. UI Layout SPM    : CSV terjemahan -> System/*.spm      (ui_translation_tool)
  5. UI Tekstur PNG   : png_work/edited/*.png -> System/     (konversi format otomatis)
  6. Video lirik OP ID: Movie/dc3ps_op.mp4 (encode sesuai docs/SPEK_ENCODE_VIDEO.md)
                        -> romfs/Movie/dc3ps_op.mp4

Komponen yang filenya tidak ada otomatis DILEWATI dengan jelas (patch tetap valid).

Pemakaian:
  python build_full_patch.py                 # bangun patch dari semua yang tersedia
  python build_full_patch.py --zip           # + buat 3 paket ZIP rilis (build_release_packages.py)
  python build_full_patch.py --install       # + pasang otomatis ke emulator Eden
  python build_full_patch.py --only script,ui --zip --install
  python build_full_patch.py --csv-config terjemahan.csv --video op_indo.mp4
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Root repo = induk dari src/nexas/ (file ini dipindah ke src/nexas/).
BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))
import ui_translation_tool as uit  # noqa: E402  (wrapper root)
import exefs_patch_tool as ept  # noqa: E402  (wrapper root)

TID = "010041601B544000"  # Da Capo III Plus Story (Nintendo Switch)
MOD_NAME = "Da Capo III Plus Story Patch"
VIDEO_NAME = "dc3ps_op.mp4"
COMPONENTS = ('script', 'ui-config', 'ui-spm', 'ui-png', 'video', 'exefs')

LINE = '=' * 79


def count_glob(pattern: str) -> int:
    import glob
    # recursive=True WAJIB: pola '**/*.binu8' tanpa flag ini hanya cocok
    # dengan file di dalam SUBFOLDER, bukan langsung di Script_Mod ->
    # dulu menyebabkan patch selalu dibangun tanpa naskah scenario.
    return len(glob.glob(pattern, recursive=True))


def default_video() -> Path | None:
    for cand in (BASE / 'romfs_mod' / 'Movie' / VIDEO_NAME,
                 BASE / 'romfs' / 'Movie' / VIDEO_NAME):
        if cand.exists() and cand.stat().st_size > 0:
            return cand
    return None


def install_edem(patch_romfs: Path, log=print) -> bool:
    eden_root = Path(os.environ.get('APPDATA', '')) / 'eden' / 'load' / TID / MOD_NAME / 'romfs'
    if not (Path(os.environ.get('APPDATA', '')) / 'eden').exists():
        log('[LEWATI] Emulator Eden tidak terdeteksi (%APPDATA%/eden).')
        return False
    eden_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(patch_romfs, eden_root, dirs_exist_ok=True)
    n = sum(len(f) for _r, _d, f in os.walk(eden_root))
    log('[OK] Terpasang ke Eden: %s (%d file)' % (eden_root, n))
    log('     (Jika Eden sedang berjalan, tutup dulu lalu ulangi agar file bisa ditimpa.)')
    return True


def zip_translation_patch(patch_dir: Path, log=print):
    zip_path = BASE / 'DC3PS_Translation_Patch.zip'
    import zipfile
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(patch_dir):
            for name in files:
                p = Path(root) / name
                z.write(p, p.relative_to(patch_dir.parent))
    mb = zip_path.stat().st_size / (1024 * 1024)
    log('[OK] %s (%.2f MB)' % (zip_path, mb))


def build(args) -> int:
    patch = Path(args.out_patch)
    romfs = patch / 'romfs'
    only = set(args.only.split(',')) if args.only else set(COMPONENTS)
    unknown = only - set(COMPONENTS)
    if unknown:
        print('[ERROR] --only tidak dikenal: %s (pilihan: %s)' % (', '.join(sorted(unknown)), ', '.join(COMPONENTS)))
        return 1

    print(LINE)
    print('   BUILDER PATCH LENGKAP — DA CAPO III PLUS STORY (Bahasa Indonesia)')
    print('   Tujuan patch : %s' % romfs)
    print('   Komponen     : %s' % ', '.join(sorted(only)))
    print(LINE)

    summary = []

    # ---------- 1. Naskah scenario (.binu8 hasil Insert) ----------
    if 'script' in only:
        src = Path(args.script_dir)
        n = count_glob(str(src / '**' / '*.binu8')) if src.is_dir() else 0
        if n:
            dst = romfs / 'Script'
            dst.mkdir(parents=True, exist_ok=True)
            for f in sorted(src.glob('**/*.binu8')):
                rel = f.relative_to(src)
                (dst / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst / rel)
            print('[OK]    Scenario : %d file .binu8 -> %s' % (n, dst))
            summary.append('Scenario : %d file script' % n)
        else:
            print('[LEWATI] Scenario : %s tidak ada / kosong (jalankan tab Insert dulu)' % src)

    # ---------- 2. Font kustom ----------
    font = BASE / 'romfs' / 'Custom Config' / 'system.datu8'
    if font.exists():
        dst = romfs / 'Config'
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(font, dst / 'system.datu8')
        print('[OK]    Font kustom: system.datu8 -> %s' % dst)

    # ---------- 3. UI Config (.datu8) ----------
    if 'ui-config' in only:
        csvs = [Path(p) for p in args.csv_config if Path(p).exists()]
        has_text = False
        for c in csvs:
            import csv as _csv
            with open(c, 'r', encoding='utf-8-sig', newline='') as fh:
                has_text = any((r.get('indonesian_translation') or '').strip() for r in _csv.DictReader(fh))
                if has_text:
                    break
        if csvs and has_text:
            uit.apply_config_csv([str(c) for c in csvs], str(patch))
            n_out = len(list((romfs / 'Config').glob('*.datu8')))
            print('[OK]    UI Config : %d file .datu8 di patch' % n_out)
            summary.append('UI Config (.datu8) : %d file' % n_out)
        else:
            print('[LEWATI] UI Config : CSV terjemahan belum diisi (%s)' %
                  ', '.join(str(c) for c in args.csv_config))

    # ---------- 4. UI Layout SPM ----------
    if 'ui-spm' in only:
        c = Path(args.csv_spm)
        has_text = False
        if c.exists():
            import csv as _csv
            with open(c, 'r', encoding='utf-8-sig', newline='') as fh:
                has_text = any((r.get('indonesian_translation') or '').strip() for r in _csv.DictReader(fh))
        if has_text:
            uit.apply_spm_csv(str(c), str(patch))
            n_out = len(list((romfs / 'System').glob('*.spm')))
            print('[OK]    UI SPM    : %d file .spm di patch' % n_out)
            summary.append('UI Layout (.spm) : %d file' % n_out)
        else:
            print('[LEWATI] UI SPM : CSV terjemahan belum diisi (%s)' % c)

    # ---------- 5. UI Tekstur PNG ----------
    if 'ui-png' in only:
        edited = Path(args.png_edited)
        n = count_glob(str(edited / '*.png')) if edited.is_dir() else 0
        if n:
            print('[...]   UI PNG    : mengemas %d file hasil edit...' % n)
            res = uit.pack_png_to_patch(str(edited), str(patch))
            if res['packed']:
                summary.append('UI PNG : %d file (%d dikonversi otomatis)' % (res['packed'], res['converted']))
        else:
            print('[LEWATI] UI PNG : %s tidak ada / kosong (audit-png -> export-png -> edit)' % edited)

    # ---------- 6. Video lirik OP Indonesia ----------
    if 'video' in only:
        vid = Path(args.video) if args.video else default_video()
        if vid and vid.exists():
            dst = romfs / 'Movie'
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vid, dst / VIDEO_NAME)
            mb = vid.stat().st_size / (1024 * 1024)
            print('[OK]    Video     : %s (%.1f MB) -> %s' % (vid, mb, dst / VIDEO_NAME))
            print('        Catatan: pastikan encode sesuai docs/SPEK_ENCODE_VIDEO.md')
            print('        (H.264 Main@L4.1, 1080p yuv420p 24fps CFR, AAC-LC 48kHz stereo).')
            summary.append('Video lirik OP : %s (%.1f MB)' % (VIDEO_NAME, mb))
        else:
            print('[LEWATI] Video : %s tidak ditemukan (opsional, wujudkan dulu di Movie/)' % VIDEO_NAME)

    # ---------- 7. ExeFS: pesan info pojok kiri-bawah (dump milik pengguna) ----------
    if 'exefs' in only:
        # path bisa dioverride dari GUI/CLI; fallback: nilai sederhana jika argumen tidak ada
        dump_dir = getattr(args, 'exefs_dump', None) or str(BASE / 'scratch' / 'exefs_dump')
        csv_path = getattr(args, 'exefs_csv', None) or str(BASE / 'scratch' / 'exefs_messages.csv')
        out_dir = getattr(args, 'exefs_out', None) or str(BASE / 'scratch' / 'exefs_patch')
        res = ept.patch_dump(dump_dir, csv_path, out_dir)
        if res['ok']:
            summary.append('ExeFS pesan info : %d penggantian' % res['total'])
            if args.install:
                eden_exefs = (Path(os.environ.get('APPDATA', '')) / 'eden' / 'exefs' / TID)
                if (Path(os.environ.get('APPDATA', '')) / 'eden').exists():
                    eden_exefs.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(res['out'], eden_exefs / 'main')
                    print('[OK]    ExeFS terpasang ke Eden: %s' % (eden_exefs / 'main'))
                else:
                    print('[LEWATI] Eden tidak terdeteksi; salin manual: %s' % res['out'])
            print('        INGAT: file main hasil patch = kode berhak cipta, JANGAN dibagikan.')
        else:
            print('[LEWATI] ExeFS : %s (taruh dump di %s bila ingin menerjemahkan pesan info)'
                  % (res['reason'], dump_dir))

    # ---------- Ringkasan ----------
    print(LINE)
    if summary:
        print('ISI PATCH YANG DIBANGUN:')
        for s in summary:
            print('  + ' + s)
    else:
        print('Tidak ada komponen yang dibangun — isi dulu salah satu sumber terjemahan.')
    print('Folder patch   : %s' % romfs)
    print(LINE)

    # ---------- Pasca-proses ----------
    if args.install:
        install_edem(romfs)
    if args.zip:
        print('[...] Membuat 3 paket ZIP rilis (Atmosphere / Emulator / Ryujinx)...')
        subprocess.run([sys.executable, str(BASE / 'build_release_packages.py')], check=False)  # wrapper root
        zip_translation_patch(patch)
    if args.install or args.zip:
        print()
    print('Selesai. Patch siap dipasang (LayeredFS: atmosphere/contents, load/, atau mods/contents).')
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out-patch', default=str(BASE / 'DC3PS_Indo_Patch'))
    p.add_argument('--script-dir', default=str(BASE / 'romfs' / 'Script_Mod'))
    p.add_argument('--csv-config', nargs='+',
                   default=[str(BASE / 'scratch' / 'ui_strings_config.csv')])
    p.add_argument('--csv-spm', default=str(BASE / 'scratch' / 'ui_strings_spm.csv'))
    p.add_argument('--png-edited', default=str(BASE / 'png_work' / 'edited'))
    p.add_argument('--video', default=None,
                   help='file video lirik OP (default: cari Movie/dc3ps_op.mp4 otomatis)')
    p.add_argument('--only', default=None,
                   help='komponen yang dibangun, dipisah koma: %s' % ','.join(COMPONENTS))
    p.add_argument('--zip', action='store_true',
                   help='buat 3 paket ZIP rilis + DC3PS_Translation_Patch.zip setelah build')
    p.add_argument('--install', action='store_true',
                   help='pasang patch ke emulator Eden setelah build')
    p.add_argument('--exefs-dump', default=str(BASE / 'scratch' / 'exefs_dump'),
                   help='folder dump ExeFS (berisi file main)')
    p.add_argument('--exefs-csv', default=str(BASE / 'scratch' / 'exefs_messages.csv'),
                   help='CSV terjemahan pesan info ExeFS')
    p.add_argument('--exefs-out', default=str(BASE / 'scratch' / 'exefs_patch'),
                   help='folder output main hasil patch ExeFS')
    args = p.parse_args()
    sys.exit(build(args))


if __name__ == '__main__':
    main()
