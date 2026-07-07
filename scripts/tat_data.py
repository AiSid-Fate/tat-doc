# -*- coding: utf-8 -*-
"""
TAT 团队通用数据取数工具
================================
多源自动 fallback：东财 → 新浪 → 腾讯，单源失败自动降级

用法：
    from tat_data import fetch_stock_daily
    df = fetch_stock_daily("600487", start="20240101", end="20260703")
    # 返回统一列名: date, open, close, high, low, volume, pct
"""
import time
import pandas as pd
import akshare as ak

def _norm(df, src):
    """归一化不同源的列名到统一 schema"""
    if src == "eastmoney":
        # 东财: 日期/开盘/收盘/最高/最低/成交量/涨跌幅
        df = df.rename(columns={'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','涨跌幅':'pct'})
    elif src == "sina":
        # 新浪: date,open,high,low,close,volume,amount,outstanding_share,turnover
        df['pct'] = df['close'].pct_change() * 100
    elif src == "tencent":
        # 腾讯: date,open,close,high,low,volume,amount
        df['pct'] = df['close'].pct_change() * 100
    # 保证 date 为 datetime、按时间升序
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df[['date','open','close','high','low','volume','pct']]

def fetch_stock_daily(code, start="20240101", end=None, adjust="qfq", max_retries=2, verbose=True):
    """
    取 A 股日线数据。自动尝试三个源，任一源成功即返回。

    Args:
        code: 6 位数字股票代码（如 "600487"）
        start/end: YYYYMMDD
        adjust: qfq/hfq/None
        max_retries: 每个源的重试次数

    Returns:
        pd.DataFrame with columns [date, open, close, high, low, volume, pct]
        排序：date 升序
    Raises:
        RuntimeError: 三个源全部失败时
    """
    if end is None:
        from datetime import date
        end = date.today().strftime('%Y%m%d')

    # 生成 sina/tencent 需要的带前缀代码
    prefix = "sh" if code.startswith(("6", "5", "9")) else ("sz" if code.startswith(("0", "3", "2")) else "bj")
    prefixed = prefix + code

    sources = [
        ("eastmoney", lambda: ak.stock_zh_a_hist(symbol=code, period="daily",
                                                  start_date=start, end_date=end, adjust=adjust)),
        ("sina",      lambda: ak.stock_zh_a_daily(symbol=prefixed,
                                                   start_date=start, end_date=end, adjust=adjust)),
        ("tencent",   lambda: ak.stock_zh_a_hist_tx(symbol=prefixed,
                                                     start_date=start, end_date=end, adjust=adjust)),
    ]

    errors = []
    for src_name, src_fn in sources:
        for attempt in range(1, max_retries + 1):
            try:
                df = src_fn()
                if df is None or len(df) == 0:
                    errors.append(f"{src_name}(try{attempt}): empty")
                    if attempt < max_retries: time.sleep(2)
                    continue
                if verbose:
                    print(f"✅ [tat_data] source={src_name} rows={len(df)} last_date={df.iloc[-1, 0]}")
                return _norm(df, src_name)
            except Exception as e:
                errmsg = f"{src_name}(try{attempt}): {type(e).__name__}: {str(e)[:80]}"
                errors.append(errmsg)
                if verbose:
                    print(f"⚠️  {errmsg}")
                if attempt < max_retries: time.sleep(2)
        # 单源全部重试失败 → 切下一源
        if verbose:
            print(f"⏭️  source={src_name} all retries failed, falling back")

    # 三个源全部失败
    raise RuntimeError(
        f"[tat_data] All 3 sources failed for {code}. Errors:\n" +
        "\n".join(f"  - {e}" for e in errors)
    )


def fetch_etf_daily(code, start="20240101", end=None, adjust="qfq", max_retries=2, verbose=True):
    """ETF 日线数据。多源兜底：东财 → 新浪。

    Args:
        code: 6 位ETF代码（如 "588200"）
    """
    if end is None:
        from datetime import date
        end = date.today().strftime('%Y%m%d')
    prefix = "sh" if code.startswith(("5",)) else "sz"
    prefixed = prefix + code

    sources = [
        ("eastmoney_etf", lambda: ak.fund_etf_hist_em(symbol=code, period="daily",
                                                       start_date=start, end_date=end, adjust=adjust)),
        ("sina_etf",      lambda: ak.fund_etf_hist_sina(symbol=prefixed)),
    ]
    errors = []
    for src_name, src_fn in sources:
        for attempt in range(1, max_retries + 1):
            try:
                df = src_fn()
                if df is None or len(df) == 0:
                    errors.append(f"{src_name}(try{attempt}): empty")
                    if attempt < max_retries: time.sleep(2)
                    continue
                if src_name == "eastmoney_etf":
                    df = df.rename(columns={'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','涨跌幅':'pct'})
                else:  # sina_etf
                    df['pct'] = df['close'].pct_change() * 100
                    # 新浪源不支持start/end过滤，需自行截断
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= pd.to_datetime(start)) & (df['date'] <= pd.to_datetime(end))]
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                if verbose:
                    print(f"✅ [tat_data] ETF {code} via {src_name} rows={len(df)} last={df.iloc[-1]['date'].date()}")
                return df[['date','open','close','high','low','volume','pct']]
            except Exception as e:
                errmsg = f"{src_name}(try{attempt}): {type(e).__name__}: {str(e)[:80]}"
                errors.append(errmsg)
                if verbose: print(f"⚠️  {errmsg}")
                if attempt < max_retries: time.sleep(2)
        if verbose: print(f"⏭️  source={src_name} all retries failed, falling back")
    raise RuntimeError(f"[tat_data] All ETF sources failed for {code}. Errors:\n" + "\n".join(f"  - {e}" for e in errors))


# ================================================================
# 实时快照 (spot) — 新浪 hq.sinajs.cn 直接HTTP
# ================================================================
# 起因: 2026-07-07 早盘扫描时 akshare 东财 spot 接口
# (stock_zh_a_spot_em / stock_zh_index_spot_em) 全部 RemoteDisconnected,
# 只有直连新浪 hq.sinajs.cn 可用。此函数固化该兜底方案。

def _to_prefix(code):
    """把纯代码补上 sh/sz/bj 前缀; 若已带前缀则原样返回"""
    code = str(code).strip().lower()
    if code.startswith(("sh", "sz", "bj")):
        return code
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"invalid code: {code}")
    first = code[0]
    if first in "659": return "sh" + code
    if first in "032": return "sz" + code
    if first in "84":  return "bj" + code
    raise ValueError(f"unknown market for code: {code}")


def fetch_realtime_spot(codes, max_retries=2, verbose=True, batch_size=50):
    """实时行情快照 (新浪源), 支持股票/指数/ETF混合传入.

    Args:
        codes: 单个代码字符串, 或代码列表. 支持 "600000"/"sh600000"/混合列表.
        max_retries: 每批的失败重试次数
        verbose: 打印取数日志
        batch_size: 单次HTTP请求最多多少代码 (默认50)

    Returns:
        pd.DataFrame with columns:
        ['code','name','open','pre_close','price','high','low','pct','volume','amount','timestamp']
        - code: 不带前缀的纯数字代码
        - price: 当前价 (指数=最新点位)
        - pct: 涨跌幅%
        - volume: 成交量 (股票=股, 指数=手, ETF=份)
        - amount: 成交额 (元)
        - timestamp: 数据时间戳 (ISO字符串, 交易时段更新, 收盘后为最后一tick)

    Raises:
        RuntimeError: 所有代码全部失败时抛出
    """
    import requests

    if isinstance(codes, str):
        codes = [codes]
    prefixed = [_to_prefix(c) for c in codes]

    # 分批
    all_rows = []
    errors = []
    for i in range(0, len(prefixed), batch_size):
        batch = prefixed[i:i+batch_size]
        url = "https://hq.sinajs.cn/list=" + ",".join(batch)
        headers = {"Referer": "https://finance.sina.com.cn",
                   "User-Agent": "Mozilla/5.0"}
        text = None
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200:
                    errors.append(f"batch{i//batch_size}(try{attempt}): HTTP {r.status_code}")
                    if attempt < max_retries: time.sleep(1)
                    continue
                text = r.content.decode('gbk', errors='replace')
                break
            except Exception as e:
                errors.append(f"batch{i//batch_size}(try{attempt}): {type(e).__name__}: {str(e)[:80]}")
                if attempt < max_retries: time.sleep(2)
        if text is None:
            continue

        # 解析: var hq_str_shXXXXXX="name,f1,f2,...";
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or '="' not in line:
                continue
            # 提取前缀+代码 与 引号内数据
            head = line.split('=')[0]           # e.g. var hq_str_sh601678
            sym = head.split('_')[-1]           # sh601678
            body = line.split('"')[1]           # "..." 内容
            if body == "":
                errors.append(f"{sym}: empty (可能停牌或无效代码)")
                continue
            parts = body.split(',')
            plain_code = sym[2:]  # 去掉sh/sz/bj

            try:
                n = len(parts)
                if n >= 15:
                    # 股票/ETF/大部分指数(34字段):
                    # 0:名称 1:今开 2:昨收 3:现价 4:最高 5:最低 6:买一价 7:卖一价
                    # 8:成交量 9:成交额 ... 30:日期 31:时间
                    # (指数的1=今开可能==昨收, 6/7=0)
                    name = parts[0]
                    open_p    = float(parts[1])
                    pre_close = float(parts[2])
                    price     = float(parts[3])
                    high      = float(parts[4])
                    low       = float(parts[5])
                    vol       = float(parts[8])
                    amt       = float(parts[9])
                    date      = parts[30] if n > 30 else ""
                    tstr      = parts[31] if n > 31 else ""
                    ts        = f"{date} {tstr}".strip()
                    pct = (price/pre_close - 1) * 100 if pre_close else 0.0
                else:
                    # 老式短格式指数(<15字段, 罕见): 名称,当前价,涨跌值,涨跌幅%,成交量,成交额
                    name = parts[0]
                    price = float(parts[1])
                    chg   = float(parts[2])
                    pct   = float(parts[3])
                    vol   = float(parts[4])
                    amt   = float(parts[5]) if n > 5 else 0.0
                    pre_close = price - chg
                    open_p, high, low = price, price, price
                    ts = ""
                row = dict(code=plain_code, name=name, open=open_p,
                           pre_close=pre_close, price=price, high=high, low=low,
                           pct=pct, volume=vol, amount=amt, timestamp=ts)
                all_rows.append(row)
            except (ValueError, IndexError) as e:
                errors.append(f"{sym}: parse fail: {type(e).__name__}: {str(e)[:60]}")

    if not all_rows:
        raise RuntimeError(f"[tat_data] fetch_realtime_spot: all codes failed. Errors:\n"
                           + "\n".join(f"  - {e}" for e in errors[:20]))
    df = pd.DataFrame(all_rows)
    if verbose:
        print(f"✅ [tat_data] realtime spot {len(df)}/{len(codes)} codes")
        if errors:
            print(f"⚠️  {len(errors)} codes/batches with issues:")
            for e in errors[:5]:
                print(f"   - {e}")
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("[TEST 1] fetch_stock_daily 多源日线")
    print("=" * 60)
    for c in ["600487", "002463"]:
        try:
            df = fetch_stock_daily(c, start="20260601", end="20260703", verbose=False)
            print(f"  {c} rows={len(df)} last_close={df.iloc[-1]['close']}")
        except Exception as e:
            print(f"  {c} FAILED: {str(e)[:80]}")

    print("\n" + "=" * 60)
    print("[TEST 2] fetch_realtime_spot 实时快照")
    print("=" * 60)
    test_codes = [
        "sh000001",  # 沪指
        "sh000300",  # 沪深300
        "002463",    # 沪电股份(自动补sz)
        "601678",    # 滨化股份
        "515880",    # 通信ETF
        "588200",    # 科创芯片ETF
        "600487",    # 亨通光电
    ]
    try:
        df = fetch_realtime_spot(test_codes, verbose=True)
        cols = ['code','name','price','pct','open','high','low','amount','timestamp']
        print(df[cols].to_string(index=False))
        print(f"\n✅ {len(df)}/{len(test_codes)} codes returned")
    except Exception as e:
        print(f"❌ realtime spot FAILED: {e}")
