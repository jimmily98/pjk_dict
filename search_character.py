import csv
import sys

CSV_PATH = "guangyun_with_all_readings.csv"

def search_character(char):
    results = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["glyph"] == char:
                results.append(row)
    return results

def print_results(results, char):
    if not results:
        print(f"没找到「{char}」的记录。")
        return
    print(f"查询结果（{char}）：")
    for i, r in enumerate(results, 1):
        print(f"Unicode: {r['unicode']}")
        print(f"普通话拼音:\n{r.get('mandarin_pinyin', '')}")
        print(f"粤拼 Jyutping:\n{r.get('cantonese_jyutping', '')}")
        print(f"Polyhedron 中古全拼:\n{r.get('polyhedron中古全拼', '')}")
        print(f"广韵地位:\n{r['广韵信息']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python search_character.py 汉字")
    else:
        char = sys.argv[1]
        results = search_character(char)
        print_results(results, char)
