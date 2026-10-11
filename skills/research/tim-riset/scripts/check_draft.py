#!/usr/bin/env python
"""Pemeriksa draf naskah: key sitasi asing, panjang kalimat, jumlah kata.

Pakai:  python check_draft.py [folder-naskah]
Exit 1 bila ada key cite yang tidak ada di bibliography.bib.

Kenapa ada: penulis subagent gampang mengarang key sitasi atau menulis kalimat
>30 kata. Memeriksa manual seluruh naskah mahal; skrip ini menjawabnya sekali jalan
sebelum naskah dikirim ke reviewer. Angka "setiap %" juga gampang hilang penyebutnya,
itu urusan reviewer, bukan skrip ini.
"""
import glob, os, re, sys

MARKERS = ("01-referensi", "04-draf")


def find_root(start):
    """Naik ke atas sampai ketemu folder proyek yang punya 01-referensi dan 04-draf.

    Jangan hitung jumlah `dirname` tetap: kedalaman skrip berbeda antara salinan di
    skill dan salinan di proyek, dan salah hitung membuat bib tidak ketemu.
    """
    d = os.path.abspath(start)
    while True:
        if all(os.path.isdir(os.path.join(d, m)) for m in MARKERS):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and os.path.isdir(arg):
        root = find_root(arg) or find_root(os.path.dirname(arg))
        draf = os.path.abspath(arg)
    else:
        root = find_root(os.path.dirname(os.path.abspath(__file__))) or find_root(os.getcwd())
        draf = None

    if not root:
        print("Akar proyek tidak ditemukan: butuh folder berisi 01-referensi dan 04-draf")
        return 1
    draf = draf or os.path.join(root, "04-draf")
    bib = os.path.join(root, "01-referensi", "bibliography.bib")
    if not os.path.exists(bib):
        print("bibliography.bib tidak ditemukan: %s" % bib)
        return 1

    keys = set(re.findall(r"@\w+\{([^,]+),", open(bib, encoding="utf-8").read()))
    print("proyek: %s\nkey di bib: %d\n" % (root, len(keys)))

    # pola cite ditulis tanpa backslash literal supaya heredoc shell tidak merusaknya
    cite = re.compile(r"[\\]cite\{([^}]+)\}")
    skip = ("|", "#", "-", "*", ">", "[")
    bad_total = 0
    for f in sorted(glob.glob(os.path.join(draf, "*.md"))):
        t = open(f, encoding="utf-8").read()
        cited = set(x.strip() for c in cite.findall(t) for x in c.split(","))
        bad = sorted(c for c in cited if c and c not in keys)
        # tabel/heading/daftar/placeholder jangan dihitung sebagai kalimat prosa
        lines = [l for l in t.splitlines() if not l.lstrip().startswith(skip)]
        sents = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(lines)) if s.strip()]
        long30 = [s for s in sents if len(s.split()) > 30 and "[ISI" not in s]
        print("%-24s %5d kata | %2d key unik | key asing: %-10s | kalimat>30 kata: %d"
              % (os.path.basename(f), len(t.split()), len(cited), bad or "TIDAK ADA", len(long30)))
        bad_total += len(bad)
        for s in long30[:2]:
            print("      > %s..." % s[:120])
    print("\nTOTAL key asing: %d" % bad_total)
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
