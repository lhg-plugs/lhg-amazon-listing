#!/usr/bin/env python3
"""lhg-amazon-listing 确定性 Listing 审计：16 条规则，零第三方依赖。

扫描目标目录下的 Listing 文档（.md / .txt），检查：
  - 红线：违禁/高风险宣称词、标题促销用语与极限词、
    Search Terms 超 250 字节、Search Terms 含 ASIN（blocker）
  - 规范：标题超 200 字符、标题缺核心关键词、标题重复词、
    五点描述不足 5 条、单条 bullet 超 500 字符、
    Search Terms 重复词、Search Terms 与标题高度重叠、
    图片数量/尺寸不达标、类目缺失（warning）
  - 完整性：产品描述过短、文档缺日期/版本（nit）

输入文档约定（命令与 skill 会按此结构产出，审计也兼容近似结构）：
  ## 标题 / ## 核心关键词 / ## 五点描述 / ## Search Terms /
  ## 图片 / ## 类目 / ## 产品描述

输出 JSON 与人类可读报告；有 blocker 时 exit 2，纯 warning 时 exit 1
（--fail-on blocker 可把 warning 降为通过），干净时 exit 0。

用法：
    python3 amazon_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning]

规则文案与检测逻辑均为本项目原创（高层思路参考 Amazon 官方卖家帮助文档
的公开规范要求，实现与文案独立撰写；详见 ATTRIBUTION.md）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-amazon-listing/listing-audit"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", "out",
}
SCAN_EXTS = {".md", ".txt", ".markdown"}

RULES = []


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        RULES.append({
            "id": rule_id, "severity": severity, "category": category,
            "title": title, "detail": detail, "check": fn,
        })
        return fn
    return deco


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file",
                 "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def parse_sections(lines):
    sections = []
    cur_head, cur_start, cur_body = "(全文)", 0, []
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^#{1,3}\s+(.*\S)\s*$", ln)
        if m:
            sections.append((cur_head, cur_start, cur_body))
            cur_head, cur_start, cur_body = m.group(1).strip(), i, []
        else:
            cur_body.append((i, ln))
    sections.append((cur_head, cur_start, cur_body))
    return sections


def sections_matching(sections, *keywords):
    return [(h, s, b) for h, s, b in sections
            if any(k in h for k in keywords)]


def section_text(body):
    return "\n".join(ln for _, ln in body)


def get_title(doc):
    secs = sections_matching(doc["sections"], "标题")
    if not secs:
        return "", 0
    _, _, body = secs[0]
    for ln_no, ln in body:
        s = ln.strip().lstrip("-*0123456789. ").strip()
        if s and not s.startswith("|") and len(s) >= 4:
            return s, ln_no
    return "", 0


def get_keywords(doc):
    secs = sections_matching(doc["sections"], "核心关键词", "关键词")
    if not secs:
        return []
    text = section_text(secs[0][2])
    parts = re.split(r"[，,、;\s]+", text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 2][:20]


def get_bullets(doc):
    secs = sections_matching(doc["sections"], "五点描述", "Bullet")
    if not secs:
        return []
    out = []
    for ln_no, ln in secs[0][2]:
        m = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$", ln)
        if m:
            out.append((ln_no, m.group(1).strip()))
    return out


def get_search_terms(doc):
    secs = sections_matching(doc["sections"], "Search Terms", "搜索词")
    if not secs:
        return [], ""
    text = section_text(secs[0][2])
    clean = re.sub(r"[#*`>\-]", " ", text)
    parts = re.split(r"[，,、;；\s]+", clean)
    terms = [p.strip() for p in parts if p.strip()]
    return terms, text


def tokenize_title(title):
    parts = re.split(r"[，,、;\s|/\\()（）【】]+", title)
    return [p for p in parts if p]


# ---------------------------------------------------------------- 红线规则


VIO_CLAIM_RES = [
    re.compile(p, re.I) for p in (
        r"治愈", r"\bcures?\b", r"治疗.{0,4}(疾病|癌症|糖尿病)",
        r"预防.{0,4}(疾病|癌症)", r"FDA\s*approved", r"FDA\s*认证",
        r"\bguaranteed\b", r"100%\s*money\s*back",
        r"eco-friendly", r"environmentally friendly",
        r"biodegradable", r"\brecyclable\b", r"\bsustainable\b",
        r"non-toxic", r"\bbest\s*seller\b", r"bestseller",
        r"#1\s*best", r"number\s*1\s*seller",
    )
]


@rule("AMZ-VIO-001", "blocker", "违禁词",
      "Listing 出现违禁/高风险宣称词",
      "医疗功效宣称（治愈/治疗疾病）、FDA 背书、环保宣称"
      "（eco-friendly/可降解等无认证宣称）、Best Seller 自封，"
      "都是亚马逊高下架风险表述。命中即 blocker，必须删除。")
def check_vio_claim(doc):
    out = []
    for ln_no, ln in doc["lines"]:
        for rx in VIO_CLAIM_RES:
            m = rx.search(ln)
            if m:
                out.append(Finding(
                    "AMZ-VIO-001", "blocker", "违禁词",
                    "Listing 出现违禁/高风险宣称词", doc["rel"], ln_no,
                    ln.strip()[:80], "命中：%s → 删除或改写为中性描述" % m.group(0)))
                break
        if len(out) >= 8:
            break
    return out


TITLE_PROMO_RES = [
    re.compile(p, re.I) for p in (
        r"free\s*shipping", r"免邮", r"包邮", r"全新上市",
        r"热卖", r"清仓", r"\bsale\b", r"great\s*gift", r"best\s*gift",
        r"完美礼物", r"送礼佳品", r"限时抢购",
    )
]
TITLE_SUPER_RES = [re.compile(p) for p in (r"最", r"第一", r"顶级", r"首选", r"之王")]


@rule("AMZ-VIO-002", "blocker", "标题合规",
      "标题含促销用语或极限词",
      "亚马逊标题政策禁止促销用语（包邮/热卖/送礼佳品等）与主观绝对化表述"
      "（最/第一/顶级）。只在标题章节内检查。")
def check_title_promo(doc):
    title, ln_no = get_title(doc)
    if not title:
        return []
    out = []
    for rx in TITLE_PROMO_RES:
        m = rx.search(title)
        if m:
            out.append(Finding(
                "AMZ-VIO-002", "blocker", "标题合规",
                "标题含促销用语：%s" % m.group(0), doc["rel"], ln_no,
                title[:80], "删除促销用语，标题只写产品本身"))
            break
    for rx in TITLE_SUPER_RES:
        m = rx.search(title)
        if m:
            out.append(Finding(
                "AMZ-VIO-002", "blocker", "标题合规",
                "标题含极限词：%s" % m.group(0), doc["rel"], ln_no,
                title[:80], "删除极限词，用参数与事实代替"))
            break
    return out


@rule("AMZ-KW-001", "blocker", "关键词",
      "Search Terms 超 250 字节",
      "亚马逊后台 Search Terms 上限 250 字节（UTF-8），超限部分直接被截断丢弃。"
      "按 UTF-8 字节数计算。")
def check_kw_bytes(doc):
    terms, _ = get_search_terms(doc)
    if not terms:
        return []
    nbytes = len(",".join(terms).encode("utf-8"))
    if nbytes > 250:
        return [Finding(
            "AMZ-KW-001", "blocker", "关键词",
            "Search Terms 共 %d 字节，超过 250 字节上限" % nbytes,
            doc["rel"], 1, "",
            "删减到 250 字节内：先删重复词，再删与标题高度重叠的词")]
    return []


ASIN_RE = re.compile(r"\bB0[A-Z0-9]{8}\b")


@rule("AMZ-KW-004", "blocker", "关键词",
      "Search Terms 含 ASIN",
      "ASIN 不许出现在 Search Terms 里（会被判操纵搜索排名）。"
      "竞品品牌词同样禁止。")
def check_kw_asin(doc):
    terms, _ = get_search_terms(doc)
    out = []
    for t in terms:
        if ASIN_RE.search(t):
            out.append(Finding(
                "AMZ-KW-004", "blocker", "关键词",
                "Search Terms 含 ASIN：%s" % t, doc["rel"], 1, t,
                "删除 ASIN，用通用品类词代替"))
    return out


# ---------------------------------------------------------------- 规范规则


@rule("AMZ-TIT-001", "warning", "标题",
      "标题超过 200 个字符",
      "多数类目标题上限为 200 个字符，超限会被截断。"
      "按字符数计算（含中文）。")
def check_title_len(doc):
    title, ln_no = get_title(doc)
    if title and len(title) > 200:
        return [Finding(
            "AMZ-TIT-001", "warning", "标题",
            "标题 %d 个字符，超过 200 上限" % len(title), doc["rel"],
            ln_no, title[:80] + "...",
            "精简到 200 字符内：品牌+核心词+关键参数+规格")]
    return []


@rule("AMZ-TIT-002", "warning", "标题",
      "标题缺少核心关键词",
      "文档声明了核心关键词，但标题里一个都没出现 = 关键词研究白做了。"
      "标题必须包含至少 1 个核心关键词。")
def check_title_kw(doc):
    title, ln_no = get_title(doc)
    kws = get_keywords(doc)
    if title and kws:
        missing = [k for k in kws if k not in title]
        if len(missing) == len(kws):
            return [Finding(
                "AMZ-TIT-002", "warning", "标题",
                "标题未包含任何核心关键词", doc["rel"], ln_no,
                title[:80], "核心关键词：%s → 至少把第 1 个写进标题"
                % "、".join(kws[:5]))]
    return []


@rule("AMZ-TIT-003", "warning", "标题",
      "标题存在重复词",
      "同一词组在标题多次出现 = 关键词堆砌，会被降权且影响阅读。"
      "2-4 字词组出现 4 次及以上即告警。")
def check_title_repeat(doc):
    title, ln_no = get_title(doc)
    if not title:
        return []
    out = []
    compact = re.sub(r"\s+", "", title)
    for n in (4, 3, 2):
        seen = set()
        for i in range(len(compact) - n + 1):
            s = compact[i:i + n]
            if s in seen or re.fullmatch(r"[0-9a-zA-Z]+", s):
                continue
            seen.add(s)
            if compact.count(s) >= 4:
                out.append(Finding(
                    "AMZ-TIT-003", "warning", "标题",
                    "标题重复词：%s（出现 %d 次）" % (s, compact.count(s)),
                    doc["rel"], ln_no, title[:80],
                    "删减重复，同一词组保留 1-2 次"))
                break
        if out:
            break
    if not out and re.fullmatch(r"[A-Z0-9\s\-/.,]+", title) and len(title) > 10:
        out.append(Finding(
            "AMZ-TIT-003", "warning", "标题",
            "标题疑似全大写", doc["rel"], ln_no, title[:80],
            "标题禁止全大写，改为首字母大写"))
    return out


@rule("AMZ-BLT-001", "warning", "五点描述",
      "五点描述不足 5 条",
      "Bullet Points 是转化主战场，少于 5 条 = 卖点没讲透。"
      "凑满 5 条，每条讲 1 个卖点。")
def check_bullets_count(doc):
    secs = sections_matching(doc["sections"], "五点描述", "Bullet")
    if not secs:
        return []
    bullets = get_bullets(doc)
    if len(bullets) < 5:
        return [Finding(
            "AMZ-BLT-001", "warning", "五点描述",
            "五点描述只有 %d 条，不足 5 条" % len(bullets),
            doc["rel"], secs[0][1], "",
            "补足到 5 条：材质/功能/场景/规格/售后各 1 条")]
    return []


@rule("AMZ-BLT-002", "warning", "五点描述",
      "单条 bullet 超过 500 个字符",
      "单条 bullet 上限约 500 字符，超长会被截断且没人读完。"
      "一条 bullet 只讲一个卖点，超了就拆。")
def check_bullet_len(doc):
    out = []
    for ln_no, b in get_bullets(doc):
        if len(b) > 500:
            out.append(Finding(
                "AMZ-BLT-002", "warning", "五点描述",
                "单条 bullet %d 字符，超过 500 上限" % len(b),
                doc["rel"], ln_no, b[:80] + "...",
                "拆成两条或精简到 500 字符内"))
    return out


@rule("AMZ-KW-002", "warning", "关键词",
      "Search Terms 存在重复词",
      "重复词浪费宝贵的 250 字节。同一词出现 2 次及以上即告警。")
def check_kw_dup(doc):
    terms, _ = get_search_terms(doc)
    if not terms:
        return []
    seen, dups = set(), set()
    for t in terms:
        tl = t.lower()
        if tl in seen:
            dups.add(t)
        seen.add(tl)
    if dups:
        return [Finding(
            "AMZ-KW-002", "warning", "关键词",
            "Search Terms 重复词：%s" % "、".join(sorted(dups)[:5]),
            doc["rel"], 1, "", "去重，每个词只保留 1 次")]
    return []


@rule("AMZ-KW-003", "warning", "关键词",
      "Search Terms 与标题高度重叠",
      "标题里已有的词再写进 Search Terms = 浪费字节。"
      "重叠率超过 50% 即告警：Search Terms 应补充标题没有的长尾词。")
def check_kw_overlap(doc):
    title, _ = get_title(doc)
    terms, _ = get_search_terms(doc)
    if not title or not terms:
        return []
    title_tokens = tokenize_title(title)
    hit = 0
    for t in terms:
        if t in title or any(tt in t or t in tt for tt in title_tokens if len(tt) >= 2):
            hit += 1
    ratio = hit / len(terms)
    if ratio > 0.5:
        return [Finding(
            "AMZ-KW-003", "warning", "关键词",
            "Search Terms 与标题重叠率 %.0f%%（%d/%d）"
            % (ratio * 100, hit, len(terms)), doc["rel"], 1, "",
            "把重叠词换成标题没有的长尾词/场景词")]
    return []


@rule("AMZ-IMG-001", "warning", "图片",
      "图片数量不足 6 张",
      "主图 + 至少 5 张辅图（场景/细节/尺寸/包装/对比）是转化基础。"
      "图片章节中可识别的图片条目少于 6 即告警。")
def check_img_count(doc):
    secs = sections_matching(doc["sections"], "图片")
    if not secs:
        return []
    n = 0
    for _, ln in secs[0][2]:
        s = ln.strip()
        if re.match(r"^\s*[-*\d.]", ln) and s and len(s) > 2:
            if re.search(r"主图|辅图|场景|细节|\.jpg|\.png|image|图片", s, re.I):
                n += 1
    if n < 6:
        return [Finding(
            "AMZ-IMG-001", "warning", "图片",
            "图片只有 %d 张，不足 6 张" % n, doc["rel"], secs[0][1], "",
            "补足：主图+场景+细节+尺寸+包装+对比 ≥6 张")]
    return []


SIZE_RE = re.compile(r"(\d{3,5})\s*[x×*]\s*(\d{3,5})")


@rule("AMZ-IMG-002", "warning", "图片",
      "图片尺寸规范缺失或不达标",
      "主图建议 2000×2000 以上（支持缩放功能）。"
      "图片章节未声明尺寸，或任一张标注尺寸小于 2000px，即告警。")
def check_img_size(doc):
    secs = sections_matching(doc["sections"], "图片")
    if not secs:
        return []
    text = section_text(secs[0][2])
    sizes = SIZE_RE.findall(text)
    if not sizes:
        return [Finding(
            "AMZ-IMG-002", "warning", "图片",
            "图片章节未声明尺寸规范", doc["rel"], secs[0][1], "",
            "每张图标注尺寸，主图 ≥2000×2000")]
    small = [(w, h) for w, h in sizes if int(w) < 2000 or int(h) < 2000]
    if small:
        return [Finding(
            "AMZ-IMG-002", "warning", "图片",
            "图片尺寸不达标：%s（要求 ≥2000×2000）"
            % "、".join("%sx%s" % s for s in small[:3]),
            doc["rel"], secs[0][1], "", "重新导出 ≥2000px 的图片")]
    return []


@rule("AMZ-CAT-001", "warning", "类目",
      "Listing 缺少类目声明",
      "类目错放 = 流量错配。文档应有专门的类目章节声明目标类目节点。"
      "缺少类目章节即告警（机器无法判定类目是否放对，人工需复核）。")
def check_category(doc):
    if not sections_matching(doc["sections"], "类目"):
        if sections_matching(doc["sections"], "标题", "五点描述"):
            return [Finding(
                "AMZ-CAT-001", "warning", "类目",
                "Listing 缺少类目声明", doc["rel"], 1, "",
                "增加'类目'章节，写清目标类目节点路径")]
    return []


# ---------------------------------------------------------------- 完整性规则


@rule("AMZ-DESC-001", "nit", "描述",
      "产品描述过短",
      "产品描述建议 ≥200 字，补充 bullet 讲不下的品牌故事与使用场景。"
      "少于 200 字即提示。")
def check_desc(doc):
    secs = sections_matching(doc["sections"], "产品描述")
    if not secs:
        return []
    text = section_text(secs[0][2]).strip()
    if 0 < len(text) < 200:
        return [Finding(
            "AMZ-DESC-001", "nit", "描述",
            "产品描述仅 %d 字，建议 ≥200 字" % len(text),
            doc["rel"], secs[0][1], "", "补充品牌故事/使用场景/注意事项")]
    return []


@rule("AMZ-DOC-001", "nit", "规范",
      "文档缺少日期或版本",
      "Listing 文档应带日期/版本号，方便回溯哪一版对应哪次优化。")
def check_doc_meta(doc):
    if not re.search(r"日期|版本|20\d{2}[-/年]", doc["text"]):
        return [Finding(
            "AMZ-DOC-001", "nit", "规范",
            "文档缺少日期或版本", doc["rel"], 1, "",
            "在文档顶部加 日期 / 版本")]
    return []


# ---------------------------------------------------------------- 主流程


def audit_doc(path, root):
    text = read_text(path)
    lines = list(enumerate(text.split("\n"), 1))
    doc = {
        "path": path,
        "rel": os.path.relpath(path, root),
        "text": text,
        "lines": lines,
        "sections": parse_sections([ln for _, ln in lines]),
    }
    findings = []
    for r in RULES:
        try:
            findings.extend(r["check"](doc))
        except Exception as e:  # 单条规则出错不影响整体
            findings.append(Finding(
                r["id"], "nit", "引擎", "规则执行异常：%s" % e,
                doc["rel"], 0, "", ""))
    return findings


def main():
    ap = argparse.ArgumentParser(description="lhg-amazon-listing 确定性 Listing 审计")
    ap.add_argument("--target", required=True, help="待扫描目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning"],
                    default="blocker", help="达到该级别即非零退出")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    files = collect_files(target)
    findings = []
    for f in files:
        findings.extend(audit_doc(f, target))

    sev_rank = {"blocker": 0, "warning": 1, "nit": 2}
    findings.sort(key=lambda x: (sev_rank.get(x.severity, 3), x.file, x.line))
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    summary = {
        "tool": TOOL, "version": VERSION, "target": target,
        "files_scanned": len(files), "rules_run": len(RULES),
        "blocker": counts["blocker"], "warning": counts["warning"],
        "nit": counts["nit"],
    }

    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("lhg-amazon-listing Listing 审计：%s" % target)
        print("扫描 %d 个文件，运行 %d 条规则" % (len(files), len(RULES)))
        print("blocker=%d warning=%d nit=%d"
              % (counts["blocker"], counts["warning"], counts["nit"]))
        for f in findings:
            print("[%s][%s] %s:%s %s"
                  % (f.severity, f.rule_id, f.file, f.line, f.title))
            if f.snippet:
                print("    %s" % f.snippet)
            if f.detail:
                print("    → %s" % f.detail)

    if counts["blocker"] > 0:
        return 2
    if args.fail_on == "warning" and counts["warning"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
