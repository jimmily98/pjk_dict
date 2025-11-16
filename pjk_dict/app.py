from flask import Flask, render_template, request
import csv
from collections import defaultdict

app = Flask(__name__)

CSV_PATH = "guangyun_with_all_readings.csv"

def load_data(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

# 预加载数据与索引
rows = load_data(CSV_PATH)

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

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    mode = "basic"
    char = ""
    from_lang = to_lang = ""
    query_results = None

    if request.method == "POST":
        mode = request.form.get("mode")

        # 基础功能 1：简单查询
        if mode == "basic":
            char = request.form.get("char_basic", "").strip()
            query_results = [r for r in rows if r["glyph"] == char]

        # 基础功能 2：跨系统查询
        elif mode == "compare":
            char = request.form.get("char_compare", "").strip()
            from_lang = request.form.get("from_lang")
            to_lang = request.form.get("to_lang")
            query_results = compare_pronunciations(rows, from_lang, to_lang, char)

    return render_template(
        "index.html",
        mode=mode,
        char=char,
        result=query_results,
        from_lang=from_lang,
        to_lang=to_lang
    )

def get_pronunciations(rows, char, key):
    return sorted({
        p.strip()
        for r in rows if r["glyph"] == char
        for p in r.get(key, "").replace("\n", "；").split("；")
        if p.strip()
    })

def compare_pronunciations(rows, from_lang, to_lang, char):
    """核心逻辑：A→B 查询（新：广韵地位折叠显示）"""
    lang_map = {
        "普通话": "mandarin_pinyin",
        "粤语": "cantonese_jyutping",
        "广韵": "polyhedron中古全拼",
    }
    col_from = lang_map.get(from_lang)
    col_to = lang_map.get(to_lang)

    if not col_from or not col_to:
        return {"error": "无效语言选项"}

    # === Step 1: 获取输入字在源语言的所有读音 ===
    readings = get_pronunciations(rows, char, col_from)
    if not readings:
        return {"error": f"未找到「{char}」的 {from_lang} 读音"}

    # === Step 2: 找同音字 ===
    idx_from = build_index(rows, col_from)
    same_sound_chars = sorted({c for p in readings for c in idx_from.get(p, [])})

    # === Step 3: 目标语言是广韵：折叠输出 ===
    if to_lang == "广韵":
        # key = (中古拼音, 广韵地位)
        fold = defaultdict(list)

        for r in rows:
            g = r["glyph"]
            if g not in same_sound_chars:
                continue

            middle_list = r.get("polyhedron中古全拼", "").replace("\n", "；").split("；")
            pos_list    = r.get("广韵信息", "").replace("\n", "；").split("；")

            # 保证一一对应
            for mid, pos in zip(middle_list, pos_list):
                mid = mid.strip()
                pos = pos.strip()
                if mid and pos:
                    fold[(mid, pos)].append(g)

        # 输出结构： { "dex（定開四上齊）": "媞遞" }
        folded_output = {
            f"{mid}（{pos}）": "".join(lst)
            for (mid, pos), lst in fold.items()
        }

        return {
            "readings": readings,
            "same_sound": same_sound_chars,
            "groups_folded": folded_output,
            "mode": "to_guangyun_fold"
        }

    # === Step 4: 普通话 / 粤语：正常输出 ===
    group = defaultdict(set)
    for r in rows:
        g = r["glyph"]
        if g not in same_sound_chars:
            continue
        for p in r.get(col_to, "").replace("\n", "；").split("；"):
            if p.strip():
                group[p.strip()].add(g)

    return {
        "readings": readings,
        "same_sound": same_sound_chars,
        "groups": {k: sorted(v) for k, v in sorted(group.items())},
        "mode": "normal"
    }


if __name__ == "__main__":
    app.run(debug=True)
