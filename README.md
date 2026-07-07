# tat-doc

TAT 投研团队的 HTML 报告归档仓库。所有生成的报告统一走这个仓库发布到 GitHub Pages，自动归档、自动索引、自动部署。

线上访问：`https://aisid-fate.github.io/tat-doc/`（Pages 启用后生效）

## 是什么

这是一个静态站点仓库。特点：

- **报告分类归档**：按 `reports/YYYY-MM/{类别}/YYYY-MM-DD_{文件名}.html` 结构存放。
- **索引自动生成**：每次 push 触发 GitHub Actions，重跑 `scripts/build_index.py`，重建 `index.html`。
- **零手动部署**：Actions 用官方 `actions/deploy-pages@v4` 推到 Pages。
- **发布只用一条命令**：本地运行 `scripts/publish_report.sh <html路径> <类别>` 完成归档、commit、push。

## 目录结构

```
tat-doc/
├── .github/workflows/pages.yml    # CI 自动部署
├── reports/                       # 报告归档目录
│   └── YYYY-MM/{类别}/            # 按月+类别双层归档
├── assets/                        # 索引页与报告共用的静态资源（如 kronos_output PNG）
├── scripts/
│   ├── build_index.py             # 索引生成（CI 里跑，本地也可跑）
│   └── publish_report.sh          # 团队成员发布报告用
├── index.html                     # 首页（由 build_index.py 自动生成，不要手改）
├── README.md                      # 本文件
├── CONTRIBUTING.md                # 团队规则（生成报告前必读）
└── .gitignore
```

## 第一次使用：3 步启用 GitHub Pages

**步骤 1：确认代码已 push 到 GitHub**

如果 push 失败，看下面「本地凭证配置」章节。

**步骤 2：在仓库开启 Pages（GitHub Actions 部署模式）**

去仓库网页：`https://github.com/AiSid-Fate/tat-doc`

1. 点顶部 `Settings`
2. 左侧 `Pages`
3. `Build and deployment` → `Source` 选 **GitHub Actions**（不要选 Deploy from a branch）
4. 保存

**步骤 3：触发一次部署**

正常 push 到 main 就会自动触发。也可以去 `Actions` 标签手动点 `Run workflow`。约 1 到 3 分钟后 `https://aisid-fate.github.io/tat-doc/` 就能访问。

## 日常使用：如何发布一份新报告

假设你在别处生成了一份 HTML，比如 `/Users/x/tmp/xxx.html`：

```bash
cd ~/AccioWork/tat-doc-repo
./scripts/publish_report.sh /Users/x/tmp/xxx.html 个股
```

脚本会：
1. 检查 HTML 有 `<title>` 和 `<meta name="report-date">`
2. 归档到 `reports/2026-07/个股/2026-07-01_xxx.html`
3. 同步 `kronos_output/`、`images/`、`img/` 等本地资源到 `assets/`
4. `git commit` + `git push`
5. 打印 Pages 访问 URL

CI 会重建 `index.html`，几分钟后线上生效。

**生成报告前请读 [CONTRIBUTING.md](CONTRIBUTING.md)**，尤其是 HTML `<head>` 里必须放的 5 个 meta 标签。

## 团队工具（数据源多源兜底）

**问题**：单一 akshare 数据源（东财 / 新浪 / 腾讯）任何一个临时故障就会让整份技术面分析或 Kronos 预测报废。

**解决**：`scripts/tat_data.py` 提供 `fetch_stock_daily()` / `fetch_etf_daily()` / `fetch_realtime_spot()`，自动依次尝试东财 → 新浪 → 腾讯，任一源成功即返回，全败才抛错。**所有取数代码都请走这个工具，禁止直接调用单一 akshare 源。**

```python
from scripts.tat_data import fetch_stock_daily, fetch_etf_daily, fetch_realtime_spot

# 历史日线（多源兜底）
df = fetch_stock_daily("600487", start="20240101", end="20260703")

# 实时快照（股票/指数/ETF混合传入,新浪 hq.sinajs.cn 直连）
spot = fetch_realtime_spot(["sh000001", "002463", "515880"])
```

遇到数据源故障时的排查流程（10 分钟内定位）：见 **[docs/data_source_troubleshooting.md](docs/data_source_troubleshooting.md)**。

## 本地凭证配置

`git push` 需要 GitHub 凭证。三种任选一种。

### 方案 A：HTTPS + Personal Access Token（推荐，新手最快）

1. 去 `https://github.com/settings/tokens` 创建 PAT（勾选 `repo` 权限）
2. 本地配一次：
   ```bash
   git config --global credential.helper osxkeychain      # macOS
   # git config --global credential.helper store          # Linux
   ```
3. 第一次 push 时，用户名填 GitHub 账号，密码填 PAT。之后自动记住。

### 方案 B：SSH Key（长期使用推荐）

1. `~/.ssh/id_rsa.pub` 或 `id_ed25519.pub` 的内容拷贝出来
2. 去 `https://github.com/settings/keys` 添加 SSH key
3. 把仓库 remote 换成 SSH：
   ```bash
   git remote set-url origin git@github.com:AiSid-Fate/tat-doc.git
   ```
4. 测试：`ssh -T git@github.com` 应该返回 `Hi AiSid-Fate! You've successfully authenticated`

### 方案 C：gh CLI

```bash
gh auth login             # 按提示走一遍
gh auth setup-git         # 让 git 用 gh 的凭证
```

## 本地跑索引生成

```bash
python3 scripts/build_index.py
```

输出 `index.html` 和 `assets/reports.json`。直接双击 `index.html` 就能看到线上一致的效果。

## 免责

本站为 TAT 投研团队内部研究推演，仅供研究参考，不构成投资建议。市场有风险，决策需谨慎。
