# compare_pronunciation.py
import csv
from collections import defaultdict


CSV_PATH = "guangyun_with_all_readings.csv"

def load_data(path):
    """加载整张表"""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def build_index(rows, key):
    """建立 {读音: [字]} 索引"""
    index = defaultdict(list)
    for r in rows:
        val = r.get(key, "")
        if not val:
            continue
        for p in val.replace("\n", "；").split("；"):
            p = p.strip()
            if p:
                index[p].append(r["glyph"])
    return index

def get_pronunciations(rows, char, key):
    """获取单字所有读音"""
    return sorted({
        p.strip()
        for r in rows if r["glyph"] == char
        for p in r.get(key, "").replace("\n", "；").split("；")
        if p.strip()
    })

def compare_pronunciations(rows, from_lang, to_lang, char):
    """核心逻辑：A→B 查询"""
    lang_map = {
        "普通话": "mandarin_pinyin",
        "粤语": "cantonese_jyutping",
        "广韵": "polyhedron中古全拼",
    }

    if from_lang not in lang_map or to_lang not in lang_map:
        print("❌ 无效语言选项。可选：普通话、粤语、广韵")
        return

    col_from = lang_map[from_lang]
    col_to = lang_map[to_lang]

    # === Step 1: 获取输入字在源语言的读音 ===
    readings = get_pronunciations(rows, char, col_from)
    if not readings:
        print(f"⚠️ 未找到「{char}」的 {from_lang} 读音。")
        return

    print(f"\n🔍 查询方向：{from_lang} → {to_lang}")
    print(f"输入字：{char}")
    print(f"{from_lang} 读音：{'；'.join(readings)}")

    # === Step 2: 建立反查索引 ===
    idx_from = build_index(rows, col_from)

    # === Step 3: 找出同音字 ===
    same_sound_chars = sorted({c for r in readings for c in idx_from.get(r, [])})
    print(f"\n{from_lang} 同音字（共 {len(same_sound_chars)} 个）：{''.join(same_sound_chars)}")

    # === Step 4: 同音字在目标语言中的读音分组 ===
    group = defaultdict(set)
    for r in rows:
        g = r["glyph"]
        if g not in same_sound_chars:
            continue
        target_field = r.get(col_to, "")
        if not target_field:
            continue
        for p in target_field.replace("\n", "；").split("；"):
            if p.strip():
                group[p.strip()].add(g)

    # === Step 5: 输出结果 ===
    print(f"\n📘 {from_lang} → {to_lang} 对应：")
    if not group:
        print(f"⚠️ 这些字在 {to_lang} 中的发音未收录。")
        return

    for pron, chars in sorted(group.items()):
        print(f"  {to_lang}发音 {pron}: {''.join(sorted(chars))}")

if __name__ == "__main__":
    rows = load_data(CSV_PATH)
    print("=== 音韵查询系统 ===")
    print("支持方向：普通话→粤语、粤语→普通话、广韵→普通话、普通话→广韵、粤语→广韵、广韵→粤语")
    from_lang = input("请选择查询源语言（普通话/粤语/广韵）：").strip()
    to_lang = input("请选择目标语言（普通话/粤语/广韵）：").strip()
    char = input("请输入要查询的汉字：").strip()
    compare_pronunciations(rows, from_lang, to_lang, char)
