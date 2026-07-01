#!/usr/bin/env bash
# publish_report.sh: 团队统一的报告发布脚本
#
# 用法：
#   ./scripts/publish_report.sh <html文件绝对路径> <类别>
# 例：
#   ./scripts/publish_report.sh /Users/x/tmp/xxx.html 个股
#
# 行为：
#   1. 校验 HTML 存在，含 <title>
#   2. 从 <meta name="report-date"> 或文件 mtime 推断日期
#   3. 复制到 reports/YYYY-MM/{类别}/YYYY-MM-DD_{filename}.html
#   4. 复制文件同目录下的 kronos_output/ 等静态资源到 assets/
#   5. git add / commit / push（若远程凭证未配好会明确报错并停止）

set -euo pipefail

# ----- 路径与常量 -----
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATEGORIES=(个股 赛道 ETF 组合 宏观 其他)

# ----- 参数校验 -----
if [ $# -lt 2 ]; then
  echo "用法: $0 <html文件绝对路径> <类别>"
  echo "类别可选: ${CATEGORIES[*]}"
  exit 1
fi

SRC="$1"
CAT="$2"

if [ ! -f "$SRC" ]; then
  echo "错误：文件不存在 $SRC" >&2
  exit 1
fi

CAT_OK=false
for c in "${CATEGORIES[@]}"; do
  if [ "$c" = "$CAT" ]; then CAT_OK=true; break; fi
done
if [ "$CAT_OK" = false ]; then
  echo "错误：类别不在白名单：$CAT" >&2
  echo "可选：${CATEGORIES[*]}" >&2
  exit 1
fi

# ----- HTML 完整性检查 -----
if ! grep -q "<title>" "$SRC"; then
  echo "错误：HTML 缺少 <title>，请补齐再发布" >&2
  exit 1
fi

# 提取日期：优先 meta name="report-date"
DATE=$(grep -o '<meta[[:space:]]*name="report-date"[[:space:]]*content="[^"]*"' "$SRC" \
  | grep -o 'content="[^"]*"' | head -1 | sed 's/content="//;s/"$//')

if [ -z "$DATE" ]; then
  # macOS / Linux stat 兼容
  if stat -f "%Sm" -t "%Y-%m-%d" "$SRC" > /dev/null 2>&1; then
    DATE=$(stat -f "%Sm" -t "%Y-%m-%d" "$SRC")
  else
    DATE=$(date -r "$SRC" +"%Y-%m-%d")
  fi
  echo "提示：HTML 未定义 report-date，使用文件 mtime $DATE"
fi

if ! [[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "错误：日期格式非法 $DATE" >&2
  exit 1
fi

MONTH="${DATE:0:7}"
BASENAME=$(basename "$SRC")
# 去掉可能的原前缀日期，避免双前缀
CLEAN=$(echo "$BASENAME" | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}_//')
# 空格替换为下划线
CLEAN=$(echo "$CLEAN" | tr ' ' '_')
DST_DIR="$REPO_ROOT/reports/$MONTH/$CAT"
DST="$DST_DIR/${DATE}_${CLEAN}"

mkdir -p "$DST_DIR"

if [ -e "$DST" ]; then
  echo "提示：目标已存在，将覆盖 $DST"
fi

cp "$SRC" "$DST"
echo "已归档 → ${DST#$REPO_ROOT/}"

# ----- 同步引用的静态资源（kronos_output 等） -----
SRC_DIR=$(dirname "$SRC")
for asset_dir in kronos_output images img; do
  if [ -d "$SRC_DIR/$asset_dir" ] && grep -q "$asset_dir/" "$SRC"; then
    TARGET="$REPO_ROOT/assets/$asset_dir"
    mkdir -p "$TARGET"
    cp -R "$SRC_DIR/$asset_dir/"* "$TARGET/" 2>/dev/null || true
    echo "已同步资源 → assets/$asset_dir/"

    # 若 HTML 用的是相对路径 kronos_output/xxx，替换为 /tat-doc/assets/kronos_output/xxx
    # 保守起见，在归档副本里改写路径。原文件不动。
    PYTHON_BIN=$(command -v python3 || command -v python)
    if [ -n "$PYTHON_BIN" ]; then
      "$PYTHON_BIN" - "$DST" "$asset_dir" <<'PY'
import re, sys
path, asset = sys.argv[1], sys.argv[2]
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()
new = re.sub(rf'(src|href)="{asset}/', rf'\1="../../../assets/{asset}/', text)
if new != text:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)
    print(f"[rewrite] 修正 {asset}/ 引用为相对 assets 路径")
PY
    fi
  fi
done

# ----- 提取标题用于 commit -----
TITLE=$(grep -o '<title>[^<]*</title>' "$SRC" | head -1 | sed 's/<title>//;s/<\/title>//')

# ----- git commit -----
cd "$REPO_ROOT"
git add "reports/$MONTH/$CAT/" assets/ 2>/dev/null || true

if git diff --cached --quiet; then
  echo "没有变更需要提交（或已 commit 过），退出。"
  exit 0
fi

COMMIT_MSG="report: [${CAT}] ${TITLE} (${DATE})"
git commit -m "$COMMIT_MSG"
echo "已提交：$COMMIT_MSG"

# ----- push -----
if ! git remote get-url origin > /dev/null 2>&1; then
  echo "错误：未配置 remote origin，请先 git remote add origin <url>" >&2
  exit 1
fi

echo "正在推送到 origin main..."
if git push origin main 2>&1; then
  # 推断 Pages URL
  URL="https://aisid-fate.github.io/tat-doc/"
  echo ""
  echo "✓ 已推送。GitHub Actions 会在几分钟内重建索引并部署 Pages。"
  echo "  访问：$URL"
else
  echo ""
  echo "推送失败。可能原因：本地 GitHub 凭证未配置。参考 README.md 的凭证配置章节。" >&2
  exit 1
fi
