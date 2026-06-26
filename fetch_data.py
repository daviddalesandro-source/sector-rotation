import json
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

SECTORS = [
    ('XLK',  'Technology',       ['AAPL','MSFT','NVDA','AMD','AVGO','ORCL','CRM','QCOM','IBM','INTC']),
    ('XLF',  'Financials',       ['JPM','BAC','WFC','GS','MS','C','AXP','BLK','SCHW','V']),
    ('XLV',  'Health Care',      ['JNJ','UNH','ABBV','PFE','MRK','TMO','ABT','LLY','AMGN','MDT']),
    ('XLY',  'Consumer Disc.',   ['AMZN','TSLA','HD','MCD','NKE','SBUX','LOW','TJX','BKNG','CMG']),
    ('XLI',  'Industrials',      ['GE','HON','UPS','RTX','CAT','DE','LMT','BA','MMM','UNP']),
    ('XLC',  'Communication',    ['GOOGL','META','NFLX','DIS','CMCSA','VZ','T','CHTR','EA','WBD']),
    ('XLP',  'Consumer Staples', ['PG','KO','PEP','COST','WMT','PM','MO','CL','KMB','GIS']),
    ('XLE',  'Energy',           ['XOM','CVX','COP','EOG','SLB','MPC','PSX','VLO','OXY','HAL']),
    ('XLU',  'Utilities',        ['NEE','DUK','SO','D','AEP','EXC','SRE','XEL','PCG','WEC']),
    ('XLB',  'Materials',        ['LIN','APD','SHW','FCX','NEM','NUE','VMC','MLM','CTVA','CF']),
    ('XLRE', 'Real Estate',      ['AMT','PLD','CCI','EQIX','PSA','O','DLR','WELL','AVB','EQR']),
]

INDICES = ['SPY', 'QQQ', 'DIA', 'IWM', '^VIX']


def build_quote_map(symbols):
    """
    Download 15 trading days of daily OHLCV for all symbols in one batch call.
    Returns dict: symbol -> {price, change_pct, volume, avg_volume, prev_close}
    """
    print(f'  Downloading {len(symbols)} symbols via yfinance…')
    hist = yf.download(
        symbols,
        period='15d',
        interval='1d',
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    # yfinance returns MultiIndex columns when >1 symbol, flat when ==1
    multi = isinstance(hist.columns, pd.MultiIndex)

    result = {}
    for sym in symbols:
        try:
            if multi:
                close  = hist['Close'][sym].dropna()
                volume = hist['Volume'][sym].dropna()
            else:
                close  = hist['Close'].dropna()
                volume = hist['Volume'].dropna()

            if len(close) < 2:
                print(f'  SKIP {sym}: not enough history ({len(close)} rows)')
                continue

            price      = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])
            change_pct = (price - prev_close) / prev_close * 100 if prev_close else 0.0

            vol     = int(volume.iloc[-1])  if not pd.isna(volume.iloc[-1])  else 0
            avg_vol = int(volume.iloc[-11:-1].mean()) if len(volume) >= 11 else (int(volume.mean()) if len(volume) else 0)

            result[sym] = {
                'price':      round(price, 2),
                'change_pct': round(change_pct, 4),
                'volume':     vol,
                'avg_volume': avg_vol,
                'prev_close': round(prev_close, 2),
            }
        except Exception as exc:
            print(f'  ERROR {sym}: {exc}')

    return result


def main():
    all_etfs   = [row[0] for row in SECTORS]
    all_stocks = list({sym for _, _, stocks in SECTORS for sym in stocks})

    print('Fetching ETFs + indices…')
    etf_data = build_quote_map(all_etfs + INDICES)

    print('Fetching individual stocks…')
    stock_data = build_quote_map(all_stocks)

    # Build sector map
    sectors_out = {}
    for etf, name, stocks in SECTORS:
        if etf in etf_data:
            sectors_out[etf] = {**etf_data[etf], 'name': name, 'stocks': stocks}
        else:
            sectors_out[etf] = {'name': name, 'stocks': stocks, 'price': 0, 'change_pct': 0, 'volume': 0, 'avg_volume': 0}

    # Build index map (strip ^ for key)
    indices_out = {}
    for sym in INDICES:
        key = sym.lstrip('^')
        if sym in etf_data:
            indices_out[key] = etf_data[sym]
        elif key in etf_data:
            indices_out[key] = etf_data[key]

    data = {
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'sectors': sectors_out,
        'indices': indices_out,
        'stocks':  stock_data,
    }

    with open('data.json', 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f'\nDone — {data["updated"]}')
    print(f'  Sectors : {len(sectors_out)}')
    print(f'  Indices : {len(indices_out)}')
    print(f'  Stocks  : {len(stock_data)}')


if __name__ == '__main__':
    main()
