import re
import unicodedata

MAX_CHARS = 56

# Control code NeXAS.
# Control code tidak dihitung sebagai karakter layar.
CONTROL_CODE = re.compile(
    r'@(?:v[A-Za-z0-9_]+|h[A-Za-z0-9_]+|t\d+|n|k|g|d|b|e|o\d+|\*stamp@[A-Za-z0-9_]+@|r[^@]+@[^@]*@)'
)


def char_width(c):
    """Menghitung lebar visual karakter (Fullwidth / CJK = 2, Halfwidth / ASCII = 1)."""
    if c in '\u3000…「」『』・―〜～★☆♪※♥':
        return 2
    w = unicodedata.east_asian_width(c)
    if w in ('F', 'W'):
        return 2
    return 1


def visible_length(text):
    """Menghitung lebar kolom visual yang benar-benar terlihat di layar."""
    clean = CONTROL_CODE.sub("", text)
    return sum(char_width(c) for c in clean)


def tokenize(text):
    """
    Memisahkan teks menjadi token kata, whitespace, dan control code.
    Control code dipertahankan tetapi tidak dihitung.
    """

    pattern = re.compile(
        r'@(?:v[A-Za-z0-9_]+|h[A-Za-z0-9_]+|t\d+|n|k|g|d|b|e|o\d+|\*stamp@[A-Za-z0-9_]+@|r[^@]+@[^@]*@)'
        r'|\s+'
        r'|[^\s@]+'
    )

    return pattern.findall(text)


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
    text = re.sub(r'([「『\(\（]\s*)(?:@g[－\-])+\s*', r'\1', text)
    text = re.sub(r'^(?:@g[－\-])+\s*', '', text)
    text = re.sub(r'\s*(?:@g[－\-])+\s*([」』\)\）!?！？])', r'\1', text)
    text = re.sub(r'\s*(?:@g[－\-])+$', '', text)
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
    text = clean_gaiji_dashes(text)
    text = re.sub(r'(@[a-zA-Z0-9_*~]+)\s+(?=@)', r'\1', text)
    text = re.sub(r"(@[a-zA-Z0-9_]*\d)([A-Za-z\u00C0-\u024F])", r"\1 \2", text)
    text = re.sub(r"(@[kgd])([A-Za-z\u00C0-\u024F])", r"\1 \2", text)
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)+)\s+', r'\1 ', text)
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)+)\s*$', r'\1', text)
    text = re.sub(r'\s+((?:@[a-zA-Z0-9_*~]+)*[」』\)\）])', r'\1', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.rstrip()


def wrap_text(text, max_chars=MAX_CHARS, initial_width=0):
    """
    Auto-wrap cerdas dengan batas visual lebar karakter.

    - Mendukung initial_width jika teks merupakan sambungan kalimat sebelumnya (@k).
    - Mempertahankan indentasi \u3000 pada awal narasi.
    - Tidak memotong kata (kata yang tidak muat langsung turun utuh ke baris berikutnya).
    - Memperhitungkan karakter fullwidth sebagai 2 kolom tampilan.
    - Spasi dihitung.
    - @n digunakan sebagai line break.
    - @n lama dihapus dan posisi wrap dihitung ulang.
    - Control code tidak dihitung.
    """
    if not text:
        return text

    text = normalize_tags_and_spacing(text)

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

    # Hapus @n lama.
    text = text.replace("@n", "")

    tokens = tokenize(text)

    lines = []
    current = ""
    pending_space = ""

    for token in tokens:

        # Whitespace menjadi separator.
        if token.isspace():
            pending_space = token
            continue

        # Control code tidak dihitung sebagai karakter.
        if CONTROL_CODE.fullmatch(token):
            current += pending_space + token
            pending_space = ""
            continue

        # Token ini adalah teks/kata biasa.
        word = token

        separator = pending_space if current else ""
        candidate = current + separator + word

        eff_width = (initial_width if not lines else 0) + visible_length(candidate)

        if eff_width <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            elif initial_width > 0 and not lines:
                # Kata pertama tidak muat di sisa ruang baris sebelumnya,
                # langsung turun ke baris baru
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

    # Jangan membuat @n setelah baris terakhir.
    return "@n".join(lines)


def is_marker_line(line):
    """Mendeteksi marker ○00000000○ / ●00000000●."""
    return bool(re.fullmatch(r'\s*[○●].*[○●]\s*', line))


def process_line(line):
    """
    Memproses satu physical line.
    Tidak pernah membuat newline tambahan.
    """

    if not line.strip():
        return line

    # Marker tidak disentuh.
    if is_marker_line(line):
        return line

    # Pertahankan indentasi asli.
    leading_match = re.match(r'^\s*', line)
    leading = leading_match.group(0)

    body = line[len(leading):]

    if not body:
        return line

    return leading + wrap_text(body)


def process_file(input_file, output_file):

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []

    for line in lines:
        # Hilangkan newline physical line sementara.
        content = line.rstrip("\r\n")

        processed = process_line(content)

        # Selalu satu physical line.
        output_lines.append(processed)

    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
        for line in output_lines:
            f.write(line + "\n")

    print("Selesai.")
    print(f"Jumlah physical line input : {len(lines)}")
    print(f"Jumlah physical line output: {len(output_lines)}")
    print(f"Output: {output_file}")


def main():

    input_file = input("File input  : ").strip()
    output_file = input("File output : ").strip()

    process_file(input_file, output_file)


if __name__ == "__main__":
    main()