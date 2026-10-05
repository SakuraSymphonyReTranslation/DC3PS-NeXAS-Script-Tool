# Spesifikasi Encode Video Movie — DC3PS (NeXAS Switch)

> 🇬🇧 English version: [SPEK_ENCODE_VIDEO_EN.md](SPEK_ENCODE_VIDEO_EN.md)
>
> 🔄 Diselaraskan dengan spesifikasi D.C.4 FD:
> [DC4FD-NeXAS-Script-Tool / docs / SPEK_ENCODE_VIDEO.md](https://github.com/SakuraSymphonyReTranslation/DC4FD-NeXAS-Script-Tool/blob/main/docs/SPEK_ENCODE_VIDEO.md)
> (revisi v2.1, Okt 2026) — tujuan yang sama: **ringan dan stabil di device lain**
> (SoC mobile entry-mid pada emulator).

Spesifikasi ini diturunkan langsung dari probe (`ffprobe`) 40 file asli di
`romfs/Movie/` DC3PS — dipakai sebagai acuan membuat video berlirik/ber-teks
Indonesia yang nanti dimasukkan ke patch mod (folder `Movie/`).

---

## Data Asli Terverifikasi (probe ffprobe, 40 file)

| Kelompok file | Video | Audio |
|---|---|---|
| `dc3_v1.mp4` | H.264 Main@L4.0, 1920x1080, yuv420p, **~23,976 fps**, ~2,2 Mbps | AAC-LC 44,1 kHz stereo ~162 kbps |
| `dc3_v2/v3_*/v4/v5/v6.mp4` (OP & event besar) | H.264 Main@L4.0, 1920x1080, yuv420p, **~29,97 fps**, ~2,9–8,1 Mbps | AAC-LC 48 kHz stereo ~160 kbps |
| `ed_*.mp4`, `stageed.mp4` (ED) | H.264 Main@L4.0, 1920x1080, yuv420p, **~23,976 fps**, ~0,4–2,4 Mbps | AAC-LC 48 kHz stereo ~163 kbps |
| `phase*.mp4`, `shot*.mp4`, `shar01.mp4` (event pendek) | H.264 Main@L4.0, 1920x1080, yuv420p, **~29,97 fps**, ~1,8–18,6 Mbps | AAC-LC 48 kHz stereo ~148–164 kbps |

Kesimpulan konsistensi: seluruh movie bawaan = **1920x1080, H.264 Main@L4.0,
yuv420p, AAC-LC stereo** — tetapi **frame rate campur** (`~23,976` untuk
`dc3_v1` + semua ED, `~29,97` untuk OP/event lainnya; `ed_last.mp4` memakai
30 fps persis). Audio `dc3_v1.mp4` 44,1 kHz; sisanya 48 kHz.
Semua file: container MP4 brand `isom` (encoder tag "Prism"), struktur box
`ftyp|free|mdat|moov` (moov di belakang).

⚠️ Catatan revisi: doc versi lama menyebut "Main@L4.1, 24 fps CFR, satu OP
`dc3ps_op.mp4`" — tidak sesuai hasil probe. File DC3PS tidak ada yang
bernama `dc3ps_op.mp4`, profil semuanya **Main@L4.0**, dan fps-nya tidak
seragam. Gunakan tabel di atas.

---

## Target Encode Wajib (video lirik/teks pengganti file Movie)

> ⚠️ **Revisi v2 (Okt 2026).** Meniru bitrate asli (3–18 Mbps) terbukti
> **terlalu berat untuk emulator di SoC mobile** (Snapdragon 6 Gen 1 / Helio G99
> pada Citron): decode-nya drop frame sehingga teks/lirik terasa telanjur
> dibanding audio. Target di bawah menggantikannya.
>
> ⚠️ **Revisi v2.1.** Resolusi **TIDAK boleh diturunkan**: engine NeXAS
> menggambar movie **1:1 tanpa scaling** — video 720p tampil sebagai jendela
> ±2/3 layar di pojok kiri-atas (terbukti di Citron). Keandalan decode
> dikejar lewat **bitrate rendah + parameter decode ringan**, bukan resolusi.

```
Codec video   : H.264, profile High, level 4.0
Resolusi      : 1920x1080 — WAJIB (engine menggambar 1:1, tidak men-scale)
Pixel format  : yuv420p
Frame rate    : MENGIKUTI SUMBER — tanpa `-r`, tanpa paksaan CFR (`-fps_mode passthrough`)
Bitrate video : CRF 22 + maxrate 4M + bufsize 8M, x264 ref=2 bframes=2 (±3–4 Mbps)
Codec audio   : AAC-LC, 48000 Hz, 2 channel, 160 kbps
Container     : MP4, +faststart
Duration      : sama dengan master (timing A/V tidak diubah sama sekali)
```

### Perintah ffmpeg siap pakai

```bash
ffmpeg -i dc3_v2_indo_master.mp4 ^
  -map 0:v:0 -map 0:a:0 ^
  -fps_mode passthrough ^
  -c:v libx264 -profile:v high -level 4.0 -preset medium -tune animation ^
  -crf 22 -maxrate 4M -bufsize 8M -x264-params ref=2:bframes=2 -pix_fmt yuv420p ^
  -c:a aac -b:a 160k -ar 48000 -ac 2 ^
  -movflags +faststart ^
  -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact ^
  dc3_v2_indo_light.mp4
```

Catatan:
- **Jangan pernah menambahkan `-r 24`** (atau filter `fps=24`) pada video lirik.
  Timestamp sumber diteruskan apa adanya (`-fps_mode passthrough`) supaya
  sinkronisasi lirik vs audio persis mengikuti master. File sumber DC3PS
  fps-nya campur (±23,976 / ±29,97) — passthrough otomatis mengikuti masing-masing.
- `-movflags +faststart` (moov di depan) dipilih meski file asli memakai
  `ftyp|free|mdat|moov` (moov di belakang): engine NeXAS Switch diketahui
  menerima keduanya (file ED asli DC4FD juga memakai moov di depan), dan
  moov di depan lebih aman untuk streaming/loading. Alternatif paling konservatif
  adalah meniru layout asli — keduanya diterima engine.
- `-map_metadata -1` + `+bitexact` membuat output deterministik tanpa metadata
  encoder (tag "Prism" dsb.) yang tidak diperlukan engine.

---

## Kenapa Encode Berat Terasa Desinkron di Emulator (analisis v2)

- File asli berat: 1080p hingga ~18,6 Mbps Main@L4.0 → beban decode besar. Di
  emulator, decoder video game berjalan di CPU bersama game + rendering; SoC
  entry-mid tidak real-time → frame video terlewat → lirik/teks (yang ter-burn
  ke gambar) tampak makin telat dibanding audio.
- Struktur file asli sendiri **benar**: A/V `start_time` = 0, durasi A/V
  konsisten, dan fps bawaan (±23,976/±29,97) tidak bermasalah. Uji cepat: kalau
  movie Jepang bawaan juga desinkron di Citron, penyebabnya 100% beban decode
  (bukan fps).
- **Terverifikasi di Citron (SD 6 Gen 1)**: menurunkan bitrate ke ~3 Mbps
  dengan profil High + `ref=2` membuat video sinkron lagi, tanpa mengubah
  timing. Resolusi tetap 1080p — video 720p uji tampil kecil di pojok kiri-atas
  (engine menggambar movie 1:1 tanpa scaling).

---

## Bitrate Asli per Konten (referensi, bukan target)

File asli DC3PS punya rentang bitrate lebar; encode ringan kita (CRF 22,
±3–4 Mbps) sengaja lebih rendah dari semuanya:

| Konten | Bitrate asli (ukuran kasar) |
|---|---|
| `dc3_v1` (OP ~151 dtk) | ~2,2 Mbps |
| `dc3_v2`–`dc3_v6` (OP/event ~103–280 dtk) | ~2,9–8,1 Mbps |
| `ed_*.mp4` / `stageed.mp4` (ED) | ~0,4–2,4 Mbps |
| `phase*.mp4` (cutscene sistem) | ~4,2–14,6 Mbps |
| `shot*.mp4` (event in-game) | ~5,6–18,6 Mbps (paling berat: shot007_x) |

Untuk konten gerak sangat tinggi (phase001, shot007_x, shot005_2) CRF 22 pada
`-preset medium` kadang melebihi maxrate 4M — itu normal (maxrate bekerja
sebagai cap per burst), hasil akhir tetap jauh lebih ringan dari asli.

---

## FPS di Atas 24/30 — Pengujian (opsional)

- Movie bawaan DC3PS ±23,976 fps (OP `dc3_v1`, semua ED) dan ±29,97 fps
  (OP/event lain). **Belum ada bukti** apakah engine NeXAS memaksa fps tertentu
  atau mengikuti timestamp kontainer.
- Untuk menguji, tersedia dua cara membuat varian **60 fps** dari master:
  - **Tes cepat (duplikasi frame, tanpa artefak, encode menit):** cukup tambahkan
    filter `fps=60` (tanpa scale — resolusi harus tetap 1080p).
  - **Kualitas (interpolasi motion-compensated, encode lama):**

```bash
ffmpeg -i dc3_v2_indo_master.mp4 ^
  -vf "minterpolate=fps=60:mi_mode=mci:scd=fdiff:scd_threshold=10" ^
  -c:v libx264 -profile:v high -level 4.0 -preset medium -tune animation ^
  -crf 22 -maxrate 4M -bufsize 8M -x264-params ref=2:bframes=2 -pix_fmt yuv420p ^
  -c:a aac -b:a 160k -ar 48000 -ac 2 ^
  -movflags +faststart ^
  -map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact ^
  dc3_v2_indo_60fps_test.mp4
```

- Cara membaca hasil tes di emulator:
  - **60 fps mulus + lirik tetap sinkron** → engine mengikuti timestamp; boleh
    pakai varian 60 fps (hanya untuk device kuat).
  - **Video melar / lirik makin telat** → engine memaksa fps asli; pakai varian
    passthrough (file utama), buang varian fps tinggi.
  - **60 fps tersendat** (wajar di SoC entry-mid; beban decode 2–2,5× lipat) →
    tetap pakai passthrough; 30–50 fps pilihan realistis untuk device menengah.

---

## Patch Integration Rules

1. Nama file **harus persis** sama dengan yang digantikan (engine memuat
   berdasarkan path RomFS, mis. `Movie/dc3_v2.mp4` → override dengan nama
   `dc3_v2.mp4`).
2. Ditempatkan di patch LayeredFS: `romfs/Movie/<nama_asli>.mp4` → meng-override
   file asli.
3. Jangan menambah/mengurangi durasi; sinkronisasi lirik dibuat di dalam durasi asli.
4. Hardsub (lirik dianimasikan/dibakar ke frame) dipilih, bukan soft-sub:
   engine tidak membaca track subtitle MP4.

---

## Status Rencana Packaging (keputusan pengguna)

- Base game **tidak digabung** ke dalam satu NSP besar (menghindari redistribusi aset berhak cipta).
- Patch Indo (skrip `.binu8` + `system.datu8` + video lirik) dikemas **terpisah** dari base.
- Format packaging final (LayeredFS ZIP vs paket installable) akan ditindaklanjuti
  pada sesi berikutnya; opsi pola `exefs/main + romfs/patch.rom` milik engine Shin (DC4)
  **tidak berlaku** untuk DC3PS karena DC3PS memakai engine NeXAS (mod murni per-file RomFS via LayeredFS).

---

## Hasil Investigasi Binary `main` NeXAS (bukti teknis)

Ekstraksi ExeFS base NSP (titlekey dari `title.keys_autogenerated` Eden,
rights ID `010041601B544000000000000000000E`) menghasilkan `main` 3.0 MB
(arsip referensi: `scratch/fd_main_reference.bin`).

String di dalam binary membuktikan:
- Ada: `CNeXASMovie`, `MovieNXTextureMan`, `Script.dat`, `__GLOBAL.binu8`,
  `PlayerName.datu8`, `GenShinGo`, ekstensi `binu8`/`datu8` — engine membaca
  file RomFS **satu per satu** dengan path langsung.
- Tidak ada: magic `ROM2`, string `patch.rom`, atau mekanisme arsip patch.
  (Pola `exefs/main + romfs/patch.rom` versi DC4 hanyalah patch kode NSO
  milik engine Shin + arsip ROM2 engine itu juga.)

Kesimpulan: satu-satunya jalur mod resmi untuk DC3PS adalah **LayeredFS per-file**
(script `.binu8`, `system.datu8`, video `Movie/*.mp4`) — dan video lirik hanya
perlu menggantikan `Movie/<nama_asli>.mp4` dengan spesifikasi di atas.

Catatan teknis ekstraksi (untuk reproduksi):
```bash
hactoolnet -k prod.keys --titlekeys title.keys_autogenerated \
  <program.nca> --exefsdir <out>
# titlekey game: 43D847B6F317CF556DBFE942AC09C8D0 (dari tik, ter-enkripsi)
```
