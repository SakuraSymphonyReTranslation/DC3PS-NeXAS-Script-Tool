# -*- coding: utf-8 -*-
"""
system_datu8_editor.py — Atur FONT SIZE UI di Config/system.datu8
Da Capo III Plus Story (NeXAS Switch, TID 010041601B544000).

ATURAN: tool ini HANYA mengubah nilai ukuran font/metrik piksel.
Nilai WARNA (FF FF FF 00 = putih, FF FF FF FF = none, 00 RR GG BB)
TIDAK pernah ditulis — ada guard khusus anti-warna di semua perintah tulis.

STRUKTUR FILE (reverse engineering):
  [0]     u32 jumlah entri (1142) — BUKAN ukuran file!
  [4]     1142 x u32 type flag
  lalu    string table (41 string: nama exe PC, URL — warisan versi PC)
  lalu    tabel referensi resource ('System.bin', 'FontColor.dat',
          'FontResource.dat', 'Interface.spm', ...)
  sisanya PARAMETER PER ELEMEN UI (message window, backlog, name plate,
          select, dst.): blok warna + metrik piksel.

  Angka kecil 0x12-0x3C (18-60 desimal) = KANDIDAT UKURAN FONT dalam piksel.
  Contoh di region 0x2600+: 33, 40, 21, 36, 39, 18, 40, 49, 21 ...
  (lihat kolom "Decoded text" di hex editor: '!', '(', '$', ''', ... —
  itu BUKAN teks, melainkan byte nilai piksel yang kebetulan printable)

NAMA ELEMEN (backlog/message/name/select) TIDAK TERSIMPAN di file — urutannya
mengikuti enum internal engine. Cara memetakan: ubah SATU nilai -> pasang patch
-> lihat elemen mana yang berubah di game -> catat di kolom "keterangan" CSV.

PERINTAH:
  info                     : ringkasan struktur file
  scan   [--csv out.csv]   : daftar kandidat font size (indeks stabil + CSV)
  apply  --csv map.csv     : terapkan kolom new_value dari CSV (anti-warna)
  set    --offset 0x263B --value 40
                           : ubah satu nilai (guard anti-warna + backup)
  diff                     : perubahan vs .bak
  restore                  : pulihkan dari .bak

CONTOH ALUR:
  1) python system_datu8_editor.py scan --csv scratch/fontsize_map.csv
  2) isi kolom new_value untuk SATU nilai dulu (mis. 40 -> 32), simpan CSV
  3) python system_datu8_editor.py apply --csv scratch/fontsize_map.csv
  4) pasang ke patch LayeredFS (Config/system.datu8), cek di game
  5) ulangi; labeli tiap baris di kolom keterangan: message/backlog/name/...
"""
import argparse
import csv
import os
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))


def default_input():
    env = os.environ.get('DC3PS_ROMFS') or os.environ.get('NEXAS_ROMFS')
    cands = []
    if env:
        cands.append(os.path.join(env, 'Config', 'system.datu8'))
    cands += [
        os.path.join(os.path.dirname(os.path.dirname(BASE)), 'romfs', 'Config', 'system.datu8'),
        os.path.join(os.path.dirname(BASE), 'romfs', 'Config', 'system.datu8'),
        os.path.join(BASE, 'romfs', 'Config', 'system.datu8'),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[-1]


def is_color_like(value):
    """True bila u32 menyerupai warna, BUKAN ukuran font."""
    b = value.to_bytes(4, 'little')
    if value == 0xFFFFFFFF:
        return True                       # FF FF FF FF (none/opaque)
    if b[0] == 0xFF and b[1] == 0xFF and b[2] == 0xFF:
        return True                       # FF FF FF xx (putih + alpha)
    if b[0] == 0x00 and (b[1] or b[2] or b[3]):
        return True                       # 00 RR GG BB (alpha 0 + RGB)
    return False


def read_u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def cmd_info(args):
    data = open(args.input, 'rb').read()
    count = read_u32(data, 0)
    types = [read_u32(data, 4 + 4 * i) for i in range(count)]
    print('File         : %s (%d byte)' % (args.input, len(data)))
    print('Jumlah entri : %d (type1=%d string, type2=%d angka)' % (
        count, types.count(1), types.count(2)))
    print('Region param : nilai kecil 18-60 di file = kandidat ukuran font piksel')
    print('Guard        : perintah tulis MENOLAK offset yang berisi warna')


def scan_candidates(data, vmin, vmax, start, end):
    """Kandidat font size: u32 bernilai kecil, BUKAN pola warna."""
    hits = []
    end = min(end, len(data) - 4)
    for a in range(start, end):
        v = read_u32(data, a)
        if vmin <= v <= vmax and not is_color_like(v):
            hits.append((a, v))
    # kelompokkan berdekatan (jarak <= 8 byte) = satu blok elemen
    groups = []
    for a, v in hits:
        if groups and a - groups[-1][-1][0] <= 8:
            groups[-1].append((a, v))
        else:
            groups.append([(a, v)])
    return hits, groups


def cmd_scan(args):
    data = open(args.input, 'rb').read()
    start = args.start if args.start is not None else 0x1532
    hits, groups = scan_candidates(data, args.min, args.max, start, args.end or len(data))
    print('File  : %s (%d byte)' % (args.input, len(data)))
    print('Scan  : 0x%X-0x%X, nilai %d..%d piksel (warna otomatis dikecualikan)'
          % (start, args.end or len(data), args.min, args.max))
    print()
    idx = 0
    rows = []
    for g in groups:
        items = ', '.join('0x%X:%d' % (a, v) for a, v in g)
        print('  blok @0x%06X : %s' % (g[0][0], items))
        for a, v in g:
            rows.append({'index': idx, 'offset_hex': '0x%06X' % a,
                         'current_value': v, 'new_value': '', 'keterangan': ''})
            idx += 1
    print()
    print('Total kandidat: %d dalam %d blok' % (len(hits), len(groups)))
    if args.csv:
        os.makedirs(os.path.dirname(os.path.abspath(args.csv)), exist_ok=True)
        with open(args.csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=[
                'index', 'offset_hex', 'current_value', 'new_value', 'keterangan'])
            w.writeheader()
            w.writerows(rows)
        print('[+] CSV peta -> %s' % args.csv)
        print('    Isi kolom "new_value" (kosong = tidak diubah) + label "keterangan".')


def cmd_apply(args):
    cur_path = args.input
    data = bytearray(open(cur_path, 'rb').read())
    changes = []
    with open(args.csv, 'r', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            nv = (r.get('new_value') or '').strip()
            if not nv:
                continue
            off = int(r['offset_hex'], 16)
            want = int(r['current_value'])
            new = int(nv, 0)
            if off + 4 > len(data):
                print('[LEWATI] 0x%X di luar file' % off)
                continue
            now = read_u32(data, off)
            if is_color_like(now):
                print('[WARNA]  0x%X berisi warna (0x%08X) — TIDAK diubah' % (off, now))
                continue
            if now != want:
                print('[LEWATI] 0x%X nilainya sudah berubah (%d != %d) — lewati'
                      % (off, now, want))
                continue
            changes.append((off, now, new))
    if not changes:
        print('Tidak ada perubahan valid di CSV.')
        return
    backup = cur_path + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(cur_path, backup)
        print('[i] Backup -> %s' % backup)
    for off, old, new in changes:
        struct.pack_into('<I', data, off, new)
        print('[OK] 0x%06X : %d -> %d' % (off, old, new))
    with open(args.output or cur_path, 'wb') as f:
        f.write(data)
    print('[+] %d perubahan font size ditulis (warna tidak tersentuh).' % len(changes))


def cmd_set(args):
    data = bytearray(open(args.input, 'rb').read())
    off = args.offset
    if off + 4 > len(data):
        sys.exit('offset di luar file')
    old = read_u32(data, off)
    if is_color_like(old) and not args.force:
        sys.exit('[DITOLAK] 0x%X berisi WARNA (0x%08X). Tool ini hanya mengubah '
                 'font size. (pakai --force jika benar-benar yakin)' % (off, old))
    backup = args.input + '.bak'
    if not os.path.exists(backup):
        shutil.copy2(args.input, backup)
        print('[i] Backup -> %s' % backup)
    struct.pack_into('<I', data, off, args.value)
    with open(args.output or args.input, 'wb') as f:
        f.write(data)
    print('[OK] 0x%06X : %d -> %d  (font size piksel)' % (off, old, args.value))


def cmd_diff(args):
    cur = open(args.input, 'rb').read()
    bak = open(args.input + '.bak', 'rb').read()
    if len(cur) != len(bak):
        print('UKURAN BEDA: %d vs %d' % (len(bak), len(cur)))
    diffs = [(i, bak[i], cur[i]) for i in range(min(len(cur), len(bak)))
             if cur[i] != bak[i]]
    if not diffs:
        print('Tidak ada perubahan vs .bak')
        return
    print('%d byte berubah vs .bak:' % len(diffs))
    for off, old, new in diffs:
        print('  0x%06X : %02X -> %02X' % (off, old, new))


def cmd_restore(args):
    backup = args.input + '.bak'
    if not os.path.exists(backup):
        sys.exit('Tidak ada backup: %s' % backup)
    shutil.copy2(backup, args.input)
    print('[OK] Dipulihkan dari %s' % backup)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', '-i', default=default_input(),
                    help='path system.datu8 (default: auto-deteksi)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    i = sub.add_parser('info', help='ringkasan struktur')
    i.set_defaults(fn=cmd_info)

    s = sub.add_parser('scan', help='scan kandidat font size + export CSV')
    s.add_argument('--min', type=int, default=12)
    s.add_argument('--max', type=int, default=72)
    s.add_argument('--start', type=lambda x: int(x, 0), default=None)
    s.add_argument('--end', type=lambda x: int(x, 0), default=None)
    s.add_argument('--csv', help='export CSV peta (index, offset, current, new, keterangan)')
    s.set_defaults(fn=cmd_scan)

    a = sub.add_parser('apply', help='terapkan new_value dari CSV scan (anti-warna)')
    a.add_argument('--csv', required=True)
    a.add_argument('--output', '-o', help='tulis ke file lain (default: timpa)')
    a.set_defaults(fn=cmd_apply)

    st = sub.add_parser('set', help='ubah satu nilai font size (guard anti-warna)')
    st.add_argument('--offset', type=lambda x: int(x, 0), required=True)
    st.add_argument('--value', type=lambda x: int(x, 0), required=True)
    st.add_argument('--output', '-o', help='tulis ke file lain (default: timpa)')
    st.add_argument('--force', action='store_true', help='paksa walau terlihat warna')
    st.set_defaults(fn=cmd_set)

    d = sub.add_parser('diff', help='perubahan vs .bak')
    d.set_defaults(fn=cmd_diff)

    r = sub.add_parser('restore', help='pulihkan dari .bak')
    r.set_defaults(fn=cmd_restore)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
