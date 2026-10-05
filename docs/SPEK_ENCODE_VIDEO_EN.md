# Movie Video Encode Specification — DC3PS (NeXAS Switch)

> 🇮🇩 Indonesian version: [SPEK_ENCODE_VIDEO.md](SPEK_ENCODE_VIDEO.md)
>
> 🔄 Aligned with the D.C.4 FD specification:
> [DC4FD-NeXAS-Script-Tool / docs / SPEK_ENCODE_VIDEO_EN.md](https://github.com/SakuraSymphonyReTranslation/DC4FD-NeXAS-Script-Tool/blob/main/docs/SPEK_ENCODE_VIDEO_EN.md)
> (revision v2.1, Oct 2026) — same goal: **lightweight and stable on other
> devices** (entry-mid mobile SoCs on emulators).

This specification is derived directly from probing (`ffprobe`) all 40 original
files in DC3PS `romfs/Movie/` — used as the reference for producing
Indonesian-subtitled/hardsubbed videos to be shipped in the patch mod
(`Movie/` folder).

---

## Verified Original Data (ffprobe, 40 files)

| File group | Video | Audio |
|---|---|---|
| `dc3_v1.mp4` | H.264 Main@L4.0, 1920x1080, yuv420p, **~23.976 fps**, ~2.2 Mbps | AAC-LC 44.1 kHz stereo ~162 kbps |
| `dc3_v2/v3_*/v4/v5/v6.mp4` (OP & big events) | H.264 Main@L4.0, 1920x1080, yuv420p, **~29.97 fps**, ~2.9–8.1 Mbps | AAC-LC 48 kHz stereo ~160 kbps |
| `ed_*.mp4`, `stageed.mp4` (ED) | H.264 Main@L4.0, 1920x1080, yuv420p, **~23.976 fps**, ~0.4–2.4 Mbps | AAC-LC 48 kHz stereo ~163 kbps |
| `phase*.mp4`, `shot*.mp4`, `shar01.mp4` (short events) | H.264 Main@L4.0, 1920x1080, yuv420p, **~29.97 fps**, ~1.8–18.6 Mbps | AAC-LC 48 kHz stereo ~148–164 kbps |

Consistency conclusion: every shipped movie is **1920x1080, H.264 Main@L4.0,
yuv420p, AAC-LC stereo** — but the **frame rate is mixed** (`~23.976` for
`dc3_v1` + all EDs, `~29.97` for the other OPs/events; `ed_last.mp4` uses exact
30 fps). Audio is 44.1 kHz in `dc3_v1.mp4`, 48 kHz elsewhere.
All files: MP4 container, brand `isom` (encoder tag "Prism"), box layout
`ftyp|free|mdat|moov` (moov at the end).

⚠️ Revision note: the old version of this document claimed "Main@L4.1, 24 fps
CFR, a single OP named `dc3ps_op.mp4`" — this does not match the probe. No
DC3PS file is named `dc3ps_op.mp4`, every profile is **Main@L4.0**, and the
frame rates are not uniform. Use the table above.

---

## Mandatory Encode Target (lyric/text video replacing a Movie file)

> ⚠️ **Revision v2 (Oct 2026).** Mimicking the original bitrate (3–18 Mbps)
> proved **too heavy for emulators on mobile SoCs** (Snapdragon 6 Gen 1 /
> Helio G99 on Citron): decoding drops frames, so burned-in lyrics/text feel
> rushed compared to the audio. The target below replaces it.
>
> ⚠️ **Revision v2.1.** Resolution must **NOT** be lowered: the NeXAS engine
> draws movies **1:1 with no scaling** — a 720p video appears as a window of
> about 2/3 of the screen in the top-left corner (verified on Citron). Decode
> reliability is achieved via **low bitrate + lightweight decode parameters**,
> not resolution.

```
Video codec   : H.264, profile High, level 4.0
Resolution    : 1920x1080 — MANDATORY (engine draws 1:1, no scaling)
Pixel format  : yuv420p
Frame rate    : FOLLOW THE SOURCE — no `-r`, no forced CFR (`-fps_mode passthrough`)
Video bitrate : CRF 22 + maxrate 4M + bufsize 8M, x264 ref=2 bframes=2 (±3–4 Mbps)
Audio codec   : AAC-LC, 48000 Hz, 2 channels, 160 kbps
Container     : MP4, +faststart
Duration      : same as the master (A/V timing untouched)
```

### Ready-to-use ffmpeg command

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

Notes:
- **Never add `-r 24`** (or an `fps=24` filter) to a lyric video. Source
  timestamps are passed through as-is (`-fps_mode passthrough`) so lyric-vs-audio
  sync matches the master exactly. DC3PS source files have mixed frame rates
  (±23.976 / ±29.97) — passthrough follows each file automatically.
- `-movflags +faststart` (moov at the front) is chosen even though the original
  files use `ftyp|free|mdat|moov` (moov at the end): the NeXAS Switch engine is
  known to accept both (the DC4FD original ED files also have moov at the
  front), and moov-first is safer for streaming/loading. The most conservative
  alternative is to mirror the original layout — both are accepted.
- `-map_metadata -1` + `+bitexact` keeps the output deterministic, without
  encoder metadata (the "Prism" tag etc.) the engine does not need.

---

## Why Heavy Encodes Feel Out of Sync on Emulators (v2 analysis)

- Heavy original files: 1080p up to ~18.6 Mbps Main@L4.0 → large decode load.
  On an emulator the game's video decoder runs on the CPU alongside the game +
  rendering; entry-mid SoCs cannot keep up in real time → video frames get
  skipped → burned-in lyrics/text drift late versus audio.
- The original file structure itself is **correct**: A/V `start_time` = 0,
  consistent A/V durations, and the stock frame rates (±23.976/±29.97) are not
  the problem. Quick test: if the shipped Japanese movies also desync on
  Citron, the cause is 100% decode load (not fps).
- **Verified on Citron (SD 6 Gen 1)**: dropping the bitrate to ~3 Mbps with
  High profile + `ref=2` restores sync without changing timing. Resolution
  stays 1080p — a test 720p video appears small in the top-left corner
  (the engine draws movies 1:1 with no scaling).

---

## Original Bitrate by Content (reference, not the target)

Original DC3PS files span a wide bitrate range; our lightweight encode
(CRF 22, ±3–4 Mbps) is deliberately below all of them:

| Content | Original bitrate (rough size) |
|---|---|
| `dc3_v1` (OP ~151 s) | ~2.2 Mbps |
| `dc3_v2`–`dc3_v6` (OP/events ~103–280 s) | ~2.9–8.1 Mbps |
| `ed_*.mp4` / `stageed.mp4` (ED) | ~0.4–2.4 Mbps |
| `phase*.mp4` (system cutscenes) | ~4.2–14.6 Mbps |
| `shot*.mp4` (in-game events) | ~5.6–18.6 Mbps (heaviest: shot007_x) |

For very high-motion content (phase001, shot007_x, shot005_2) CRF 22 at
`-preset medium` sometimes exceeds the 4M maxrate — that is normal (maxrate
acts as a per-burst cap); the result is still far lighter than the original.

---

## FPS Above 24/30 — Testing (optional)

- Stock DC3PS movies run at ±23.976 fps (OP `dc3_v1`, all EDs) and ±29.97 fps
  (other OPs/events). There is **no evidence yet** whether the NeXAS engine
  forces a specific fps or follows container timestamps.
- To test, two ways exist to build a **60 fps** variant from the master:
  - **Quick test (frame duplication, no artifacts, minutes-long encode):** just
    add the `fps=60` filter (no scale — resolution must stay 1080p).
  - **Quality (motion-compensated interpolation, long encode):**

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

- How to read the results on an emulator:
  - **60 fps smooth + lyrics stay in sync** → the engine follows timestamps;
    the 60 fps variant is fine (only on powerful devices).
  - **Video stretches / lyrics drift later** → the engine forces the original
    fps; ship the passthrough variant (the main file) and discard the
    high-fps one.
  - **60 fps stutters** (expected on entry-mid SoCs; 2–2.5x the decode load) →
    keep passthrough; 30–50 fps is the realistic range for mid-range devices.

---

## Patch Integration Rules

1. The file name must be **exactly** the one being replaced (the engine loads by
   RomFS path, e.g. `Movie/dc3_v2.mp4` → override as `dc3_v2.mp4`).
2. Place it in the LayeredFS patch: `romfs/Movie/<original_name>.mp4` →
   overrides the original file.
3. Do not lengthen or shorten the duration; lyric sync is built inside the
   original duration.
4. Hardsub (animated/burned-in lyrics) is used instead of soft-sub: the engine
   does not read MP4 subtitle tracks.

---

## Packaging Plan Status (user decision)

- The base game is **not** merged into one big NSP (avoids redistributing copyrighted assets).
- The Indonesian patch (`.binu8` scripts + `system.datu8` + lyric videos) is packaged **separately** from the base.
- The final packaging format (LayeredFS ZIP vs installable package) will be
  followed up in a later session; the `exefs/main + romfs/patch.rom` pattern of
  the Shin engine (DC4) does **not** apply to DC3PS because DC3PS uses the
  NeXAS engine (purely per-file RomFS mods via LayeredFS).

---

## `main` Binary Investigation Results (NeXAS, technical evidence)

ExeFS extraction of the base NSP (titlekey from Eden's
`title.keys_autogenerated`, rights ID `010041601B544000000000000000000E`)
yields a 3.0 MB `main` (reference archive: `scratch/fd_main_reference.bin`).

Strings inside the binary prove:
- Present: `CNeXASMovie`, `MovieNXTextureMan`, `Script.dat`, `__GLOBAL.binu8`,
  `PlayerName.datu8`, `GenShinGo`, the `binu8`/`datu8` extensions — the engine
  reads RomFS files **one by one** via direct paths.
- Absent: the `ROM2` magic, the string `patch.rom`, or any patch-archive
  mechanism. (The DC4 `exefs/main + romfs/patch.rom` pattern is just the Shin
  engine's NSO code patch + that engine's own ROM2 archive.)

Conclusion: the only official modding path for DC3PS is **per-file LayeredFS**
(`.binu8` scripts, `system.datu8`, `Movie/*.mp4` videos) — a lyric video only
needs to replace `Movie/<original_name>.mp4` with the specification above.

Extraction notes (for reproduction):
```bash
hactoolnet -k prod.keys --titlekeys title.keys_autogenerated \
  <program.nca> --exefsdir <out>
# game titlekey: 43D847B6F317CF556DBFE942AC09C8D0 (from the ticket, encrypted)
```
