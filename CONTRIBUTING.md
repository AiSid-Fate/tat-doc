# 团队协作规则（生成报告前必读）

所有生成 HTML 报告的成员都要遵守。这不是建议，是硬规则。

## 1. HTML head 必须写 5 个 meta 标签

每一份要发布的 HTML，`<head>` 里必须包含这五行。缺一份 `publish_report.sh` 会把日期推断为文件 mtime、把类别推断为路径，容易出错。

```html
<meta name="report-title" content="国电南瑞 交易执行方案">
<meta name="report-date" content="2026-07-05">
<meta name="report-category" content="个股">
<meta name="report-tags" content="国电南瑞,600406,决策链">
<meta name="report-summary" content="一句话摘要，写清标的和结论，不超过 80 字。">
```

字段说明：

| 字段 | 说明 |
|---|---|
| report-title | 报告主标题。索引卡片会用这个。 |
| report-date | 报告日期，格式 `YYYY-MM-DD`。决定归档到哪个月。 |
| report-category | 类别。**必须**是白名单里的一个：`个股` / `赛道` / `ETF` / `组合` / `宏观` / `其他`。 |
| report-tags | 逗号分隔的标签，用于搜索。控制在 3 到 6 个之内。 |
| report-summary | 一句话摘要。80 字以内，写清标的和结论。 |

## 2. 视觉与文案规范

沿用团队已有的深色金融风视觉语言：

- 背景 `#0a0e14`，A 股语义色（红涨绿跌琥珀警示）。
- 数字用 `font-variant-numeric: tabular-nums` 等宽对齐。
- 图标用内联 SVG，不用 emoji。
- 响应式，375px 和桌面都不能横向滚动。
- 图表色附文字标签，不单独依赖颜色传意。

文案按 humanizer 规范：

- 禁用 em dash 和 en dash（U+2014 和 U+2013 两个长横线）。用句号、逗号、括号替代。
- 去营销腔（「大象起舞」「令人瞩目」「彰显」「见证」这类词砍掉）。
- 结论要具体，给数字。不写「表现优异」，写「Q1 扣非 +109%」。
- 长短句结合，句式自然。

## 3. 发布流程（唯一路径）

**不允许绕过脚本直接 `git push` HTML**。因为脚本会：
- 校验 meta 是否齐全
- 归档到正确路径
- 复制静态资源
- 重写图片路径

流程：

1. 本地生成 HTML，头部加齐 5 个 meta。
2. 本地自检（无 em/en dash、SVG 图标、tabular-nums、无横向滚动、免责声明齐）。
3. 运行：
   ```bash
   cd ~/AccioWork/tat-doc-repo
   ./scripts/publish_report.sh <html文件绝对路径> <类别>
   ```
4. 脚本执行完，CI 会自动重建索引 + 部署 Pages。

## 4. 类别白名单

只允许这 6 个类别：

| 类别 | 用于 |
|---|---|
| 个股 | 单一 A 股/港股/美股的分析或方案 |
| 赛道 | 行业/产业链维度的研判 |
| ETF | 基金或指数产品分析 |
| 组合 | 组合诊断、切换方案、资产配置 |
| 宏观 | 宏观经济、政策、货币、大类资产 |
| 其他 | 以上都不适合的兜底 |

不要私自新增分类。要新增走 PR。

## 5. 文件名规范

- 只用中文、英文字母、数字、下划线、连字符。**不含空格**。
- 描述性强。`国电南瑞_交易方案.html` 好，`report_20260705_v3_final.html` 不好。
- 脚本会自动加日期前缀，源文件名不要写日期。

## 6. 严禁事项

| 事项 | 原因 |
|---|---|
| 手动编辑 `index.html` | 每次 CI 都会覆盖你的改动 |
| 手动改 `reports/` 目录结构 | 索引扫描依赖固定路径规则 |
| 上传敏感信息（Token/密码/账号） | 仓库是公开的 |
| 用 em dash 或 en dash | 违反 humanizer 规范 |
| 用 emoji 当图标 | 违反视觉规范 |

## 7. 遇到问题

- 脚本报错「缺少 title」：加 `<title>xxx</title>` 到 HTML head。
- 脚本报错「类别不在白名单」：检查拼写，或用「其他」兜底。
- push 失败：看 README「本地凭证配置」章节。
- Pages 页面 404：去仓库 Settings → Pages 确认 Source 是 `GitHub Actions`。
- 报告索引没更新：去 Actions 标签看最近一次 workflow 是否成功。

## 8. 免责

本仓库为 TAT 投研团队内部研究归档，所有内容仅供研究参考，不构成投资建议。
