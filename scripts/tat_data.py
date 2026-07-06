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
    """ETF 日线数据（东财源为主，其他源对ETF支持不全）"""
    if end is None:
        from datetime import date
        end = date.today().strftime('%Y%m%d')
    for attempt in range(1, max_retries * 3 + 1):  # ETF多试几次
        try:
            df = ak.fund_etf_hist_em(symbol=code, period="daily",
                                     start_date=start, end_date=end, adjust=adjust)
            if df is not None and len(df) > 0:
                df = df.rename(columns={'日期':'date','开盘':'open','收盘':'close','最高':'high','最低':'low','成交量':'volume','涨跌幅':'pct'})
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                if verbose:
                    print(f"✅ [tat_data] ETF {code} rows={len(df)} last={df.iloc[-1]['date'].date()}")
                return df[['date','open','close','high','low','volume','pct']]
        except Exception as e:
            if verbose: print(f"⚠️  ETF fetch attempt {attempt}: {type(e).__name__}: {str(e)[:80]}")
            time.sleep(3)
    raise RuntimeError(f"[tat_data] ETF {code} fetch failed after {max_retries*3} retries")


if __name__ == "__main__":
    # 自测: 亨通(之前失败)+沪电
    for c in ["600487", "002463"]:
        try:
            df = fetch_stock_daily(c, start="20260601", end="20260703")
            print(f"  {c} last close = {df.iloc[-1]['close']}")
        except Exception as e:
            print(f"  {c} FAILED: {e}")
