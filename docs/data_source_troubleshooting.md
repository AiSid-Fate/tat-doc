# TAT数据源故障排查手册

> **首次收录**：2026-07-06（起因：亨通光电600487取数10次全部失败事件）
> **核心原则**：**"数据不通 = 分析白搭"**。任何数据取数脚本必须内置多源自动降级机制。
> **配套工具**：[../scripts/tat_data.py](../scripts/tat_data.py) 提供 `fetch_stock_daily()` 和 `fetch_etf_daily()`

---

## 一、常见根因清单

### 根因 A：单一数据源接口临时故障（最常见）
- **表现**：某个源持续 `ConnectionError` / `RemoteDisconnected` / `SSLError`
- **本次案例**：东财 `push2his.eastmoney.com` API 对 akshare 客户端持续拒绝，但其他源(新浪/腾讯)正常
- **诊断方法**：三源对照同一标的、对照另一标的（如002463 vs 600487），排除是"该标的独有问题"
- **修复**：使用 `tat_data.fetch_stock_daily()` 自动降级到新浪/腾讯

### 根因 B：akshare库版本 / requests session 复用
- **表现**：同一进程反复请求同一URL累积失败，重启Python进程后暂时恢复
- **诊断**：`pip show akshare` 看版本；干净的Python进程重试是否好转
- **修复**：`pip install --upgrade akshare`；避免长期运行进程内反复调用同一源

### 根因 C：SSL证书 / DNS / 代理
- **表现**：`SSLCertVerificationError` / `Name or service not known`
- **诊断**：
  ```bash
  curl -Is --max-time 8 https://push2his.eastmoney.com/
  env | grep -i proxy   # 排查环境变量污染
  ```
- **修复**：更新certifi (`pip install --upgrade certifi`)；`unset HTTP_PROXY HTTPS_PROXY`；重启网络

### 根因 D：数据源反爬 / 频控
- **表现**：短时高频调用后收到403、空响应、验证码页面
- **诊断**：单次curl返回200但akshare返回错误 = 反爬识别
- **修复**：调用间加 `time.sleep(2-5)`；换UA；换源

### 根因 E：特定标的接口异常
- **表现**：一源对多数标的正常，但对某一/某几只标的持续失败
- **诊断**：三源对该标的+对照标的（用tat_data测试脚本）
- **修复**：切换到该标的正常返回的源；如全部源都失败，等待数小时

---

## 二、标准排查流程（10分钟内定位）

### Step 1：单源对照测试
```python
import akshare as ak, time
def test(name, fn, *args, **kw):
    try:
        df=fn(*args,**kw)
        return f"✅ {name} rows={len(df)}"
    except Exception as e:
        return f"❌ {name}: {type(e).__name__}: {str(e)[:80]}"

# 目标标的
for src, fn, kwargs in [
    ("东财",   ak.stock_zh_a_hist,    dict(symbol="600487", period="daily", start_date="20250101", end_date="20260703", adjust="qfq")),
    ("新浪",   ak.stock_zh_a_daily,   dict(symbol="sh600487", start_date="20250101", end_date="20260703", adjust="qfq")),
    ("腾讯",   ak.stock_zh_a_hist_tx, dict(symbol="sh600487", start_date="20250101", end_date="20260703", adjust="qfq")),
]:
    print(test(src, fn, **kwargs)); time.sleep(2)
```

### Step 2：对照另一只已知能跑的标的
- 如果**该标的失败 + 对照标的成功** → 是标的特定问题
- 如果**该标的失败 + 对照标的也失败** → 是源本身故障（走 Step 3 换源）
- 如果**该源某标的成功但某标的失败** → 目标源对该标的临时限流（换源）

### Step 3：直连curl验证网络层
```bash
curl -Is --max-time 8 "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600487&klt=101&fqt=1"
curl -Is --max-time 8 "https://finance.sina.com.cn/realstock/company/sh600487/hisdata_klc_qfq.js"
```
- 都200 → 是akshare库/session问题（Step 4）
- 有的200有的失败 → 具体源的网络层问题（换源）

### Step 4：akshare库诊断
```bash
pip show akshare | head -3
pip install --upgrade akshare
```
- 版本过老（<1.15）优先升级
- 升级后重启Python进程再试

### Step 5：如全部失败
- 记录 3 源 + 直连 curl 全部失败的完整错误码
- 等待 30-60 分钟后重试（源侧临时问题多数一小时内自愈）
- 如仍失败，如实报告，不伪造数据（严守 SKILL.md 与 circuit breaker 规则）

---

## 三、编码规范：所有取数代码必须使用 tat_data 兜底

**❌ 禁止直接调用单一 akshare 源：**
```python
# BAD - 无兜底,一炸就全废
df = ak.stock_zh_a_hist(symbol="600487", ...)
```

**✅ 强制使用兜底工具：**
```python
from scripts.tat_data import fetch_stock_daily
# 或将 scripts/tat_data.py 复制到分析脚本同目录后 `from tat_data import ...`
df = fetch_stock_daily("600487", start="20240101", end="20260703")
# 返回统一 schema: date, open, close, high, low, volume, pct
```

**兜底逻辑**：
1. 优先东财源（数据最全）
2. 东财失败 → 新浪源
3. 新浪失败 → 腾讯源
4. 三源全败 → RuntimeError 抛出，如实报告不伪造

**每源最多重试2次（可配置）**，避免死循环，符合 circuit breaker 原则。

---

## 四、Kronos-forecast 特殊说明

Kronos 脚本 `kronos_forecast.py` 内部通过 akshare 取数，本身没有多源兜底。

**建议改造**：在 `kronos_forecast.py` 内 `_fetch_data()` 函数里改用 `tat_data.fetch_stock_daily()`。

**临时应急方案**：如 Kronos 取数失败，可手动先用 tat_data 取数保存到 CSV，然后修改 Kronos 脚本从 CSV 读入（需要脚本作者支持）。

---

## 五、故障 log 归档

每次遇到数据源故障，请在此文档尾部追加：

### 2026-07-06 东财API 对 akshare 客户端持续拒绝
- **标的**：600487、002463（多标的均受影响）
- **错误**：`ConnectionError: RemoteDisconnected('Remote end closed connection without response')`
- **诊断结果**：
  - 东财：❌ 全部标的失败
  - 新浪：✅ 所有标的正常
  - 腾讯：✅ 所有标的正常
  - 直接curl `push2his.eastmoney.com`：返回 200（说明是接口对akshare客户端拒绝，非网络）
- **修复**：建立 `tat_data.py` 多源兜底工具，主源改新浪，东财降为备用
- **恢复情况**：待观察，可能自愈

---

## 六、检查清单

在使用任何数据的分析开始前，请自查：

- [ ] 分析脚本是否用 `tat_data.fetch_stock_daily()` 而非直接调用单一 akshare 源
- [ ] Kronos-forecast 目标标的是否先用 tat_data 验证能取到数
- [ ] 如取数失败，是否按 5-step 流程逐步诊断而非盲重试
- [ ] 如仍失败，是否如实报告并归档到本文档，而非伪造数据

**这份文档存在的意义就是：让"数据不通 = 白搭"永远不再发生。**
