# ExeFS CSV Workflow Guide — DC3PS Info Messages (NeXAS Switch)

> 🇮🇩 Versi Indonesia: [PANDUAN_EXEFS_CSV.md](PANDUAN_EXEFS_CSV.md)

This guide covers the complete workflow for translating the **bottom-left info
messages** of Da Capo III Plus Story — the transient text shown on Quick Load /
Quick Save / Jump / Auto-save (e.g. `QUICK 1番をロードしました`) — and how to manage the
`exefs_messages.csv` file.

These messages are **not stored in RomFS** (`.datu8`/`.spm`/`.png`); they are embedded
in the **game executable** (the `main` file in the ExeFS area, an LZ4-compressed NSO).

---

## Workflow Overview

```text
Dump ExeFS (your own copy)            [main + main.npdm]
        │  copy to scratch/exefs_dump/main
        ▼
1. SCAN     python exefs_patch_tool.py scan
        │  locates CSV strings in the binary (auto NSO/LZ4 decompression)
        ▼
2. FILL CSV edit scratch/exefs_messages.csv  (indonesian_translation column)
        │  or add new rows via:
        │  python exefs_patch_tool.py discover
        ▼
3. APPLY    python exefs_patch_tool.py apply
        │  result: scratch/exefs_patch/main  (uncompressed NSO)
        ▼
4. INSTALL  copy to %APPDATA%\eden\exefs\010041601B544000\main
            (or Atmosphere: atmosphere/exefs/<TID>/main)
```

Steps 1–4 are also available as the **Scan ExeFS / ExeFS Apply / Discover ExeFS**
buttons in the GUI (`run_gui.bat`, *UI Translation* tab) and as the **ExeFS** component
of the *Build Patch Lengkap* (Full Patch Build) tab.

---

## 1. Dump the ExeFS (one-time)

1. Dump the ExeFS from **your own legally-owned copy** of the game (same dump tool you
   used for RomFS). Only `main` is required (+ `main.npdm` for archiving).
2. Copy it to `scratch/exefs_dump/main`.
3. **NEVER upload the `main` file anywhere** — it is copyrighted code. The dump and
   patch folders are already gitignored.

> Safety note: `exefs_patch_tool` never writes into the dump folder. Patch results are
> always written to `scratch/exefs_patch/main`.

## 2. Scan

```bash
python exefs_patch_tool.py scan
```

- The tool reads every CSV row and searches for `japanese_text` in the decompressed
  image (encodings tried in order: **UTF-8 → Shift_JIS → UTF-16-LE**).
- This game's main binary uses **UTF-8**, so the hits that matter are the `[utf-8]` ones.
- Slot size = the byte length of the original JP string — that is the maximum budget
  for your translation.

## 3. Filling `exefs_messages.csv`

Columns:

| Column | Content | Editable? |
|---|---|---|
| `japanese_text` | Exact search key in the binary | ❌ Never edit/delete/reorder |
| `indonesian_translation` | Translation (≤ JP byte length) | ✅ Free; empty = safe (not replaced) |
| `keterangan` | Human-facing note about the string | ✅ Free (ignored by the tool) |

Key translation rules (see also `scratch/exefs_messages_BACA_SAYA.txt`, auto-generated
by the tool):

1. **Byte budget**: `len(translation.encode('utf-8'))` must be ≤
   `len(jp.encode('utf-8'))`. Too long → the tool **SKIPS** that row (safe, text stays
   Japanese) and reports it. Example: `番をロードしました` is 30 bytes, which fits
   ` telah dimuat` (18 bytes).
2. **No newlines** and no control characters.
3. **Leading spaces are intentional**: rows whose key starts with a slot marker
   (`番を…`) are translated with a leading space because they concatenate after a number
   on screen (`QUICK 1` + ` telah dimuat`).
4. **Mind Japanese aspect**: `〜しました/ました` = "has been …", `〜しています` =
   "is being …", `〜します` = "will be …". Do not collapse distinct meanings into one
   word.
5. **Beware partial strings**: some CSV keys are *fragments* of longer strings in the
   binary (e.g. `不足しています` is a prefix of `不足しています。`). Fragments are patched
   after their full-string variants; whenever the scan shows the full string, prefer
   adding the **full-string key**.
6. The CSV is saved as **UTF-8** (BOM allowed). One row = one JP↔ID pair.

## 4. Discover — adding new strings to the CSV

```bash
python exefs_patch_tool.py discover
```

- The tool scans the image with a Japanese-run regex, filters message-like strings
  (endings `しました/します/ません/…` plus keywords such as ロード/セーブ/ジャンプ), and
  **appends new JP rows** with empty translations (existing rows are untouched).
- New rows carry a note in the `keterangan` column marking them as discovered.
- Fill in the translations, then run `apply`.

## 5. Apply

```bash
python exefs_patch_tool.py apply
```

- Replaces each occurrence of the JP string with the translation **padded with spaces**
  to the original byte length — the binary layout never shifts by a single byte.
- Patch order: longest keys first, so specific variants are replaced before their short
  fallback fragments.
- Log `[OK] 'key' -> 'translation' xN [utf-8]` = success; `[SKIP]` = the translation
  exceeds the byte budget for that encoding (review rule 1 above).
- Result: `scratch/exefs_patch/main` (a valid NSO with compression/hash flags cleared).

## 6. Installing to emulator / console

| Target | Location |
|---|---|
| Eden / Citron / Yuzu / Sudachi | `%APPDATA%\<emulator>\exefs\010041601B544000\main` |
| Ryujinx | Options → Manage Mods → ExeFS → select the patched `main` |
| Atmosphere (real Switch) | `atmosphere/exefs/010041601B544000/main` |

Delete the patched `main` from that folder to return to the original Japanese text.

> Crash on boot? Remove the patched `main` from the emulator's exefs folder — the game
> returns to normal immediately.

---

## The ExeFS Component in the Full Patch Builder

`build_full_patch.py` (and the GUI's *Build Patch Lengkap* tab) includes an `exefs`
component that combines steps 5–6: patch the dump → auto-install to Eden via
`--install`. This component is **not included in the distribution ZIP** (copyrighted
code — every user must dump and patch their own).

## Safety & Ethics

- ExeFS dumps and patched binaries contain copyrighted code: **never upload or share them**.
- The translation CSV itself is pure text and may be shared freely.
- The tool only touches UI message strings — never program logic.
