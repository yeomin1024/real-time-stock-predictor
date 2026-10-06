import pandas as pd, numpy as np
e = pd.read_csv(r'lab\gh\sim_equity.csv', encoding='utf-8-sig')
t = pd.read_csv(r'lab\gh\sim_trades.csv', encoding='utf-8-sig')
e['inv'] = 1 - e['현금($)'] / e['자산($)']
print('EOD invested mean %.2f, median %.2f, days with 0 invested %.2f' % (e.inv.mean(), e.inv.median(), (e.inv < 0.01).mean()))
print('exposure dist', e['국면노출'].describe().round(2).to_dict(), 'exp0 days', (e['국면노출'] == 0).mean().round(2))
print(e.groupby(e['국면노출'].round(1))['inv'].agg(['count', 'mean']).round(2))
t['ts'] = pd.to_datetime(t['시각(ET)'])
b = t[t['구분'] == '매수'].reset_index(drop=True); s = t[t['구분'] == '매도'].reset_index(drop=True)
print('buys', len(b), 'sells', len(s))
print(s['사유'].str.extract(r'^(\S+)')[0].value_counts().head(8))
print(s.groupby(s['사유'].str.extract(r'(손절|익절|보유기한|장마감)')[0])['수익률(%)'].agg(['count', 'mean']).round(2))
e['날짜'] = pd.to_datetime(e['날짜']); y = e.set_index('날짜')['자산($)']
print(y.resample('QE').last().pct_change().round(3).to_string())
