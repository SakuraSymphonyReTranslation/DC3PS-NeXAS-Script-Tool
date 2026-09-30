# Game UI Translation Guide — DC3PS (NeXAS Switch)

> 🇮🇩 Versi Bahasa Indonesia: [README_UI_TRANSLATION.md](README_UI_TRANSLATION.md)

This document explains **where the game's UI text lives** (menus, buttons, Scenario Mode
labels, scenario titles), what format it uses, and the workflow for translating it.

---

## UI File Map

| File | Contents | JP Strings | Priority |
|---|---|---|---|
| `romfs/System/config.spm` | Config screen labels (system/message/keyboard/mouse/touch/gamepad) | ~74 unique | High |
| `romfs/System/command.spm` | In-game command menu (AUTO, SKIP, SAVE, LOAD, etc.) | 23 unique | High |
| `romfs/System/checkwindow.spm` | Confirmation popups (Yes/No) | 17 unique | High |
| `romfs/System/scenario_menu.spm` | **Scenario Mode UI** (character names: ひより/そらね/にの/ありす/ちよ子, プロローグ label) | 9 unique | High |
| `romfs/System/tabbar.spm` | Menu tabs (SAGA/EXTRA etc.) | 14 unique | High |
| `romfs/System/save.spm`, `loading.spm`, `titlebar.spm`, `backlog.spm`, `systembar.spm`, `systemmenu.spm`, `menuhelp.spm`, `messagewindow.spm`, `quickconfigbar.spm`, `extramode*.spm` | Labels on the remaining screens | 2–12 unique each | Medium |
| `romfs/Config/event.datu8` | **All scenario/event titles** (216 titles) | 216 | **Highest** |
| `romfs/Config/eventtype.datu8` | Event type labels in Scenario Mode (通常イベント = Normal Event, etc.) | 12 | **Highest** |
| `romfs/Config/button.datu8` | In-game button help/tooltips | 296 | Medium |
| `romfs/Config/buttonex.datu8` | Config window help text | 10 | Medium |
| `romfs/Config/char.datu8` | Character names | 14 | Medium |
| `romfs/Config/bgm.datu8` | Song titles (BGM mode) | 50 | Low |

**Encoding:** `.spm` files use **Shift_JIS**, `.datu8` files use **UTF-8** (length-prefixed strings).

> Note: many SPM labels are drawn as **PNG textures** (not rendered text).
> Strings inside SPM files are mostly *layer names* and *tooltips*; if a label appears
> as an image, the PNG in `romfs/System/*.png` is what needs replacing (edit the image).

---

## How to Extract UI Text

Main tool: **`ui_translation_tool.py`** (self-contained, no dependencies beyond Python 3.8+; Pillow optional for PNG features).

> 💡 Every mode below is also available in the **GUI** (`run_gui.bat`) — the **UI Translation**
> tab (6 buttons) and the **Build Full Patch** tab (combines scenario + UI + video into one patch).

```bash
python ui_translation_tool.py extract
```

Output:
- `scratch/ui_strings_spm.csv` — 698 unique strings from 64 SPM files (columns: japanese_text, files, indonesian_translation)
- `scratch/ui_strings_config.csv` — 598 strings from Config datu8 (columns: file, row_index, column, japanese_text, indonesian_translation)

Fill the `indonesian_translation` column with your translations.

## How to Apply Translations

### A. Config `.datu8` (event.datu8 = scenario titles, eventtype, button, etc.) — AUTOMATIC

```bash
# dry-run first to check without writing anything
python ui_translation_tool.py apply-config scratch/ui_strings_config.csv --dry-run

# write the translated .datu8 files to the patch folder
python ui_translation_tool.py apply-config scratch/ui_strings_config.csv
```

- Default destination: `DC3PS_Indo_Patch/romfs/Config/` (change with `--out-patch <folder>`).
- Only rows with a filled `indonesian_translation` column are replaced; every other row/column is
  guaranteed **byte-for-byte untouched** (verified automatically after writing).
- String length may change (field length is recalculated automatically); row & column counts must stay the same.
- Multiple CSVs can be combined: `apply-config file1.csv file2.csv`.

### B. Layout `.spm` (config, command, scenario_menu, etc.) — AUTOMATIC with caveats

```bash
python ui_translation_tool.py apply-spm scratch/ui_strings_spm.csv --dry-run
python ui_translation_tool.py apply-spm scratch/ui_strings_spm.csv
```

- Each file's encoding is auto-detected (mostly Shift_JIS, some UTF-8).
- Safe for **same-byte-length translations**. For different lengths, the tool tries the
  fallback encoding (Shift_JIS → UTF-8); strings that still cannot be converted are reported
  as "needs a manual SPM editor".
- Verify the results against the checklists below (tab bar etc.) and test in-game.

### C. Image labels (PNG textures) — EDIT IN PHOTOSHOP/GIMP

Most UI labels are rendered from **PNG textures** (`romfs/System/*.png`), not text.
The tool provides a complete workflow:

```bash
python ui_translation_tool.py audit-png     # list text-bearing PNG candidates (CSV + HTML gallery)
python ui_translation_tool.py export-png    # copy candidates to png_work/src/
# -> copy the PNGs you want to edit to png_work/edited/ (same names), edit in Photoshop/GIMP
python ui_translation_tool.py pack-png      # validate + auto-convert + copy to the patch
```

Key rules:
- **Canvas dimensions must match the original exactly** — different sizes are rejected automatically.
- **Format is free**: save RGB, RGBA, indexed/16-bit from Photoshop — `pack-png` analyzes the
  original PNG's format (color type, bit depth, palette, transparency) and **automatically converts**
  your edit to be compatible with the target UI file.
- Packed files go to `--out-patch` (default `DC3PS_Indo_Patch/romfs/System/`).

Visual review of candidates: open `scratch/png_text_audit.html` (537 candidates from 660 System PNGs).

---

## UI Translation Priority Checklist

1. [ ] `Config/event.datu8` — 216 scenario titles (shown in Scenario Mode & backlog)
2. [ ] `Config/eventtype.datu8` — 12 event type labels
3. [ ] `System/scenario_menu.spm` — character names & scenario menu labels
4. [ ] `System/command.spm` — in-game command menu
5. [ ] `System/config.spm` + `Config/buttonex.datu8` — settings screen
6. [ ] `Config/button.datu8` — 296 button tooltips
7. [ ] `System/checkwindow.spm` — Yes/No popups
8. [ ] `Config/char.datu8` — character names
9. [ ] The rest: save/load/titlebar/tabbar/extramode (optional)
