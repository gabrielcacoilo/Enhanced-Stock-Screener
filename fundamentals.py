"""
fundamentals.py - Multi-year fundamental analysis for a single company.

Works on the ANNUAL statements returned by yfinance (usually the last 4 fiscal
years) instead of one-day snapshot ratios. Every number used for a decision is
computed here from the statements, so it can be traced and sanity-checked.

Academic models used:
  * Piotroski F-Score (2000)  - 9 accounting tests of improving fundamentals
  * Altman Z-Score   (1968)   - bankruptcy / distress risk
  * Beneish M-Score  (1999)   - statistical fingerprint of earnings manipulation
  * Reverse DCF               - what growth is today's price assuming?
"""
import math
import statistics

import pandas as pd

DISCOUNT_RATE = 0.09      # required annual return used in DCF maths
TERMINAL_GROWTH = 0.025   # long-run growth after year 10
DCF_YEARS = 10


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def clean(v):
    """Convert anything to a float, or None if missing / NaN / inf."""
    try:
        if v is None:
            return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def cagr(new, old, years):
    if new is None or old is None or years <= 0 or new <= 0 or old <= 0:
        return None
    return (new / old) ** (1.0 / years) - 1


def series_cagr(vals):
    """vals are newest-first. CAGR between the newest and oldest valid points."""
    idx = [i for i, v in enumerate(vals) if v is not None]
    if len(idx) < 2:
        return None
    i_new, i_old = idx[0], idx[-1]
    return cagr(vals[i_new], vals[i_old], i_old - i_new)


def mean(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def normalize_statement(df):
    """Columns -> 'YYYY-MM' strings, newest first, mostly-empty columns removed."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    df = df.copy()
    try:
        df.columns = [pd.Timestamp(c).strftime('%Y-%m') for c in df.columns]
    except Exception:
        return None
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    keep = [c for c in df.columns if df[c].notna().mean() > 0.3]
    if not keep:
        return None
    return df[sorted(keep, reverse=True)]


def get_series(df, names, periods):
    """First matching row (by any of `names`) as a list aligned to `periods`."""
    if df is None:
        return [None] * len(periods)
    for n in names:
        if n in df.index:
            row = df.loc[n]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            return [clean(row[p]) if p in row.index else None for p in periods]
    return [None] * len(periods)


def tax_rate(tax, pretax):
    if tax is None or pretax is None or pretax <= 0:
        return 0.21
    return min(max(tax / pretax, 0.0), 0.35)


# ----------------------------------------------------------------------------
# Valuation maths
# ----------------------------------------------------------------------------
def pv_constant_growth(fcf0, g, r=DISCOUNT_RATE, tg=TERMINAL_GROWTH, years=DCF_YEARS):
    total, f = 0.0, fcf0
    for y in range(1, years + 1):
        f *= (1 + g)
        total += f / (1 + r) ** y
    terminal = f * (1 + tg) / (r - tg)
    return total + terminal / (1 + r) ** years


def reverse_dcf(ev, fcf0):
    """Annual FCF growth (next 10 yrs) that justifies today's enterprise value."""
    if ev is None or fcf0 is None or ev <= 0 or fcf0 <= 0:
        return None
    lo, hi = -0.30, 0.60
    if pv_constant_growth(fcf0, lo) > ev:
        return lo
    if pv_constant_growth(fcf0, hi) < ev:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if pv_constant_growth(fcf0, mid) < ev:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def dcf_fading(fcf0, g_start, r=DISCOUNT_RATE, tg=TERMINAL_GROWTH, years=DCF_YEARS):
    """DCF where growth fades linearly from g_start to terminal growth."""
    total, f = 0.0, fcf0
    for y in range(1, years + 1):
        g = g_start + (tg - g_start) * (y - 1) / (years - 1)
        f *= (1 + g)
        total += f / (1 + r) ** y
    terminal = f * (1 + tg) / (r - tg)
    return total + terminal / (1 + r) ** years


# ----------------------------------------------------------------------------
# Academic scores
# ----------------------------------------------------------------------------
def _v(lst, i):
    return lst[i] if len(lst) > i else None


def piotroski(ni, cfo, ta, ltd, ca, cl, shares, rev, gp):
    tests = []
    roa0, roa1 = safe_div(_v(ni, 0), _v(ta, 0)), safe_div(_v(ni, 1), _v(ta, 1))
    if roa0 is not None:
        tests.append(roa0 > 0)
    if _v(cfo, 0) is not None:
        tests.append(_v(cfo, 0) > 0)
    if roa0 is not None and roa1 is not None:
        tests.append(roa0 > roa1)
    if _v(cfo, 0) is not None and _v(ni, 0) is not None:
        tests.append(_v(cfo, 0) > _v(ni, 0))
    lev0 = safe_div(_v(ltd, 0) or 0.0, _v(ta, 0))
    lev1 = safe_div(_v(ltd, 1) or 0.0, _v(ta, 1))
    if lev0 is not None and lev1 is not None:
        tests.append(lev0 <= lev1)
    cr0, cr1 = safe_div(_v(ca, 0), _v(cl, 0)), safe_div(_v(ca, 1), _v(cl, 1))
    if cr0 is not None and cr1 is not None:
        tests.append(cr0 > cr1)
    if _v(shares, 0) is not None and _v(shares, 1) is not None:
        tests.append(_v(shares, 0) <= _v(shares, 1) * 1.005)
    gm0, gm1 = safe_div(_v(gp, 0), _v(rev, 0)), safe_div(_v(gp, 1), _v(rev, 1))
    if gm0 is not None and gm1 is not None:
        tests.append(gm0 > gm1)
    at0, at1 = safe_div(_v(rev, 0), _v(ta, 0)), safe_div(_v(rev, 1), _v(ta, 1))
    if at0 is not None and at1 is not None:
        tests.append(at0 > at1)
    if len(tests) < 7:
        return None, len(tests)
    return round(sum(tests) / len(tests) * 9, 1), len(tests)


def altman_z(wc, re_, ebit, mcap, tl, sales, ta):
    if None in (wc, re_, ebit, mcap, tl, sales, ta) or ta <= 0 or tl <= 0:
        return None
    return (1.2 * wc / ta + 1.4 * re_ / ta + 3.3 * ebit / ta
            + 0.6 * mcap / tl + 1.0 * sales / ta)


def beneish(rev, gp, ar, ca, ppe, ta, dep, sga, cl, ltd, ni, cfo):
    try:
        r0, r1 = rev[0], rev[1]
        dsri = (ar[0] / r0) / (ar[1] / r1)
        gmi = (gp[1] / r1) / (gp[0] / r0)
        aqi = (1 - (ca[0] + ppe[0]) / ta[0]) / (1 - (ca[1] + ppe[1]) / ta[1])
        sgi = r0 / r1
        depi = (dep[1] / (dep[1] + ppe[1])) / (dep[0] / (dep[0] + ppe[0]))
        sgai = (sga[0] / r0) / (sga[1] / r1)
        lvgi = ((cl[0] + (ltd[0] or 0)) / ta[0]) / ((cl[1] + (ltd[1] or 0)) / ta[1])
        tata = (ni[0] - cfo[0]) / ta[0]
        m = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
             + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
        return clean(m)
    except (TypeError, ZeroDivisionError, IndexError):
        return None


# ----------------------------------------------------------------------------
# Main analysis
# ----------------------------------------------------------------------------
def analyze_fundamentals(info, inc_raw, bal_raw, cf_raw):
    res = {'data_ok': False, 'metrics': {}, 'trends': {},
           'red_flags': [], 'warnings': [], 'data_notes': []}
    info = info or {}
    m = res['metrics']

    # ---- Market data (snapshot, used only for valuation & price action) ----
    price = clean(info.get('currentPrice')) or clean(info.get('regularMarketPrice'))
    shares_out = clean(info.get('sharesOutstanding'))
    mcap = clean(info.get('marketCap'))
    if mcap is None and price and shares_out:
        mcap = price * shares_out
    m['price'] = price
    m['market_cap'] = mcap
    high52 = clean(info.get('fiftyTwoWeekHigh'))
    dma200 = clean(info.get('twoHundredDayAverage'))
    m['change_52w'] = clean(info.get('52WeekChange'))
    m['price_vs_200dma'] = (price / dma200 - 1) if price and dma200 else None
    m['drawdown'] = (price / high52 - 1) if price and high52 else None
    m['pe_trailing'] = clean(info.get('trailingPE'))
    m['pe_forward'] = clean(info.get('forwardPE'))
    m['pb'] = clean(info.get('priceToBook'))
    div_rate = clean(info.get('dividendRate'))
    # dividendRate / price avoids yfinance's inconsistent dividendYield units
    m['dividend_yield'] = (div_rate / price) if div_rate and price else 0.0
    eps_t, eps_f = clean(info.get('trailingEps')), clean(info.get('forwardEps'))
    m['eps_trailing'], m['eps_forward'] = eps_t, eps_f
    m['eps_expected_change'] = (eps_f / eps_t - 1) if eps_t and eps_t > 0 and eps_f is not None else None

    # ---- Data validation ----
    fin_cur, px_cur = info.get('financialCurrency'), info.get('currency')
    if fin_cur and px_cur and fin_cur != px_cur:
        res['data_notes'].append(
            f"Statements are in {fin_cur} but the price is in {px_cur}; ratios would be wrong, so the stock is not rated.")
        return res
    if price and shares_out and mcap and abs(price * shares_out / mcap - 1) > 0.25:
        res['data_notes'].append('Market cap and share count disagree (probably several share classes); per-share values are approximate.')

    inc, bal, cf = (normalize_statement(x) for x in (inc_raw, bal_raw, cf_raw))
    if inc is None or bal is None or cf is None:
        res['data_notes'].append('Annual financial statements unavailable from Yahoo.')
        return res
    periods = sorted(set(inc.columns) & set(bal.columns) & set(cf.columns), reverse=True)[:4]
    n = len(periods)
    m['years'] = n
    if n < 3:
        res['data_notes'].append(f'Only {n} year(s) of aligned statements; at least 3 are needed for trend analysis.')
        return res

    def S(df, names):
        return get_series(df, names, periods)

    rev = S(inc, ['Total Revenue', 'Operating Revenue'])
    gp = S(inc, ['Gross Profit'])
    cogs = S(inc, ['Cost Of Revenue', 'Reconciled Cost Of Revenue'])
    if all(x is None for x in gp):
        gp = [r - c if r is not None and c is not None else None for r, c in zip(rev, cogs)]
    op_inc = S(inc, ['Operating Income', 'Total Operating Income As Reported'])
    ebit = S(inc, ['EBIT'])
    ebit = [e if e is not None else o for e, o in zip(ebit, op_inc)]
    ebitda = S(inc, ['EBITDA', 'Normalized EBITDA'])
    ni = S(inc, ['Net Income Common Stockholders', 'Net Income',
                 'Net Income From Continuing Operation Net Minority Interest'])
    int_exp = S(inc, ['Interest Expense', 'Interest Expense Non Operating'])
    pretax = S(inc, ['Pretax Income'])
    tax = S(inc, ['Tax Provision'])
    sga = S(inc, ['Selling General And Administration'])
    rd = S(inc, ['Research And Development', 'Research & Development', 'Research and Development'])
    dil_shares = S(inc, ['Diluted Average Shares', 'Basic Average Shares'])

    ta = S(bal, ['Total Assets'])
    ca = S(bal, ['Current Assets'])
    cl = S(bal, ['Current Liabilities'])
    tl = S(bal, ['Total Liabilities Net Minority Interest'])
    total_debt = S(bal, ['Total Debt'])
    ltd = S(bal, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation'])
    equity = S(bal, ['Stockholders Equity', 'Common Stock Equity'])
    retained = S(bal, ['Retained Earnings'])
    wc = S(bal, ['Working Capital'])
    cash = S(bal, ['Cash Cash Equivalents And Short Term Investments', 'Cash And Cash Equivalents'])
    bs_shares = S(bal, ['Ordinary Shares Number', 'Share Issued'])
    ar = S(bal, ['Accounts Receivable', 'Receivables'])
    ppe = S(bal, ['Net PPE'])
    invested = S(bal, ['Invested Capital'])

    cfo = S(cf, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'])
    capex = S(cf, ['Capital Expenditure'])
    fcf = S(cf, ['Free Cash Flow'])
    fcf = [f if f is not None else (o - abs(c) if o is not None and c is not None else o)
           for f, o, c in zip(fcf, cfo, capex)]
    sbc = S(cf, ['Stock Based Compensation'])
    dep = S(cf, ['Depreciation And Amortization', 'Depreciation Amortization Depletion'])
    if all(x is None for x in dep):
        dep = S(inc, ['Reconciled Depreciation'])

    shares = dil_shares if any(x is not None for x in dil_shares) else bs_shares

    critical = {'revenue': rev[0], 'operating cash flow': cfo[0], 'free cash flow': fcf[0],
                'total assets': ta[0], 'market cap': mcap, 'price': price}
    missing = [k for k, v in critical.items() if v is None]
    if missing:
        res['data_notes'].append('Missing critical data: ' + ', '.join(missing) + '.')
        return res
    if rev[0] <= 0:
        res['data_notes'].append('No meaningful revenue reported.')
        return res
    res['data_ok'] = True

    # ---- Owner free cash flow (FCF minus stock-based compensation) ----
    owner = [f - (s or 0.0) if f is not None else None for f, s in zip(fcf, sbc)]
    if all(s is None for s in sbc):
        res['data_notes'].append('No stock-compensation line found; owner FCF = reported FCF.')
    recent = [x for x in owner[:3] if x is not None]
    avg3 = sum(recent) / len(recent) if len(recent) >= 2 else owner[0]
    latest = owner[0]
    # use the latest year unless it is a spike well above a positive 3-year average
    norm_owner = latest if (latest is not None and (avg3 is None or avg3 <= 0 or latest <= 1.3 * avg3)) else avg3
    m['owner_fcf'] = latest
    m['owner_fcf_norm'] = norm_owner
    m['sbc_to_revenue'] = safe_div(sbc[0], rev[0]) if sbc[0] is not None else None

    # ---- Balance sheet / EV ----
    sector_str = str(info.get('sector') or '')
    is_financial = ('Financial' in sector_str)
    debt0 = total_debt[0]
    if debt0 is None:
        debt0 = 0.0
        res['data_notes'].append("No 'Total Debt' line; treated as debt-free.")
    cash0 = cash[0] or 0.0
    # For banks & insurers, balance-sheet cash and short-term investments represent
    # customer deposits or policyholder float held against liabilities, not excess
    # corporate cash that can be subtracted from Market Cap in Enterprise Value.
    net_debt = 0.0 if is_financial else (debt0 - cash0)
    ev = mcap + net_debt
    m['net_debt'] = net_debt
    m['ev'] = ev

    # ---- Empirical Academic Factors (SSRN / Novy-Marx / Ball / Hou-Xue-Zhang / Lev) ----
    # 1. Novy-Marx (2013 JFE): Gross Profitability = Gross Profit / Total Assets
    m['gross_profitability'] = safe_div(gp[0], ta[0])
    # 2. Ball, Gerakos, Linnainmaa, Nikolaev (2016 JFE): Cash-Based Operating Profitability = CFO / Total Assets
    m['cash_op_profitability'] = safe_div(cfo[0], ta[0])
    # 3. Hou, Xue, Zhang (2015 RFS): Asset Growth Rate = (Assets_t - Assets_t-1) / Assets_t-1 (Capital Discipline)
    m['asset_growth'] = (ta[0] / ta[1] - 1.0) if len(ta) > 1 and ta[0] is not None and ta[1] is not None and ta[1] > 0 else None
    # 4. Baruch Lev & Anup Srivastava (2019 SSRN 3442539): Capitalized Knowledge & R&D Capital (5-yr straight line)
    rd_capital = 0.0
    has_rd = any(x is not None and x > 0 for x in rd)
    if has_rd:
        for k in range(min(n, 5)):
            if rd[k] is not None and rd[k] > 0:
                rd_capital += rd[k] * (1.0 - 0.2 * k)
    m['rd_capital'] = rd_capital if has_rd else 0.0

    # ---- Quality & ROIC (needed before valuation for fundamental growth) ----
    roic_list = []
    for i in range(n):
        e = ebit[i]
        ic = invested[i]
        if ic is None and equity[i] is not None:
            ic = (equity[i] if is_financial else (total_debt[i] or 0.0) + equity[i] - (cash[i] or 0.0))
        if e is not None and ic is not None and ic > 0:
            roic_list.append(e * (1 - tax_rate(tax[i], pretax[i])) / ic)
        elif is_financial and ni[i] is not None and equity[i] is not None and equity[i] > 0:
            roic_list.append(ni[i] / equity[i])
        else:
            roic_list.append(None)
    m['roic'] = mean(roic_list[:3])
    gm = [safe_div(g, r) for g, r in zip(gp, rev)]
    gm_valid = [x for x in gm if x is not None]
    m['gross_margin'] = gm[0]
    m['gm_volatility'] = statistics.pstdev(gm_valid) if len(gm_valid) >= 3 else None
    opm = [safe_div(o, r) for o, r in zip(op_inc, rev)]
    m['op_margin'] = opm[0]
    opm_idx = [i for i, v in enumerate(opm) if v is not None]
    m['op_margin_change'] = (opm[opm_idx[0]] - opm[opm_idx[-1]]) if len(opm_idx) >= 2 else None
    f_score, f_tests = piotroski(ni, cfo, ta, ltd, ca, cl, shares, rev, gp)
    m['piotroski'], m['piotroski_tests'] = f_score, f_tests
    ni3 = [x for x in ni[:3] if x is not None]
    ow3 = [x for x in owner[:3] if x is not None]
    if len(ni3) >= 2 and len(ow3) >= 2 and sum(ni3) > 0:
        m['cash_conversion'] = min(sum(ow3) / sum(ni3), 3.0)
    else:
        m['cash_conversion'] = None

    # ---- Value & Academic Expectations Engine (SSRN / Mauboussin / Penman / Cifuentes) ----
    m['owner_fcf_yield'] = safe_div(norm_owner, mcap)
    m['ebit_ev'] = safe_div(ebit[0], ev) if ev > 0 else None
    rev_cagr = series_cagr(rev)
    m['rev_cagr'] = rev_cagr
    implied = reverse_dcf(ev, norm_owner)
    m['implied_growth'] = implied
    m['growth_gap'] = (rev_cagr - implied) if rev_cagr is not None and implied is not None else None

    # Modern SSRN Multi-Scenario Probabilistic Valuation (Cifuentes 2016 / Mauboussin / Penman)
    # Fundamental growth = Reinvestment Rate * ROIC
    roic_val = m.get('roic') or 0.10
    reinvest_rate = 0.40
    if norm_owner and ebit[0] and ebit[0] > 0:
        nopat = ebit[0] * (1.0 - tax_rate(tax[0], pretax[0]))
        if nopat > 0:
            reinvest_rate = max(0.15, min(0.75, 1.0 - (norm_owner / nopat)))
    g_fund = max(0.0, reinvest_rate * roic_val)
    
    # Blended sustainable growth: 50% fundamental economic engine + 50% actual historical revenue execution
    rcagr_clamped = min(max(rev_cagr or 0.0, -0.05), 0.35)
    g_base = min(max(0.50 * g_fund + 0.50 * rcagr_clamped, -0.05), 0.22)
    g_bear = max(-0.05, g_base * 0.60)
    g_bull = min(0.30, g_base * 1.30)

    shares_for_value = shares_out or (shares[0] if shares else None)
    if norm_owner and norm_owner > 0 and shares_for_value:
        # Base Case (Standard WACC = 9.0%, terminal growth = 2.5%)
        fair_equity_base = dcf_fading(norm_owner, g_base, r=DISCOUNT_RATE, tg=TERMINAL_GROWTH) - net_debt
        fair_price_base = max(0.0, fair_equity_base / shares_for_value)
        
        # Bear / Stressed Case (-1 sigma: lower growth, higher discount rate 10.5%)
        fair_equity_bear = dcf_fading(norm_owner, g_bear, r=0.105, tg=TERMINAL_GROWTH) - net_debt
        fair_price_bear = max(0.0, fair_equity_bear / shares_for_value)
        
        # Bull / High-Execution Case (+1 sigma: higher growth, premium WACC 8.0%)
        fair_equity_bull = dcf_fading(norm_owner, g_bull, r=0.080, tg=TERMINAL_GROWTH) - net_debt
        fair_price_bull = max(0.0, fair_equity_bull / shares_for_value)

        m['dcf_growth_used'] = g_base
        m['fair_value'] = fair_price_base
        m['fair_value_base'] = fair_price_base
        m['fair_value_bear'] = fair_price_bear
        m['fair_value_bull'] = fair_price_bull
        m['fair_value_mos'] = (fair_price_base / price - 1.0) if price else None
    else:
        m['dcf_growth_used'] = m['fair_value'] = m['fair_value_base'] = m['fair_value_bear'] = m['fair_value_bull'] = m['fair_value_mos'] = None

    # ---- Growth ----
    owner_ps = [safe_div(o, s) for o, s in zip(owner, shares)]
    m['owner_fcf_ps_cagr'] = series_cagr(owner_ps)

    # ---- Financial strength ----
    e0 = ebitda[0]
    m['net_debt_ebitda'] = (net_debt / e0) if e0 and e0 > 0 else None
    ie = abs(int_exp[0]) if int_exp[0] else None
    if ie:
        m['interest_coverage'] = safe_div(ebit[0], ie)
    else:
        m['interest_coverage'] = 100.0 if net_debt <= 0 else None
    wc0 = wc[0] if wc[0] is not None else (ca[0] - cl[0] if ca[0] is not None and cl[0] is not None else None)
    m['altman_z'] = None if is_financial else altman_z(wc0, retained[0], ebit[0], mcap, tl[0], rev[0], ta[0])
    m['beneish_m'] = None if is_financial else beneish(rev, gp, ar, ca, ppe, ta, dep, sga, cl, ltd, ni, cfo)

    # ---- Shareholder alignment ----
    m['share_cagr'] = series_cagr(shares)

    # ---- Trends for charts (oldest -> newest) ----
    res['trends'] = {
        'years': list(reversed(periods)),
        'revenue': list(reversed(rev)),
        'op_margin': list(reversed(opm)),
        'owner_fcf': list(reversed(owner)),
        'shares': list(reversed(shares)),
        'roic': list(reversed(roic_list)),
    }

    # ======================================================================
    # HARD RED FLAGS  (any one of these excludes the stock from the basket)
    # ======================================================================
    rf, wn = res['red_flags'], res['warnings']
    if latest is not None and latest <= 0:
        rf.append(f'Negative owner cash flow last year (FCF minus stock comp = {latest/1e9:.2f}B).')
    neg_years = sum(1 for x in fcf[:4] if x is not None and x < 0)
    if neg_years >= 2:
        rf.append(f'Free cash flow was negative in {neg_years} of the last {n} years.')
    if rev_cagr is not None and rev_cagr < -0.01 and (m['op_margin_change'] or 0) < 0:
        rf.append(f'Shrinking business: revenue {rev_cagr*100:.1f}%/yr and operating margin falling.')
    if m['share_cagr'] is not None and m['share_cagr'] > 0.02:
        rf.append(f"Shareholder dilution: share count growing {m['share_cagr']*100:.1f}%/yr.")
    if m['net_debt_ebitda'] is not None and m['net_debt_ebitda'] > 4:
        rf.append(f"Heavy debt: net debt is {m['net_debt_ebitda']:.1f}x EBITDA (limit 4x).")
    if e0 is not None and e0 <= 0 and net_debt > 0:
        rf.append('Negative EBITDA while carrying net debt.')
    if m['interest_coverage'] is not None and m['interest_coverage'] < 3:
        rf.append(f"Weak interest coverage: operating profit only {m['interest_coverage']:.1f}x interest (min 3x).")
    if m['altman_z'] is not None and m['altman_z'] < 1.8:
        rf.append(f"Altman Z-Score {m['altman_z']:.2f} is in the distress zone (< 1.8).")

    # ======================================================================
    # WARNINGS  (score penalty, shown in the report, not an automatic exclusion)
    # ======================================================================
    # Forward EPS decline is a forecast, not an accounting failure. It is also
    # distorted when trailing GAAP EPS contains one-off gains (e.g. mark-to-market
    # gains on equity stakes) that the analyst forward estimate excludes. It is
    # therefore a scored warning (see compute_scores) rather than a hard red flag.
    if m['eps_expected_change'] is not None and m['eps_expected_change'] < -0.15:
        wn.append(
            f"Forward EPS estimate is {abs(m['eps_expected_change'])*100:.0f}% below trailing EPS: either a cyclical "
            f"earnings peak or trailing EPS inflated by one-off gains. Check the income statement for non-recurring items.")
    if m['beneish_m'] is not None and m['beneish_m'] > -1.78:
        wn.append(f"Beneish M-Score {m['beneish_m']:.2f} resembles past earnings manipulators (> -1.78). Often a false alarm for fast growers; read the cash-flow statement.")
    if m['cash_conversion'] is not None and m['cash_conversion'] < 0.6:
        wn.append(f"Low cash conversion: only {m['cash_conversion']*100:.0f}% of reported profit became owner cash over 3 years.")
    if m['owner_fcf_yield'] is not None and m['owner_fcf_yield'] > 0.25:
        wn.append('Unusually high cash yield; check for one-offs (asset sales, working-capital swings) or data errors.')
    if (m['change_52w'] is not None and m['change_52w'] < -0.30
            and m['price_vs_200dma'] is not None and m['price_vs_200dma'] < 0):
        wn.append(f"Strong downtrend ({m['change_52w']*100:.0f}% in 12 months, below 200-day average): falling-knife risk.")
    if m['sbc_to_revenue'] is not None and m['sbc_to_revenue'] > 0.10:
        wn.append(f"Stock compensation is {m['sbc_to_revenue']*100:.0f}% of revenue.")
    if m['gm_volatility'] is not None and m['gm_volatility'] > 0.05:
        wn.append('Gross margins swing a lot year to year (cyclical or commodity-driven business).')

    # ======================================================================
    # OBJECTIVE ECONOMIC REALITY ENGINE: PLEASING SIGNALS & THROW-OFFS
    # (Warren Buffett / Charlie Munger Owner-Earnings Quality Framework)
    # ======================================================================
    pleasing = []
    throwoffs = []

    # 1. Real Cash Yield (Owner FCF / Market Cap >= 4.5%)
    if m.get('owner_fcf_yield') is not None and m['owner_fcf_yield'] >= 0.045:
        pleasing.append(f"High Cash Yield: {m['owner_fcf_yield']*100:.1f}% Owner FCF yield returned to capital today.")
    elif m.get('owner_fcf_yield') is not None and m['owner_fcf_yield'] <= 0.015:
        throwoffs.append(f"Low Cash Yield: Only {m['owner_fcf_yield']*100:.2f}% Owner FCF yield (expensive cash valuation).")

    # 2. Return on Capital (ROIC >= 18%)
    if m.get('roic') is not None and m['roic'] >= 0.18:
        pleasing.append(f"High Compounding Power: 3Y ROIC is {m['roic']*100:.1f}% (seeds multiply rapidly).")
    elif m.get('roic') is not None and m['roic'] < 0.10:
        throwoffs.append(f"Weak Return on Capital: 3Y ROIC is {m['roic']*100:.1f}% (fails 10% hurdle rate).")

    # 3. Cash Conversion (CFO >= 90% of Net Income)
    if m.get('cash_conversion') is not None and m['cash_conversion'] >= 0.90:
        pleasing.append(f"Pristine Cash Conversion: {m['cash_conversion']*100:.0f}% of reported profit verified as real cash.")
    elif m.get('cash_conversion') is not None and m['cash_conversion'] < 0.60:
        throwoffs.append(f"Poor Cash Conversion: Only {m['cash_conversion']*100:.0f}% of reported earnings became cash.")

    # 4. Asset Productivity (Novy-Marx Gross Profit / Assets >= 28%)
    if m.get('gross_profitability') is not None and m['gross_profitability'] >= 0.28:
        pleasing.append(f"High Asset Productivity: Novy-Marx GP/Assets is {m['gross_profitability']*100:.1f}% (strong economic moat).")
    elif m.get('gross_profitability') is not None and m['gross_profitability'] < 0.15:
        throwoffs.append(f"Low Asset Productivity: Novy-Marx GP/Assets is {m['gross_profitability']*100:.1f}% (heavy asset drag).")

    # 5. Shareholder Loyalty / Buybacks (Diluted shares retiring >= 1.0%/yr)
    if m.get('share_cagr') is not None and m['share_cagr'] <= -0.010:
        pleasing.append(f"Active Float Retirement: Buybacks retiring {abs(m['share_cagr'])*100:.1f}% of shares per year.")
    elif m.get('share_cagr') is not None and m['share_cagr'] > 0.015:
        throwoffs.append(f"Shareholder Dilution: Share count expanding {m['share_cagr']*100:.1f}%/yr (ownership diluted).")

    # 6. Fortress Balance Sheet (Net Cash or Net Debt <= 1.5x EBITDA, Altman Z >= 2.99)
    is_fortress = (m.get('net_debt_ebitda') is not None and m['net_debt_ebitda'] <= 1.5) or (m.get('net_debt') is not None and m['net_debt'] <= 0)
    if is_fortress and (m.get('altman_z') is None or m.get('altman_z') >= 2.99):
        pleasing.append("Balance Sheet Fortress: Net cash or minimal debt (< 1.5x EBITDA) with safe distance to default.")
    elif m.get('net_debt_ebitda') is not None and m['net_debt_ebitda'] > 3.0:
        throwoffs.append(f"Heavy Debt Leverage: Net debt is {m['net_debt_ebitda']:.1f}x EBITDA.")

    # Add hard red flags as throw-offs
    for rf_item in rf:
        if rf_item not in throwoffs:
            throwoffs.append(f"Dealbreaker: {rf_item}")

    m['pleasing_signals'] = pleasing
    m['throw_offs'] = throwoffs
    m['pleasing_count'] = len(pleasing)
    m['throwoff_count'] = len(throwoffs)
    return res
