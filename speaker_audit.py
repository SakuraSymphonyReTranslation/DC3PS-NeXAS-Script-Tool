# -*- coding: utf-8 -*-
"""
speaker_audit.py — Audit nama speaker naskah vs glossarium.

CSTL (atho64.github.io/cstl) menolak paste terjemahan dengan error
"[#N] Nama karakter hilang" bila parser-nya gagal memisahkan nama speaker
dari baris paste (mis. nama dengan tanda baca seperti "Gadis Cantik?").
Menambahkan entri nama ke glossarium + panel "Terjemahan Nama Karakter"
membuat parser yakin bahwa "Nama: pesan" adalah pemisahan yang benar.

Tool ini membandingkan semua speaker unik di CSV hasil csv_dump.py dengan
entri [character] di glossarium.txt, dan melaporkan yang belum terpetakan.

Perintah:
  audit   -c <folder/file CSV> -g <glossarium.txt> [--verbose]
  suggest -c <folder/file CSV> -g <glossarium.txt>
          (usul baris [character] untuk speaker yang belum ada)

Contoh:
  python speaker_audit.py audit   -c "../naskah_csv" -g "glossarium.txt"
  python speaker_audit.py suggest -c "../naskah_csv" -g "glossarium.txt"

Catatan (2026-10): corpus CSV lama tools/naskah_csv sudah dihapus dan
csv_dump.py kini deprecated. Alur resmi adalah export JSON CSTL; tool ini
masih membaca CSV sampai diadaptasi ke sumber JSON.
"""
import argparse
import csv
import glob
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Speaker di bawah ini tidak perlu entri glossarium (bukan nama/epithet
# yang diterjemahkan, hanya penanda teknis).
IGNORE_PATTERNS = (
    re.compile(r'^タイトル画面'),   # pesan sistem, bukan speaker
)


def load_glossary_characters(gloss_path):
    """Return set nama JP dari entri [character] glossarium."""
    chars = set()
    with open(gloss_path, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\[character\]\s+(\S+)\s*=', line)
            if m:
                chars.add(m.group(1))
    return chars


def load_speakers(csv_path):
    """Return Counter(speaker -> jumlah baris) dari semua CSV."""
    if not os.path.exists(csv_path):
        raise SystemExit(
            '[!] Path CSV tidak ditemukan: %r - corpus lama tools/naskah_csv '
            'sudah dihapus dan csv_dump.py deprecated. Hasilkan CSV baru '
            'atau tunggu adaptasi speaker_audit ke export JSON.' % csv_path)
    files = (sorted(glob.glob(os.path.join(csv_path, '**', '*.csv'), recursive=True))
             if os.path.isdir(csv_path) else [csv_path])
    if not files:
        raise SystemExit(
            '[!] Tidak ada file CSV di %r - corpus lama tools/naskah_csv '
            'sudah dihapus dan csv_dump.py deprecated. Hasilkan CSV baru '
            'atau tunggu adaptasi speaker_audit ke export JSON.' % csv_path)
    speakers = Counter()
    for fp in files:
        with open(fp, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                s = (row.get('speaker') or '').strip()
                if s:
                    speakers[s] += 1
    return speakers


def cmd_audit(args):
    chars = load_glossary_characters(args.glossary)
    speakers = load_speakers(args.csv)
    missing = {s: n for s, n in speakers.items()
               if s not in chars and not any(p.search(s) for p in IGNORE_PATTERNS)}
    print('[*] Speaker unik : %d' % len(speakers))
    print('[*] Terpetakan   : %d' % (len(speakers) - len(missing)))
    print('[!] Belum ada    : %d' % len(missing))
    if args.verbose or not missing:
        for s in sorted(missing, key=lambda x: (-missing[x], x)):
            print('  %5d  %s' % (missing[s], s))
    if missing:
        print('\n[!] Tambahkan entri [character] untuk nama di atas ke glossarium,')
        print('    lalu isi juga panel "Terjemahan Nama Karakter (Opsional)" di CSTL.')
    else:
        print('[+] Semua speaker sudah terpetakan di glossarium.')


def cmd_suggest(args):
    chars = load_glossary_characters(args.glossary)
    speakers = load_speakers(args.csv)
    missing = sorted(
        (s for s in speakers if s not in chars
         and not any(p.search(s) for p in IGNORE_PATTERNS)),
        key=lambda s: (-speakers[s], s))
    if not missing:
        print('[+] Tidak ada speaker yang perlu ditambahkan.')
        return
    print('[*] Usul entri (ganti terjemahan sebelum dipakai):\n')
    for s in missing:
        print('[character] %s = ??? {perlu review}' % s)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('audit', help='laporkan speaker yang belum ada di glossarium')
    a.add_argument('-c', '--csv', required=True)
    a.add_argument('-g', '--glossary', required=True)
    a.add_argument('-v', '--verbose', action='store_true',
                   help='selalu tampilkan daftar lengkap')
    a.set_defaults(fn=cmd_audit)

    s = sub.add_parser('suggest', help='usul baris [character] untuk speaker baru')
    s.add_argument('-c', '--csv', required=True)
    s.add_argument('-g', '--glossary', required=True)
    s.set_defaults(fn=cmd_suggest)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
