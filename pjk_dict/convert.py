# convert.py
import sqlite3, csv
import re

DB = "kuankhiunn.sqlite"
OUT = "kuankhiunn_guangyun.csv"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

# 反切直接来自 syllables.cet；romA 是 Polyhedron 中古全拼
query = """
SELECT 
    k.glyph,
    s.sjeng,
    s.xu,
    s.hey,
    s.tonk,
    s.dew,
    s.romA,
    s.cet
FROM kuankhiunn AS k
JOIN syllables AS s ON k.cet = s.cet
WHERE k.glyph IS NOT NULL
"""

rows = cursor.execute(query).fetchall()
conn.close()

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "glyph", "unicode",
        "sjeng", "xu", "hey", "tonk", "dew",
        "polyhedron中古全拼", "fanqie"
    ])
    skipped = 0
    for glyph, sjeng, xu, hey, tonk, dew, romA, fanqie in rows:
        try:
            if not glyph or len(glyph) != 1:
                skipped += 1
                continue
            unicode_hex = f"U+{ord(glyph):04X}"
            writer.writerow([glyph, unicode_hex, sjeng, xu, hey, tonk, dew, romA or "", fanqie or ""])
        except Exception:
            skipped += 1
            continue

def load_unihan_variants(path):
    trad2simp = {}
    pattern = re.compile(r"U\+([0-9A-F]{4,5})")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("U+") or "kSimplifiedVariant" not in line:
                continue
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            trad_code = parts[0]
            variants = parts[2]
            trad_match = pattern.match(trad_code)
            if not trad_match:
                continue
            trad_char = chr(int(trad_match.group(1), 16))
            simp_codes = pattern.findall(variants)
            if simp_codes:
                simp_char = chr(int(simp_codes[0], 16))
                trad2simp[trad_char] = simp_char
    return trad2simp


def load_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames


def augment_with_simplified(csv_path, unihan_path):
    trad2simp = load_unihan_variants(unihan_path)
    rows, fieldnames = load_csv(csv_path)

    # 建立繁体 → [多行记录] 对应表
    trad_map = {}
    for row in rows:
        trad_map.setdefault(row["glyph"], []).append(row)

    added = 0
    new_rows = rows.copy()

    for trad, simp in trad2simp.items():
        if trad in trad_map and simp != trad and len(simp) == 1:
            for base_row in trad_map[trad]:
                new_row = base_row.copy()
                new_row["glyph"] = simp
                new_row["unicode"] = f"U+{ord(simp):04X}"
                new_rows.append(new_row)
                added += 1

    # === Step 4: 写回 CSV ===
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)


augment_with_simplified(csv_path="kuankhiunn_guangyun.csv",unihan_path="Unihan_Variants.txt")