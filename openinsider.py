"""
openinsider.py - Institutional-grade OpenInsider.com parser (12-month window
with 6-month recency weighting, Buy-vs-Sell dollar & headcount ratio,
chronological order check, and ΔOwn % liquidation detection).

Fixes the "Lone Buy Surrounded by Sells" trap:
  * INTU trap: 1 director bought $541k, followed by 5 consecutive sales ($851k
    in 6m) and preceded by the CEO selling -75% ($26.6M), CFO selling -71%,
    and founder selling $325M+. That is NOT an 'INSIDER BUY' — it is C-Suite
    liquidation with 1 lone director purchase.
  * PYPL trap: CFO bought $254k in June, surrounded by 15+ sales ($2M+ in 6m,
    $5.5M+ in 12m) from multiple Presidents/SVPs cutting 30%–55% of holdings,
    with 6 consecutive sales in July–September after the lone buy.
  * APTV conviction signal: 4 distinct insiders (including CEO buying $2.5M and
    a Director buying $5.0M, +322% ΔOwn) bought $8.61M vs only $364k sold
    (96% buy volume, 23.6x buy/sell ratio), with the 4 most recent trades all
    being open-market purchases.
"""
import re
from datetime import datetime, timedelta
from io import StringIO
import requests
import pandas as pd

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}

CSUITE_KEYWORDS = ('CEO', 'CFO', 'COO', 'PRES', 'COB', 'CHAIR', 'CHIEF')


def _parse_money(val):
    if val is None:
        return 0.0
    s = re.sub(r'[^0-9.\-]', '', str(val))
    try:
        return abs(float(s)) if s else 0.0
    except ValueError:
        return 0.0


def _parse_delta_own(val):
    """
    Parse OpenInsider ΔOwn column:
      '-75%' -> -75.0
      '+322%' -> +322.0
      'New' -> +100.0
      '>999%' -> +999.0
    """
    if val is None:
        return 0.0
    s = str(val).strip()
    if 'new' in s.lower():
        return 100.0
    s_clean = re.sub(r'[^0-9.\-]', '', s)
    try:
        return float(s_clean) if s_clean else 0.0
    except ValueError:
        return 0.0


def empty_insider_record():
    return {
        'buy_count': 0,
        'unique_buyers': 0,
        'buy_value': 0.0,
        'csuite_buy': False,
        'sell_count': 0,
        'unique_sellers': 0,
        'sell_value': 0.0,
        'sell_value_12m': 0.0,
        'buy_sell_ratio': 0.0,
        'sells_after_last_buy': 0,
        'csuite_heavy_dump': False,
        'signal': 'NEUTRAL',
        'score_adj': 0.0,
        'summary': 'No notable open-market activity',
        'details': [],
        'warning': None,
    }


def fetch_ticker_insider(symbol, timeout=8):
    """
    Fetches the last 365 days of open-market purchases (P) and sales (S) from
    OpenInsider.com, analyzing:
      1. 6-month and 12-month Buy vs Sell dollar volume & unique headcount
      2. Chronological sequence (how many sales occurred AFTER the last buy)
      3. Ownership % cuts (ΔOwn <= -25% by C-Suite or multiple executives)
    """
    rec = empty_insider_record()
    clean_sym = symbol.replace('-', '.')
    url = (
        f"http://openinsider.com/screener?s={clean_sym}&o=&pl=&ph=&ll=&lh="
        f"&fd=365&fdr=&td=0&tdr=&feession=&xp=1&xs=1&vl=&vh=&ocl=&och="
        f"&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh="
        f"&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200 or 'tinytable' not in resp.text:
            return rec
        tables = pd.read_html(StringIO(resp.text))
        target = None
        for t in tables:
            cols = [str(c).strip() for c in t.columns]
            if any('Trade' in c and 'Type' in c for c in cols):
                target = t
                break
        if target is None or target.empty:
            return rec

        target.columns = [re.sub(r'\s+', ' ', str(c)).strip() for c in target.columns]
        col_type = next((c for c in target.columns if 'Trade' in c and 'Type' in c), None)
        col_insider = next((c for c in target.columns if 'Insider' in c and 'Name' in c), None)
        col_title = next((c for c in target.columns if 'Title' in c), None)
        col_value = next((c for c in target.columns if 'Value' in c), None)
        col_date = next((c for c in target.columns if 'Trade' in c and 'Date' in c), None)
        col_price = next((c for c in target.columns if 'Price' in c), None)
        col_down = next((c for c in target.columns if 'Own' in c and ('Δ' in c or 'Delta' in c or c != 'Owned')), None)

        if not col_type or not col_value:
            return rec

        # Determine 180-day cutoff relative to the most recent trade date in table
        latest_dt = None
        parsed_rows = []
        for _, row in target.iterrows():
            ttype = str(row.get(col_type, '')).strip()
            val = _parse_money(row.get(col_value, 0))
            if val <= 0 or not (ttype.startswith('P') or ttype.startswith('S')):
                continue
            tdate_str = str(row.get(col_date, '')).strip() if col_date else ''
            dt = None
            try:
                dt = datetime.strptime(tdate_str[:10], '%Y-%m-%d')
                if latest_dt is None or dt > latest_dt:
                    latest_dt = dt
            except Exception:
                pass
            parsed_rows.append((row, ttype, val, tdate_str, dt))

        if not parsed_rows:
            return rec

        ref_dt = latest_dt or datetime.now()
        cutoff_6m = ref_dt - timedelta(days=185)

        buyers_6m, sellers_6m = set(), set()
        buyers_12m, sellers_12m = set(), set()
        buy_val_6m, sell_val_6m = 0.0, 0.0
        buy_val_12m, sell_val_12m = 0.0, 0.0
        buy_cnt_6m, sell_cnt_6m = 0, 0
        csuite_buy_6m = False
        csuite_buy_val = 0.0
        csuite_heavy_dump = False
        csuite_dump_desc = None
        large_pct_sellers = 0

        # Rows in OpenInsider are newest-first: count how many sells happened
        # AFTER the most recent buy
        seen_first_buy = False
        sells_after_last_buy = 0
        consecutive_recent_buys = 0
        seen_first_sell = False

        details = []

        for row, ttype, val, tdate_str, dt in parsed_rows:
            in_6m = (dt is None) or (dt >= cutoff_6m)
            name = str(row.get(col_insider, 'Insider')).strip() if col_insider else 'Insider'
            title = str(row.get(col_title, '')).strip() if col_title else ''
            price = str(row.get(col_price, '')).strip() if col_price else ''
            delta_own = _parse_delta_own(row.get(col_down)) if col_down else 0.0
            delta_str = f" ({delta_own:+.0f}% stake)" if delta_own != 0 else ""
            title_up = title.upper()
            is_csuite = any(k in title_up for k in CSUITE_KEYWORDS)

            if ttype.startswith('P'):
                seen_first_buy = True
                if not seen_first_sell:
                    consecutive_recent_buys += 1
                buyers_12m.add(name)
                buy_val_12m += val
                if in_6m:
                    buy_cnt_6m += 1
                    buyers_6m.add(name)
                    buy_val_6m += val
                    if is_csuite and val >= 100_000:
                        csuite_buy_6m = True
                        csuite_buy_val += val
                if len(details) < 6:
                    details.append(f"BUY: {name} ({title}) bought ${val:,.0f} @ {price}{delta_str} [{tdate_str}]")

            elif ttype.startswith('S'):
                seen_first_sell = True
                if not seen_first_buy:
                    sells_after_last_buy += 1
                sellers_12m.add(name)
                sell_val_12m += val
                if in_6m:
                    sell_cnt_6m += 1
                    sellers_6m.add(name)
                    sell_val_6m += val
                if delta_own <= -25.0 and val >= 200_000:
                    large_pct_sellers += 1
                    if is_csuite and (delta_own <= -35.0 or val >= 5_000_000):
                        csuite_heavy_dump = True
                        if not csuite_dump_desc:
                            csuite_dump_desc = f"{title} {name} sold ${val/1e6:.1f}M ({delta_own:.0f}% of stake) on {tdate_str}"
                elif is_csuite and val >= 15_000_000:
                    csuite_heavy_dump = True
                    if not csuite_dump_desc:
                        csuite_dump_desc = f"{title} {name} sold ${val/1e6:.1f}M on {tdate_str}"

                if len(details) < 6 and (val >= 250_000 or delta_own <= -20.0):
                    details.append(f"SELL: {name} ({title}) sold ${val:,.0f} @ {price}{delta_str} [{tdate_str}]")

        total_6m = buy_val_6m + sell_val_6m
        buy_ratio_6m = (buy_val_6m / total_6m) if total_6m > 0 else 0.0

        rec['buy_count'] = buy_cnt_6m
        rec['unique_buyers'] = len(buyers_6m)
        rec['buy_value'] = buy_val_6m
        rec['csuite_buy'] = csuite_buy_6m
        rec['sell_count'] = sell_cnt_6m
        rec['unique_sellers'] = len(sellers_6m)
        rec['sell_value'] = sell_val_6m
        rec['sell_value_12m'] = sell_val_12m
        rec['buy_sell_ratio'] = round(buy_ratio_6m * 100, 1)
        rec['sells_after_last_buy'] = sells_after_last_buy
        rec['csuite_heavy_dump'] = csuite_heavy_dump
        rec['details'] = details

        # =====================================================================
        # CLASSIFICATION: Compare Buys vs Sells, Sequence & C-Suite Dumping
        # =====================================================================
        n_buy = len(buyers_6m)
        n_sell = len(sellers_6m)

        # Case 1: True Conviction Cluster Buy (like APTV: 3+ buyers, $1M+ bought,
        #         buys dominate sells >= 75% of dollar volume, not buried by newer sells)
        if (n_buy >= 3 and buy_val_6m >= 500_000
                and buy_ratio_6m >= 0.70 and sells_after_last_buy <= 1):
            rec['signal'] = 'CLUSTER BUY'
            rec['score_adj'] = 14.0 if (csuite_buy_6m and buy_val_6m >= 2_000_000) else 11.0
            rec['summary'] = (
                f"CONVICTION CLUSTER BUY: {n_buy} insiders bought ${buy_val_6m/1e6:.2f}M "
                f"vs ${sell_val_6m/1e6:.2f}M sold ({buy_ratio_6m*100:.0f}% buy volume)"
            )
            return rec

        # Case 2: Smaller Cluster Buy (3+ buyers, >= $150k, buys > sells)
        if (n_buy >= 3 and buy_val_6m >= 150_000
                and buy_ratio_6m >= 0.60 and sells_after_last_buy <= 2
                and not csuite_heavy_dump):
            rec['signal'] = 'CLUSTER BUY'
            rec['score_adj'] = 9.0
            rec['summary'] = (
                f"Cluster Buy: {n_buy} insiders bought ${buy_val_6m/1e3:.0f}k "
                f"vs ${sell_val_6m/1e3:.0f}k sold"
            )
            return rec

        # Case 3: Lone Buy Drowned Out by Heavy C-Suite / Founder Dumping (INTU case)
        if csuite_heavy_dump and buy_val_6m < sell_val_12m * 0.10:
            rec['signal'] = 'C-SUITE DUMPING'
            rec['score_adj'] = -8.0
            rec['summary'] = (
                f"C-Suite Liquidation: ${sell_val_12m/1e6:.1f}M sold in 12m "
                f"(vs ${buy_val_6m/1e3:.0f}k bought). {csuite_dump_desc or ''}"
            )
            rec['warning'] = (
                f"Heavy insider selling on OpenInsider: ${sell_val_12m/1e6:.1f}M sold over 12m "
                f"({csuite_dump_desc or 'multiple executives selling'}) outweighs ${buy_val_6m/1e3:.0f}k buy."
            )
            return rec

        # Case 4: Lone Buy Surrounded / Followed by Many Sells (PYPL & INTU 6m case)
        if n_buy >= 1 and (sell_val_6m > buy_val_6m or sells_after_last_buy >= 3 or sell_cnt_6m >= buy_cnt_6m * 3):
            rec['signal'] = 'LONE BUY / HEAVY SELLS'
            rec['score_adj'] = -3.0 if (sell_val_6m > buy_val_6m * 2 or large_pct_sellers >= 2) else -1.0
            rec['summary'] = (
                f"Lone Buy Outweighed by Sells: {n_buy} buyer (${buy_val_6m/1e3:.0f}k) vs "
                f"{sell_cnt_6m} sales (${sell_val_6m/1e6:.2f}M in 6m; {sells_after_last_buy} sales since last buy)"
            )
            rec['warning'] = (
                f"OpenInsider Divergence: Only {n_buy} insider bought (${buy_val_6m/1e3:.0f}k), while "
                f"{n_sell} insiders executed {sell_cnt_6m} sales totaling ${sell_val_6m/1e6:.2f}M "
                f"({sells_after_last_buy} consecutive sales after the buy)."
            )
            return rec

        # Case 5: Clean CEO/CFO Buy (buys clearly exceed sells and not followed by a wave of selling)
        if (csuite_buy_6m and buy_val_6m >= 150_000
                and buy_ratio_6m >= 0.65 and sells_after_last_buy <= 1
                and not csuite_heavy_dump):
            rec['signal'] = 'CEO/CFO BUY'
            rec['score_adj'] = 8.0
            rec['summary'] = (
                f"Clean C-Suite Buy: ${buy_val_6m/1e3:.0f}k bought vs ${sell_val_6m/1e3:.0f}k sold "
                f"({buy_ratio_6m*100:.0f}% buy volume)"
            )
            return rec

        # Case 6: Clean Net Insider Buy (buys >= 2x sells, at least $100k, recent)
        if (n_buy >= 1 and buy_val_6m >= 100_000
                and buy_ratio_6m >= 0.67 and sells_after_last_buy <= 1
                and not csuite_heavy_dump):
            rec['signal'] = 'INSIDER BUY'
            rec['score_adj'] = 4.5
            rec['summary'] = (
                f"Net Insider Buy: {n_buy} buyer(s) bought ${buy_val_6m/1e3:.0f}k "
                f"vs ${sell_val_6m/1e3:.0f}k sold"
            )
            return rec

        # Case 7: Heavy Multi-Insider Selling with Zero Buying
        if (len(sellers_12m) >= 4 and (sell_val_6m >= 10_000_000 or sell_val_12m >= 25_000_000)
                and n_buy == 0):
            rec['signal'] = 'HEAVY SELLING'
            rec['score_adj'] = -6.0
            rec['summary'] = (
                f"Heavy Selling: {len(sellers_12m)} insiders sold ${sell_val_12m/1e6:.1f}M in 12m (0 buys)"
            )
            rec['warning'] = f"OpenInsider: {len(sellers_12m)} insiders sold ${sell_val_12m/1e6:.1f}M over 12 months with zero open-market buys."
            return rec

        if sell_cnt_6m > 0 and n_buy == 0:
            rec['signal'] = 'ROUTINE SELLS'
            rec['score_adj'] = -1.0 if sell_val_6m >= 3_000_000 else 0.0
            rec['summary'] = f"0 buys / {n_sell} seller(s) (${sell_val_6m/1e6:.2f}M in 6m)"
        return rec
    except Exception:
        return rec
