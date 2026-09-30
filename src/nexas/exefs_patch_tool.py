"""
exefs_patch_tool.py — Patcher Pesan Info UI Da Capo III Plus Story (area ExeFS / file `main`).

Apa ini?
  Beberapa teks UI (mis. pesan info pojok kiri-bawah: "QUICK 1番をロードしました"
  saat Quick Load/Quick Save/Jump) TIDAK tersimpan di romfs (.datu8/.spm/.png),
  melainkan tertanam di executable game (`main` di ExeFS). Tool ini mencarinya
  di dump ExeFS milikmu sendiri lalu menggantinya dengan terjemahan Indonesia
  DENGAN PANJANG BYTE SAMA (dipad spasi) agar offset tidak bergeser.

  File `main` dari ExeFS berformat **NSO (ter-kompresi LZ4)** — tool ini
  mendekompresinya OTOMATIS (murni python, tanpa dependensi), mem-patch
  string pada image hasil dekompresi, lalu menulis ulang NSO tanpa kompresi
  (flags dibersihkan) yang tetap valid dimuat emulator/Atmosphere.

  Daftar string & terjemahan dibaca dari CSV sehingga bisa DIEDIT MANUAL:
      scratch/exefs_messages.csv   (kolom: japanese_text, indonesian_translation, keterangan)

PENTING (kebijakan):
  - Dump ExeFS berisi kode berhak cipta. JANGAN pernah meng-upload file `main`
    (asli maupun hasil patch) ke GitHub / tempat publik. Folder dump & hasil
    patch sudah di-gitignore.
  - Hasil patch hanya untuk pemakaian pribadi di konsol/emulator milikmu.

Cara pakai:
  1) Dump ExeFS game sendiri (lihat README bagian "Dump ExeFS Manual")
     -- file yang dibutuhkan cukup `main` (NSO, boleh langsung dari exefs).
  2) Taruh di  scratch/exefs_dump/main
  3) Edit terjemahan manual di: scratch/exefs_messages.csv
  4) python exefs_patch_tool.py scan     # cari string dari CSV (auto-dekompresi NSO)
  5) python exefs_patch_tool.py apply    # terapkan -> scratch/exefs_patch/main
  6) Pasang hasil patch ke emulator (lihat output tool).
"""
import csv
import os
import re
import struct
import sys

try:
    import lz4.block as _lz4block  # pip install lz4 (disarankan)
except ImportError:
    _lz4block = None

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DUMP_DIR = os.path.join('scratch', 'exefs_dump')
OUT_DIR = os.path.join('scratch', 'exefs_patch')
CSV_PATH = os.path.join('scratch', 'exefs_messages.csv')

DEFAULT_ROWS = [
    ('番をロードしました', ' dimuat', 'QUICK 1番をロードしました -> QUICK 1 dimuat'),
    ('をロードしました', ' dimuat', 'pesan load umum'),
    ('番をロードしています', ' dimuat', 'varian sedang memuat slot'),
    ('をロードしています', ' dimuat', 'varian sedang memuat'),
    ('ロードしました', ' dimuat', 'potongan pendek fallback'),
    ('ロードしています', ' dimuat', 'potongan pendek varian'),
    ('番をセーブしました', ' disimpan', 'QUICK 1番をセーブしました -> QUICK 1 disimpan'),
    ('をセーブしました', ' disimpan', 'pesan save umum'),
    ('をセーブしています', ' disimpan', 'varian sedang menyimpan'),
    ('セーブしました', ' disimpan', 'potongan pendek fallback'),
    ('セーブしています', ' disimpan', 'potongan pendek varian'),
    ('オートセーブしました', ' auto-save', 'auto save selesai'),
    ('オートセーブしています', ' auto-save', 'sedang auto save'),
    ('の選択肢にジャンプしました', ' dilompati', 'lompat ke pilihan N selesai (13 huruf)'),
    ('選択肢にジャンプしました', ' dilompati', 'fallback tanpa の'),
    ('の選択肢へジャンプします', ' dilompati', 'varian へ + akan'),
    ('選択肢へジャンプします', ' dilompati', 'varian fallback'),
    ('にジャンプしました', ' lompat', 'fallback pendek'),
    ('ジャンプしました', ' lompat', 'fallback terpendek (MAX 8 huruf JP)'),
    ('クイックロードしました', ' quick load', 'quick load selesai (bila ada string penuh)'),
    ('クイックセーブしました', ' quick save', 'quick save selesai (bila ada string penuh)'),
    ('クイックロード', ' Quick Load', 'label quick load'),
    ('クイックセーブ', ' Quick Save', 'label quick save'),
    ('サスペンドしました', ' suspend disimpan', 'suspend/save-and-exit'),
    ('タイトルへ戻りました', ' kembali ke title', 'kembali ke judul'),
    ('デフォルトに戻しました', ' kembali ke default', 'reset pengaturan'),
    ('削除しました', ' dihapus', 'hapus data save'),
    ('移動しました', ' dipindah', 'pindah/tukar data save'),
    ('データがありません', ' tidak ada data', 'slot kosong'),
    ('を読み込みました', ' dimuat', 'varian formal memuat'),
]


def ensure_csv_at(path: str):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['japanese_text', 'indonesian_translation', 'keterangan'])
            for row in DEFAULT_ROWS:
                w.writerow(row)
        print('[i] CSV template dibuat: %s — EDIT FILE INI untuk terjemahan manual.' % path)


def ensure_csv():
    ensure_csv_at(CSV_PATH)


def _load_csv(csv_path: str):
    """Return list of (jp, idn, keterangan). Spasi terjemahan dipertahankan verbatim."""
    ensure_csv_at(csv_path)
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            jp = (r.get('japanese_text') or '').strip()
            idn = r.get('indonesian_translation') or ''
            ket = (r.get('keterangan') or '').strip()
            if jp:
                rows.append((jp, idn, ket))
    return rows


def load_csv():
    return _load_csv(CSV_PATH)


def _find_main(dump_dir: str):
    # Boleh berupa path FILE langsung (mis. hasil picker GUI) — jangan disalin
    # ke folder dump agar dump asli tidak pernah tertimpa hasil patch.
    if os.path.isfile(dump_dir):
        return dump_dir
    for name in ('main', 'main.bin', 'main.elf'):
        p = os.path.join(dump_dir, name)
        if os.path.exists(p):
            return p
    return None


def find_main():
    return _find_main(DUMP_DIR)


# ============================ NSO handling ============================

def lz4_block_decompress(src: bytes, dst_size: int) -> bytes:
    """Dekompresi blok LZ4: utama pakai library lz4 (teruji), fallback implementasi internal."""
    if _lz4block is not None:
        return _lz4block.decompress(src, uncompressed_size=dst_size)
    dst = bytearray()
    i, n = 0, len(src)
    while i < n and len(dst) < dst_size:
        token = src[i]
        i += 1
        lit_len = token >> 4
        if lit_len == 15:
            while True:
                b = src[i]
                i += 1
                lit_len += b
                if b != 255:
                    break
        dst += src[i:i + lit_len]
        i += lit_len
        if len(dst) >= dst_size:
            break
        if i + 2 > n:  # tidak ada match lagi (akhir blok)
            break
        offset = src[i] | (src[i + 1] << 8)
        i += 2
        match_len = token & 0xF
        if match_len == 15:
            while True:
                b = src[i]
                i += 1
                match_len += b
                if b != 255:
                    break
        match_len += 4
        start = len(dst) - offset
        if start < 0:
            raise ValueError('LZ4: offset match tidak valid')
        if match_len > dst_size - len(dst):
            match_len = dst_size - len(dst)
        # copy dengan slice (aman utk overlapping: sumber disalin dulu)
        dst += dst[start:start + match_len]
    if len(dst) != dst_size:
        raise ValueError('LZ4 (fallback internal): ukuran hasil %d != ekspektasi %d '
                         '(pasang paket "pip install lz4" untuk dekompresi yang andal)'
                         % (len(dst), dst_size))
    return bytes(dst)


def nso_parse(data: bytes):
    """Parse header NSO0 sesuai SwitchBrew:
      0x10/0x20/0x30 : FileOffset, MemoryOffset, Size(uncompressed) per segmen
      0x3C           : BssSize
      0x60/0x64/0x68 : compressed size per segmen
      0x0C           : flags (bit0-2 compress, bit3-5 hash-check)
    """
    if data[:4] != b'NSO0':
        raise ValueError('bukan NSO (magic %r)' % data[:4])
    flags = struct.unpack_from('<I', data, 0x0C)[0]
    segs = []
    # triple per segmen: @0x10 (.text), @0x20 (.ro), @0x30 (.data) — stride 0x10
    # (di antara triple ada gap utk ModuleNameOffset/Size @0x1C/0x2C)
    for si, name in enumerate(('.text', '.ro', '.data')):
        file_off, mem_off, size = struct.unpack_from('<III', data, 0x10 + 0x10 * si)
        comp_size = struct.unpack_from('<I', data, 0x60 + 4 * si)[0]
        compressed = bool(flags & (1 << si))
        segs.append({'name': name, 'file_off': file_off, 'mem_off': mem_off,
                     'size': size, 'comp_size': comp_size if compressed else size,
                     'compressed': compressed})
    bss_size = struct.unpack_from('<I', data, 0x3C)[0]
    return {'flags': flags, 'segs': segs, 'bss_size': bss_size}


def nso_decompress(data: bytes):
    """NSO -> image memori (segmen di MemoryOffset masing-masing + bss nol)."""
    info = nso_parse(data)
    total = max(s['mem_off'] + s['size'] for s in info['segs']) + info['bss_size']
    img = bytearray(total)
    for s in info['segs']:
        raw = data[s['file_off']:s['file_off'] + s['comp_size']]
        if s['compressed']:
            raw = lz4_block_decompress(raw, s['size'])
        img[s['mem_off']:s['mem_off'] + s['size']] = raw
    return bytes(img), info


def nso_build_uncompressed(img: bytes, info: dict) -> bytes:
    """Image memori -> NSO tanpa kompresi (flags=0: tak ada LZ4 & tak ada cek hash)."""
    hdr = bytearray(0x100)
    hdr[0:4] = b'NSO0'
    struct.pack_into('<I', hdr, 0x0C, 0)  # flags=0
    fo = 0x100
    for si, s in enumerate(info['segs']):
        mem_off, size = s['mem_off'], s['size']
        struct.pack_into('<III', hdr, 0x10 + 0x10 * si, fo, mem_off, size)
        struct.pack_into('<I', hdr, 0x60 + 4 * si, size)  # comp size = size (tak dipakai)
        if len(hdr) < fo:  # jaga-jaga (harusnya tidak terjadi, fo mulai 0x100)
            hdr.extend(b'\x00' * (fo - len(hdr)))
        hdr[fo:fo + size] = img[mem_off:mem_off + size]
        fo += size
        if fo % 0x10:
            fo += 0x10 - (fo % 0x10)
    struct.pack_into('<I', hdr, 0x3C, info['bss_size'])
    return bytes(hdr[:fo])


def load_main_image(dump_dir: str = None, log=print):
    """Baca dump main. Return (image, is_nso, info_or_None, path)."""
    path = _find_main(dump_dir or DUMP_DIR)
    if not path:
        return None, False, None, None
    data = open(path, 'rb').read()
    if data[:4] == b'NSO0':
        img, info = nso_decompress(data)
        return img, True, info, path
    return data, False, None, path


def scan_image(image: bytes, csv_path: str):
    """Scan string CSV pada image. Return list hit (dict)."""
    rows = _load_csv(csv_path)
    return find_hits(image, [(jp, idn) for jp, idn, _k in rows]), rows


def apply_to_image(image: bytes, csv_path: str, log=print):
    """Terapkan terjemahan CSV pada image (bytes). Return (image_baru, total, skipped)."""
    rows = [(jp, idn, k) for jp, idn, k in _load_csv(csv_path) if idn]
    if not rows:
        return bytes(image), 0, ['Tidak ada terjemahan di CSV: %s' % csv_path]
    data = bytearray(image)
    rows = sorted(rows, key=lambda r: len(r[0]), reverse=True)  # potongan panjang dulu
    total, skipped = 0, []
    for jp, idn, _k in rows:
        for enc in ('utf-8', 'shift_jis', 'utf-16-le'):
            nb = jp.encode(enc)
            count = 0
            while True:
                idx = bytes(data).find(nb)
                if idx < 0:
                    break
                try:
                    repl = pad_to_bytes(idn, len(nb), enc)
                except ValueError as e:
                    skipped.append(str(e))
                    break
                data[idx:idx + len(nb)] = repl
                count += 1
                total += 1
            if count:
                log('[OK] %r -> %r x%d [%s] (slot %d byte dipertahankan)'
                    % (jp, idn, count, enc, len(nb)))
    return bytes(data), total, skipped


# ============================ pencarian & patch ============================

def find_hits(data: bytes, terms):
    hits = []
    seen = set()
    for term, _idn in terms:
        for enc in ('utf-8', 'shift_jis', 'utf-16-le'):
            needle = term.encode(enc)
            start = 0
            while True:
                idx = data.find(needle, start)
                if idx < 0:
                    break
                ctx = data[max(0, idx - 40):idx + len(needle) + 60]
                key = (idx, enc)
                if key not in seen:
                    seen.add(key)
                    hits.append({'offset': idx, 'enc': enc, 'term': term, 'ctx': ctx})
                start = idx + 1
    return sorted(hits, key=lambda h: h['offset'])


def pad_to_bytes(text: str, nbytes: int, enc: str) -> bytes:
    b = text.encode(enc, errors='strict')
    if len(b) > nbytes:
        raise ValueError('terjemahan %d byte > asli %d byte (enc=%s): %r'
                         % (len(b), nbytes, enc, text))
    pad = b' \x00' if enc == 'utf-16-le' else b' '
    return b + pad * ((nbytes - len(b)) // len(pad))


# ============================ perintah ============================

# ============================ auto-discover pesan ============================

# Run karakter Jepang (kana/kanji/fullwidth/tanda baca UI) minimal 4 karakter
JP_RUN_RE = re.compile(r'[ぁ-んァ-ヶ一-鿿々ー「」『』（）：・０-９Ａ-Ｚａ-ｚ？！～＋]{4,}')
MSG_END_RE = re.compile(r'(しました|します|ました|ません|でした|ています|でいます|です)$')
MSG_KEYWORDS = ('ロード', 'セーブ', 'ジャンプ', 'オート', 'クイック', 'データ',
                'サスペンド', 'タイトル', 'デフォルト', '削除', '移動', '読み込')
GUIDE = (
    'PANDUAN ISI CSV (agar game TIDAK error):\n'
    ' 1. Kolom japanese_text JANGAN diubah/dipindah/dihapus — itu kunci pencarian persis di binary.\n'
    ' 2. Terjemahan maksimal SAMA PANJANG dengan japanese_text (tool menghitung byte otomatis).\n'
    '    Kalau kepanjangan: tool me-SKIP string itu (aman, tetap Jepang) dan melaporkannya.\n'
    ' 3. Tanpa Enter/newline/karakter kontrol di terjemahan — satu baris teks saja.\n'
    ' 4. Spasi di awal/akhir terjemahan disengaja (menempel ke nomor slot, mis. "QUICK 1 dimuat").\n'
    ' 5. Terjemahan KOSONG = string tidak diganti (100% aman).\n'
    ' 6. Simpan tetap sebagai CSV UTF-8 (Excel: Save As -> CSV UTF-8). Jangan ganti ekstensi.\n'
    ' 7. Jangan edit file main hasil patch dengan hex editor — ulangi apply dari CSV saja.\n'
    ' 8. Satu baris = satu pasangan; jangan merge/sort baris.\n'
    ' 9. Game crash setelah patch? Hapus main di folder exefs emulator -> kembali 100% asli\n'
    '    (patch ExeFS tidak menyentuh save data).')


def discover_messages(image: bytes):
    """Ekstrak kandidat string pesan info Jepang dari image (3 encoding).
    Return list string unik terurut (terpanjang dulu)."""
    seen = set()
    for enc in ('utf-8', 'shift_jis', 'utf-16-le'):
        try:
            text = image.decode(enc, errors='ignore')
        except (UnicodeDecodeError, LookupError):
            continue
        for m in JP_RUN_RE.finditer(text):
            s = m.group()
            if s in seen or len(s) > 48:
                continue
            seen.add(s)
    out = [s for s in seen
           if MSG_END_RE.search(s) or any(k in s for k in MSG_KEYWORDS)]
    return sorted(out, key=lambda s: (-len(s), s))


def discover_to_csv(dump_dir: str, csv_path: str, log=print) -> int:
    """Scan dump main, tambahkan kandidat pesan yang BELUM ada di CSV
    (terjemahan kosong = hanya dicari, tidak diganti). Return jumlah baris baru."""
    img, is_nso, info, path = load_main_image(dump_dir, log=log)
    if img is None:
        log('[Discover] Tidak ada dump main di %s — dump ExeFS dulu.' % dump_dir)
        return 0
    log('[Discover] Sumber: %s%s' % (path, ' [NSO ter-dekompresi]' if is_nso else ''))
    cands = discover_messages(img)
    existing = {jp for jp, _i, _k in _load_csv(csv_path)}
    new = [s for s in cands if s not in existing]
    if new:
        os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)
        with open(csv_path, 'a', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            for s in new:
                w.writerow([s, '', '(auto-discover) isi terjemahan — baca PANDUAN di exefs_messages_BACA_SAYA.txt'])
    log('[Discover] %d kandidat ditemukan, %d BARU ditambahkan ke %s'
        % (len(cands), len(new), csv_path))
    if new:
        log('[Discover] Isi kolom indonesian_translation di CSV (ikuti PANDUAN), lalu ExeFS Apply.')
    return len(new)


def write_guide(work_dir: str):
    os.makedirs(work_dir, exist_ok=True)
    p = os.path.join(work_dir, 'exefs_messages_BACA_SAYA.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(GUIDE + '\n')
    return p


def cmd_scan():
    img, is_nso, info, path = load_main_image()
    if img is None:
        print('[ERROR] Tidak menemukan %s/{main,main.bin,main.elf}' % DUMP_DIR)
        print('        Dump ExeFS game-mu dulu, lalu taruh file "main" di situ.')
        print('        (file biasanya puluhan MB; boleh langsung NSO dari exefs)')
        return 1
    rows = load_csv()
    print('File   : %s (%.1f MB)%s' % (path, os.path.getsize(path) / 1048576,
                                        '  [NSO ter-dekompresi otomatis]' if is_nso else ''))
    if is_nso:
        for s in info['segs']:
            print('   seg %-6s mem=0x%X size=0x%X %s' % (s['name'], s['mem_off'], s['size'],
                                                         '(lz4)' if s['compressed'] else ''))
    print('CSV    : %s (%d entri)' % (CSV_PATH, len(rows)))
    hits = find_hits(img, [(jp, idn) for jp, idn, _k in rows])
    if not hits:
        print('[TIDAK KETEMU] Tidak ada string dari CSV di dump ini.')
        print('  Kemungkinan: versi game berbeda / susunan huruf lain / pesan memang tidak ada.')
        return 1
    print('Ditemukan %d lokasi (offset pada image ter-dekompresi):\n' % len(hits))
    for h in hits:
        tr = next((i for jp, i, _k in rows if jp == h['term']), '')
        status = 'TERJEMAHAN: %r' % tr if tr else '(terjemahan kosong — isi CSV dulu)'
        print('  offset 0x%08X [%s] kunci=%r  %s' % (h['offset'], h['enc'], h['term'], status))
        print('      ctx: %r' % h['ctx'])
    print()
    print('Edit terjemahan di CSV: %s' % CSV_PATH)
    print('Lalu jalankan: python exefs_patch_tool.py apply')
    return 0


def patch_dump(dump_dir: str, csv_path: str, out_dir: str, log=print) -> dict:
    """API programatik utk GUI/builder: scan+apply dump main di dump_dir.
    Return {'ok', 'total', 'skipped', 'out', 'reason'}."""
    img, is_nso, info, path = load_main_image(dump_dir, log=log)
    if img is None:
        log('[LEWATI] Tidak ada dump main di %s (dump ExeFS dulu bila mau menerjemahkan'
            ' pesan info)' % dump_dir)
        return {'ok': False, 'total': 0, 'skipped': [], 'out': None, 'reason': 'no-dump'}
    log('[ExeFS] Sumber : %s (%.1f MB)%s' % (path, os.path.getsize(path) / 1048576,
                                             ' [NSO]' if is_nso else ''))
    new_img, total, skipped = apply_to_image(img, csv_path, log=log)
    if not total:
        for s in sorted(set(skipped)):
            log('[SKIP]', s)
        return {'ok': False, 'total': 0, 'skipped': skipped, 'out': None,
                'reason': 'no-match (jalankan scan dulu / isi CSV)'}
    for s in sorted(set(skipped)):
        log('[SKIP]', s)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'main')
    if is_nso:
        open(out, 'wb').write(nso_build_uncompressed(new_img, info))
        log('[ExeFS] NSO ditulis ulang tanpa kompresi (flags dibersihkan).')
    else:
        open(out, 'wb').write(new_img)
    log('[ExeFS] SELESAI: %d penggantian -> %s' % (total, out))
    return {'ok': True, 'total': total, 'skipped': skipped, 'out': out, 'reason': None}


def cmd_apply():
    res = patch_dump(DUMP_DIR, CSV_PATH, OUT_DIR)
    if not res['ok']:
        return 1
    gp = write_guide(os.path.dirname(CSV_PATH) or '.')
    print('PANDUAN isi CSV: %s' % gp)
    print()
    print('CARA PASANG (pilih salah satu):')
    print('  Eden/emulator : salin sebagai %APPDATA%\\eden\\exefs\\010041601B544000\\main')
    print('  Ryujinx       : Options -> Manage Mods -> ExeFS -> pilih file main ini')
    print('  Atmosphere    : atmosphere/exefs/010041601B544000/main')
    print()
    print('INGAT: file main hasil patch = kode berhak cipta. JANGAN dibagikan/upload.')
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'scan'
    ensure_csv()
    if cmd == 'scan':
        sys.exit(cmd_scan())
    elif cmd == 'apply':
        sys.exit(cmd_apply())
    elif cmd == 'csv':
        print('CSV terjemahan: %s' % CSV_PATH)
        print('(buka & edit kolom indonesian_translation secara manual)')
        sys.exit(0)
    elif cmd == 'discover':
        write_guide(os.path.dirname(CSV_PATH) or '.')
        n = discover_to_csv(DUMP_DIR, CSV_PATH)
        print('PANDUAN isi CSV: %s' % os.path.join(os.path.dirname(CSV_PATH) or '.',
                                                  'exefs_messages_BACA_SAYA.txt'))
        sys.exit(0 if n >= 0 else 1)
    else:
        print(__doc__)
        sys.exit(1)


def cmd_apply():
    res = patch_dump(DUMP_DIR, CSV_PATH, OUT_DIR)
    if not res['ok']:
        return 1
    print()
    print('CARA PASANG (pilih salah satu):')
    print('  Eden/emulator : salin sebagai %APPDATA%\\eden\\exefs\\010041601B544000\\main')
    print('  Ryujinx       : Options -> Manage Mods -> ExeFS -> pilih file main ini')
    print('  Atmosphere    : atmosphere/exefs/010041601B544000/main')
    print()
    print('INGAT: file main hasil patch = kode berhak cipta. JANGAN dibagikan/upload.')
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'scan'
    ensure_csv()
    if cmd == 'scan':
        sys.exit(cmd_scan())
    elif cmd == 'apply':
        sys.exit(cmd_apply())
    elif cmd == 'csv':
        print('CSV terjemahan: %s' % CSV_PATH)
        print('(buka & edit kolom indonesian_translation secara manual)')
        sys.exit(0)
    elif cmd == 'discover':
        sys.exit(0 if discover_to_csv(DUMP_DIR, CSV_PATH) or True else 1)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
