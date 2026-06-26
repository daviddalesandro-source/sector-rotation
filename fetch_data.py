import json
import requests
from datetime import datetime, timezone

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://finance.yahoo.com/',
}

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


def get_session_and_crumb():
    s = requests.Session()
    s.headers.update(HEADERS)
    # Visit Yahoo Finance to get session cookies
    s.get('https://finance.yahoo.com/', timeout=10)
    # Fetch crumb
    r = s.get('https://query1.finance.yahoo.com/v1/test/getcrumb', timeout=10)
    crumb = r.text.strip().strip('"')
    return s, crumb


def fetch_quotes(session, crumb, symbols):
    chunk_size = 20
    results = {}
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]
        url = (
            'https://query1.finance.yahoo.com/v7/finance/quote'
            f'?symbols={",".join(chunk)}&crumb={crumb}'
            '&fields=regularMarketPrice,regularMarketChangePercent,'
            'regularMarketVolume,averageDailyVolume10Day,'
            'regularMarketPreviousClose,shortName'
        )
        r = session.get(url, timeout=10)
        r.raise_for_status()
        for q in r.json().get('quoteResponse', {}).get('result', []):
            results[q['symbol']] = {
                'price':     round(q.get('regularMarketPrice', 0), 2),
                'change_pct': round(q.get('regularMarketChangePercent', 0), 4),
                'volume':    int(q.get('regularMarketVolume', 0)),
                'avg_volume': int(q.get('averageDailyVolume10Day', 0)),
                'prev_close': round(q.get('regularMarketPreviousClose', 0), 2),
                'name':      q.get('shortName', ''),
            }
    return results


def main():
    session, crumb = get_session_and_crumb()

    all_etfs   = [s[0] for s in SECTORS]
    all_stocks = list({sym for _, _, stocks in SECTORS for sym in stocks})

    print('Fetching ETFs and indices...')
    etf_data = fetch_quotes(session, crumb, all_etfs + INDICES)

    print('Fetching individual stocks...')
    stock_data = fetch_quotes(session, crumb, all_stocks)

    # Build sector map
    sectors_out = {}
    for etf, name, stocks in SECTORS:
        sectors_out[etf] = {
            **etf_data.get(etf, {}),
            'name': name,
            'stocks': stocks,
        }

    # Build index map (strip ^ for key)
    indices_out = {}
    for sym in INDICES:
        key = sym.lstrip('^')
        if sym in etf_data:
            indices_out[key] = etf_data[sym]
        elif key in etf_data:
            indices_out[key] = etf_data[key]

    data = {
        'updated':  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'sectors':  sectors_out,
        'indices':  indices_out,
        'stocks':   stock_data,
    }

    with open('data.json', 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"Done. Updated at {data['updated']}")
    print(f"  Sectors:  {len(sectors_out)}")
    print(f"  Indices:  {len(indices_out)}")
    print(f"  Stocks:   {len(stock_data)}")


if __name__ == '__main__':
    main()
