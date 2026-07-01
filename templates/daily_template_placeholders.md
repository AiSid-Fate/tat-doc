# 日报模板占位符清单

模板文件：`templates/daily_template.html`

所有占位符格式统一：`{{XXX}}`。填充时直接文本替换即可。整块不需要的（如某日无 RED FLAG）就把整块占位符所在的父容器一起删掉，不留残余。

## 1. HTML meta（head 里必填）

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{{REPORT_DATE}}` | 报告日期，`YYYY-MM-DD` | `2026-07-01` |
| `{{REPORT_TAGS}}` | 逗号分隔标签，3 到 6 个 | `持仓分析,操作复盘,组合诊断,日报` |
| `{{REPORT_SUMMARY}}` | 一句话摘要，80 字以内 | `AI算力β升至87.4%，沪电单仓35.1%触警戒。` |

## 2. 报头

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{{VOLUME_NO}}` | 期数，从 001 递增 | `002` |
| `{{DATE_LONG}}` | 长日期含星期 | `2026 年 7 月 2 日 星期四` |

## 3. 头条

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{{HEADLINE_KICKER}}` | 头条上方红色小标签 | `组合危险等级升级` |
| `{{HEADLINE_TITLE}}` | 大标题，可含 `<em>红色高亮</em>` | `AI 算力 β 升至 <em>87.4%</em>` |
| `{{HEADLINE_LEDE}}` | 头条导语 2 到 3 句 | `再平衡执行完毕，方向反了。88% 到 87.4% 是浮盈稀释出来的。` |

## 4. 4 个今日速览 KPI

每个 KPI 有 4 个字段：LABEL 标签、VALUE 数值、COLOR 颜色类（`up`/`down`/`warn`/空）、NOTE 副注。

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{{KPI1_LABEL}}` | 第 1 张卡标签 | `组合市值` |
| `{{KPI1_VALUE}}` | 第 1 张卡主数字 | `12.4 万` |
| `{{KPI1_COLOR}}` | 颜色类（可空） | `up`（涨/危险深红）/ `down`（跌/看空绿）/ `warn`（琥珀）/ 空（黑色） |
| `{{KPI1_NOTE}}` | 第 1 张卡副注 | `上期 9.11 万` |

`KPI2/3/4` 同上，共 16 个占位符。

## 5. 今日操作复盘表

| 占位符 | 含义 | 示例 |
|---|---|---|
| `{{OPERATIONS_COUNT}}` | 表格上方 meta 提示 | `7` |
| `{{OPERATIONS_ROWS}}` | 表格 `<tr>` 行合集，每行 5 列 | 见下方 HTML 模板 |

单行 HTML 模板：
```html
<tr>
  <td>操作描述 @ 价格</td>
  <td><span class="tag tag-bad">反向</span></td>   <!-- tag-ok/tag-warn/tag-bad/tag-neutral -->
  <td class="r">~1.06 万</td>
  <td class="pos">最严重错误</td>                     <!-- pos=红 / neg=绿 / amber=琥珀 -->
  <td>问题点简述</td>
</tr>
```

## 6. 持仓状态表

| 占位符 | 含义 |
|---|---|
| `{{POSITIONS_COUNT}}` | 持仓只数 |
| `{{TOTAL_VALUE}}` | 组合总市值 |
| `{{POSITIONS_ROWS}}` | 6 列 `<tr>` 集合 |

单行 HTML：
```html
<tr>
  <td><b>标的名</b> 代码</td>
  <td>类别</td>
  <td class="r">4.35 万</td>
  <td class="r pos">35.1%</td>
  <td class="r pos">+0.63%</td>
  <td>风险提示</td>
</tr>
```

## 7. 关键提示 (Red Flag)

| 占位符 | 含义 |
|---|---|
| `{{FLAGS_COUNT}}` | 提示条数 |
| `{{RED_FLAGS}}` | 多个 flag div 拼接 |
| `{{PULLQUOTE_TEXT}}` | 引用块金句 |

单条 flag HTML：
```html
<div class="flag">
  <div class="fh">RED FLAG 01 · 简短标签</div>
  <p>正文。可用 <b>红色高亮</b> 强调关键数字。</p>
</div>
```

## 8. 明日 T+1 应对清单

| 占位符 | 含义 |
|---|---|
| `{{TOMORROW_ACTIONS}}` | `<li>` 列表，每条一个动作 |

单条 HTML：
```html
<li><b>动作名 -100 股</b> @ 价格附近，简述目的与预期兑现金额。</li>
```

## 9. 侧栏三张 mini-tab

| 占位符 | 含义 | 单行 HTML |
|---|---|---|
| `{{WATCH_LEVELS}}` | 明日盯盘点位 | `<tr><td>沪电 MA20</td><td class="r">136.7</td></tr>` |
| `{{TARGET_DEVIATION}}` | 组合目标偏离 | `<tr><td>AI 算力 β</td><td class="r pos">87.4% / 目标 50%</td></tr>` |
| `{{KEY_DATES}}` | 本周关键日期 | `<tr><td>7/2 周四</td><td class="r">T+1 首波减仓</td></tr>` |

## 10. 验证清单 (可复用为周度/月度目标追踪)

| 占位符 | 含义 |
|---|---|
| `{{VERIFY_TITLE}}` | 章节标题 | `8 月中报三档验证清单` |
| `{{VERIFY_A_TITLE}}` | A 档标题 | `加满档 双击启动` |
| `{{VERIFY_A_BODY}}` | A 档内容 HTML | 两三行 `<p>` 条件 + 一行 `<div class="act">` 动作 |
| `{{VERIFY_B_TITLE}}` / `{{VERIFY_B_BODY}}` | B 档 | 同上 |
| `{{VERIFY_C_TITLE}}` / `{{VERIFY_C_BODY}}` | C 档 | 同上 |

单档 body HTML：
```html
<p>指标 1：<b>阈值</b></p>
<p>指标 2：<b>阈值</b></p>
<div class="act">动作：<b>加满 / 观察 / 清 60%</b></div>
```

## 11. 文案纪律 (humanizer)

生成后自检：
- 全文 `grep "—" file.html` 和 `grep "–" file.html` 都必须返回空（模板里表格空占位符用 `--`）
- 禁用 emoji 做图标（`class="tag"` 等文字标签替代）
- 数字用 `class="num"` 或直接放在 `.mini-tab td.r` 里等宽对齐
- 结论要具体，给数字。不写「表现良好」，写「浮盈 +32.7%」
