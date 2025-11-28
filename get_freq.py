import pandas as pd
import json
from opencc import OpenCC

# ------------------------------
# 1. 读取普通话字频表
# ------------------------------

print("正在读取普通话字频表…")

df = pd.read_excel(
    "CharFreq-Modern.xls",
    sheet_name="CharFreq",
    skiprows=5,
    engine="xlrd"  
)

print("列名为：", df.columns.tolist())

# 假设列名确为 "汉字" 与 "频率"
mandarin_freq = {
    row["汉字"]: int(row["频率"])
    for _, row in df.iterrows()
    if isinstance(row["汉字"], str) and len(row["汉字"]) == 1
}

with open("mandarin_freq_raw.json", "w", encoding="utf-8") as f:
    json.dump(mandarin_freq, f, ensure_ascii=False, indent=2)

print("✔ 普通话字频导出成功：mandarin_freq_raw.json（简体）")

# ------------------------------
# 2. 读取粤语字频表
# ------------------------------

print("正在读取粤语字频表…")

df2 = pd.read_csv(
    "charcount.csv",
    skiprows=93,
    header=None,
    names=["字", "頻率"],
    encoding="utf-8"
)

print("列名为：", df2.columns.tolist())
cantonese_freq = {
    row["字"]: int(row["頻率"])
    for _, row in df2.iterrows()
    if isinstance(row["字"], str) and len(row["字"]) == 1
}

with open("cantonese_freq_raw.json", "w", encoding="utf-8") as f:
    json.dump(cantonese_freq, f, ensure_ascii=False, indent=2)

print("✔ 粤语字频导出成功：cantonese_freq_raw.json（繁体）")

# ------------------------------
# 3. 读取广韵字表 提取所有字形
# ------------------------------

print("正在读取广韵字表…")

df3 = pd.read_csv("guangyun_with_all_readings.csv", encoding="utf-8-sig")
glyph_list = sorted(set(df3["glyph"].tolist()))

print(f"✔ 从广韵数据库读取到 {len(glyph_list)} 个字形。")

# ------------------------------
# 4. 构建 mandarin_freq_all
# ------------------------------

def build_mandarin_freq_all(mandarin_freq_raw, glyph_list):
    t2s = OpenCC('t2s')  # 繁 → 简
    freq_all = {}
    for g in glyph_list:
        simp = t2s.convert(g)
        freq_all[g] = mandarin_freq_raw.get(simp, 0)
    return freq_all

mandarin_freq_all = build_mandarin_freq_all(mandarin_freq, glyph_list)

with open("mandarin_freq_all.json", "w", encoding="utf-8") as f:
    json.dump(mandarin_freq_all, f, ensure_ascii=False, indent=2)

print("✔ 普通话字频（全字集）已导出：mandarin_freq_all.json")

# ------------------------------
# 5. 构建 cantonese_freq_all
# ------------------------------

def build_cantonese_freq_all(cantonese_freq_raw, glyph_list):
    s2t = OpenCC('s2t')  # 简 → 繁
    freq_all = {}
    for g in glyph_list:
        trad = s2t.convert(g)
        freq_all[g] = cantonese_freq_raw.get(trad, 0)
    return freq_all

cantonese_freq_all = build_cantonese_freq_all(cantonese_freq, glyph_list)

with open("cantonese_freq_all.json", "w", encoding="utf-8") as f:
    json.dump(cantonese_freq_all, f, ensure_ascii=False, indent=2)

print("✔ 粤语字频（全字集）已导出：cantonese_freq_all.json")

# ------------------------------
# 6. 综合频率 overall_freq
# ------------------------------

overall = {
    g: max(mandarin_freq_all.get(g, 0), cantonese_freq_all.get(g, 0))
    for g in glyph_list
}

with open("overall_freq.json", "w", encoding="utf-8") as f:
    json.dump(overall, f, ensure_ascii=False, indent=2)

print("✔ 综合字频已导出：overall_freq.json")
print("🎉 全部频率表已成功生成！")
