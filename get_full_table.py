# get_full_table.py
import csv, re
from collections import defaultdict

CSV_IN = "kuankhiunn_guangyun.csv"
UNIHAN_READINGS = "Unihan_Readings.txt"
JYUTPING_TSV = "list.tsv"
CSV_OUT = "guangyun_with_all_readings.csv"

UNI_LINE = re.compile(r"^(U\+[0-9A-F]{4,6})\t(k[A-Za-z0-9]+)\t(.+)$")
PINYIN_RE = re.compile(r"[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+")

def parse_unihan_readings(path):
    """
    返回:
      readings[U+XXXX] = {
        "mandarin": set([...]),
        "cantonese": set([...])
      }
    综合多来源提取普通话/粤语多音；kSMSZD2003Readings 里提取 '粵xxx'。
    """
    target = {
        "kMandarin", "kHanyuPinyin", "kHanyuPinlu", "kTGHZ2013", "kXHC1983",
        "kCantonese", "kSMSZD2003Readings"
    }
    readings = defaultdict(lambda: {"mandarin": set(), "cantonese": set()})
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line or line.startswith("#"): 
                continue
            m = UNI_LINE.match(line.strip())
            if not m: 
                continue
            ucode, key, val = m.groups()
            if key not in target:
                continue

            if key in {"kMandarin", "kHanyuPinyin", "kHanyuPinlu", "kTGHZ2013", "kXHC1983"}:
                parts = re.split(r"[,\s;:()]+", val)
                for p in parts:
                    p = p.strip()
                    if p and PINYIN_RE.fullmatch(p):
                        readings[ucode]["mandarin"].add(p)

            elif key == "kCantonese":
                parts = re.split(r"[,\s;]+", val.strip())
                for p in parts:
                    if re.fullmatch(r"[a-z]+\d", p):
                        readings[ucode]["cantonese"].add(p)

            elif key == "kSMSZD2003Readings":
                # 如: "dàn粵daam6 xiáng粵hong4"
                jyuts = re.findall(r"粵([a-z]+\d)", val)
                readings[ucode]["cantonese"].update(jyuts)

    # 集合 → 分号分隔字符串
    for u, d in readings.items():
        d["mandarin"] = "；".join(sorted(d["mandarin"]))
        d["cantonese"] = "；".join(sorted(d["cantonese"]))
    return readings

def load_jyutping_table(path):
    """
    载入 jyutping-table/list.tsv：
      * 一字多行（多读音） -> 累加 set
      * 行形如：字 \t U+XXXX \t jyutping \t initial \t rime \t tone
      * 为稳妥：从行中查找第一个形如 [a-z]+[1-6] 的字段作为 jyutping
    返回: dict[char] = set({jyut...})
    """
    data = defaultdict(set)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            ch = parts[0]
            if not ch or len(ch) != 1:
                continue
            # 找到行内的所有 jyutping
            for field in parts[1:]:
                field = field.strip()
                if re.fullmatch(r"[a-z]+\d", field):
                    data[ch].add(field)
    return data

def main():
    # 1) 解析 Unihan（拼音）
    unihan = parse_unihan_readings(UNIHAN_READINGS)

    # 2) 解析 jyutping-table（补全粤音；多行多读音全纳入）
    jyut = load_jyutping_table(JYUTPING_TSV)

    # 3) 读入基础广韵 CSV
    with open(CSV_IN, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        base_rows = list(reader)

    # 4) 聚合同一 glyph 的多地位
    #    形成 entries[glyph] = {
    #        "unicode": U+XXXX (任选一致值),
    #        "triples": set of (广韵信息, 反切, romA),
    #    }
    entries = {}
    for r in base_rows:
        glyph = r["glyph"]
        if not glyph or len(glyph) != 1:
            continue
        u = r["unicode"].strip()

        # 广韵信息顺序：sjeng + xu + tonk + dew + hey （示例“匣江平二开”）
        guangyun_info = f"{r['sjeng']}{r['xu']}{r['tonk']}{r['dew']}{r['hey']}".strip()
        fanqie = (r.get("fanqie") or "").strip()
        romA = (r.get("polyhedron中古全拼") or "").strip()

        bundle = (guangyun_info, fanqie, romA)

        if glyph not in entries:
            entries[glyph] = {"unicode": u, "triples": set()}
        # 如果同一 glyph 出现不同 unicode（极少见），以首次为准
        entries[glyph]["triples"].add(bundle)

    # 5) 生成最终行：同字多地位 -> 同一行，多行对齐（以 \n 分隔）
    out_rows = []
    for glyph, info in entries.items():
        u = info["unicode"]
        triples = sorted(info["triples"], key=lambda t: (t[0], t[1], t[2]))

        # 对应列分开、多行对齐
        gy_lines  = [t[0] for t in triples if t[0]]
        fq_lines  = [t[1] for t in triples if t[1]]
        rom_lines = [t[2] for t in triples if t[2]]

        gy_cell  = "\n".join(gy_lines)
        fq_cell  = "\n".join(fq_lines)
        rom_cell = "\n".join(rom_lines)

        # —— 拼音合并 ——
        uni_p = unihan.get(u, {})
        mand = uni_p.get("mandarin", "")
        canton = uni_p.get("cantonese", "")

        # jyutping-table 以字为键，再并入
        if glyph in jyut:
            cand = set(canton.split("；")) if canton else set()
            cand.update(jyut[glyph])
            canton = "；".join(sorted(cand))

        out_rows.append({
            "glyph": glyph,
            "unicode": u,
            "广韵信息": gy_cell,
            "反切": fq_cell,
            "polyhedron中古全拼": rom_cell,
            "mandarin_pinyin": mand,
            "cantonese_jyutping": canton
        })

    # 6) 写出
    fieldnames = ["glyph", "unicode", "广韵信息", "反切", "polyhedron中古全拼",
                  "mandarin_pinyin", "cantonese_jyutping"]
    with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"✅ 已生成 {CSV_OUT}（{len(out_rows)} 行，每字聚合多地位 & 多读音）")

if __name__ == "__main__":
    main()
