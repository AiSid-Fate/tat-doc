#!/usr/bin/env python3
"""Build index.html for tat-doc.

Scans reports/**/*.html, extracts <title> and report-* meta tags, groups them
by category and month, then writes a dark financial-themed index page with
category filter chips.

Runs in GitHub Actions (see .github/workflows/pages.yml) and locally.
Uses only the Python 3 standard library.
"""

from __future__ import annotations

import html as htmllib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
OUTPUT = ROOT / "index.html"

CATEGORY_WHITELIST = ["个股", "赛道", "ETF", "组合", "宏观", "其他"]

META_RE = re.compile(
    r'<meta\s+name=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\']\s*/?>',
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass
class Report:
    path: Path            # relative to repo root, e.g. reports/2026-06/个股/xxx.html
    href: str             # url-encoded href for <a>
    title: str
    date: str             # YYYY-MM-DD
    category: str
    tags: List[str]
    summary: str
    month: str            # YYYY-MM


def read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def parse_report(html_path: Path) -> Report:
    text = read_text(html_path)
    metas = {name.lower(): content for name, content in META_RE.findall(text)}
    title_match = TITLE_RE.search(text)
    default_title = html_path.stem
    title = metas.get("report-title") or (title_match.group(1).strip() if title_match else default_title)

    # date: meta > filename prefix > file mtime
    date = metas.get("report-date", "").strip()
    fname_date = re.match(r"^(\d{4}-\d{2}-\d{2})_", html_path.name)
    if not date and fname_date:
        date = fname_date.group(1)
    if not date:
        ts = datetime.fromtimestamp(html_path.stat().st_mtime)
        date = ts.strftime("%Y-%m-%d")

    # category: meta > parent dir name > 其他
    category = metas.get("report-category", "").strip()
    if not category:
        parts = html_path.relative_to(REPORTS_DIR).parts
        category = parts[1] if len(parts) >= 2 else "其他"
    if category not in CATEGORY_WHITELIST:
        category = "其他"

    tags_raw = metas.get("report-tags", "")
    tags = [t.strip() for t in re.split(r"[,，、]", tags_raw) if t.strip()]

    summary = metas.get("report-summary", "").strip()
    if not summary:
        summary = "（未提供摘要，请在 HTML head 内加 <meta name=\"report-summary\">）"

    rel = html_path.relative_to(ROOT)
    href_parts = [urlpart_quote(p) for p in rel.parts]
    href = "/".join(href_parts)

    month = date[:7] if len(date) >= 7 else "unknown"

    return Report(
        path=rel,
        href=href,
        title=title,
        date=date,
        category=category,
        tags=tags,
        summary=summary,
        month=month,
    )


def urlpart_quote(s: str) -> str:
    # keep chinese chars; quote spaces and special chars
    from urllib.parse import quote
    return quote(s, safe="._-~()[]")


def scan_reports() -> List[Report]:
    if not REPORTS_DIR.exists():
        return []
    reports: List[Report] = []
    for path in sorted(REPORTS_DIR.rglob("*.html")):
        try:
            reports.append(parse_report(path))
        except Exception as exc:
            print(f"[warn] failed to parse {path}: {exc}", file=sys.stderr)
    reports.sort(key=lambda r: (r.date, r.title), reverse=True)
    return reports


# ------------- HTML rendering -------------

def esc(s: str) -> str:
    return htmllib.escape(s, quote=True)


SVG_ICONS = {
    "spark": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    "book": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 5a2 2 0 012-2h12v18H6a2 2 0 01-2-2z"/><path d="M8 7h6M8 11h6"/></svg>',
    "chart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><rect x="7" y="10" width="3" height="7"/><rect x="12" y="6" width="3" height="11"/><rect x="17" y="13" width="3" height="4"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    "tag": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12l-8 8-9-9V3h8z"/><circle cx="7" cy="7" r="1.5"/></svg>',
    "cat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
    "repo": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h11a4 4 0 014 4v12H8a4 4 0 01-4-4z"/><path d="M8 2v14M12 8h4"/></svg>',
}


def render_card(r: Report) -> str:
    tag_html = "".join(
        f'<span class="tg">{esc(t)}</span>' for t in r.tags[:6]
    )
    return f'''\
      <article class="card" data-category="{esc(r.category)}" data-date="{esc(r.date)}">
        <div class="c-head">
          <span class="pill p-{esc(r.category)}">{esc(r.category)}</span>
          <span class="c-date num">{esc(r.date)}</span>
        </div>
        <h3 class="c-title"><a href="{r.href}">{esc(r.title)}</a></h3>
        <p class="c-sum">{esc(r.summary)}</p>
        <div class="c-tags">{tag_html}</div>
        <a class="c-link" href="{r.href}">
          阅读全文 {SVG_ICONS["arrow"]}
        </a>
      </article>'''


def render_page(reports: List[Report]) -> str:
    total = len(reports)
    latest = reports[0].date if reports else "-"
    cats = sorted({r.category for r in reports}, key=lambda c: CATEGORY_WHITELIST.index(c) if c in CATEGORY_WHITELIST else 99)
    cat_counts = {c: sum(1 for r in reports if r.category == c) for c in cats}

    filter_html = f'''\
        <button class="chip active" data-filter="all" type="button">
          {SVG_ICONS["cat"]} 全部 <span class="num">{total}</span>
        </button>''' + "".join(
        f'\n        <button class="chip" data-filter="{esc(c)}" type="button">{esc(c)} <span class="num">{cat_counts[c]}</span></button>'
        for c in cats
    )

    cards_html = "\n".join(render_card(r) for r in reports) or (
        '<div class="empty">还没有报告。用 <code>scripts/publish_report.sh</code> 发布第一份。</div>'
    )

    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TAT 投研报告库 · tat-doc</title>
<style>
:root{{
  --bg:#0a0e14; --bg2:#0d1117; --surface:#11161f; --surface2:#161c28;
  --border:#1f2733; --border2:#2a3543;
  --text:#e6edf3; --text2:#aebacb; --text3:#7d8aa0;
  --up:#ff4d4f; --down:#16c784; --warn:#f5a623;
  --accent:#4c8dff; --accent-soft:#16243f; --gold:#caa23a; --gold-soft:#2e2410;
  --radius:14px; --shadow-1:0 1px 2px rgba(0,0,0,.4); --shadow-2:0 6px 20px rgba(0,0,0,.45);
  --mono:"SF Mono","JetBrains Mono","Roboto Mono",ui-monospace,Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:15px;line-height:1.6;
  -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(900px 500px at 80% -10%,rgba(76,141,255,.07),transparent 60%);
  background-attachment:fixed}}
.num{{font-variant-numeric:tabular-nums;font-family:var(--mono);letter-spacing:-.2px}}
.wrap{{max-width:1200px;margin:0 auto;padding:0 18px}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{opacity:.85}}

header{{padding:44px 0 24px}}
.eyebrow{{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--gold);background:var(--gold-soft);
  border:1px solid #5a4718;padding:6px 13px;border-radius:999px;font-weight:600}}
.eyebrow svg{{width:14px;height:14px}}
h1{{font-size:clamp(26px,4.4vw,40px);margin:20px 0 12px;letter-spacing:-.5px;
  background:linear-gradient(180deg,#fff,#aebacb);-webkit-background-clip:text;background-clip:text;color:transparent}}
.lead{{font-size:clamp(15px,2vw,17px);color:var(--text2);max-width:800px;line-height:1.7}}
.repo-link{{display:inline-flex;align-items:center;gap:7px;font-size:13px;color:var(--text2);
  background:var(--surface);border:1px solid var(--border);padding:7px 13px;border-radius:999px;margin-top:18px}}
.repo-link svg{{width:14px;height:14px;color:var(--text3)}}

.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:26px}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow-1)}}
.kpi .k{{font-size:12px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;display:flex;align-items:center;gap:6px}}
.kpi .k svg{{width:13px;height:13px}}
.kpi .v{{font-size:24px;font-weight:700;font-family:var(--mono);margin-top:6px}}
.kpi .s{{font-size:11.5px;color:var(--text3);margin-top:2px}}
.kpi .v.accent{{color:var(--accent)}} .kpi .v.gold{{color:var(--gold)}} .kpi .v.warn{{color:var(--warn)}}

.toolbar{{margin:32px 0 22px;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:14px 16px;box-shadow:var(--shadow-1);
  display:flex;flex-wrap:wrap;gap:10px;align-items:center;position:sticky;top:0;z-index:10;
  backdrop-filter:blur(8px)}}
.toolbar .lbl{{font-size:12px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;
  display:flex;align-items:center;gap:6px;margin-right:2px}}
.toolbar .lbl svg{{width:14px;height:14px}}
.chip{{background:var(--bg2);border:1px solid var(--border);color:var(--text2);padding:7px 13px;
  border-radius:999px;font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;
  display:inline-flex;align-items:center;gap:7px;transition:background .18s,color .18s,border-color .18s}}
.chip svg{{width:14px;height:14px}}
.chip:hover{{background:var(--surface2);color:var(--text)}}
.chip.active{{background:var(--accent-soft);color:var(--accent);border-color:#21345a}}
.chip .num{{color:var(--text3);font-size:12px;font-weight:400}}
.chip.active .num{{color:var(--accent)}}
.search{{margin-left:auto;background:var(--bg2);border:1px solid var(--border);border-radius:999px;
  padding:6px 14px;color:var(--text);font-size:13px;font-family:inherit;min-width:180px;flex:1;max-width:280px}}
.search:focus{{outline:2px solid var(--accent);outline-offset:1px;border-color:var(--accent)}}

.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;padding-bottom:40px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:20px;box-shadow:var(--shadow-1);display:flex;flex-direction:column;gap:10px;transition:border-color .18s,transform .18s}}
.card:hover{{border-color:var(--border2);transform:translateY(-2px)}}
.card[hidden]{{display:none}}
.c-head{{display:flex;justify-content:space-between;align-items:center}}
.pill{{display:inline-block;padding:3px 10px;border-radius:6px;font-size:11.5px;font-weight:700;font-family:var(--mono)}}
.p-个股{{background:var(--accent-soft);color:var(--accent)}}
.p-赛道{{background:#3a2e12;color:var(--warn)}}
.p-ETF{{background:#10302a;color:var(--down)}}
.p-组合{{background:var(--gold-soft);color:var(--gold);border:1px solid #5a4718}}
.p-宏观{{background:#3a1c1f;color:var(--up)}}
.p-其他{{background:var(--surface2);color:var(--text3)}}
.c-date{{font-size:12px;color:var(--text3)}}
.c-title{{font-size:16px;font-weight:700;line-height:1.4}}
.c-title a{{color:var(--text)}}
.c-title a:hover{{color:var(--accent)}}
.c-sum{{font-size:13px;color:var(--text2);line-height:1.6;flex:1}}
.c-tags{{display:flex;flex-wrap:wrap;gap:5px}}
.tg{{font-size:11px;padding:2px 8px;border-radius:5px;background:var(--bg2);color:var(--text3);border:1px solid var(--border);font-family:var(--mono)}}
.c-link{{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:var(--accent);margin-top:2px}}
.c-link svg{{width:14px;height:14px}}
.empty{{grid-column:1/-1;padding:40px;text-align:center;color:var(--text3);
  background:var(--surface);border:1px dashed var(--border);border-radius:var(--radius)}}

footer{{border-top:1px solid var(--border);padding:22px 0 40px;color:var(--text3);font-size:12.5px;text-align:center}}
footer .disc{{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:12px 16px;margin-bottom:14px;color:var(--text2);font-size:13px;line-height:1.6}}
footer .disc b{{color:var(--warn)}}

@media (max-width:640px){{
  .kpis{{grid-template-columns:1fr}}
  .toolbar{{position:static}}
  .search{{margin-left:0;max-width:none;width:100%}}
}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="eyebrow">{SVG_ICONS["spark"]} TAT 投研团队 · 报告归档中心</span>
    <h1>TAT 投研报告库</h1>
    <p class="lead">团队公开的投研报告归档，按月份和类别自动整理。每次 push 触发 GitHub Actions 重建索引并部署到 Pages。</p>
    <a class="repo-link" href="https://github.com/AiSid-Fate/tat-doc" target="_blank" rel="noopener">{SVG_ICONS["repo"]} <b>AiSid-Fate/tat-doc</b></a>
    <div class="kpis">
      <div class="kpi"><div class="k">{SVG_ICONS["book"]} 报告总数</div><div class="v accent">{total}</div><div class="s">已归档 HTML 数量</div></div>
      <div class="kpi"><div class="k">{SVG_ICONS["clock"]} 最近更新</div><div class="v gold">{esc(latest)}</div><div class="s">最新一份的日期</div></div>
      <div class="kpi"><div class="k">{SVG_ICONS["cat"]} 分类数</div><div class="v warn">{len(cats)}</div><div class="s">当前活跃的分类数</div></div>
    </div>
  </header>

  <div class="toolbar" role="toolbar" aria-label="分类筛选">
    <span class="lbl">{SVG_ICONS["tag"]} 筛选</span>
{filter_html}
    <input class="search" type="search" placeholder="按标题或标签搜索" aria-label="搜索报告">
  </div>

  <main class="grid" id="grid">
{cards_html}
  </main>

  <footer>
    <div class="disc"><b>免责声明：</b>本站为 TAT 投研团队内部研究推演，仅供研究参考，<b>不构成投资建议</b>。市场有风险，决策需谨慎。</div>
    <div>索引由 <code>scripts/build_index.py</code> 自动生成。构建时间 {build_time}</div>
  </footer>
</div>

<script>
(function(){{
  const chips = document.querySelectorAll('.chip');
  const cards = document.querySelectorAll('.card');
  const search = document.querySelector('.search');
  let cat = 'all', q = '';
  function apply(){{
    const kw = q.trim().toLowerCase();
    cards.forEach(c => {{
      const okCat = (cat === 'all' || c.dataset.category === cat);
      const okQ = !kw || c.textContent.toLowerCase().includes(kw);
      c.hidden = !(okCat && okQ);
    }});
  }}
  chips.forEach(ch => ch.addEventListener('click', () => {{
    chips.forEach(x => x.classList.remove('active'));
    ch.classList.add('active');
    cat = ch.dataset.filter;
    apply();
  }}));
  search.addEventListener('input', e => {{ q = e.target.value; apply(); }});
}})();
</script>
</body>
</html>
'''


def main() -> int:
    reports = scan_reports()
    html = render_page(reports)
    OUTPUT.write_text(html, encoding="utf-8")
    manifest = [
        {"title": r.title, "date": r.date, "category": r.category, "href": r.href, "tags": r.tags}
        for r in reports
    ]
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "reports.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] wrote {OUTPUT.relative_to(ROOT)} with {len(reports)} report(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
