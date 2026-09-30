"""
ui_translation_tool.py — Extract & pack terjemahan UI Da Capo III Plus Story
(NeXAS Switch, TID 010041601B544000).

Perintah:
  extract                  Dump semua string JP dari System/*.spm + Config/*.datu8 ke CSV
  apply-config <csv...>    Terapkan terjemahan CSV -> Config/*.datu8 ke folder patch
  apply-spm <csv>          Terapkan terjemahan CSV -> System/*.spm ke folder patch
  audit-png                Audit PNG System yang diduga ber-teks Jepang (CSV + galeri HTML)
  export-png               Salin PNG kandidat ke png_work/src/ untuk diedit (Photoshop dll)
  pack-png                 Validasi & salin PNG hasil edit (png_work/edited/) ke folder patch

Tool ini self-contained (stdlib saja; Pillow hanya opsional untuk audit PNG).
Catatan DC3PS: Config/system.datu8 adalah konfigurasi font khusus (bukan tabel
datu8 standar) dan otomatis dilewati.
"""
import argparse
import csv
import glob
import html
import os
import re
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Root repo = dua tingkat di atas file ini (src/nexas/ -> src/ -> root).
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Path RomFS game DC3PS: override lewat env DC3PS_ROMFS / NEXAS_ROMFS.
# Default: folder romfs di samping repo tool ini (layout dump Eden:
# <dump>/<TID>/romfs + <dump>/<TID>/tools/DC3PS-NeXAS-Script-Tool),
# fallback ke folder romfs/ di dalam repo bila ada.
_romfs_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(BASE)), 'romfs'),  # ../../romfs (layout dump: <TID>/tools/<repo> -> <TID>/romfs)
    os.path.join(os.path.dirname(BASE), 'romfs'),   # ../romfs dari repo tool
    os.path.join(BASE, 'romfs'),                    # romfs/ di dalam repo
]
ROMFS = os.environ.get('DC3PS_ROMFS') or os.environ.get('NEXAS_ROMFS') \
    or next((p for p in _romfs_candidates if os.path.isdir(p)), _romfs_candidates[1])
SPM_DIR = os.path.join(ROMFS, 'System')
CFG_DIR = os.path.join(ROMFS, 'Config')
OUT_DIR = os.path.join(BASE, 'scratch')
DEFAULT_OUT_PATCH = os.path.join(BASE, 'DC3PS_Indo_Patch')
PNG_WORK = os.path.join(BASE, 'png_work')

# File Config DC3PS yang formatnya BUKAN tabel datu8 standar.
# system.datu8 DC3PS = konfigurasi font (header pertama 1142, bukan jumlah
# kolom) — memaksa parser tabel gagal/menggantung, jadi selalu dilewati.
NON_DATU8_FILES = {'system.datu8'}

CONFIG_FILES = [
    'button.datu8', 'buttonex.datu8', 'eventtype.datu8', 'keycommand.datu8',
    'event.datu8', 'cgmode.datu8', 'replaymode.datu8', 'scene.datu8',
    'char.datu8', 'trophy.datu8', 'bgm.datu8', 'musicmode.datu8',
]

def is_japanese(text: str) -> bool:
    return bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', text))

# ============================================================ datu8 (Config)
DATU8_TYPE_SIZES = {2: 4, 3: 1, 5: 2, 4: 8}  # 1/6 = string (int32 len + bytes)

def datu8_parse(data: bytes):
    """Return (types, rows); setiap sel = bytes mentah (string belum didekode).

    Dengan sanity-check agar file yang BUKAN tabel datu8 (mis. system.datu8
    DC3PS yang merupakan konfigurasi font) langsung gagal cepat, dan agar
    ukuran string negatif tidak membuat offset mundur (infinite loop).
    """
    cnt, = struct.unpack_from('<i', data, 0)
    if cnt <= 0 or cnt > 1024:
        raise ValueError('bukan tabel datu8 standar (jumlah kolom = %d)' % cnt)
    types = list(struct.unpack_from('<%di' % cnt, data, 4))
    off = 4 + 4 * cnt
    rows = []
    while off < len(data):
        row = []
        for t in types:
            if t in (1, 6):
                if off + 4 > len(data):
                    raise ValueError('string header terpotong di offset %d' % off)
                sz, = struct.unpack_from('<i', data, off); off += 4
                if sz < 0 or off + sz > len(data):
                    raise ValueError('ukuran string tidak valid (%d) di offset %d' % (sz, off - 4))
                row.append(data[off:off + sz]); off += sz
            elif t in DATU8_TYPE_SIZES:
                n = DATU8_TYPE_SIZES[t]
                if off + n > len(data):
                    raise ValueError('sel terpotong di offset %d' % off)
                row.append(data[off:off + n]); off += n
            else:
                raise ValueError('tipe elemen tidak dikenal %d di offset %d' % (t, off))
        rows.append(row)
    return types, rows

def datu8_build(types, rows) -> bytes:
    out = struct.pack('<i', len(types))
    out += struct.pack('<%di' % len(types), *types)
    for row in rows:
        for t, v in zip(types, row):
            if t in (1, 6):
                out += struct.pack('<i', len(v)) + v
            else:
                out += v
    return out

def split_string_bytes(raw: bytes):
    """String datu8 = utf8 + NUL (+ sisa byte apa pun setelah NUL pertama)."""
    i = raw.find(b'\x00')
    if i < 0:
        return raw, b''
    return raw[:i], raw[i + 1:]

def apply_config_csv(csv_paths, out_patch: str, dry_run: bool = False):
    by_file = {}  # filename -> {(row, col): translation}
    total = 0
    for path in csv_paths:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                trans = (r.get('indonesian_translation') or '').strip()
                if not trans:
                    continue
                fn = (r.get('file') or '').strip()
                if not fn or '/' in fn or '\\' in fn or '..' in fn:
                    print('[LEWATI] baris dengan file tidak valid: %r' % fn)
                    continue
                try:
                    key = (int(r['row_index']), int(r['column']))
                except (KeyError, ValueError):
                    print('[LEWATI] baris tanpa row_index/column valid: %r' % (r,))
                    continue
                by_file.setdefault(fn, {})[key] = trans
                total += 1
    if not by_file:
        print('Tidak ada terjemahan di CSV. Isi kolom indonesian_translation dulu.')
        return

    ok_files = 0
    for fn, edits in sorted(by_file.items()):
        if fn in NON_DATU8_FILES:
            print('[LEWATI] %s: format font khusus DC3PS (bukan tabel datu8 standar)' % fn)
            continue
        src = os.path.join(CFG_DIR, fn)
        if not os.path.exists(src):
            print('[LEWATI] %s tidak ada di %s' % (fn, CFG_DIR))
            continue
        data = open(src, 'rb').read()
        types, rows = datu8_parse(data)
        applied, missing = 0, []
        for (ri, ci), trans in sorted(edits.items()):
            if not (0 <= ri < len(rows) and 0 <= ci < len(types)):
                missing.append((ri, ci))
                continue
            if types[ci] not in (1, 6):
                missing.append((ri, ci))
                continue
            body, suffix = split_string_bytes(rows[ri][ci])
            if not dry_run:
                rows[ri][ci] = trans.encode('utf-8') + b'\x00' + suffix
            applied += 1
        if missing:
            print('[PERINGATAN] %s: %d sel di luar jangkauan: %s'
                  % (fn, len(missing), missing[:8]))
        if dry_run:
            print('[DRY] %s: %d sel akan diganti' % (fn, applied))
            continue
        blob = datu8_build(types, rows)
        # verifikasi struktural: jumlah baris/kolom & sel tak tersentuh tetap sama
        otypes, orows = datu8_parse(data)
        ntypes, nrows = datu8_parse(blob)
        assert otypes == ntypes and len(orows) == len(nrows), 'struktur berubah!'
        for ri, (ro, rn) in enumerate(zip(orows, nrows)):
            for ci in range(len(otypes)):
                if (ri, ci) not in edits and ro[ci] != rn[ci]:
                    raise AssertionError('sel (%d,%d) %s berubah tanpa sengaja' % (ri, ci, fn))
        dst = os.path.join(out_patch, 'romfs', 'Config', fn)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(blob)
        print('[OK] %s: %d/%d string diterjemahkan (ukuran %d -> %d byte)'
              % (fn, applied, len(edits), len(data), len(blob)))
        ok_files += 1
    if not dry_run:
        print('Selesai: %d file .datu8 ditulis ke %s' % (ok_files, os.path.join(out_patch, 'romfs', 'Config')))

# ============================================================ SPM (System)
UTF8_RUN = re.compile(
    rb'(?:[\x20-\x7e]'
    rb'|(?:\xe3[\x80-\x83][\x80-\xbf])'
    rb'|(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf])'
    rb'|(?:\xef[\xbc-\xbf][\x80-\xbf]))+'
)
SJIS_RUN = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+')

def spm_detect_utf8(data: bytes) -> bool:
    for m in UTF8_RUN.finditer(data):
        try:
            if is_japanese(m.group().decode('utf-8')):
                return True
        except UnicodeDecodeError:
            pass
    return False

def spm_replace_all(data: bytes, mapping: dict, encoding: str):
    """Ganti string di semua run; return (blob, replaced_count)."""
    run_re = UTF8_RUN if encoding == 'utf-8' else SJIS_RUN
    out, last, count = [], 0, 0
    for m in run_re.finditer(data):
        try:
            text = m.group().decode(encoding)
        except UnicodeDecodeError:
            continue
        if text in mapping:
            out.append(data[last:m.start()])
            out.append(mapping[text].encode(encoding))
            last = m.end()
            count += 1
    out.append(data[last:])
    return b''.join(out), count

def apply_spm_csv(csv_path: str, out_patch: str, dry_run: bool = False):
    mapping = {}
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            jp = (r.get('japanese_text') or '').strip()
            tr = (r.get('indonesian_translation') or '').strip()
            if jp and tr:
                mapping[jp] = tr
    if not mapping:
        print('Tidak ada terjemahan di CSV:', csv_path)
        return

    stats = {'same': 0, 'sjis': 0, 'skip': 0, 'nf': 0}
    files = sorted(glob.glob(os.path.join(SPM_DIR, '*.spm')))
    for fn in files:
        data = open(fn, 'rb').read()
        utf8 = spm_detect_utf8(data)
        enc = 'utf-8' if utf8 else 'shift_jis'
        blob, count = spm_replace_all(data, mapping, enc)
        if count:
            rel = os.path.basename(fn)
            if dry_run:
                print('[DRY] %s: %d kemunculan akan diganti (encoding %s)' % (rel, count, enc))
            else:
                dst = os.path.join(out_patch, 'romfs', 'System', rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as f:
                    f.write(blob)
                print('[OK] %s: %d kemunculan diganti (encoding %s, %d -> %d byte)'
                      % (rel, count, enc, len(data), len(blob)))
        # statistik string yang tak tertangani
        for jp in mapping:
            if jp.encode('utf-8') in data or (not utf8 and jp.encode('shift_jis', errors='ignore') in data):
                new = mapping[jp]
                if len(new.encode('utf-8')) == len(jp.encode('utf-8')):
                    stats['same'] += 1
                elif utf8:
                    try:
                        new.encode('shift_jis')
                        stats['sjis'] += 1
                    except UnicodeEncodeError:
                        stats['skip'] += 1
                else:
                    stats['same'] += 1
    if dry_run:
        print('[DRY] selesai (tidak ada file ditulis)')
    else:
        print('Selesai. Catatan panjang string: sama=%d, fallback Shift_JIS=%d, '
              'tak bisa dikonversi (perlu editor SPM manual)=%d'
              % (stats['same'], stats['sjis'], stats['skip']))

# ============================================================ audit PNG
PNG_SIG = b'\x89PNG\r\n\x1a\n'
PNG_CT_NAME = {0: 'grayscale', 2: 'RGB', 3: 'palet (P)', 4: 'grayscale+alpha', 6: 'RGBA'}
PNG_CT_MODE = {0: 'L', 2: 'RGB', 4: 'LA', 6: 'RGBA'}

def png_ihdr(path: str) -> dict:
    """Baca IHDR (+ keberadaan PLTE/tRNS) langsung dari byte PNG."""
    with open(path, 'rb') as f:
        head = f.read(33)
    if not head.startswith(PNG_SIG):
        raise ValueError('bukan file PNG: %s' % path)
    w, h = struct.unpack_from('>II', head, 16)
    bitdepth, colortype = head[24], head[25]
    interlace = head[28]
    # scan chunk names untuk PLTE/tRNS
    plte = trns = False
    with open(path, 'rb') as f:
        f.seek(8)
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            ln, = struct.unpack('>I', hdr[:4])
            ctype = hdr[4:8]
            if ctype == b'PLTE':
                plte = True
            elif ctype == b'tRNS':
                trns = True
            f.seek(ln + 4, 1)  # lewati data + CRC
            if ctype == b'IEND':
                break
    return {'w': w, 'h': h, 'bitdepth': bitdepth, 'colortype': colortype,
            'interlace': interlace, 'plte': plte, 'trns': trns}

def png_convert_to_match(img, want: dict):
    """Konversi gambar hasil edit agar kompatibel dengan IHDR file asli.
    Return (img_siap_simpan, catatan)."""
    notes = []
    ct, bd = want['colortype'], want['bitdepth']
    if img.mode == 'P':
        img = img.convert('RGBA')  # buka palet sebagai RGBA agar alpha tak hilang
    if ct == 6:
        out = img.convert('RGBA')
    elif ct == 2:
        out = img.convert('RGB')
        if img.mode in ('RGBA', 'LA', 'P'):
            notes.append('alpha dibuang (asli RGB tanpa alpha)')
    elif ct == 4:
        out = img.convert('LA')
    elif ct == 0:
        out = img.convert('1' if bd == 1 else 'L')
    elif ct == 3:
        maxc = 2 ** bd
        method = __import__('PIL.Image', fromlist=['Image']).Quantize.FASTOCTREE
        out = img.quantize(colors=maxc, method=method, dither=__import__('PIL.Image', fromlist=['Image']).Dither.NONE)
        notes.append('dikuantisasi ke <=%d warna (palet baru, PLTE ikut tertanam)' % maxc)
    else:
        raise ValueError('color type PNG asli tidak didukung: %d' % ct)
    if want['interlace']:
        notes.append('PERINGATAN: asli interlaced; hasil disimpan non-interlaced (tetap PNG valid)')
    if bd not in (8, 1) or (ct == 3 and bd != 8):
        notes.append('PERINGATAN: bit depth asli %d; hasil 8-bit (umumnya masih kompatibel)' % bd)
    return out, notes

EXCLUDE_PNG_RE = re.compile(
    r'^(boka|alice|asatosu|sakuya|mura|koto|nenene|yuzu|aru|beni|sara|charsoundface'
    r'|chatface|face|stand|bg\d|ef|wind|rain|snow|light|smoke|kira)',
    re.I)
TEXT_HINT_RE = re.compile(
    r'(caption|title|bgmname|bgmtitle|caution|help|tooltip|menu|label|save|load'
    r'|config|tab|extrainfo|eventname|charaname|messagewindow|systembar|name)', re.I)
STATE_SUFFIX_RE = re.compile(r'_(ov|on|off|over|l|s|u|d|a|b)$', re.I)

def png_candidates():
    """Daftar PNG System yang diduga mengandung teks UI (heuristik nama file)."""
    out = []
    try:
        from PIL import Image
        has_pil = True
    except ImportError:
        has_pil = False
    for path in sorted(glob.glob(os.path.join(SPM_DIR, '*.png'))):
        name = os.path.basename(path)
        stem = os.path.splitext(name)[0]
        core = STATE_SUFFIX_RE.sub('', stem)
        reasons, priority = [], None
        if EXCLUDE_PNG_RE.search(stem):
            continue
        if TEXT_HINT_RE.search(core):
            reasons.append('nama mengandung kata teks-UI')
            priority = 'tinggi'
        if re.search(r'\d', core):
            reasons.append('bernomor (kemungkinan set label)')
            priority = priority or 'sedang'
        if re.search(r'_(ov|on|off|over)$', stem, re.I):
            reasons.append('varian state tombol (_on/_off/_ov)')
            priority = priority or 'sedang'
        if not reasons:
            continue
        w = h = 0
        if has_pil:
            try:
                with Image.open(path) as im:
                    w, h = im.size
            except Exception:
                w = h = -1
        out.append({'path': path, 'name': name, 'w': w, 'h': h,
                    'reasons': '; '.join(reasons), 'priority': priority})
    return out

def audit_png(out_dir: str):
    cands = png_candidates()
    csv_path = os.path.join(out_dir, 'png_text_audit.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['include', 'file', 'width', 'height', 'priority', 'reasons'])
        for c in cands:
            w.writerow([1, c['name'], c['w'], c['h'], c['priority'], c['reasons']])
    print('[OK] %d kandidat PNG ber-teks -> %s' % (len(cands), csv_path))

    html_path = os.path.join(out_dir, 'png_text_audit.html')
    rows = []
    for i, c in enumerate(cands):
        rel = os.path.relpath(c['path'], out_dir).replace('\\', '/')
        rows.append(
            '<tr><td>%d</td><td><code>%s</code></td><td>%s</td><td>%dx%s</td>'
            '<td>%s</td><td><img src="%s" style="max-width:260px;max-height:80px;'
            'image-rendering:pixelated;background:#333"></td></tr>'
            % (i + 1, html.escape(c['name']), html.escape(c['priority']),
               c['w'], c['h'], html.escape(c['reasons']), html.escape(rel)))
    doc = ('<!doctype html><html><head><meta charset="utf-8"><title>Audit PNG Teks UI'
           ' Da Capo III Plus Story</title><style>body{font-family:system-ui;background:#111;color:#eee}'
           'table{border-collapse:collapse}td,th{border:1px solid #444;padding:4px 8px}'
           '</style></head><body><h1>Kandidat PNG ber-teks Jepang (%d file)</h1>'
           '<p>Buka file ini dari folder scratch agar gambar tampil. Edit PNG yang '
           'perlu diterjemahkan, lalu jalankan export-png / pack-png.</p>'
           '<table><tr><th>#</th><th>File</th><th>Prioritas</th><th>Ukuran</th>'
           '<th>Alasan</th><th>Pratinjau</th></tr>%s</table></body></html>'
           % (len(cands), '\n'.join(rows)))
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print('[OK] galeri review -> %s' % html_path)

def export_png(work_dir: str):
    cands = png_candidates()
    src_dir = os.path.join(work_dir, 'src')
    os.makedirs(src_dir, exist_ok=True)
    ok = fail = 0
    for c in cands:
        dst = os.path.join(src_dir, c['name'])
        try:
            if os.path.exists(dst):
                os.remove(dst)  # buang dulu: menimpa file yang terbuka di Photoshop/viewer bisa errno 22
        except OSError:
            pass
        try:
            # copyfile (bukan copy2): timestamp dump ROM sering tidak valid & tak diperlukan
            shutil.copyfile(c['path'], dst)
            ok += 1
        except OSError as e:
            fail += 1
            print('[GAGAL] %s: %s' % (c['name'], e))
            print('        -> Tutup aplikasi yang membuka file ini (Photoshop/viewer) lalu ulangi Export PNG.')
    print('[OK] %d PNG diekspor ke %s' % (ok, src_dir))
    if fail:
        print('[!] %d PNG gagal diekspor (file terkunci program lain?)' % fail)
    guide = os.path.join(work_dir, 'BACA_SAYA.txt')
    with open(guide, 'w', encoding='utf-8') as f:
        f.write(
            'CARA KERJA EDIT PNG UI (Photoshop / GIMP / Aseprite):\n'
            '1. Semua PNG asli ada di: png_work/src/\n'
            '2. Salin PNG yang mau diterjemahkan ke: png_work/edited/ (nama file sama)\n'
            '3. Edit gambarnya: ganti teks Jepang dengan Bahasa Indonesia.\n'
            '   - JANGAN ubah ukuran kanvas (dimensi harus sama persis).\n'
            '   - Format simpan bebas (RGB / RGBA / indexed / 16-bit semua boleh):\n'
            '     pack-png otomatis menganalisa format PNG asli (color type, bit depth,\n'
            '     palet, transparansi) dan MENGKONVERSI hasil edit agar kompatibel\n'
            '     dengan file UI yang dituju.\n'
            '4. Jalankan:  python ui_translation_tool.py pack-png\n'
            '   -> file tervalidasi/dikonversi disalin ke folder patch (romfs/System/).\n\n'
            'Kandidat + alasan: scratch/png_text_audit.csv / png_text_audit.html\n')
    if fail:
        print('[!] %d PNG gagal diekspor (file terkunci program lain?)' % fail)
    print('     Panduan: %s' % guide)

def pack_png_to_patch(edited_dir: str, out_patch: str, log=print) -> dict:
    """Kemas PNG hasil edit (edited_dir) ke out_patch/romfs/System dengan analisa
    IHDR asli + konversi format otomatis. Return statistik {'packed','converted','skipped','errors'}."""
    result = {'packed': 0, 'converted': 0, 'skipped': 0, 'errors': []}
    try:
        from PIL import Image
    except ImportError:
        log('Pillow belum terpasang (pip install pillow) — dibutuhkan konversi/validasi.')
        result['errors'].append('Pillow tidak terpasang')
        return result
    for path in sorted(glob.glob(os.path.join(edited_dir, '*.png'))):
        name = os.path.basename(path)
        orig = os.path.join(SPM_DIR, name)
        if not os.path.exists(orig):
            log('[LEWATI] %s bukan file System yang dikenal' % name)
            result['skipped'] += 1
            continue
        try:
            want = png_ihdr(orig)
            got = png_ihdr(path)
        except ValueError as e:
            log('[LEWATI] %s' % e)
            result['skipped'] += 1
            continue
        if (got['w'], got['h']) != (want['w'], want['h']):
            log('[LEWATI] %s: dimensi %dx%d != asli %dx%d — kanvas harus sama persis'
                % (name, got['w'], got['h'], want['w'], want['h']))
            result['skipped'] += 1
            continue
        if open(path, 'rb').read() == open(orig, 'rb').read():
            log('[LEWATI] %s: identik dengan asli (belum diedit?)' % name)
            result['skipped'] += 1
            continue
        if (got['bitdepth'], got['colortype'], got['trns']) == \
           (want['bitdepth'], want['colortype'], want['trns']):
            final, notes = None, []          # format sudah sama, simpan apa adanya
        else:
            with Image.open(path) as im:
                final, notes = png_convert_to_match(im.convert('RGBA')
                                                    if im.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P')
                                                    else im, want)
        dst = os.path.join(out_patch, 'romfs', 'System', name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if final is None:
            shutil.copy2(path, dst)
        else:
            final.save(dst, 'PNG')
            # verifikasi IHDR hasil konversi
            check = png_ihdr(dst)
            if (check['w'], check['h'], check['colortype']) != (want['w'], want['h'], want['colortype']):
                log('[GAGAL] %s: konversi tidak menghasilkan format target '
                    '(dapat ct=%d, inginkan ct=%d)' % (name, check['colortype'], want['colortype']))
                os.remove(dst)
                result['skipped'] += 1
                result['errors'].append('konversi gagal: %s' % name)
                continue
            result['converted'] += 1
        detail = (' | '.join(notes)) if notes else ''
        log('[OK] %s (%dx%d %s)%s' % (name, want['w'], want['h'],
              PNG_CT_NAME[want['colortype']], (' [' + detail + ']') if detail else ''))
        result['packed'] += 1
    log('Selesai PNG: %d dikemas (%d dikonversi otomatis), %d dilewati.'
        % (result['packed'], result['converted'], result['skipped']))
    return result

def pack_png(work_dir: str, out_patch: str):
    src_dir = os.path.join(work_dir, 'src')
    edited_dir = os.path.join(work_dir, 'edited')
    if not os.path.isdir(src_dir):
        print('Folder %s tidak ada. Jalankan export-png dulu.' % src_dir)
        return
    if not os.path.isdir(edited_dir):
        os.makedirs(edited_dir, exist_ok=True)
        print('Folder %s dibuat. Isi dulu dengan hasil edit, lalu jalankan lagi.' % edited_dir)
        return
    pack_png_to_patch(edited_dir, out_patch)

# ============================================================ extract
def extract_all(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    # 1) SPM: string unik
    spm_strings = {}
    for fn in sorted(glob.glob(os.path.join(SPM_DIR, '*.spm'))):
        data = open(fn, 'rb').read()
        utf8 = spm_detect_utf8(data)
        run_re = UTF8_RUN if utf8 else SJIS_RUN
        enc = 'utf-8' if utf8 else 'shift_jis'
        for m in run_re.finditer(data):
            try:
                t = m.group().decode(enc)
            except UnicodeDecodeError:
                continue
            if is_japanese(t) and len(t) >= 2:
                spm_strings.setdefault(t, set()).add(os.path.basename(fn))
    out1 = os.path.join(out_dir, 'ui_strings_spm.csv')
    with open(out1, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['japanese_text', 'files', 'indonesian_translation'])
        for t in sorted(spm_strings, key=lambda s: (sorted(spm_strings[s]), s)):
            w.writerow([t, ' '.join(sorted(spm_strings[t])), ''])
    print('[SPM]     %d string unik -> %s' % (len(spm_strings), out1))

    # 2) Config datu8: per file/row/col
    out2 = os.path.join(out_dir, 'ui_strings_config.csv')
    n = 0
    with open(out2, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['file', 'row_index', 'column', 'japanese_text', 'indonesian_translation'])
        for path in sorted(glob.glob(os.path.join(CFG_DIR, '*.datu8'))):
            name = os.path.basename(path)
            if name in NON_DATU8_FILES:
                print('[LEWATI] %s: bukan tabel datu8 standar (font config khusus DC3PS)' % name)
                continue
            try:
                types, rows = datu8_parse(open(path, 'rb').read())
            except (ValueError, struct.error) as e:
                print('[LEWATI] %s: %s' % (name, e))
                continue
            for i, row in enumerate(rows):
                for col, t in enumerate(types):
                    if t not in (1, 6):
                        continue
                    body, _ = split_string_bytes(row[col])
                    try:
                        s = body.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                    if is_japanese(s) and s.strip():
                        w.writerow([name, i, col, s, ''])
                        n += 1
    print('[Config]  %d string -> %s' % (n, out2))

# ============================================================ main
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out-patch', default=DEFAULT_OUT_PATCH,
                   help='folder patch tujuan (default: DC3PS_Indo_Patch)')
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('extract', help='dump string JP SPM + Config ke CSV')
    pe = sub.add_parser('export-png', help='ekspor PNG kandidat ke png_work/src')
    pe.add_argument('--work-dir', default=PNG_WORK)
    pa = sub.add_parser('audit-png', help='audit PNG ber-teks Jepang')
    pa.add_argument('--out-dir', default=OUT_DIR)
    pc = sub.add_parser('apply-config', help='terapkan CSV terjemahan ke datu8')
    pc.add_argument('csv', nargs='+')
    pc.add_argument('--dry-run', action='store_true')
    ps = sub.add_parser('apply-spm', help='terapkan CSV terjemahan ke SPM')
    ps.add_argument('csv')
    ps.add_argument('--dry-run', action='store_true')
    pp = sub.add_parser('pack-png', help='kemas PNG hasil edit ke folder patch')
    pp.add_argument('--work-dir', default=PNG_WORK)

    args = p.parse_args()
    if args.cmd == 'extract':
        extract_all(OUT_DIR)
    elif args.cmd == 'apply-config':
        apply_config_csv(args.csv, args.out_patch, args.dry_run)
    elif args.cmd == 'apply-spm':
        apply_spm_csv(args.csv, args.out_patch, args.dry_run)
    elif args.cmd == 'audit-png':
        audit_png(args.out_dir)
    elif args.cmd == 'export-png':
        export_png(args.work_dir)
    elif args.cmd == 'pack-png':
        pack_png(args.work_dir, args.out_patch)

if __name__ == '__main__':
    main()
