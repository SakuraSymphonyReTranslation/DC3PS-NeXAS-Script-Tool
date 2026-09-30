# Panduan Terjemahan UI Game — DC3PS (NeXAS Switch)

> 🇬🇧 English version: [README_UI_TRANSLATION_EN.md](README_UI_TRANSLATION_EN.md)

Dokumen ini menjelaskan **di mana teks UI game** (menu, tombol, label Scenario Mode,
judul scenario) berada, formatnya, dan alur kerja menerjemahkannya ke Bahasa Indonesia.

---

## Peta File UI

| File | Isi | Jumlah String JP | Prioritas |
|---|---|---|---|
| `romfs/System/config.spm` | Label layar Config (sistem/pesan/keyboard/mouse/touch/gamepad) | ~74 unik | Tinggi |
| `romfs/System/command.spm` | Menu perintah in-game (AUTO, SKIP, SAVE, LOAD, dll) | 23 unik | Tinggi |
| `romfs/System/checkwindow.spm` | Popup konfirmasi (Ya/Tidak) | 17 unik | Tinggi |
| `romfs/System/scenario_menu.spm` | **UI Scenario Mode** (nama karakter: ひより/そらね/にの/ありす/ちよ子, label プロローグ) | 9 unik | Tinggi |
| `romfs/System/tabbar.spm` | Tab menu (SAGA/EXTRA dll) | 14 unik | Tinggi |
| `romfs/System/save.spm`, `loading.spm`, `titlebar.spm`, `backlog.spm`, `systembar.spm`, `systemmenu.spm`, `menuhelp.spm`, `messagewindow.spm`, `quickconfigbar.spm`, `extramode*.spm` | Label-label layar lainnya | 2–12 unik masing-masing | Sedang |
| `romfs/Config/event.datu8` | **Judul semua scenario/event** (216 judul) | 216 | **Tertinggi** |
| `romfs/Config/eventtype.datu8` | Label tipe event di Scenario Mode (通常イベント = Event Normal, dst) | 12 | **Tertinggi** |
| `romfs/Config/button.datu8` | Teks help/tooltips tombol in-game | 296 | Sedang |
| `romfs/Config/buttonex.datu8` | Teks help config window | 10 | Sedang |
| `romfs/Config/char.datu8` | Nama karakter | 14 | Sedang |
| `romfs/Config/bgm.datu8` | Judul lagu (BGM mode) | 50 | Rendah |

**Format encoding:** file `.spm` memakai **Shift_JIS**, file `.datu8` memakai **UTF-8** (string length-prefixed).

> Catatan: banyak label SPM digambar sebagai **tekstur PNG** (bukan text render).
> String yang ada di SPM umumnya adalah *nama layer* dan *tooltip*; jika label tampak
> sebagai gambar, yang perlu diganti adalah PNG di `romfs/System/*.png` (edit gambar).

---

## Cara Mengekstrak Teks UI

Tool utama: **`ui_translation_tool.py`** (self-contained, tanpa dependensi selain Python 3.8+; Pillow opsional untuk fitur PNG).

> 💡 Semua mode di bawah ini juga tersedia di **GUI** (`run_gui.bat`) — tab **UI Translation**
> (6 tombol) dan tab **Build Patch Lengkap** (menggabungkan scenario + UI + video ke satu patch).

```bash
python ui_translation_tool.py extract
```

Output:
- `scratch/ui_strings_spm.csv` — 698 string unik dari 64 file SPM (kolom: japanese_text, files, indonesian_translation)
- `scratch/ui_strings_config.csv` — 598 string dari Config datu8 (kolom: file, row_index, column, japanese_text, indonesian_translation)

Isi kolom `indonesian_translation` dengan terjemahan Anda.

## Cara Menerapkan Terjemahan

### A. Config `.datu8` (event.datu8 = judul scenario, eventtype, button, dll) — OTOMATIS

```bash
# dry-run dulu untuk cek tanpa menulis file
python ui_translation_tool.py apply-config scratch/ui_strings_config.csv --dry-run

# tulis .datu8 hasil terjemahan ke folder patch
python ui_translation_tool.py apply-config scratch/ui_strings_config.csv
```

- Default tujuan: `DC3PS_Indo_Patch/romfs/Config/` (ubah dengan `--out-patch <folder>`).
- Hanya baris yang kolom `indonesian_translation`-nya terisi yang diganti; baris/kolom lain dijamin **byte-per-byte tidak tersentuh** (diverifikasi otomatis setelah menulis).
- Panjang string bebas berubah (field length dihitung ulang otomatis); jumlah baris & kolom harus tetap.
- Bisa menggabung beberapa CSV: `apply-config file1.csv file2.csv`.

### B. Layout `.spm` (config, command, scenario_menu, dll) — OTOMATIS dengan batasan

```bash
python ui_translation_tool.py apply-spm scratch/ui_strings_spm.csv --dry-run
python ui_translation_tool.py apply-spm scratch/ui_strings_spm.csv
```

- Encoding tiap file dideteksi otomatis (kebanyakan Shift_JIS, beberapa UTF-8).
- Aman untuk **terjemahan dengan panjang byte sama**. Untuk panjang berbeda, tool mencoba fallback
  encoding lawas (Shift_JIS → UTF-8); string yang tetap tidak bisa dikonversi dilaporkan
  sebagai "perlu editor SPM manual".
- Cocokkan hasilnya dengan daftar di bawah (tab bar / checklist) dan uji in-game.

### C. Label bergambar (tekstur PNG) — EDIT DI PHOTOSHOP/GIMP

Sebagian besar label UI dirender dari **tekstur PNG** (`romfs/System/*.png`), bukan teks.
Tool menyediakan alur kerja lengkap:

```bash
python ui_translation_tool.py audit-png     # daftar kandidat PNG ber-teks (CSV + galeri HTML)
python ui_translation_tool.py export-png    # salin kandidat ke png_work/src/
# -> salin PNG yang mau diedit ke png_work/edited/ (nama sama), edit di Photoshop/GIMP
python ui_translation_tool.py pack-png      # validasi + konversi otomatis + salin ke patch
```

Aturan penting:
- **Dimensi kanvas harus sama persis** dengan asli — beda dimensi otomatis ditolak.
- **Format bebas**: simpan RGB, RGBA, indexed/16-bit dari Photoshop — `pack-png` menganalisa
  format PNG asli (color type, bit depth, palet, transparansi) lalu **mengonversi otomatis**
  hasil edit agar kompatibel dengan file UI yang dituju.
- Hasil pack dikirim ke `--out-patch` (default `DC3PS_Indo_Patch/romfs/System/`).

Review visual kandidat: buka `scratch/png_text_audit.html` (537 kandidat dari 660 PNG System).

---

## Cara Menerapkan Terjemahan

### A. Config `.datu8` (event.datu8 = judul scenario, eventtype, button, dll)

Lihat cara A di atas — `apply-config` menggantikan langkah manual converter Aquarium:

```bash
python ui_translation_tool.py apply-config scratch/ui_strings_config.csv
```

> ⚠️ **Penting:** panjang string boleh berubah (field size di-recalculate otomatis),
> tapi **jumlah baris dan kolom tidak boleh berubah** (tool menolak sel di luar jangkauan).

### B. Layout `.spm` (config, command, scenario_menu, dll)

Gunakan mode `apply-spm` (lihat atas). File SPM ber-layout binary (magic `SPM VER-2.02`);
string di dalamnya adalah nama layer + tooltip, encoding dideteksi otomatis.

**Label bergambar:** sebagian besar label SPM dirender dari **tekstur PNG**
(`romfs/System/*.png`, misal `ConfigMenu01.png`). Untuk label bergambar, gunakan alur
`audit-png` → `export-png` → edit di Photoshop → `pack-png` (lihat cara C di atas).

---

## Checklist Prioritas Terjemahan UI

1. [ ] `Config/event.datu8` — 216 judul scenario (tampil di Scenario Mode & backlog)
2. [ ] `Config/eventtype.datu8` — 12 label tipe event
3. [ ] `System/scenario_menu.spm` — nama karakter & label menu scenario
4. [ ] `System/command.spm` — menu perintah in-game
5. [ ] `System/config.spm` + `Config/buttonex.datu8` — layar settings
6. [ ] `Config/button.datu8` — 296 tooltip tombol
7. [ ] `System/checkwindow.spm` — popup Ya/Tidak
8. [ ] `Config/char.datu8` — nama karakter
9. [ ] Sisanya: save/load/titlebar/tabbar/extramode (opsional)
