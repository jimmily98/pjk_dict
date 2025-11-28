from flask import Flask, render_template, request
import csv
import json
from collections import defaultdict

app = Flask(__name__)

CSV_PATH = "guangyun_with_all_readings.csv"

# ================================
# 读取基础广韵 + 拼音数据
# ================================
def load_data(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

rows = load_data(CSV_PATH)

# ================================
# 读取频率表（提前生成）
# ================================
with open("mandarin_freq_all.json", "r", encoding="utf-8") as f:
    mandarin_freq = json.load(f)

with open("cantonese_freq_all.json", "r", encoding="utf-8") as f:
    cantonese_freq = json.load(f)


# ================================
# 建立 {读音 : [字]} 索引
# ================================
def build_index(rows, key):
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


# ================================
# 过滤字是否常用
# ================================
def is_common_char(glyph, from_lang):
    """根据源语言决定用哪个字频过滤"""
    if from_lang == "普通话":
        return mandarin_freq.get(glyph, 0) > 0
    if from_lang == "粤语":
        return cantonese_freq.get(glyph, 0) > 0
    # 广韵 → 只要出现在广韵数据中即可
    return True


# ================================
# 工具：根据 key 获取字的所有读音
# ================================
def get_pronunciations(rows, char, key):
    return sorted({
        p.strip()
        for r in rows if r["glyph"] == char
        for p in r.get(key, "").replace("\n", "；").split("；")
        if p.strip()
    })


# ================================
# 核心：跨系统查询
# ================================
def compare_pronunciations(rows, from_lang, to_lang, char, filter_common):

    lang_map = {
        "普通话": "mandarin_pinyin",
        "粤语": "cantonese_jyutping",
        "广韵": "polyhedron中古全拼",
    }
    col_from = lang_map.get(from_lang)
    col_to = lang_map.get(to_lang)

    if not col_from or not col_to:
        return {"error": "无效语言选项"}

    # ==== 1. 输入字在源语言的所有读音 ====
    readings = get_pronunciations(rows, char, col_from)
    if not readings:
        return {"error": f"未找到「{char}」的 {from_lang} 读音"}

    # ==== 2. 找同音字 ====
    idx_from = build_index(rows, col_from)
    same_sound = sorted({glyph for p in readings for glyph in idx_from.get(p, [])})

    # ==== 3. 进行频率过滤 ====
    if filter_common:
        same_sound = [g for g in same_sound if is_common_char(g, from_lang)]

    # ==== 4. 目标语言 = 广韵 → 特殊折叠格式 ====
    if to_lang == "广韵":
        fold = defaultdict(list)

        for r in rows:
            g = r["glyph"]
            if g not in same_sound:
                continue

            mids = r.get("polyhedron中古全拼", "").replace("\n", "；").split("；")
            poses = r.get("广韵信息", "").replace("\n", "；").split("；")

            for mid, pos in zip(mids, poses):
                mid = mid.strip()
                pos = pos.strip()
                if mid and pos:
                    fold[(mid, pos)].append(g)

        grouped = {
            f"{mid}（{pos}）": "".join(lst)
            for (mid, pos), lst in fold.items()
        }

        return {
            "mode": "to_guangyun_fold",
            "readings": readings,
            "same_sound": same_sound,
            "groups_folded": grouped
        }

    # ==== 5. 普通话 / 粤语 输出 ====
    group = defaultdict(set)
    for r in rows:
        g = r["glyph"]
        if g not in same_sound:
            continue
        for p in r.get(col_to, "").replace("\n", "；").split("；"):
            if p.strip():
                group[p.strip()].add(g)

    return {
        "mode": "normal",
        "readings": readings,
        "same_sound": same_sound,
        "groups": {k: sorted(v) for k, v in sorted(group.items())}
    }


# ================================
# Flask 路由
# ================================
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    mode = "basic"
    char = ""
    from_lang = to_lang = ""
    filter_common = False

    if request.method == "POST":
        mode = request.form.get("mode")

        if mode == "basic":
            char = request.form.get("char_basic", "").strip()
            result = [r for r in rows if r["glyph"] == char]

        elif mode == "compare":
            char = request.form.get("char_compare", "").strip()
            from_lang = request.form.get("from_lang")
            to_lang = request.form.get("to_lang")
            filter_common = request.form.get("filter_common") == "on"

            result = compare_pronunciations(
                rows, from_lang, to_lang, char, filter_common
            )

    return render_template(
        "index.html",
        mode=mode,
        char=char,
        result=result,
        from_lang=from_lang,
        to_lang=to_lang,
        filter_common=filter_common
    )


if __name__ == "__main__":
    app.run(debug=True)
