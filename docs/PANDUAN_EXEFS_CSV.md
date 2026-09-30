# Panduan Workflow CSV ExeFS — Pesan Info DC3PS (NeXAS Switch)

> 🇬🇧 English version: [EXEFS_CSV_GUIDE_EN.md](EXEFS_CSV_GUIDE_EN.md)

Panduan ini menjelaskan alur kerja lengkap menerjemahkan **pesan info pojok kiri-bawah**
game Da Capo III Plus Story — teks yang muncul sesaat saat Quick Load/Quick Save/
Jump/Auto-save (mis. `QUICK 1番をロードしました`) — beserta cara mengelola file
`exefs_messages.csv`.

Pesan-pesan ini **tidak tersimpan di RomFS** (`.datu8`/`.spm`/`.png`), melainkan tertanam
di **executable game** (file `main` di area ExeFS, berformat NSO ter-kompresi LZ4).

---

## Ringkasan Alur

```text
Dump ExeFS (milikmu sendiri)          [main + main.npdm]
        │  salin ke scratch/exefs_dump/main
        ▼
1. SCAN     python exefs_patch_tool.py scan
        │  mencari string CSV di binary (auto-dekompresi NSO/LZ4)
        ▼
2. ISI CSV  edit scratch/exefs_messages.csv  (kolom indonesian_translation)
        │  atau tambah baris baru via:
        │  python exefs_patch_tool.py discover
        ▼
3. APPLY    python exefs_patch_tool.py apply
        │  hasil: scratch/exefs_patch/main  (NSO tanpa kompresi)
        ▼
4. PASANG   salin ke %APPDATA%\eden\exefs\010041601B544000\main
            (atau Atmosphere: atmosphere/exefs/<TID>/main)
```

Semua langkah 1–4 juga tersedia sebagai tombol **Scan ExeFS / ExeFS Apply /
Discover ExeFS** di GUI (`run_gui.bat`, tab *UI Translation*) dan sebagai komponen
**ExeFS** di tab *Build Patch Lengkap*.

---

## 1. Dump ExeFS (sekali di awal)

1. Dump ExeFS dari **salinan game resmi milikmu sendiri** (tool dump yang sama dengan
   saat mengekstrak RomFS). File yang dibutuhkan cukup `main` (+ `main.npdm` untuk arsip).
2. Salin ke `scratch/exefs_dump/main`.
3. **JANGAN pernah meng-upload file `main` ke mana pun** — itu kode berhak cipta.
   Folder dump & hasil patch sudah di-gitignore.

> Aman-aman: `exefs_patch_tool` TIDAK pernah menulis ke folder dump. Hasil patch selalu
> ditulis ke `scratch/exefs_patch/main`.

## 2. Scan

```bash
python exefs_patch_tool.py scan
```

- Tool membaca semua baris CSV, mencari `japanese_text` di image hasil dekompresi
  (encoding dicoba berurutan: **UTF-8 → Shift_JIS → UTF-16-LE**).
- Binary main game ini memakai **UTF-8**, jadi hit yang relevan adalah `[utf-8]`.
- Ukuran slot = panjang byte string JP asli — inilah budget maksimal terjemahanmu.

## 3. Mengisi `exefs_messages.csv`

Kolom:

| Kolom | Isi | Boleh diubah? |
|---|---|---|
| `japanese_text` | Kunci pencarian persis di binary | ❌ JANGAN diubah/dihapus/diurut ulang |
| `indonesian_translation` | Terjemahan (≤ panjang byte JP asli) | ✅ Bebas; kosong = aman (tidak diganti) |
| `keterangan` | Catatan fungsi string untuk manusia | ✅ Bebas (tidak dipakai tool) |

Aturan penting terjemahan (baca juga `scratch/exefs_messages_BACA_SAYA.txt` yang
dibuat otomatis oleh tool):

1. **Batas byte**: `len(terjemahan.encode('utf-8'))` harus ≤ `len(jp.encode('utf-8'))`.
   Kepanjangan → tool **SKIP** baris itu (aman, teks tetap Jepang) dan melaporkannya.
   Contoh: `番をロードしました` = 30 byte → muat untuk ` telah dimuat` (18 byte).
2. **Tanpa newline** dan tanpa karakter kontrol.
3. **Spasi di awal itu disengaja**: baris ber-prefix nomor (`番を…` = "…番") diterjemahkan
   dengan leading space karena menempel setelah angka di layar (`QUICK 1` + ` telah dimuat`).
4. **Perhatikan aspek Jepang**: `〜しました/ました` = "telah …", `〜しています` = "sedang …",
   `〜します` = "akan …". Jangan satukan makna yang berbeda (jangan semua jadi "dimuat").
5. **Waspadai string parsial**: beberapa kunci CSV adalah *potongan* string yang lebih
   panjang di binary (mis. `不足しています` adalah prefix dari `不足しています。`).
   Kunci potongan diurut dipatch SETELAH string utuhnya, jadi selalu utamakan
   menambahkan **kunci string utuh** dari hasil scan bila tersedia.
6. CSV disimpan sebagai **UTF-8** (boleh dengan BOM). Baris = 1 pasangan JP↔ID.

## 4. Discover — menambah string baru ke CSV

```bash
python exefs_patch_tool.py discover
```

- Tool memindai image dengan regex run-karakter Jepang, menyaring pesan (akhiran
  `しました/します/ません/…` + kata kunci seperti ロード/セーブ/ジャンプ), lalu **menambahkan
  baris JP baru** dengan terjemahan kosong (tidak mengubah baris lama).
- Kolom `keterangan` baris baru berisi penanda bahwa string itu hasil discover.
- Isi terjemahannya di CSV, lalu jalankan `apply`.

## 5. Apply

```bash
python exefs_patch_tool.py apply
```

- Mengganti setiap kemunculan string JP dengan terjemahan **dipad spasi** sampai
  panjang byte asli — offset binary tidak bergeser satu byte pun.
- Urutan patch: kunci terpanjang dulu, agar varian spesifik terganti sebelum fallback pendeknya.
- Log `[OK] 'kunci' -> 'terjemahan' xN [utf-8]` = sukses; `[SKIP]` = terjemahan
  kepanjangan di encoding itu (periksa aturan batas byte di atas).
- Hasil: `scratch/exefs_patch/main` (NSO valid, flags kompresi/hash dibersihkan).

## 6. Memasang ke emulator / konsol

| Target | Lokasi |
|---|---|
| Eden / Citron / Yuzu / Sudachi | `%APPDATA%\<emulator>\exefs\010041601B544000\main` |
| Ryujinx | Options → Manage Mods → ExeFS → pilih file `main` hasil patch |
| Atmosphere (Switch asli) | `atmosphere/exefs/010041601B544000/main` |

Hapus file `main` di lokasi itu untuk kembali ke teks Jepang asli.

> Crash saat boot? Hapus `main` hasil patch dari folder exefs emulator — game kembali normal.

---

## Komponen ExeFS di Builder Patch Lengkap

`build_full_patch.py` (dan tab *Build Patch Lengkap* di GUI) memiliki komponen `exefs`
yang menggabungkan langkah 5–6: patch dump → pasang otomatis ke Eden melalui
`--install`. Komponen ini **tidak ikut ZIP distribusi** (kode berhak cipta — setiap
pengguna harus dump & patch sendiri).

## Keamanan & Etika

- Dump & hasil patch ExeFS berisi kode berhak cipta: **jangan pernah di-upload atau dibagikan**.
- CSV terjemahan boleh dibagikan bebas (teks murni, bukan bagian game).
- Tool hanya menyentuh string pesan UI — bukan logika program.
