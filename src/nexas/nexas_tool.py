#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeXAS Script Extractor & Inserter (Switch) — KHUSUS Da Capo III Plus Story.
Title ID: 010041601B544000 (Nintendo Switch)
Mendukung format JSON:
- Dialog:  {"name": "...", "message": "..."}
- Monolog: {"message": "..."}
Menjaga tag voice (@v...), formatting ruby (@r...), face tag (@h...), tag waktu (@t...), dsb.
"""

import os
import sys
import json
import re
import struct
import argparse
from pathlib import Path

GAME_TITLE = "Da Capo III Plus Story"
GAME_TID = "010041601B544000"

VOICE_REGEX = re.compile(r'^(@v\S+?)(?=[「『（\s]|$)\s*')

# Kata kunci sistem engine (di akhir scene opcode (0,nama),(5,1),(0,pesan)
# bisa memakai string ini sebagai "pesan" — bukan nama pembicara).
SYSTEM_KEYWORDS = {
    'ReplayMode', 'EventMode', 'Title', 'System', 'PackList', 'BGM',
    'cgmode', 'musicmode', 'extramode', 'backlog',
}


def is_plausible_speaker_name(name_str):
    """Nama pembicara yang layak: pendek, bukan tag, mengandung CJK atau ASCII kata.

    Versi lebih longgar dari is_asset_or_system_string untuk konteks mapping
    opcode (0,nama),(5,1),(0,pesan) — pola posisi sudah cukup kuat, sehingga
    nama Latin seperti 'SAX' (DC3PS) tidak ikut terbuang. Tetap menolak kata
    kunci sistem, nama file, dan id scene.
    """
    if not name_str:
        return False
    s = name_str.strip()
    if not s or len(s) > 20 or s.startswith('@'):
        return False
    if s in SYSTEM_KEYWORDS:
        return False
    if any('\u3040' <= c <= '\u9fff' for c in s):
        return True
    # Nama Latin murni: tidak boleh mengandung digit/underscore (id scene
    # seperti 'dc3_1_1212_d1_cmn' tidak lolos) dan tidak boleh berakhiran
    # ekstensi file ('sakura.spm' dsb.).
    if re.match(r'^[A-Za-z][A-Za-z \-.]*$', s) and not re.search(
        r'\.(png|opus|jpg|jpeg|bmp|nmv|fxb|ttc|ttf|fnt|spm|bin|binu8|dat|datu8|csv|mp4|txt)$',
        s, re.IGNORECASE,
    ):
        return True
    return False

def is_asset_or_system_string(s):
    if not s or not s.strip():
        return True
    clean = s.strip()
    lower = clean.lower()
    # File extensions
    if any(lower.endswith(ext) for ext in [
        '.png', '.opus', '.jpg', '.jpeg', '.bmp', '.nmv', '.fxb', 
        '.ttc', '.ttf', '.fnt', '.spm', '.bin', '.binu8', '.dat', '.datu8', '.csv'
    ]):
        return True
    # Sound/music identifiers (e.g. se083, bgm001, voice123, sys001)
    if re.match(r'^(?:se|bgm|voice|sys)\d+', clean, re.IGNORECASE):
        return True
    # Known engine keywords / scene jump targets
    if clean in ['ReplayMode', 'EventMode', 'Title', 'System', 'PackList', 'cgmode', 'musicmode', 'BGM']:
        return True
    # Short formatting commands like @b
    if clean.startswith('@b') and len(clean) <= 5:
        return True
    # Pure ASCII symbols / labels / IDs (must not contain any Japanese / CJK characters)
    if re.match(r'^[a-zA-Z0-9_\-\.\:\/]+$', clean) and not any('\u3040' <= c <= '\u9fff' for c in clean):
        return True
    return False

def parse_binu8(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    pos = 0
    version = data[0:9]
    if version[0:3] == b'VER':
        pos = 9
        unk_count = struct.unpack('<L', data[pos:pos+4])[0]
        pos += 4 + unk_count * 4
    elif version[0] == 9 and version[4:7] == b'VER':
        pos = 13
        unk_count = struct.unpack('<L', data[pos:pos+4])[0]
        pos += 4 + unk_count * 4
    else:
        pos = 0

    def _read_count(offset, what):
        if offset + 4 > len(data):
            raise ValueError(f'{file_path}: header terpotong saat membaca {what}')
        return struct.unpack('<L', data[offset:offset+4])[0]

    init_code_count = _read_count(pos, 'init_code_count')
    if init_code_count > len(data) // 8:
        raise ValueError(
            f'{file_path}: init_code_count tidak masuk akal ({init_code_count}) '
            f'— kemungkinan bukan script NeXAS standar')
    pos += 4 + init_code_count * 8

    code_count = _read_count(pos, 'code_count')
    if code_count > len(data) // 8:
        raise ValueError(
            f'{file_path}: code_count tidak masuk akal ({code_count}) '
            f'— kemungkinan bukan script NeXAS standar')
    pos += 4
    codes = [struct.unpack('<II', data[pos+i*8:pos+i*8+8]) for i in range(code_count)]
    pos += code_count * 8

    header_prefix = data[:pos]
    str_count = struct.unpack('<L', data[pos:pos+4])[0]
    pos += 4

    strings = []
    for _ in range(str_count):
        slen = struct.unpack('<L', data[pos:pos+4])[0]
        pos += 4
        s_bytes = data[pos:pos+slen-1]
        s = s_bytes.decode('utf-8', errors='replace')
        pos += slen
        strings.append(s)

    footer_bytes = data[pos:]

    # Bytecode speaker map:
    # Pada engine NeXAS, pembicara dialog dipasangkan melalui opcode:
    # (0, name_idx), (5, 1), (0, msg_idx)
    msg_to_speaker = {}
    for i in range(len(codes) - 2):
        if codes[i+1] == (5, 1) and codes[i][0] == 0 and codes[i+2][0] == 0:
            name_idx = codes[i][1]
            msg_idx = codes[i+2][1]
            if name_idx < len(strings) and msg_idx < len(strings):
                name_str = strings[name_idx].strip()
                if is_plausible_speaker_name(name_str):
                    msg_to_speaker[msg_idx] = (name_idx, name_str)

    return {
        'header_prefix': header_prefix,
        'str_count': str_count,
        'strings': strings,
        'codes': codes,
        'msg_to_speaker': msg_to_speaker,
        'footer_bytes': footer_bytes,
        'filesize': len(data)
    }

def extract_script(binu8_path, out_json_path):
    parsed = parse_binu8(binu8_path)
    strings = parsed['strings']
    msg_to_speaker = parsed['msg_to_speaker']

    entries = []
    total_strings = len(strings)

    # Lacak pembicara dialog aktif untuk menangani dialog bersambung (@k)
    active_speaker = None
    speaker_def_indices = {n_idx for n_idx, _ in msg_to_speaker.values()}

    for i in range(total_strings):
        s = strings[i]
        if is_asset_or_system_string(s):
            continue

        clean = s.strip()

        # Cek apakah string ini adalah definisi nama karakter
        is_speaker_def = i in speaker_def_indices
        is_msg = i in msg_to_speaker

        if is_msg:
            active_speaker = msg_to_speaker[i][1]
        elif is_speaker_def and not is_msg:
            # Ini adalah slot definisi nama pembicara, jangan diekstrak sebagai baris dialog/monolog terpisah!
            continue
        elif clean.startswith('「') or clean.startswith('『') or VOICE_REGEX.match(clean):
            if not is_msg:
                active_speaker = None
        elif clean.startswith('\u3000'):
            # Narasi / monolog
            active_speaker = None

        # Deteksi apakah baris ini adalah bagian percakapan karakter:
        # 1. Memiliki nama di bytecode (is_msg)
        # 2. Diawali tanda petik/kurung 「...」 atau suara @v
        # 3. Merupakan SAMBUNGAN dari dialog sebelumnya yang belum ditutup (misal diawali @k lalu dilanjutkan di string ini)
        is_speech = (is_msg or 
                     clean.startswith('「') or 
                     clean.startswith('『') or 
                     VOICE_REGEX.match(clean) or 
                     (active_speaker is not None and (clean.endswith('」') or clean.endswith('』') or '@k' in clean)))

        clean_msg = strip_ruby_tags(VOICE_REGEX.sub('', s).strip())

        entry = {}
        if is_speech and active_speaker:
            entry["name"] = active_speaker
        entry["message"] = clean_msg
        entries.append(entry)

        # Jika dialog sudah selesai (tutup kurung 」 dan tidak ada sambungan @k lagi), reset active_speaker
        if (clean.endswith('」') or clean.endswith('』')) and not clean.endswith('@k'):
            active_speaker = None

    os.makedirs(os.path.dirname(os.path.abspath(out_json_path)), exist_ok=True)
    with open(out_json_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    return len(entries)

EMBEDDED_NAME_REGEX = re.compile(r'^([A-Za-z0-9_ \.\-]+?)\s*:\s*([「『"“\'].+)', re.DOTALL)
EMBEDDED_BRACKET_REGEX = re.compile(r'^\[([A-Za-z0-9_ \.\-]+?)\]\s*(.+)', re.DOTALL)

def strip_ruby_tags(text):
    """
    Menghapus tag Ruby / Furigana (@r... atau @・@) dan menyisakan teks intinya.
    Contoh:
      - @rあ@・@@rい@・@@rつ@・@ -> あいつ
      - @rd@・@@ri@・@@ra@・@ -> dia
      - @r系統樹の径@パ　ス@ -> 系統樹の径
      - @r七月七日@きょう@ -> 七月七日
    """
    if not text:
        return text
    # Pola standar: @rBase@Ruby@ -> Base
    cleaned = re.sub(r"@[rR]([^@]+)@[^@]*@", r"\1", text)
    # Sisa tag bouten / titik penekanan
    cleaned = re.sub(r"@・@", "", cleaned)
    cleaned = re.sub(r"@[rR]", "", cleaned)
    return cleaned

def clean_gaiji_dashes(text):
    """
    Membersihkan tag Gaiji dash (@g－ atau @g-) bawaan naskah Jepang:
    1. Di awal kalimat atau setelah tanda kurung pembuka (「@g－@g－...):
       Dihapus total tanpa spasi karena merupakan awalan kata.
    2. Di sebelum tanda baca penutup atau tanda kurung penutup (...@g－@g－」):
       Dihapus tanpa menyisakan spasi kosong.
    3. Di tengah kalimat antar kata (kata1@g－@g－kata2):
       Diubah menjadi tepat 1 spasi pemisah biasa.
    """
    if not text:
        return text
    # 1. Awalan kalimat / setelah kurung pembuka: hapus total tanpa spasi
    text = re.sub(r'([「『\(\（]\s*)(?:@g[－\-])+\s*', r'\1', text)
    text = re.sub(r'^(?:@g[－\-])+\s*', '', text)

    # 2. Sebelum tanda baca penutup / kurung penutup
    #    (termasuk tanda baca tengah , 、 。 agar tidak jadi "kata ,")
    text = re.sub(r'\s*(?:@g[－\-])+\s*([」』\)\）!?！？、，。])', r'\1', text)
    text = re.sub(r'\s*(?:@g[－\-])+$', '', text)

    # 3. Di tengah kalimat (antara kata): jadikan tepat 1 spasi
    text = re.sub(r'\s*(?:@g[－\-])+\s*', ' ', text)
    return text

def normalize_tags_and_spacing(text):
    """
    Mengatur spasi di sekitar tag kontrol (@t..., @h..., dll.) agar rapi dan tidak double space:
    1. Membersihkan tag gaiji dash (@g－ atau @g-).
    2. Menghapus spasi antar tag yang berurutan (@t0100 @hFace -> @t0100@hFace).
    3. Menyisipkan spasi pemisah jika tag langsung menempel dengan huruf Latin di belakangnya,
       agar kata tidak tertelan oleh parser tag engine NeXAS (@hFace123Kata -> @hFace123 Kata).
    4. Jika terdapat spasi sebelum tag dan sesudah tag, buang spasi sebelum tag sehingga
       hanya ada 1 spasi yang tampak di layar (menghindari double space seperti 'Sora-nee.  Lagian').
    5. Menghapus spasi sebelum tag kontrol di akhir teks (seperti @k, @t..., dll.) agar tidak
       menyebabkan double space saat disambung oleh baris berikutnya (chained continuation).
    6. Menghapus spasi sebelum tanda kurung penutup atau tanda baca penutup.
    """
    if not text:
        return text

    # Bersihkan gaiji dash terlebih dahulu
    text = clean_gaiji_dashes(text)

    # Hapus spasi antar tag berurutan (@t0100 @hFace -> @t0100@hFace)
    text = re.sub(r'(@[a-zA-Z0-9_*~]+)\s+(?=@)', r'\1', text)

    # Tag yang berakhiran angka menempel dengan huruf Latin: @hAlice_l150215Kata -> @hAlice_l150215 Kata
    text = re.sub(r"(@[a-zA-Z0-9_]*\d)([A-Za-z\u00C0-\u024F])", r"\1 \2", text)
    # Tag huruf tunggal menempel dengan huruf Latin: @kKata -> @k Kata
    text = re.sub(r"(@[kgd])([A-Za-z\u00C0-\u024F])", r"\1 \2", text)

    # Jika ada spasi di SEBELUM tag dan spasi di SESUDAH tag:
    # Contoh: "Sora-nee. @t0810@hNino_0130207 Lagian" -> "Sora-nee.@t0810@hNino_0130207 Lagian"
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)+)\s+', r'\1 ', text)

    # Hapus spasi sebelum tag kontrol yang berada di akhir string (seperti @k, @t..., dll.):
    # Contoh: "……, @t0215@hNino_0160208@k" -> "……,@t0215@hNino_0160208@k"
    # Contoh: "Tunggu…… @k" -> "Tunggu……@k"
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)+)\s*$', r'\1', text)

    # Hapus spasi sebelum kurung siku penutup atau tanda baca penutup:
    # Contoh: "Teks 」" -> "Teks」"
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)*[」』\)\）])', r'\1', text)

    # Bersihkan spasi ganda biasa jika ada
    text = re.sub(r' {2,}', ' ', text)
    return text.rstrip()

def clean_translated_entry(entry):
    """
    Membersihkan entry terjemahan:
    1. Memisahkan awalan nama 'Nama: 「...」' jika terselip di dalam message.
    2. Menghapus tag ruby sisa (@rd@・@).
    3. Membersihkan gaiji dash (@g－) dan menormalisasi spasi tag agar tidak double space.
    4. Menjaga dan menormalisasi format command stiker phonechat (@d@*stamp@<name>@).
    """
    msg = entry.get("message", "")
    if msg:
        if '@*stamp' in msg or 'comu_stamp' in msg:
            m_stamp = re.search(r'comu_stamp\w+', msg)
            if m_stamp:
                entry["message"] = f"@d@*stamp@{m_stamp.group(0)}@"
            return
        msg = strip_ruby_tags(msg)
        msg = normalize_tags_and_spacing(msg)
        entry["message"] = msg

    if ("name" not in entry or not entry["name"]) and msg:
        m = EMBEDDED_NAME_REGEX.match(msg)
        if m:
            entry["name"] = m.group(1).strip()
            entry["message"] = m.group(2).strip()
            return
        m2 = EMBEDDED_BRACKET_REGEX.match(msg)
        if m2:
            entry["name"] = m2.group(1).strip()
            entry["message"] = m2.group(2).strip()
            return
    elif "name" in entry and entry["name"] and msg:
        m = EMBEDDED_NAME_REGEX.match(msg)
        if m:
            entry["message"] = m.group(2).strip()
        else:
            m2 = EMBEDDED_BRACKET_REGEX.match(msg)
            if m2:
                entry["message"] = m2.group(2).strip()

def repair_broken_comu_words(text, prev_d=""):
    """
    Memperbaiki kata-kata yang terbelah akibat sisa kode @n dari naskah Jepang.
    Misalnya: 'me@narik' -> 'menarik', 'pelari@nan' -> 'pelarian', 'menghala@nngi' -> 'menghalangi'.
    """
    if not text:
        return text

    # Daftar kata terbelah yang umum akibat tag @n Jepang yang tersisa
    known_fixes = {
        'me@narik': 'menarik',
        'pelari@nan': 'pelarian',
        'menghala@nngi': 'menghalangi',
        'muncu@nl': 'muncul',
        'merang@nkum': 'merangkum',
        'ti@ndak': 'tidak',
        'Wonder@nland': 'Wonderland',
        'e@nvent': 'event',
        'al@nat': 'alat',
        'ke@nmari': 'kemari',
        'ke sana ke@nmari': 'ke sana kemari',
        'Miu@ntan': 'Miu-tan',
        'Saki@nsan': 'Saki-san',
        'ke@ndewasaan': 'kedewasaan',
        'ber@nbeda': 'berbeda',
        'gra@ntis': 'gratis',
        'ca@nra': 'cara',
    }
    for broken, fixed in known_fixes.items():
        text = text.replace(broken, fixed)

    clean_prev = prev_d.replace('@d', '').replace('@k', '').strip() if prev_d else ""
    def repl(match):
        w1, w2 = match.group(1), match.group(2)
        if clean_prev:
            low_prev = clean_prev.lower()
            if (w1 + w2).lower() in low_prev:
                return w1 + w2
            if (w1 + '-' + w2).lower() in low_prev:
                return w1 + '-' + w2
            if (w1 + 'n' + w2).lower() in low_prev:
                return w1 + 'n' + w2
        return w1 + ' ' + w2

    return re.sub(r'([a-zA-Z\u00C0-\u024F]+)@n([a-zA-Z\u00C0-\u024F]+)', repl, text)

def format_comu_bubble_text(text, prev_d=""):
    """
    Format khusus untuk teks percakapan di dalam balon obrolan (Comu / Phonechat).
    
    1. Memperbaiki kata yang terbelah akibat @n sisa Jepang.
    2. Pesan Pendek (<= 50 kolom visual): tampilkan utuh dalam 1 baris tanpa @n (memakai Frame 1 ramping).
    3. Pesan Sedang (<= 106 kolom visual): dibagi proporsional ke dalam 2 baris (tiap baris <= 54 kolom visual).
    4. Pesan Sangat Panjang (> 106 kolom visual): dibagi proporsional ke dalam 3 baris (tiap baris <= 52 kolom visual).
    """
    text = repair_broken_comu_words(text, prev_d)
    clean = text.replace('@d', '').replace('@k', '').replace('@n', ' ').replace('\n', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    words = clean.split(' ')
    total_len = visible_length(clean)

    # 1. Pesan Pendek (<= 56 kolom visual): tetap utuh 1 baris (Frame 1 ramping)
    if total_len <= 56 or len(words) <= 1:
        return clean

    # 2. Cek apakah bisa 2 baris proporsional (tiap baris <= 56 kolom visual)
    best_2 = None
    best_2_score = float('inf')
    for i in range(1, len(words)):
        l1 = ' '.join(words[:i])
        l2 = ' '.join(words[i:])
        v1 = visible_length(l1)
        v2 = visible_length(l2)
        if v1 <= 56 and v2 <= 56:
            penalty = 0
            if len(words[i:]) == 1 and len(words[i]) <= 3:
                penalty += 50
            penalty += max(0, v1 - 54) * 20 + max(0, v2 - 54) * 20
            score = max(v1, v2) * 2 + abs(v1 - v2) + penalty
            if score < best_2_score:
                best_2_score = score
                best_2 = [l1, l2]

    if best_2:
        return f"{best_2[0]}@n{best_2[1]}"

    # 3. Jika teks sangat panjang (> 110 kolom), bagi ke dalam 3 baris (tiap baris <= 54 kolom visual)
    best_3 = None
    best_3_score = float('inf')
    for i in range(1, len(words) - 1):
        for j in range(i + 1, len(words)):
            l1 = ' '.join(words[:i])
            l2 = ' '.join(words[i:j])
            l3 = ' '.join(words[j:])
            lens = [visible_length(l1), visible_length(l2), visible_length(l3)]
            if all(l <= 54 for l in lens):
                penalty = sum(max(0, l - 52) * 30 for l in lens)
                variance = max(lens) - min(lens)
                score = max(lens) * 10 + variance + penalty
                if score < best_3_score:
                    best_3_score = score
                    best_3 = [l1, l2, l3]

    if best_3:
        return '@n'.join(best_3)

    return apply_word_wrap(clean, max_len=54)

# Gunakan implementasi algoritma dari script_auto_wrap jika tersedia
try:
    import script_auto_wrap  # wrapper root
except ImportError:
    try:
        from . import script_auto_wrap  # pemakaian sebagai paket src.nexas
    except ImportError:
        script_auto_wrap = None
    def apply_word_wrap(text, max_len=56, initial_width=0):
        if not max_len or max_len <= 0:
            return text
        if script_auto_wrap is None:
            return text
        return script_auto_wrap.wrap_text(text, max_chars=max_len, initial_width=initial_width)
    def visible_length(text):
        if script_auto_wrap is None:
            return len(text)
        return script_auto_wrap.visible_length(text)
except ImportError:
    import unicodedata
    def char_width(c):
        if c in '\u3000…「」『』・―〜～★☆♪※♥':
            return 2
        w = unicodedata.east_asian_width(c)
        if w in ('F', 'W'):
            return 2
        return 1

    def visible_length(text):
        clean = re.sub(r'@(?:v[A-Za-z0-9_]+|h[A-Za-z0-9_]+|t\d+|n|k|g)', '', text)
        return sum(char_width(c) for c in clean)

    def apply_word_wrap(text, max_len=56, initial_width=0):
        if not max_len or max_len <= 0:
            return text
        leading_indent = ""
        leading_space = ""
        if text.startswith("\u3000"):
            leading_indent = "\u3000"
            text = text[1:]
            initial_width += 2
        elif text.startswith(" "):
            leading_space = " "
            text = text.lstrip(" ")
            initial_width += 1

        text = text.replace("@n", "")
        tokens = re.findall(r'@(?:v[A-Za-z0-9_]+|h[A-Za-z0-9_]+|t\d+|n|k|g|[a-zA-Z0-9_]+)|\s+|[^\s@]+', text)
        lines = []
        current = ""
        pending_space = ""
        for token in tokens:
            if token.isspace():
                pending_space = token
                continue
            if re.match(r'^@(?:v[A-Za-z0-9_]+|h[A-Za-z0-9_]+|t\d+|n|k|g)', token):
                current += pending_space + token
                pending_space = ""
                continue
            word = token
            separator = pending_space if current else ""
            candidate = current + separator + word
            eff_width = (initial_width if not lines else 0) + visible_length(candidate)
            if eff_width <= max_len:
                current = candidate
            else:
                if current:
                    lines.append(current)
                elif initial_width > 0 and not lines:
                    lines.append("")
                current = word
                initial_width = 0
            pending_space = ""
        if current:
            lines.append(current)
        if lines:
            if leading_indent:
                lines[0] = leading_indent + lines[0]
            elif leading_space and lines[0]:
                lines[0] = leading_space + lines[0]
        return "@n".join(lines)

def insert_script(binu8_orig_path, json_path, binu8_out_path, word_wrap=56):
    parsed = parse_binu8(binu8_orig_path)
    orig_strings = parsed['strings']
    total_strings = len(orig_strings)

    with open(json_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    # Otomatis bersihkan setiap entry dari nama yang terselip di dalam message
    for entry in entries:
        clean_translated_entry(entry)

    new_strings = list(orig_strings)

    # Check if entries have metadata index tags (_idx_msg)
    has_meta = len(entries) > 0 and "_idx_msg" in entries[0]

    if has_meta:
        for entry in entries:
            if "name" in entry and "_idx_name" in entry:
                idx_name = entry["_idx_name"]
                new_strings[idx_name] = entry["name"]

            if "_idx_msg" in entry:
                idx_msg = entry["_idx_msg"]
                msg = entry.get("message", "")
                voice_tag = entry.get("_voice")
                orig_s = orig_strings[idx_msg]
                if not voice_tag and orig_s.startswith('\u3000') and not msg.startswith('\u3000') and not msg.startswith('「') and not msg.startswith('『'):
                    msg = f"\u3000{msg}"
                if word_wrap > 0:
                    msg = apply_word_wrap(msg, word_wrap)
                if voice_tag:
                    new_msg = f"{voice_tag}{msg}"
                else:
                    new_msg = msg
                new_strings[idx_msg] = new_msg
    else:
        # Sequential match using bytecode mapping
        msg_to_speaker = parsed['msg_to_speaker']
        speaker_def_indices = {n_idx for n_idx, _ in msg_to_speaker.values()}
        entry_idx = 0
        num_entries = len(entries)
        prev_line_col = 0
        last_speaker = None

        # QC: hitung posisi yang seharusnya dikonsumsi (string non-aset,
        # non-slot-nama) lalu bandingkan dengan jumlah entri JSON.
        speaker_def_indices = {n_idx for n_idx, _ in msg_to_speaker.values()}
        expected = 0
        for idx, s in enumerate(orig_strings):
            if is_asset_or_system_string(s):
                continue
            if idx in speaker_def_indices and idx not in msg_to_speaker:
                continue
            expected += 1
        if expected != num_entries:
            arah = 'kurang' if num_entries < expected else 'lebih'
            print(f"[!] PERINGATAN {os.path.basename(binu8_orig_path)}: JSON punya "
                  f"{num_entries} entri, script membutuhkan {expected} — "
                  f"{arah} {abs(expected - num_entries)}. Baris tersisa memakai teks asli.")

        for i in range(total_strings):
            s = orig_strings[i]
            if is_asset_or_system_string(s):
                continue

            if entry_idx >= num_entries:
                break

            clean = s.strip()
            is_speaker_def = i in speaker_def_indices
            is_msg = i in msg_to_speaker

            # 1. Slot definisi nama pembicara saja (bukan dialog), lewati
            if is_speaker_def and not is_msg:
                continue

            # 2. Penanganan Khusus Stiker Phonechat / Comu Stamp (@*stamp):
            is_stamp_orig = ('@*stamp' in s) or ('comu_stamp' in s)
            curr_msg = entries[entry_idx].get("message", "") if entry_idx < num_entries else ""
            is_stamp_entry = ('@*stamp' in curr_msg) or ('comu_stamp' in curr_msg)

            if is_stamp_orig or is_stamp_entry:
                entry = entries[entry_idx]
                msg_val = entry.get("message", "")
                m_stamp = re.search(r'comu_stamp\w+', msg_val) or re.search(r'comu_stamp\w+', s)
                if m_stamp:
                    new_strings[i] = f"@d@*stamp@{m_stamp.group(0)}@"
                else:
                    new_strings[i] = s
                prev_line_col = 0
                entry_idx += 1
                continue

            # 3. Penanganan Khusus Phonechat / Tablet (@d):
            if s.startswith('@d'):
                entry = entries[entry_idx]
                clean_m = entry.get("message", "").replace('@d', '').replace('@k', '').strip()
                if word_wrap > 0:
                    clean_m = apply_word_wrap(clean_m, word_wrap)
                new_strings[i] = f"@d{clean_m}@k"
                prev_line_col = 0
                entry_idx += 1
                continue
            elif i > 0 and orig_strings[i-1].startswith('@d') and not ('@*stamp' in orig_strings[i-1] or 'comu_stamp' in orig_strings[i-1]):
                entry = entries[entry_idx]
                prev_d_msg = entries[entry_idx - 1].get("message", "") if entry_idx > 0 else ""
                new_strings[i] = format_comu_bubble_text(entry.get("message", ""), prev_d=prev_d_msg)
                prev_line_col = 0
                entry_idx += 1
                continue

            # 4. SEMUA PESAN DIALOG & NARASI (termasuk sambungan @k):
            entry = entries[entry_idx]
            curr_speaker = entry.get("name")

            # Update speaker name if defined in bytecode
            if is_msg and "name" in entry:
                n_idx = msg_to_speaker[i][0]
                new_strings[n_idx] = entry["name"]

            # Update message
            msg = entry.get("message", "")
            v_match = VOICE_REGEX.match(s)

            # Cek apakah string ini merupakan sambungan langsung pada baris yang sama (chained continuation)
            is_continuation = (
                prev_line_col > 0
                and not v_match
                and not msg.startswith('「')
                and not msg.startswith('『')
                and not s.startswith('「')
                and not s.startswith('『')
                and (
                    (bool(curr_speaker) and curr_speaker == last_speaker)
                    or (not curr_speaker and (not is_msg or (i in msg_to_speaker and msg_to_speaker[i][1] == last_speaker)))
                )
            )

            if not is_continuation:
                prev_line_col = 0

            is_narrative = (not curr_speaker) and (not is_continuation)
            if is_msg:
                if is_narrative:
                    last_speaker = None
                elif curr_speaker:
                    last_speaker = curr_speaker

            if is_continuation:
                # Sambungan dialog pada baris yang sama (chained continuation @k)
                msg = msg.lstrip(' ')
                if not msg.startswith('\u3000'):
                    msg = f" {msg}"
                if word_wrap > 0:
                    msg = apply_word_wrap(msg, word_wrap, initial_width=prev_line_col)
            else:
                if not v_match and s.startswith('\u3000') and not msg.startswith('\u3000') and not msg.startswith('「') and not msg.startswith('『'):
                    msg = f"\u3000{msg}"
                if word_wrap > 0:
                    msg = apply_word_wrap(msg, word_wrap, initial_width=0)

            if v_match:
                new_strings[i] = f"{v_match.group(1)}{msg}"
            else:
                new_strings[i] = msg

            # Update prev_line_col untuk string berikutnya
            res_str = new_strings[i]
            # Jika kalimat/kutipan telah ditutup dengan '」' atau '』', dialog selesai (tidak ada sambungan ke baris berikutnya)
            has_closed_quote = bool(
                re.search(r'[」』](?:@[a-zA-Z0-9_*~]+)*\s*$', res_str)
                or re.search(r'[」』](?:@[a-zA-Z0-9_*~]+)*\s*$', s)
            )

            if (
                res_str.rstrip().endswith('@k')
                and not res_str.endswith('@n@k')
                and not res_str.endswith('@n')
                and not has_closed_quote
                and not is_narrative
            ):
                parts = res_str.split('@n')
                if len(parts) > 1:
                    prev_line_col = visible_length(parts[-1])
                else:
                    prev_line_col = prev_line_col + visible_length(parts[0])
            else:
                prev_line_col = 0

            entry_idx += 1

    # Rebuild binu8 binary
    os.makedirs(os.path.dirname(os.path.abspath(binu8_out_path)), exist_ok=True)
    with open(binu8_out_path, 'wb') as f:
        f.write(parsed['header_prefix'])
        f.write(struct.pack('<L', len(new_strings)))

        for s in new_strings:
            s_bytes = s.encode('utf-8')
            f.write(struct.pack('<L', len(s_bytes) + 1))
            f.write(s_bytes)
            f.write(b'\x00')

        f.write(parsed['footer_bytes'])

    return len(entries)

def main():
    parser = argparse.ArgumentParser(
        description="NeXAS Switch Script Tool (Extract / Insert) - Da Capo III Plus Story",
        epilog=f"Khusus {GAME_TITLE} (Nintendo Switch, TID {GAME_TID})."
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Extract
    ext_parser = subparsers.add_parser('extract', help='Extract .binu8 to .json (name + message / message)')
    ext_parser.add_argument('-i', '--input', required=True, help='Input binu8 file or folder')
    ext_parser.add_argument('-o', '--output', required=True, help='Output json file or folder')

    # Insert
    ins_parser = subparsers.add_parser('insert', help='Insert translated .json back into .binu8')
    ins_parser.add_argument('-b', '--base', required=True, help='Original binu8 file or folder')
    ins_parser.add_argument('-j', '--json', required=True, help='Translated json file or folder')
    ins_parser.add_argument('-o', '--output', required=True, help='Output binu8 file or folder')
    ins_parser.add_argument('-w', '--wordwrap', type=int, default=56, help='Max visual width per line before @n (0 to disable, default: 56)')

    args = parser.parse_args()

    print(f"[*] Game: {GAME_TITLE} (TID {GAME_TID})")
    print("[*] Word wrap rekomendasi: 56 kolom")

    if args.command == 'extract':
        in_p = Path(args.input)
        out_p = Path(args.output)
        if in_p.is_file():
            cnt = extract_script(str(in_p), str(out_p))
            print(f"[+] Extracted {cnt} entries: {in_p.name} -> {out_p}")
        elif in_p.is_dir():
            files = [p for p in in_p.glob('**/*.binu8') if p.name != '__global.binu8']
            print(f"[*] Found {len(files)} binu8 files in {in_p}...")
            total = 0
            for p in sorted(files):
                rel = p.relative_to(in_p)
                dst = out_p / rel.with_suffix('.json')
                cnt = extract_script(str(p), str(dst))
                total += cnt
            print(f"[+] Successfully extracted {len(files)} files ({total} total entries) to {out_p}")

    elif args.command == 'insert':
        base_p = Path(args.base)
        json_p = Path(args.json)
        out_p = Path(args.output)
        wrap_val = args.wordwrap
        if base_p.is_file():
            cnt = insert_script(str(base_p), str(json_p), str(out_p), word_wrap=wrap_val)
            print(f"[+] Inserted {cnt} entries into {out_p}")
        elif base_p.is_dir():
            json_files = list(json_p.glob('**/*.json'))
            print(f"[*] Found {len(json_files)} json files in {json_p} (WordWrap={wrap_val})...")
            count = 0
            for jf in sorted(json_files):
                rel = jf.relative_to(json_p)
                bin_base = base_p / rel.with_suffix('.binu8')
                if not bin_base.exists():
                    continue
                bin_out = out_p / rel.with_suffix('.binu8')
                insert_script(str(bin_base), str(jf), str(bin_out), word_wrap=wrap_val)
                count += 1
            print(f"[+] Successfully inserted {count} scripts into {out_p}")

if __name__ == '__main__':
    main()
