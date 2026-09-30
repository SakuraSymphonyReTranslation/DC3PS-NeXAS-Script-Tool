# -*- coding: utf-8 -*-
"""
csv_dump.py — Dump naskah Da Capo III Plus Story ke CSV per chapter,
siap diisi terjemahan, dengan kolom nama karakter.

Satu file script .binu8 -> satu CSV dengan kolom:
  index     : nomor urut entri (SESAI urutan extractor/inserter JSON, sehingga
              terjemahan bisa dipakai ulang lintas format)
  speaker   : nama pembicara dari bytecode (kosong = narasi/monolog)
  original  : teks asli (dibersihkan tag ruby/gaiji, seperti extractor)
  translation : kolom isian terjemahan (kosongkan bila belum diterjemahkan)
  notes     : catatan penerjemah (opsional)

Perintah:
  dump   -i <folder/file .binu8> -o <folder output CSV>
  insert -b <folder/file .binu8> -c <folder/file CSV> -o <folder output> [-w 56]

Contoh:
  python csv_dump.py dump -i "../../romfs/Script" -o "../naskah_csv"
  python csv_dump.py insert -b "../../romfs/Script" -c "../naskah_csv" -o "../Script_Mod" -w 56
"""
import argparse
import csv
import os
import struct
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from src.nexas.nexas_tool import (  # noqa: E402
    parse_binu8, extract_script, strip_ruby_tags, is_asset_or_system_string,
)


def cmd_dump(args):
    in_p = Path(args.input)
    out_p = Path(args.output)
    files = sorted(in_p.glob('**/*.binu8')) if in_p.is_dir() else [in_p]
    files = [f for f in files if f.name != '__global.binu8']
    print('[*] %d file .binu8' % len(files))
    total_rows = 0
    for f in files:
        rel = f.relative_to(in_p) if in_p.is_dir() else Path(f.name)
        dst = out_p / rel.with_suffix('.csv')
        dst.parent.mkdir(parents=True, exist_ok=True)
        entries = _dump_entries(str(f))
        with open(dst, 'w', newline='', encoding='utf-8-sig') as fo:
            w = csv.writer(fo)
            w.writerow(['index', 'speaker', 'original', 'translation', 'notes'])
            for i, (spk, msg) in enumerate(entries):
                w.writerow([i, spk, msg, '', ''])
        total_rows += len(entries)
    print('[+] CSV selesai -> %s (%d baris total)' % (out_p, total_rows))


def _dump_entries(bin_path):
    """Return [(speaker, cleaned_message), ...] urut, identik dengan extractor."""
    parsed = parse_binu8(bin_path)
    strings = parsed['strings']
    msg_to_speaker = parsed['msg_to_speaker']

    entries = []
    active_speaker = None
    speaker_def_indices = {n_idx for n_idx, _ in msg_to_speaker.values()}
    import re
    VOICE = re.compile(r'^(@v\S+?)(?=[「『（\s]|$)\s*')

    for i in range(len(strings)):
        s = strings[i]
        if is_asset_or_system_string(s):
            continue
        clean = s.strip()
        is_msg = i in msg_to_speaker
        is_speaker_def = i in speaker_def_indices and not is_msg

        if is_msg:
            active_speaker = msg_to_speaker[i][1]
        elif is_speaker_def:
            continue
        elif clean.startswith('「') or clean.startswith('『') or VOICE.match(clean):
            active_speaker = None
        elif clean.startswith('\u3000'):
            active_speaker = None

        is_speech = (is_msg
                     or clean.startswith('「') or clean.startswith('『')
                     or VOICE.match(clean)
                     or (active_speaker is not None and
                         (clean.endswith('」') or clean.endswith('』') or '@k' in clean)))

        clean_msg = strip_ruby_tags(VOICE.sub('', s).strip())
        spk = active_speaker if (is_speech and active_speaker) else ''
        entries.append((spk, clean_msg))
    return entries


def cmd_insert(args):
    base_p = Path(args.base)
    csv_p = Path(args.csv)
    out_p = Path(args.output)
    csvs = sorted(csv_p.glob('**/*.csv')) if csv_p.is_dir() else [csv_p]
    print('[*] %d CSV' % len(csvs))
    count = 0
    for cf in csvs:
        rel = cf.relative_to(csv_p) if csv_p.is_dir() else Path(cf.name)
        bin_base = base_p / rel.with_suffix('.binu8')
        if not bin_base.exists():
            print('[LEWATI] base tidak ada untuk %s' % rel)
            continue
        bin_out = out_p / rel.with_suffix('.binu8')
        bin_out.parent.mkdir(parents=True, exist_ok=True)

        entries = []
        originals = _dump_entries(str(bin_base))
        with open(cf, 'r', encoding='utf-8-sig', newline='') as fi:
            for idx, r in enumerate(csv.DictReader(fi)):
                spk = (r.get('speaker') or '').strip()
                msg = (r.get('translation') or '').strip()
                if not msg:
                    # Baris belum diterjemahkan -> pakai teks asli agar tidak
                    # terhapus saat injeksi (sesuai peringatan parsial).
                    if idx < len(originals):
                        spk, msg = originals[idx]
                    else:
                        continue
                entries.append({'name': spk, 'message': msg})
        if not entries:
            print('[LEWATI] CSV kosong: %s' % cf)
            continue

        # peringatan jumlah baris
        parsed = parse_binu8(str(bin_base))
        speaker_def = {n for n, _ in parsed['msg_to_speaker'].values()}
        expected = sum(
            1 for i, s in enumerate(parsed['strings'])
            if not is_asset_or_system_string(s)
            and not (i in speaker_def and i not in parsed['msg_to_speaker']))
        filled = sum(1 for e in entries if e['message'])
        if filled and filled != expected:
            print('[!] %s: terisi %d/%d baris (baris kosong = teks asli dipakai)'
                  % (rel, filled, expected))

        # pakai JSON path internal: tulis JSON sementara lalu insert_script
        import json as _json
        tmp_json = out_p / '.tmp_json' / rel.with_suffix('.json')
        tmp_json.parent.mkdir(parents=True, exist_ok=True)
        _json.dump(entries, open(tmp_json, 'w', encoding='utf-8'),
                   ensure_ascii=False, indent=1)
        from src.nexas.nexas_tool import insert_script
        n = insert_script(str(bin_base), str(tmp_json), str(bin_out),
                          word_wrap=args.wordwrap)
        tmp_json.unlink()
        count += 1
    print('[+] %d CSV diinjeksi -> %s' % (count, out_p))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    d = sub.add_parser('dump', help='dump .binu8 -> CSV per chapter')
    d.add_argument('-i', '--input', required=True)
    d.add_argument('-o', '--output', required=True)
    d.set_defaults(fn=cmd_dump)

    ins = sub.add_parser('insert', help='injeksi CSV terjemahan kembali ke .binu8')
    ins.add_argument('-b', '--base', required=True)
    ins.add_argument('-c', '--csv', required=True)
    ins.add_argument('-o', '--output', required=True)
    ins.add_argument('-w', '--wordwrap', type=int, default=56)
    ins.set_defaults(fn=cmd_insert)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
