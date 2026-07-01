# macOS launchd 每日提醒定时任务

每交易日 15:30 (A 股收盘后) 自动触发一个准备脚本，提醒你打开 Accio 让 TAT 团队生成当日日报。

## 先把话说清楚

launchd 能做什么、不能做什么：

- **能做**：按时间触发一个确定性 shell 脚本、写日志、弹通知、准备工作目录、下载数据文件。
- **不能做**：自动打开 Accio 让 AI agent 帮你分析投研并生成报告。Agent 会话是交互式的，不是无头服务。

**所以这个 launchd 任务的价值是**：每交易日 15:30 准时提醒你、把当日工作目录 (含最新持仓 CSV 空白) 准备好、写入待办日志。剩下"跑一遍 TAT 团队诊断 → 填模板 → 发布"仍需要你手动打开会话。

如果哪天 Accio 支持无头 API，把 shell 脚本里的一行调用换成 API 请求就能真自动。今天不能。

## launchd vs cron

macOS 推荐 launchd，不推荐 cron，原因：

| 维度 | launchd | cron |
|---|---|---|
| 系统集成 | macOS 官方 init 系统，登录/唤醒自动重挂 | 需要 crond 服务，Apple 已弱化支持 |
| 唤醒补跑 | 系统睡眠错过的任务，唤醒后自动补跑一次 | 直接跳过 |
| 环境变量 | 显式声明，避免 PATH 悬空 | 继承弱环境，PATH 常出问题 |
| 日志 | 内置 StandardOutPath / StandardErrorPath | 自己 `>> log 2>&1` |
| 权限控制 | 内建 GUI 权限提示 | 无 |

Apple 从 10.10 起就把 cron 标为 legacy，新配置一律走 launchd。

## 步骤 1：写触发脚本 `~/.local/bin/tat_daily.sh`

```bash
#!/usr/bin/env bash
# tat_daily.sh: 每交易日收盘后触发的提醒 + 目录准备脚本
# 由 launchd 每周一到周五 15:30 调用

set -euo pipefail

# 日期
DATE=$(date +%Y-%m-%d)
WEEKDAY=$(date +%u)  # 1=一 7=日

# 遇周末不做事 (launchd 里已经只配了工作日, 双保险)
if [ "$WEEKDAY" -gt 5 ]; then
  echo "$(date '+%F %T') 周末不触发" >> "$HOME/Library/Logs/tat-daily.log"
  exit 0
fi

# 工作区
WORKROOT="$HOME/AccioWork"
DAILY_DIR="$WORKROOT/daily-briefings/$DATE"
mkdir -p "$DAILY_DIR"

# 从模板复制一份空白日报到当日目录
TEMPLATE="$HOME/AccioWork/tat-doc-repo/templates/daily_template.html"
DEST="$DAILY_DIR/TAT投研日报_${DATE}.html"
if [ ! -f "$DEST" ] && [ -f "$TEMPLATE" ]; then
  cp "$TEMPLATE" "$DEST"
fi

# 写日志
LOG="$HOME/Library/Logs/tat-daily.log"
{
  echo "----------------------------------------"
  echo "$(date '+%F %T') 日报触发"
  echo "  当日工作目录: $DAILY_DIR"
  echo "  空白日报: $DEST"
  echo "  下一步: 打开 Accio, 让 TAT 团队根据今日收盘持仓/操作生成日报, 填入 $DEST 后运行:"
  echo "    cd $HOME/AccioWork/tat-doc-repo"
  echo "    ./scripts/publish_report.sh \"$DEST\" 日报"
  echo "----------------------------------------"
} >> "$LOG"

# 弹一个 macOS 通知 (osascript 是 macOS 内置的, 不需要额外装东西)
/usr/bin/osascript -e "display notification \"当日工作目录已准备: $DAILY_DIR\" with title \"TAT 投研日报\" subtitle \"收盘后 · $DATE\" sound name \"Ping\""

exit 0
```

保存后加执行权限：

```bash
chmod +x ~/.local/bin/tat_daily.sh
mkdir -p ~/Library/Logs   # 保险起见
```

先手动跑一次验证：

```bash
~/.local/bin/tat_daily.sh
tail -20 ~/Library/Logs/tat-daily.log
```

看到日志追加了一段，且屏幕右上角弹了 macOS 通知，就说明脚本本身没问题。

## 步骤 2：写 launchd 配置 `~/Library/LaunchAgents/com.tat.daily-report.plist`

保存下面这段到 `~/Library/LaunchAgents/com.tat.daily-report.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.tat.daily-report</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>$HOME/.local/bin/tat_daily.sh</string>
  </array>

  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>30</integer></dict>
  </array>

  <key>StandardOutPath</key>
  <string>/Users/YOURNAME/Library/Logs/tat-daily.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOURNAME/Library/Logs/tat-daily.err.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/YOURNAME/.local/bin</string>
  </dict>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

**注意**：
- `Weekday`：launchd 里 1=周一, 2=周二 ...5=周五, 0/7=周日。上面配的是周一到周五 15:30。
- `YOURNAME` 两处要替换成你的实际用户名 (你的用户名是 `sidfate`，直接替换即可)
- launchd 不认 `~` 或环境变量，路径必须写绝对
- `PATH` 要显式声明，不然脚本里调用 `gh`、`git` 等命令找不到

## 步骤 3：加载、验证、卸载

```bash
# 加载 (立即生效，会按 StartCalendarInterval 触发)
launchctl load ~/Library/LaunchAgents/com.tat.daily-report.plist

# 查看是否加载成功
launchctl list | grep tat.daily-report
# 应输出类似: -   0   com.tat.daily-report   (PID 是 - 因为没在跑, 0 是上次退出码)

# 手动触发一次 (不等 15:30)
launchctl start com.tat.daily-report

# 看日志确认触发
tail -30 ~/Library/Logs/tat-daily.log
tail -10 ~/Library/Logs/tat-daily.out.log
tail -10 ~/Library/Logs/tat-daily.err.log

# 卸载 (改配置前先卸载再加载)
launchctl unload ~/Library/LaunchAgents/com.tat.daily-report.plist
```

## 步骤 4：临时改时间来测试

不必等真 15:30，改成 2 分钟后触发一次验证。假设现在 14:20，改成 14:22：

1. 编辑 plist，把 `StartCalendarInterval` 里的一个 `<dict>` 改成：
   ```xml
   <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>22</integer></dict>
   ```
   （去掉 Weekday 就是每天都触发一次）
2. 卸载再加载：
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.tat.daily-report.plist
   launchctl load ~/Library/LaunchAgents/com.tat.daily-report.plist
   ```
3. 等 2 分钟，屏幕右上角应弹通知，`~/Library/Logs/tat-daily.log` 也有新记录。
4. 验证过后，把时间改回 15:30，再 unload/load 一次。

## 常见问题

### Q1: `launchctl load` 报 `Load failed: 5: Input/output error`

多半是 plist XML 语法错。先跑 `plutil ~/Library/LaunchAgents/com.tat.daily-report.plist`，正常返回 `OK`，异常会指出行号。

### Q2: 到时间了没弹通知

依次查：
```bash
# 1. launchd 有没有真触发
tail -10 ~/Library/Logs/tat-daily.err.log

# 2. 权限：脚本能不能跑
ls -la ~/.local/bin/tat_daily.sh   # 要看到 -rwx------

# 3. 通知权限：系统设置 → 通知 → 「脚本编辑器」允许通知开
```

### Q3: 日志说找不到 gh / git 命令

`EnvironmentVariables.PATH` 里缺目录。补上 gh 装的位置，比如 `/Users/sidfate/.local/bin`。

### Q4: Mac 睡眠期间任务错过了会补跑吗

会。launchd 唤醒后会补跑一次错过的 `StartCalendarInterval`，不会漏。这也是相对 cron 的主要优势。

### Q5: 我想周六日也触发做周复盘怎么办

在 `StartCalendarInterval` 里加两个 dict：
```xml
<dict><key>Weekday</key><integer>6</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
<dict><key>Weekday</key><integer>7</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
```

### Q6: 交易日历怎么办 (节假日不开盘)

launchd 本身不认交易日历。两种应对：
- **简单方案**：在 `tat_daily.sh` 里加交易日判断 (维护一个节假日列表或调 tushare/ akshare 的 `tool_trade_date_hist_sina` 接口判断)
- **手动方案**：节假日当天忽略提醒即可，反正是准备目录 + 提醒，不会造成脏数据

## 完整触发链路总览

```
15:30 A股收盘
   ↓
launchd 触发 tat_daily.sh
   ↓
脚本 mkdir 当日目录 + cp 模板 + 写日志 + 弹通知
   ↓
你看到通知, 打开 Accio 让 TAT 团队根据今日行情生成日报内容
   ↓
把内容填入 $HOME/AccioWork/daily-briefings/YYYY-MM-DD/TAT投研日报_YYYY-MM-DD.html
   ↓
执行 publish_report.sh 归档 + push + CI 触发
   ↓
几分钟后 https://aisid-fate.github.io/tat-doc/ 更新
```

launchd 干的是链条最前的两步。剩下的等 Accio 提供无头 API 或后台任务能力再考虑全自动。
