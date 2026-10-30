"""
research_agent.py - Automated Qualitative & Catalyst Research Agent for the Top
Selected Stocks.

Runs ONLY on the selected Top Basket (10-15 stocks) so it finishes in ~10 seconds.
For each selected stock, it fetches and synthesizes:
  1. Official SEC EDGAR Filings (latest 10-K Annual Report, 10-Q Quarterly Report,
     and 8-K Material Event filing with direct clickable sec.gov links).
  2. Next Earnings Release Date & Event-Risk Countdown (flags binary earnings risk
     if reporting within 7 days).
  3. Live Multi-Source Financial News & Analyst Actions (Google News RSS + Yahoo
     Finance + Finviz analyst upgrades/downgrades & short interest) with clickable
     source URLs.
  4. Automated Moat & Pricing-Power Diagnosis (Wide Moat vs Narrow Moat vs
     Cyclical, derived from 4-yr gross-margin stability, ROIC, and business model).
  5. Synthesized Bull Case, Bear Case ("Why is it cheap?"), Execution Plan
     (Tranche 1 / Tranche 2 sizing), and Quantitative Exit Invalidation Triggers.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
try:
    import yfinance as yf
except ImportError:
    yf = None

HTTP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}
# SEC EDGAR requires a descriptive User-Agent header per fair-access policy
SEC_HEADERS = {
    'User-Agent': 'QuantWorkstationResearch/2.0 (Educational-Research; contact@localhost.localdomain)',
    'Accept-Encoding': 'gzip, deflate',
}

BEAR_THEMES = [
    ('Margin / Cost Pressure', ['margin', 'cost', 'inflation', 'tariff', 'supply chain', 'pricing pressure', 'headwind']),
    ('Demand / Macro Slowdown', ['slowdown', 'demand', 'guidance', 'cut', 'miss', 'weak', 'recession', 'consumer', 'ev slowdown']),
    ('Competition / Disruption', ['competit', 'market share', 'ai ', 'rival', 'disrupt', 'glp-1', 'ozempic']),
    ('Regulatory / Legal Overhang', ['antitrust', 'doj', 'ftc', 'regul', 'lawsuit', 'investigation', 'probe', 'Medicare', 'medicaid']),
    ('Analyst Downgrade / Target Cut', ['downgrade', 'lower', 'cut price target', 'underperform', 'sell', 'bearish']),
]

BULL_THEMES = [
    ('Earnings / Guidance Beat', ['beat', 'raise', 'strong', 'record', 'outperform', 'growth', 'surge', 'accelerate']),
    ('Contract / Product Catalyst', ['contract', 'award', 'launch', 'partner', 'approval', 'fda', 'backlog', 'deal']),
    ('Shareholder Returns / Buybacks', ['buyback', 'repurchase', 'dividend', 'capital return', 'undervalued']),
    ('Analyst Upgrade / Bullish Call', ['upgrade', 'overweight', 'buy rating', 'top pick', 'raise price target']),
]


_SEC_CIK_CACHE = None


def _load_sec_cik_map():
    """Fetches SEC ticker -> CIK mapping once and caches in memory."""
    global _SEC_CIK_CACHE
    if _SEC_CIK_CACHE is not None:
        return _SEC_CIK_CACHE
    try:
        r = requests.get('https://www.sec.gov/files/company_tickers.json', headers=SEC_HEADERS, timeout=8)
        if r.status_code == 200:
            data = r.json()
            mapping = {}
            for _, item in data.items():
                t = str(item.get('ticker', '')).upper()
                cik = str(item.get('cik_str', '')).zfill(10)
                if t and cik:
                    mapping[t] = cik
            _SEC_CIK_CACHE = mapping
            return mapping
    except Exception:
        pass
    return {}


def fetch_sec_filings(symbol, cik_map):
    """Returns clickable links to the latest 10-K, 10-Q, and 8-K on sec.gov."""
    filings = []
    cik = cik_map.get(symbol.upper()) or cik_map.get(symbol.replace('-', '.').upper())
    if not cik:
        return [
            {
                'form': 'SEC EDGAR',
                'date': 'Latest',
                'title': f'All Official SEC Filings for {symbol} (10-K, 10-Q, 8-K)',
                'url': f'https://www.sec.gov/edgar/searchedgar/companysearch?cik={symbol}',
            }
        ]
    try:
        url = f'https://data.sec.gov/submissions/CIK{cik}.json'
        r = requests.get(url, headers=SEC_HEADERS, timeout=8)
        if r.status_code == 200:
            recent = r.json().get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accs = recent.get('accessionNumber', [])
            docs = recent.get('primaryDocument', [])
            cik_int = str(int(cik))
            wanted = {'10-K': False, '10-Q': False, '8-K': False}
            for form, fdate, acc, doc in zip(forms, dates, accs, docs):
                if form in wanted and not wanted[form]:
                    acc_clean = acc.replace('-', '')
                    doc_url = f'https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{doc}'
                    desc = {
                        '10-K': 'Annual Report (Full Audited Statements, Risk Factors & Moat)',
                        '10-Q': 'Latest Quarterly Report (Unread Footnotes & Margin Trends)',
                        '8-K': 'Latest Current Report (Earnings Release / Material Event)',
                    }[form]
                    filings.append({
                        'form': form,
                        'date': fdate,
                        'title': f'{symbol} Form {form} — {desc}',
                        'url': doc_url,
                    })
                    wanted[form] = True
                if all(wanted.values()):
                    break
    except Exception:
        pass

    if not filings:
        filings.append({
            'form': 'SEC EDGAR',
            'date': 'Latest',
            'title': f'Official SEC EDGAR Filings Page for {symbol}',
            'url': f'https://www.sec.gov/edgar/browse/?CIK={cik}',
        })
    return filings


def fetch_google_news_rss(symbol, company_name, max_items=8):
    """Fetches recent news articles with clickable links via Google News RSS."""
    articles = []
    short_co = re.sub(r'\b(Inc\.?|Corp\.?|Corporation|plc|Ltd\.?|Company|Holdings|Group)\b', '', company_name, flags=re.I).strip()
    query = quote_plus(f'"{symbol}" OR "{short_co}" stock')
    url = f'https://news.google.com/rss/search?q={query}+when:60d&hl=en-US&gl=US&ceid=US:en'
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=7)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall('.//item')[:max_items]:
                title_raw = (item.findtext('title') or '').strip()
                link = (item.findtext('link') or '').strip()
                pub_date = (item.findtext('pubDate') or '')[:16].strip()
                source_el = item.find('source')
                publisher = source_el.text.strip() if source_el is not None and source_el.text else 'Financial News'
                if ' - ' in title_raw:
                    title_clean = title_raw.rsplit(' - ', 1)[0].strip()
                else:
                    title_clean = title_raw
                if title_clean and link:
                    articles.append({
                        'title': title_clean,
                        'publisher': publisher,
                        'date': pub_date,
                        'url': link,
                    })
    except Exception:
        pass
    return articles


def fetch_finviz_data(symbol):
    """Scrapes Finviz for recent analyst ratings/price targets and short interest."""
    out = {'analyst_actions': [], 'short_float': None, 'inst_own': None, 'target_price': None}
    url = f'https://finviz.com/quote.ashx?t={symbol.replace(".", "-")}'
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=7)
        if r.status_code != 200:
            return out
        html = r.text

        m_sf = re.search(r'>Short Float<.*?><b>([0-9.]+%)</b>', html, re.S)
        if m_sf:
            out['short_float'] = m_sf.group(1)
        m_io = re.search(r'>Inst Own<.*?><b>([0-9.]+%)</b>', html, re.S)
        if m_io:
            out['inst_own'] = m_io.group(1)
        m_tp = re.search(r'>Target Price<.*?><b>([0-9.]+)</b>', html, re.S)
        if m_tp:
            out['target_price'] = float(m_tp.group(1))

        # Parse analyst outer-ratings table if present
        rows = re.findall(r'<tr[^>]*class="[^"]*fv-elan-row[^"]*"[^>]*>(.*?)</tr>', html, re.S)
        if not rows:
            rows = re.findall(r'<td width="100%" class="fullview-ratings-inner">\s*<table[^>]*>(.*?)</table>', html, re.S)
        for chunk in rows[:5]:
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', chunk, re.S)]
            if len(cells) >= 4:
                out['analyst_actions'].append(' | '.join(c for c in cells[:5] if c))
    except Exception:
        pass
    return out


def fetch_earnings_date_and_profile(symbol):
    """Fetches business summary and next earnings date from yfinance."""
    out = {'summary': '', 'industry': '', 'earnings_date': None, 'days_to_earnings': None}
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        out['summary'] = info.get('longBusinessSummary') or ''
        out['industry'] = info.get('industry') or info.get('sector') or ''

        # Try calendar for next earnings date
        cal = t.calendar
        next_dt = None
        if isinstance(cal, dict) and 'Earnings Date' in cal:
            ed_list = cal['Earnings Date']
            if ed_list:
                first = ed_list[0]
                next_dt = datetime.combine(first, datetime.min.time()) if hasattr(first, 'year') else None
        if next_dt:
            out['earnings_date'] = next_dt.strftime('%Y-%m-%d')
            out['days_to_earnings'] = (next_dt.date() - datetime.now().date()).days
    except Exception:
        pass
    return out


def evaluate_moat(row, profile):
    """Classifies economic moat & pricing power from multi-year ROIC and margins."""
    roic = row.get('roic') or 0
    gm = row.get('gross_margin') or 0
    opm = row.get('op_margin') or 0
    opm_chg = row.get('op_margin_change') or 0

    if roic >= 0.18 and (gm >= 0.40 or opm >= 0.18) and opm_chg >= -0.02:
        rating = 'WIDE MOAT (Strong Pricing Power)'
        desc = (
            f"3Y average ROIC of {roic*100:.1f}% and operating margin of {opm*100:.1f}% "
            f"({opm_chg*100:+.1f} pts over 3Y) demonstrate durable competitive advantages and pricing power."
        )
    elif roic >= 0.12 and opm >= 0.10:
        rating = 'NARROW MOAT (Solid Market Position)'
        desc = (
            f"3Y average ROIC of {roic*100:.1f}% exceeds the ~9% cost of capital with a {opm*100:.1f}% "
            f"operating margin, indicating a defensible niche or switching-cost advantage."
        )
    else:
        rating = 'COMPETITIVE / CYCLICAL'
        desc = (
            f"3Y ROIC is {roic*100:.1f}% with a {opm*100:.1f}% operating margin. Business returns depend "
            f"on industry supply/demand discipline and cost control rather than effortless pricing power."
        )
    return rating, desc


def _detect_themes(news_items):
    """Returns (bear_labels, bull_labels) detected in the news headlines."""
    all_titles = ' | '.join((n.get('title') or '').lower() for n in (news_items or []))
    bears = [label for label, kws in BEAR_THEMES if any(k.lower() in all_titles for k in kws)]
    bulls = [label for label, kws in BULL_THEMES if any(k.lower() in all_titles for k in kws)]
    return bears, bulls


def _valuation_phrase(row):
    """Plain-English price vs. probabilistic DCF fair value, without mixing signs and 'premium'."""
    fv = row.get('fair_value')
    price = row.get('price')
    mos = row.get('fair_value_mos')
    fv_bear = row.get('fair_value_bear')
    fv_bull = row.get('fair_value_bull')
    if fv is None or not price or mos is None:
        return None, None
    if fv <= 0:
        return 'neg', "DCF base fair value is zero once net debt is subtracted from discounted owner cash flow."
    range_str = f" [Probabilistic range: Bear ${fv_bear:.0f} to Bull ${fv_bull:.0f}]" if (fv_bear and fv_bull and fv_bear > 0) else ""
    if mos >= 0:
        return 'pos', f"Trades at +{mos*100:.0f}% upside to Base DCF fair value (${fv:.2f}){range_str}."
    prem = (price / fv - 1) * 100
    return 'neg', (
        f"Price is {prem:.0f}% above Base DCF fair value (${fv:.2f}){range_str}, "
        f"implying {abs(mos)*100:.0f}% downside if it reverts to base fair value."
    )


def _requalify_condition(flag):
    """Maps a hard red flag to the concrete condition that would lift it."""
    f = (flag or '').lower()
    if 'negative owner cash flow' in f or 'free cash flow was negative' in f:
        return 'owner cash flow (FCF minus stock comp) turns positive and stays positive'
    if 'shrinking business' in f:
        return 'revenue returns to growth or operating margin stops falling'
    if 'dilution' in f:
        return 'share count growth falls below 2%/yr'
    if 'heavy debt' in f:
        return 'net debt falls below 4x EBITDA'
    if 'negative ebitda' in f:
        return 'EBITDA turns positive or net debt is eliminated'
    if 'interest coverage' in f:
        return 'operating profit covers interest expense at least 3x'
    if 'altman' in f:
        return 'Altman Z-Score recovers above 1.8'
    if 'headline alert' in f:
        return 'the flagged legal / regulatory headline is resolved in SEC filings'
    return 'the flagged issue is resolved'


def _strengths_summary(row, fcf_y):
    """Lists the gates a stock still passes, so a red flag does not read as a blanket failure."""
    out = []
    altz = row.get('altman_z')
    if altz is not None and altz >= 2.99:
        out.append(f"Altman Z {altz:.2f} (safe)")
    gp_ta = row.get('gross_profitability')
    if gp_ta is not None and gp_ta >= 0.30:
        out.append(f"Novy-Marx Gross Profitability {gp_ta*100:.0f}%")
    cfo_ta = row.get('cash_op_profitability')
    if cfo_ta is not None and cfo_ta >= 0.12:
        out.append(f"Ball Cash Operating Profitability {cfo_ta*100:.0f}%")
    nd = row.get('net_debt_ebitda')
    if nd is not None and nd <= 1.5:
        out.append('net cash' if nd <= 0 else f"net debt only {nd:.1f}x EBITDA")
    sh = row.get('share_cagr')
    if sh is not None and sh <= -0.01:
        out.append(f"buybacks retiring {abs(sh)*100:.1f}% of shares per year")
    if fcf_y >= 4.5:
        out.append(f"{fcf_y:.1f}% Owner FCF yield")
    roic = row.get('roic')
    if roic is not None and roic >= 0.15:
        out.append(f"{roic*100:.1f}% 3Y ROIC")
    return out


def compose_dossier_narrative(row, news_items, short_float, moat_rating, earnings_date, days_to_earnings):
    """
    Pure function (no network): builds the bear case, bull case, verdict, action plan
    and exit triggers from the audited row plus previously fetched research inputs.
    Used both by live research and to regenerate stored dossiers offline.
    """
    sym = row['ticker']
    detected_bears, detected_bulls = _detect_themes(news_items)

    imp = row.get('implied_growth')
    rcagr = row.get('rev_cagr')
    dd = row.get('drawdown')
    fcf_y = (row.get('owner_fcf_yield') or 0) * 100
    mos = (row.get('fair_value_mos') or 0) * 100
    pio = row.get('piotroski')
    val_tone, val_text = _valuation_phrase(row)

    bear_narrative = []
    bull_thesis = []

    # --- Price action & sector momentum context (Moskowitz & Grinblatt 1999) ---
    if dd is not None and dd <= -0.20:
        bear_narrative.append(f"Shares are down {dd*100:.0f}% from their 52-week high.")

    sec = row.get('sector')
    SECTOR_HEADWINDS = {
        'Technology': (-0.238, 50.6),
        'Consumer Cyclical': (-0.220, 42.1),
        'Basic Materials': (-0.207, 36.4),
        'Communication Services': (-0.201, 40.0),
    }
    SECTOR_TAILWINDS = {
        'Energy': (-0.080, 5.3),
        'Financial Services': (-0.105, 4.9),
        'Healthcare': (-0.106, 18.3),
    }
    if sec in SECTOR_HEADWINDS:
        dd_val, corr_pct = SECTOR_HEADWINDS[sec]
        bear_narrative.append(
            f"Sector Macro Headwind ({sec}): The {sec} sector is experiencing broad institutional selling pressure "
            f"(average constituent down {dd_val*100:.1f}% from peak; {corr_pct:.0f}% in a correction). "
            f"Industry momentum research (Moskowitz & Grinblatt 1999) shows sector headwinds can drag down even high-quality compounders."
        )
    elif sec in SECTOR_TAILWINDS:
        dd_val, corr_pct = SECTOR_TAILWINDS[sec]
        bull_thesis.append(
            f"Sector Macro Tailwind ({sec}): Institutional capital is actively rotating into {sec} with strong relative resilience "
            f"(average pullback only {dd_val*100:.1f}%; low correction breadth)."
        )

    # --- Valuation: only a bull point when the cash yield is genuinely high ---
    if fcf_y <= 0:
        bear_narrative.append(
            f"Generates a {fcf_y:.1f}% negative Owner FCF yield (after subtracting stock-based compensation)."
        )
    elif fcf_y >= 4.5:
        bull_thesis.append(
            f"Generates a {fcf_y:.1f}% true Owner FCF yield after stock-based compensation "
            f"(you pay about {100/fcf_y:.0f}x owner cash flow)."
        )
    elif fcf_y < 2.5:
        bear_narrative.append(
            f"Thin {fcf_y:.1f}% Owner FCF yield after stock-based compensation: the price is about "
            f"{100/fcf_y:.0f}x owner cash flow, leaving little valuation cushion."
        )
    if val_tone == 'pos' and mos > 5:
        bull_thesis.append(val_text)
    elif val_tone == 'neg' and (mos <= -10 or (row.get('fair_value') or 0) <= 0):
        bear_narrative.append(val_text)

    eps_chg = row.get('eps_expected_change')
    if eps_chg is not None and eps_chg < -0.15:
        bear_narrative.append(
            f"Forward EPS estimate is {abs(eps_chg)*100:.0f}% below trailing EPS (cyclical peak, or one-off gains inflating trailing EPS)."
        )

    # --- Quality & balance sheet ---
    roic = row.get('roic')
    if roic is not None and roic >= 0.15:
        bull_thesis.append(f"3Y average ROIC of {roic*100:.1f}% is well above the ~9% cost of capital.")
    if pio is not None and pio >= 7:
        bull_thesis.append(f"Piotroski F-Score of {pio:.0f}/9: profitability, leverage and efficiency are improving.")
    elif pio is not None and pio <= 3:
        bear_narrative.append(f"Piotroski F-Score of only {pio:.0f}/9: fundamentals are deteriorating.")
    altz = row.get('altman_z')
    nd = row.get('net_debt_ebitda')
    if altz is not None and altz >= 2.99 and (nd is None or nd <= 1.5):
        lev = 'net cash' if (nd is not None and nd <= 0) else (f"net debt {nd:.1f}x EBITDA" if nd is not None else 'low leverage')
        bull_thesis.append(f"Fortress balance sheet: Altman Z-Score {altz:.2f} with {lev}.")

    # --- Shareholder alignment ---
    sh = row.get('share_cagr') or 0
    if sh <= -0.015:
        bull_thesis.append(f"Management is aggressively retiring {abs(sh*100):.1f}% of diluted shares per year via buybacks.")
    elif sh >= 0.02:
        bear_narrative.append(f"Shareholders face +{sh*100:.1f}%/yr share count dilution.")
    sig = row.get('insider_signal')
    if sig in ('CLUSTER BUY', 'CEO/CFO BUY', 'INSIDER BUY'):
        bull_thesis.append(f"Confirmed OpenInsider conviction: {row.get('insider_summary')}.")
    elif sig == 'LONE BUY / HEAVY SELLS':
        bear_narrative.append(f"Caution: {row.get('insider_summary')} (insiders are net sellers despite 1 lone purchase).")
    elif sig in ('C-SUITE DUMPING', 'HEAVY SELLING'):
        bear_narrative.append(f"Executive selling alert: {row.get('insider_summary')}.")

    # --- News & sentiment ---
    if detected_bears:
        bear_narrative.append(f"Recent news headlines focus on: {', '.join(detected_bears)}.")
    if short_float:
        bear_narrative.append(f"Short interest stands at {short_float} of float.")
    if detected_bulls:
        bull_thesis.append(f"Positive news catalysts active: {', '.join(detected_bulls)}.")
    if not bull_thesis:
        bull_thesis.append("No quantitative valuation or cash-flow counter-thesis currently active; requires fundamental turnaround.")

    # --- Verdict & action plan ---
    wt = row.get('position_weight_pct') or 6.7
    score = row.get('composite_score') or 0
    fv = row.get('fair_value') or 0
    flags = row.get('red_flags') or []

    if not row.get('data_ok'):
        verdict = "UNRATED — INCOMPLETE OR NON-USD 10-K STATEMENTS"
        verdict_color = "b-slate"
        action_plan = (
            f"Multi-year 10-K financial statements for {sym} are incomplete or reported in a non-USD currency. "
            f"Inspect official SEC EDGAR filings manually before sizing any position."
        )
    elif flags:
        verdict = "DISQUALIFIED / AVOID — HARD RED FLAG"
        verdict_color = "b-red"
        conds = []
        for fl in flags:
            c = _requalify_condition(fl)
            if c not in conds:
                conds.append(c)
        strengths = _strengths_summary(row, fcf_y)
        action_plan = (
            f"Fails {len(flags)} mandatory gate{'s' if len(flags) > 1 else ''}: {' '.join(flags)} "
            f"Red-flagged stocks are capped at 39/100 (current score {score:.1f}). "
            f"Re-qualifies when {'; and '.join(conds)}."
        )
        if strengths:
            action_plan += f" Still passing: {', '.join(strengths)}."
    elif sig in ('C-SUITE DUMPING', 'HEAVY SELLING'):
        verdict = f"HOLD / WATCHLIST — {sig} DETECTED"
        verdict_color = "b-amber"
        action_plan = (
            f"Passes every 10-K balance sheet gate (Score: {score:.1f}/100, Owner FCF yield: {fcf_y:.1f}%), "
            f"but OpenInsider records show aggressive executive selling ({row.get('insider_summary')}). "
            f"Wait for insider liquidation to subside or demand a wider DCF margin of safety before entering."
        )
    elif score < 60.0:
        verdict = f"WATCHLIST / HOLD — SCORE {score:.1f}/100 (BELOW 60.0 BUY THRESHOLD)"
        verdict_color = "b-slate"
        val_bit = f" {val_text}" if val_text else ''
        action_plan = (
            f"Financially solvent with zero hard red flags, but the {fcf_y:.1f}% Owner FCF yield and current price "
            f"do not offer enough discount for basket inclusion.{val_bit}"
            + (f" Monitor for a pullback toward fair value (${fv:.2f})." if fv > 0 else '')
        )
    elif days_to_earnings is not None and 0 <= days_to_earnings <= 7:
        verdict = f"WAIT FOR EARNINGS ({earnings_date} — IN {days_to_earnings} DAYS)"
        verdict_color = "b-amber"
        action_plan = (
            f"Binary Event Alert: {sym} reports earnings on {earnings_date} ({days_to_earnings} days away). "
            f"Do NOT initiate before the print. Wait for the 8-K/10-Q release, confirm Owner FCF and margins hold, then enter."
        )
    elif sig == 'LONE BUY / HEAVY SELLS':
        verdict = "CAUTIOUS ACCUMULATE (TRANCHE 1 ONLY — WATCH INSIDER SELLS)"
        verdict_color = "b-blue"
        action_plan = (
            f"Fundamentals and cash yield ({fcf_y:.1f}%) are strong, but executives were net sellers after a lone buy. "
            f"Start with a half-sized Tranche 1 ({wt/2:.1f}% portfolio weight) and require margin stability before adding."
        )
    elif (dd or 0) <= -0.35:
        verdict = "PHASED BUY IN 2 TRANCHES (DEEP VALUE + DOWNTREND)"
        verdict_color = "b-green"
        action_plan = (
            f"Deep value setup (+{mos:.0f}% DCF upside, {fcf_y:.1f}% Owner FCF yield) in a stock down {dd*100:.0f}%. "
            f"Buy Tranche 1 ({wt/2:.1f}% weight) now; add Tranche 2 ({wt/2:.1f}% weight) once price closes above its 50-day average."
        )
    else:
        verdict = f"HIGH-CONVICTION BUY (TARGET WEIGHT: {wt:.1f}%)"
        verdict_color = "b-gold"
        action_plan = (
            f"Clean multi-year audit, strong moat ({(moat_rating or '').split('(')[0].strip()}), and {fcf_y:.1f}% Owner FCF yield. "
            f"Next earnings date: {earnings_date or 'TBD'}. Initiate Tranche 1 ({wt/2:.1f}%) now and Tranche 2 on normal pullbacks."
        )

    return {
        'verdict': verdict,
        'verdict_color': verdict_color,
        'bear_narrative': ' '.join(bear_narrative),
        'bull_thesis': bull_thesis,
        'action_plan': action_plan,
        'invalidation_triggers': [],
    }


def synthesize_research_dossier(row, cik_map):
    """Builds the complete autonomous research dossier with opinion & sources."""
    sym = row['ticker']
    co = row['company']

    sec_filings = fetch_sec_filings(sym, cik_map)
    news_items = fetch_google_news_rss(sym, co, max_items=8)
    finviz = fetch_finviz_data(sym)
    profile = fetch_earnings_date_and_profile(sym)

    moat_rating, moat_desc = evaluate_moat(row, profile)
    e_date = profile.get('earnings_date')
    days_e = profile.get('days_to_earnings')

    narrative = compose_dossier_narrative(
        row, news_items, finviz.get('short_float'), moat_rating, e_date, days_e
    )

    biz_summary = profile['summary']
    if len(biz_summary) > 420:
        biz_summary = biz_summary[:417].rsplit(' ', 1)[0] + '...'

    dossier = {
        'industry': profile.get('industry') or row.get('sector'),
        'business_summary': biz_summary,
        'moat_rating': moat_rating,
        'moat_desc': moat_desc,
        'earnings_date': e_date,
        'days_to_earnings': days_e,
        'short_float': finviz.get('short_float'),
        'inst_own': finviz.get('inst_own'),
        'wall_st_target': finviz.get('target_price'),
        'analyst_actions': finviz.get('analyst_actions', []),
        'sec_filings': sec_filings,
        'news_sources': news_items,
        'external_links': [
            {'label': f'{sym} on TradingView Chart', 'url': f'https://www.tradingview.com/chart/?symbol={sym}'},
            {'label': f'{sym} on OpenInsider.com', 'url': f'http://openinsider.com/screener?s={sym}&fd=365'},
            {'label': f'{sym} SEC EDGAR Filings (10-K / 10-Q)', 'url': f'https://www.sec.gov/edgar/searchedgar/companysearch?cik={sym}'},
            {'label': f'{sym} Yahoo Finance Financials & Transcripts', 'url': f'https://finance.yahoo.com/quote/{sym}/financials/'},
            {'label': f'{sym} Finviz Institutional & Analyst Chart', 'url': f'https://finviz.com/quote.ashx?t={sym}'},
        ],
    }
    dossier.update(narrative)
    return dossier


def refresh_dossier_narrative(row):
    """Regenerates the verdict/thesis text of a stored dossier offline (no network)."""
    doc = row.get('research')
    if not doc:
        return row
    e_date = doc.get('earnings_date')
    days_e = doc.get('days_to_earnings')
    if e_date:
        try:
            days_e = (datetime.strptime(e_date, '%Y-%m-%d').date() - datetime.now().date()).days
            doc['days_to_earnings'] = days_e
        except Exception:
            pass
    doc.update(compose_dossier_narrative(
        row, doc.get('news_sources') or [], doc.get('short_float'), doc.get('moat_rating'), e_date, days_e
    ))
    return row


def enrich_top_stocks_with_research(rows, max_research=18):
    """
    Runs deep qualitative/catalyst/SEC/news research in parallel on the Top Basket
    stocks (plus top Tier A runner-ups, up to `max_research` stocks total).
    """
    candidates = [r for r in rows if r.get('in_basket')]
    if len(candidates) < max_research:
        tier_a = [r for r in rows if r.get('tier') == 'A' and not r.get('in_basket')]
        candidates.extend(tier_a[: max_research - len(candidates)])

    if not candidates:
        return

    print(f"\n[*] Running Deep Research Agent (SEC 10-K/10-Q + News + Earnings Calendar + Moat Verdict) on top {len(candidates)} stocks...")
    cik_map = _load_sec_cik_map()

    with ThreadPoolExecutor(max_workers=6) as pool:
        fut_map = {pool.submit(synthesize_research_dossier, r, cik_map): r for r in candidates}
        for fut in as_completed(fut_map):
            r = fut_map[fut]
            try:
                dossier = fut.result()
                r['research'] = dossier
                print(f"    [Research OK] {r['ticker']:5} -> {dossier['verdict']} | Moat: {dossier['moat_rating']} | Sources: {len(dossier['news_sources'])} articles, {len(dossier['sec_filings'])} SEC filings", flush=True)
            except Exception:
                r['research'] = None


def enrich_single_stock_with_research(row):
    """
    Runs deep qualitative, SEC EDGAR, Finviz, and News research on a single stock row
    (regardless of tier) for on-demand single-ticker analysis.
    """
    if not row:
        return None
    try:
        cik_map = _load_sec_cik_map()
        row['research'] = synthesize_research_dossier(row, cik_map)
    except Exception:
        row['research'] = None
    return row
