import os, sys, pickle, logging
sys.path.insert(0, r"C:\Users\yunyc\AppData\Roaming\Claude\scratch-workspaces\b6865dac-8bd7-46ae-9800-2e7400624b04\96c25c59-7f54-4734-8e22-7bcb1d072443\scratch-2026-10-01-23bdc0")
import kiwoom_autotrader as K
IND = sorted(set(K.PRIOR_INDUSTRY_TO_SECTOR) | set(K.PRIOR_INDUSTRY_TO_SECTOR.values()))
p = os.path.join("lab", "data", "bars_60m_x.pkl")
d = pickle.load(open(p, "rb"))
new = K.download_hourly_yf([c for c in IND if c not in d])
d.update(new)
pickle.dump(d, open(p, "wb"))
print(len(IND), "industry/sector ETFs; got", len(new), sorted(new)); print("missing", [c for c in IND if c not in d])
print({c: str(v.ts.min())[:10] for c, v in new.items() if str(v.ts.min()) > "2023-11-04"})
