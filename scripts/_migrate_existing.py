#!/usr/bin/env python3
"""One-shot migration for existing HTMLs in the workspace.

Reads from /Users/sidfate/AccioWork/2026-06-22-20-07-55/, injects the 5 required
meta tags if missing, copies to reports/2026-06/<category>/<date>_<name>.html,
copies kronos_output/ referenced PNGs to assets/kronos_output/, and rewrites
img src from `kronos_output/xxx.png` to `../../../assets/kronos_output/xxx.png`.

Run once from repo root:
    python3 scripts/_migrate_existing.py
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

SRC_DIR = Path("/Users/sidfate/AccioWork/2026-06-22-20-07-55")
REPO = Path(__file__).resolve().parent.parent
REPORTS = REPO / "reports"
ASSETS = REPO / "assets"

# filename -> (category, date, tags, summary)
MANIFEST = {
    "PCB三股投研汇报.html": (
        "个股",
        "2026-06-25",
        ["胜宏科技", "沪电股份", "鹏鼎控股", "PCB", "AI算力"],
        "PCB 三股综合排序沪电>胜宏>鹏鼎。均处 AI 算力 β 估值顶部，无安全边际。",
    ),
    "A股AI算力赛道研判.html": (
        "赛道",
        "2026-06-25",
        ["AI算力", "光模块", "PCB", "服务器", "IDC"],
        "全链基本面真景气估值已透支。18/25 龙头分位 90%+。真机会在服务器 ODM、IDC、铜连接。",
    ),
    "通信ETF光模块研判.html": (
        "ETF",
        "2026-06-26",
        ["通信ETF", "515880", "光模块", "中际旭创", "新易盛"],
        "中期逻辑未破，估值驱动的普涨大行情已结束。现价 1.798 是高位，等回踩 MA20。",
    ),
    "功率半导体潜力赛道研判.html": (
        "赛道",
        "2026-07-01",
        ["功率半导体", "国电南瑞", "上能电气", "汇川技术", "Kronos"],
        "本体过热，真潜力在上下游。三重共振 Top3：国电南瑞、上能电气、汇川技术。",
    ),
    "三股切换五层决策链_汇总.html": (
        "组合",
        "2026-07-01",
        ["国电南瑞", "汇川技术", "上能电气", "组合切换", "五层决策"],
        "三股 22-24% 仓位替代 AI 算力 β。AI 敞口 88% 降到 48-52%，最大回撤 -30% 腰斩 -12%。",
    ),
    "三股基本面深化_汇总.html": (
        "个股",
        "2026-06-30",
        ["国电南瑞", "汇川技术", "上能电气", "基本面"],
        "三股基本面深化分析汇总。估值分位、Q1 财报、ROE、订单端全景。",
    ),
    "三股切换_看跌汇报汇总.html": (
        "组合",
        "2026-06-30",
        ["三股切换", "看跌", "多空辩论"],
        "三股切换看跌方论证汇总。剪刀差、估值陷阱、Optimus 未落地等风险点。",
    ),
    "国电南瑞_看跌汇报.html": (
        "个股",
        "2026-06-29",
        ["国电南瑞", "600406", "看跌"],
        "国电南瑞看跌方论证。Q1 扣非仅 +5.4%，α 弹性一般，戴维斯双击难启动。",
    ),
    "胜宏沪电_看跌汇报.html": (
        "个股",
        "2026-06-25",
        ["胜宏科技", "沪电股份", "看跌"],
        "胜宏沪电看跌方论证。估值分位 99% 顶部，融资拥挤，业绩降档风险。",
    ),
}

META_TEMPLATE = """<meta name="report-title" content="{title}">
<meta name="report-date" content="{date}">
<meta name="report-category" content="{category}">
<meta name="report-tags" content="{tags}">
<meta name="report-summary" content="{summary}">"""


def inject_meta(html: str, title: str, date: str, category: str, tags: list, summary: str) -> str:
    # skip if all 5 already exist
    have = re.findall(r'<meta\s+name="(report-[a-z]+)"', html)
    needed = {"report-title", "report-date", "report-category", "report-tags", "report-summary"}
    if needed.issubset(set(have)):
        return html
    # remove any existing report-* metas to re-inject clean
    html = re.sub(r'\s*<meta\s+name="report-[a-z]+"\s+content="[^"]*"\s*/?>', "", html, flags=re.IGNORECASE)
    inject = META_TEMPLATE.format(
        title=title.replace('"', "&quot;"),
        date=date,
        category=category,
        tags=",".join(tags),
        summary=summary.replace('"', "&quot;"),
    )
    # insert after <meta charset ...> or after <head>
    m = re.search(r'(<meta\s+charset="[^"]+"[^>]*>)', html, re.IGNORECASE)
    if m:
        idx = m.end()
        return html[:idx] + "\n" + inject + html[idx:]
    return re.sub(r"(<head>)", r"\1\n" + inject, html, count=1, flags=re.IGNORECASE)


def rewrite_asset_paths(html: str) -> tuple[str, list]:
    """Rewrite kronos_output/xxx.png to ../../../assets/kronos_output/xxx.png; return list of referenced pngs."""
    refs = re.findall(r'(?:src|href)="kronos_output/([^"]+)"', html)
    html = re.sub(r'((?:src|href))="kronos_output/', r'\1="../../../assets/kronos_output/', html)
    return html, refs


def main() -> int:
    if not SRC_DIR.exists():
        print(f"[error] source dir missing: {SRC_DIR}")
        return 1

    ASSETS.mkdir(exist_ok=True)
    asset_kron_dir = ASSETS / "kronos_output"

    migrated = 0
    for fname, (category, date, tags, summary) in MANIFEST.items():
        src = SRC_DIR / fname
        if not src.exists():
            print(f"[skip] source missing: {fname}")
            continue

        month = date[:7]
        dst_dir = REPORTS / month / category
        dst_dir.mkdir(parents=True, exist_ok=True)

        # clean filename: replace spaces with underscore
        clean = fname.replace(" ", "_")
        dst = dst_dir / f"{date}_{clean}"

        html = src.read_text(encoding="utf-8")
        # infer real <title>
        tmatch = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        real_title = tmatch.group(1).strip() if tmatch else fname
        html = inject_meta(html, real_title, date, category, tags, summary)
        html, kron_refs = rewrite_asset_paths(html)

        for r in kron_refs:
            src_png = SRC_DIR / "kronos_output" / r
            if src_png.exists():
                asset_kron_dir.mkdir(parents=True, exist_ok=True)
                dst_png = asset_kron_dir / r
                if not dst_png.exists():
                    shutil.copy2(src_png, dst_png)

        dst.write_text(html, encoding="utf-8")
        print(f"[ok] {fname} -> {dst.relative_to(REPO)}")
        migrated += 1

    print(f"\nmigrated {migrated} report(s).")
    print(f"assets/kronos_output has {len(list(asset_kron_dir.glob('*.png'))) if asset_kron_dir.exists() else 0} png(s).")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
