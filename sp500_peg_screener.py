"""
sp500_peg_screener.py - Institutional Multi-Year Forensic, Reverse-DCF &
OpenInsider Stock Analysis Engine for the S&P 500.

Architecture:
  1. Strict Data Validation (no missing-data passes; fixes dividend-yield bugs)
  2. 4-Year Statement Trends (Owner FCF after Stock-Based Compensation, ROIC,
     Operating Margin direction, Share Count CAGR)
  3. Academic Forensic Models (Piotroski F-Score, Altman Z-Score, Beneish M-Score)
  4. Reverse DCF Valuation (market-implied 10Y growth vs actual 3Y CAGR)
  5. OpenInsider 6-Month Open-Market Purchase & Cluster-Buy Scanner
  6. Diversified Basket Selector (Top 15, Max 3 per Sector) + SPY Track Record
"""
import json
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


def ensure_package(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        return __import__(import_name)
    except ImportError:
        return None


ensure_package("yfinance")
ensure_package("pandas")
ensure_package("lxml")
ensure_package("requests")

import logging
try:
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
except Exception:
    pass

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import pandas as pd
except ImportError:
    pd = None

from fundamentals import analyze_fundamentals
from openinsider import fetch_ticker_insider, empty_insider_record
from portfolio_tracker import record_and_evaluate
from dashboard_builder import build_html_dashboard
from research_agent import enrich_top_stocks_with_research, enrich_single_stock_with_research

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "sp500_tierlist.csv")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, "sp500_tierlist_dashboard.html")

def get_yf_session():
    """
    Returns a session with Chrome browser TLS impersonation (via curl_cffi) or
    realistic User-Agent headers to avoid cloud IP blocking on Yahoo Finance.
    """
    try:
        from curl_cffi import requests as c_requests
        return c_requests.Session(impersonate="chrome")
    except Exception:
        import requests
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        return s

BASKET_MAX_STOCKS = 15
BASKET_MAX_PER_SECTOR = 3

FULL_SP500 = [
    "A","AAL","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM","ADP",
    "ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALL",
    "ALLE","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS",
    "AON","AOS","APA","APD","APH","APTV","ARE","ATO","AVB","AVGO","AVY",
    "AWK","AXP","AZO","BA","BAC","BAX","BBWI","BBY","BDX","BEN","BF-B","BG",
    "BIIB","BIO","BK","BKNG","BKR","BLDR","BLK","BMY","BR","BRK-B","BRO","BSX",
    "BWA","BX","BXP","C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI",
    "CCL","CDNS","CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI",
    "CINF","CL","CLX","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF","COO",
    "COP","COR","COST","CPAY","CPB","CPRT","CPT","CRL","CRM","CRWD","CSCO",
    "CSGP","CSX","CTAS","CTRA","CTSH","CTVA","CVS","CVX","CZR","D",
    "DAL","DAY","DD","DE","DECK","DFS","DG","DGX","DHI","DHR","DIS",
    "DLR","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN","DXCM",
    "EA","EBAY","ECL","ED","EFX","EL","EMN","EMR","ENPH","EOG","EPAM","EQIX",
    "EQR","EQT","ES","ESS","ETN","ETR","ETSY","EVRG","EW","EXC","EXPD",
    "EXPE","EXR","F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FI",
    "FICO","FIS","FITB","FMC","FOX","FOXA","FRT","FSLR","FTNT",
    "FTV","GD","GDDY","GE","GEHC","GEN","GILD","GIS","GL","GLW","GM","GNRC",
    "GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW","HAL","HAS","HBAN","HCA",
    "HD","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUBB","HUM","HWM",
    "IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC","INTU","INVH","IP",
    "IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JCI",
    "JKHY","JNJ","JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KLAC",
    "KMB","KMI","KMX","KO","KR","KVUE","L","LDOS","LEN","LH","LHX","LIN",
    "LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB",
    "LYV","MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET",
    "META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH","MOS",
    "MPC","MPWR","MRK","MRNA","MS","MSCI","MSFT","MSI","MTB","MTCH","MTD",
    "MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW",
    "NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA","NXPI","O",
    "ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PANW","PARA","PAYC",
    "PAYX","PCAR","PCG","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PKG",
    "PLD","PM","PNC","PNR","PNW","POOL","PPG","PPL","PRU","PSA","PSX","PTC",
    "PVH","PWR","PYPL","QCOM","QRVO","RCL","REG","REGN","RF","RHI",
    "RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC",
    "SBUX","SCHW","SEE","SHW","SJM","SLB","SMCI","SNA","SNPS",
    "SO","SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SWK","SWKS",
    "SYF","SYK","SYY","T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TFX",
    "TGT","TJX","TMO","TMUS","TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA",
    "TSN","TT","TTWO","TXN","TXT","TYL","UAL","UBER","UDR","UHS","ULTA",
    "UNH","UNP","UPS","URI","USB","V","VFC","VICI","VLO","VLTO","VMC","VRSK",
    "VRSN","VRTX","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WDC","WEC",
    "WELL","WFC","WHR","WM","WMB","WMT","WRB","WST","WTW","WY","WYNN",
    "XEL","XOM","XRAY","XYL","YUM","ZBH","ZBRA","ZION","ZTS"
]

LETHAL_NEWS_KEYWORDS = [
    'sec probe', 'sec investigation', 'subpoena', 'accounting fraud',
    'restate earnings', 'restatement', 'indictment', 'accounting irregularities',
    'doj investigation', 'short seller report'
]


def get_sp500_tickers():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        tickers = tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if len(tickers) > 400:
            print(f"[OK] Fetched {len(tickers)} tickers from Wikipedia.")
            return tickers
    except Exception:
        pass
    print(f"[OK] Using built-in S&P 500 list ({len(FULL_SP500)} tickers).")
    return FULL_SP500


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _scale(val, lo, hi, max_pts):
    if val is None:
        return max_pts * 0.35
    if val <= lo:
        return 0.0
    if val >= hi:
        return float(max_pts)
    return float(max_pts) * (val - lo) / (hi - lo)


def scan_headline_risks(ticker_obj):
    flags = []
    try:
        news = ticker_obj.news
        if news:
            for item in news[:8]:
                title = item.get('title', '') or ''
                if not title and isinstance(item.get('content'), dict):
                    title = item['content'].get('title', '') or ''
                t_low = title.lower()
                for kw in LETHAL_NEWS_KEYWORDS:
                    if kw in t_low:
                        flags.append(f"Headline Alert ({kw}): {title[:65]}")
                        break
    except Exception:
        pass
    return flags


def build_due_diligence(symbol, m, insider):
    """Generate tailored human due-diligence questions from the company's numbers."""
    questions = []
    imp = m.get('implied_growth')
    rcagr = m.get('rev_cagr')
    if imp is not None and rcagr is not None:
        if imp < 0:
            questions.append(
                f"Market Pricing Declining Cash Flows: Current price implies {imp*100:.1f}%/yr FCF contraction "
                f"(vs {rcagr*100:.1f}%/yr historical 3Y revenue growth). Identify what structural threat "
                f"(new competitor, patent cliff, or technology shift) is scaring the market."
            )
        elif imp < rcagr:
            questions.append(
                f"Growth Expectation Gap: Market prices in {imp*100:.1f}%/yr FCF growth vs {rcagr*100:.1f}%/yr "
                f"historical revenue CAGR. Verify whether recent growth was a temporary post-pandemic or cyclical boost."
            )
    opm_chg = m.get('op_margin_change')
    if opm_chg is not None and opm_chg < -0.01:
        questions.append(
            f"Margin Compression Check: Operating margin slipped {opm_chg*100:.1f} percentage points over the "
            f"multi-year window. Check the 10-K to see if pricing power is eroding or if low-margin lines are growing faster."
        )
    sbc_rev = m.get('sbc_to_revenue')
    if sbc_rev is not None and sbc_rev > 0.04:
        questions.append(
            f"Stock Compensation Scrutiny: SBC is {sbc_rev*100:.1f}% of revenue. We already deducted SBC from Owner FCF, "
            f"but verify management isn't issuing excessive options at depressed prices."
        )
    sig = insider.get('signal', 'NEUTRAL')
    if sig in ('CLUSTER BUY', 'CEO/CFO BUY', 'INSIDER BUY'):
        questions.append(
            f"Genuine Net Insider Buying ({sig}): {insider.get('summary')}. "
            f"Buyers outweighed sellers ({insider.get('buy_sell_ratio', 0):.0f}% buy volume) with no wave of selling afterward."
        )
    elif sig in ('LONE BUY / HEAVY SELLS', 'C-SUITE DUMPING', 'HEAVY SELLING'):
        questions.append(
            f"Insider Selling Alert ({sig}): {insider.get('summary')}. "
            f"Do NOT rely on a lone insider purchase when multiple other executives are actively selling shares."
        )
    else:
        questions.append(
            f"No Open-Market Insider Buys in 6 Months ({ insider.get('summary') }): Management may be buying back shares "
            f"with corporate cash, but executives haven't bought shares personally on the open market recently."
        )
    ag = m.get('asset_growth')
    if ag is not None and ag > 0.20:
        questions.append(
            f"Capital Discipline Check (Hou-Xue-Zhang Factor): Total assets grew {ag*100:.1f}% last year. "
            f"Verify whether this expansion was driven by a debt-funded acquisition or CapEx spike, and ensure ROIC is not diluting."
        )
    gp_ta = m.get('gross_profitability')
    if gp_ta is not None and gp_ta < 0.15:
        questions.append(
            f"Asset Productivity Check (Novy-Marx Factor): Gross Profit / Total Assets is {gp_ta*100:.1f}% (below 15% threshold). "
            f"Assess whether this asset-heavy structure exposes the company to fixed-cost margin compression in a downturn."
        )
    questions.append(
        f"Customer & Moat Test for {symbol}: Before allocating 5%–7% of your basket here, ask: if {symbol} raised "
        f"prices by 5% tomorrow, would customers stay or switch to a competitor?"
    )
    return questions


def compute_scores(m, red_flags, warnings, insider):
    # 1. Real Cash Generation & Economic Yield Pillar (0 - 30 pts) - Buffett / Munger Owner Earnings
    # Owner FCF Yield: cash return on capital today (0 - 16 pts, benchmark 2.0% - 8.5%)
    val_fcf = _scale(m.get('owner_fcf_yield'), 0.020, 0.085, 16.0)
    # Cash Conversion: CFO / Net Income (0 - 8 pts, benchmark 60% - 120%)
    val_conv = _scale(m.get('cash_conversion'), 0.60, 1.20, 8.0)
    # Expectations Gap: rev_cagr - implied_growth (0 - 6 pts)
    val_gap = _scale(m.get('growth_gap'), -0.04, 0.08, 6.0)
    # Forward earnings decline penalty
    eps_chg = m.get('eps_expected_change')
    val_eps_pen = 0.0
    if eps_chg is not None and eps_chg < -0.15:
        val_eps_pen = 2.0 + _scale(-eps_chg, 0.15, 0.45, 4.0)
    val_score = _clamp(val_fcf + val_conv + val_gap - val_eps_pen, 0.0, 30.0)

    # 2. Economic Profitability & Compounding Power Pillar (0 - 30 pts) - Novy-Marx (2013) / Ball et al. (2016)
    # Economic ROIC (0 - 12 pts, benchmark 8% - 25%)
    q_roic = _scale(m.get('roic'), 0.08, 0.25, 12.0)
    # Novy-Marx Gross Profitability: GP / Total Assets (0 - 10 pts, benchmark 0.15 - 0.45)
    gp_ta = m.get('gross_profitability')
    q_gp = _scale(gp_ta, 0.15, 0.45, 10.0)
    # Ball et al. Cash Operating Profitability: CFO / Total Assets (0 - 8 pts, benchmark 0.05 - 0.20)
    cfo_ta = m.get('cash_op_profitability')
    q_cfo = _scale(cfo_ta, 0.05, 0.20, 8.0)
    qual_score = _clamp(q_roic + q_gp + q_cfo, 0.0, 30.0)

    # 3. Balance Sheet Fortress & Forensics Pillar (0 - 20 pts) - Asness QMJ / Altman / Beneish
    nd_ebitda = m.get('net_debt_ebitda')
    if nd_ebitda is None:
        s_debt = 4.0
    elif nd_ebitda <= 0:
        s_debt = 8.0
    else:
        s_debt = 8.0 - _scale(nd_ebitda, 0.0, 3.5, 8.0)
    s_altz = 3.5 if m.get('altman_z') is None else _scale(m.get('altman_z'), 1.8, 4.0, 6.0)
    s_forensic = 6.0
    if m.get('beneish_m') is not None and m['beneish_m'] > -1.78:
        s_forensic -= 3.5
    s_forensic -= min(len(warnings) * 1.2, 4.5)
    safe_score = _clamp(s_debt + s_altz + max(0.0, s_forensic), 0.0, 20.0)

    # 4. Capital Discipline & Shareholder Alignment Pillar (0 - 20 pts) - Hou, Xue, Zhang (2015)
    # Share retirement / buyback discipline vs dilution (0 - 7 pts)
    sh_cagr = m.get('share_cagr')
    if sh_cagr is None:
        g_shr = 3.0
    elif sh_cagr <= -0.025:
        g_shr = 7.0
    elif sh_cagr <= 0.0:
        g_shr = 5.0
    else:
        g_shr = max(0.0, 3.0 - _scale(sh_cagr, 0.0, 0.02, 3.0))

    # Hou, Xue, Zhang (2015 RFS) Capital Discipline / Asset Growth (0 - 7 pts)
    ag = m.get('asset_growth')
    if ag is None:
        g_ag = 4.0
    elif ag <= 0.08:
        g_ag = 7.0  # conservative capital allocation
    elif ag <= 0.18:
        g_ag = 5.0  # healthy organic expansion
    else:
        g_ag = max(0.0, 5.0 - _scale(ag, 0.18, 0.40, 5.0))  # penalize empire building / overinvestment

    # OpenInsider net buying adjustment (0 - 6 pts)
    ins_adj = insider.get('score_adj', 0.0)
    align_score = _clamp(g_shr + g_ag + ins_adj, 0.0, 20.0)

    total = val_score + qual_score + safe_score + align_score
    if red_flags:
        total = min(total, 39.0)
    return round(total, 1), round(val_score, 1), round(qual_score, 1), round(safe_score, 1), round(align_score, 1)


def analyze_single_ticker(symbol, force_full=False):
    try:
        session = get_yf_session()
        t = yf.Ticker(symbol, session=session)

        info = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}

        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')

        # Fallback to fast_info and history if info was rate-limited or blocked by cloud anti-bot
        if not price or info.get('quoteType') == 'NONE':
            try:
                fi = t.fast_info
                px = getattr(fi, 'last_price', None) or getattr(fi, 'previous_close', None)
                if px:
                    price = float(px)
                    info['currentPrice'] = price
                    info['regularMarketPrice'] = price
                    info['previousClose'] = getattr(fi, 'previous_close', price)
                    info['marketCap'] = getattr(fi, 'market_cap', None)
                    info['currency'] = getattr(fi, 'currency', 'USD')
            except Exception:
                pass

        if not price:
            try:
                hist = t.history(period='5d')
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    info['currentPrice'] = price
                    info['regularMarketPrice'] = price
            except Exception:
                pass

        if not price:
            print(f"[!] Warning: No price data available from Yahoo Finance for {symbol}", flush=True)
            return None

        name = info.get('shortName') or info.get('longName') or symbol
        sector = info.get('sector') or 'Financials/Other'

        inc = t.income_stmt
        bal = t.balance_sheet
        cf = t.cashflow

        fund = analyze_fundamentals(info, inc, bal, cf)
        m = fund['metrics']
        red_flags = list(fund['red_flags'])
        warnings = list(fund['warnings'])
        data_notes = list(fund['data_notes'])

        # Lazy Pipeline Evaluation during 500-stock scans: Short-circuit disqualified stocks
        # unless force_full=True (used when the user audits a single ticker on demand).
        if not force_full and (not fund['data_ok'] or len(red_flags) > 0):
            headline_risk = False
            insider = empty_insider_record()
            if not fund['data_ok']:
                val_s = qual_s = safe_s = align_s = comp_s = 0.0
            else:
                comp_s, val_s, qual_s, safe_s, align_s = compute_scores(m, red_flags, warnings, insider)
            dd_questions = build_due_diligence(symbol, m, insider) if fund['data_ok'] else data_notes
        else:
            news_flags = scan_headline_risks(t)
            headline_risk = len(news_flags) > 0
            if headline_risk:
                red_flags.extend(news_flags)

            insider = fetch_ticker_insider(symbol)
            if insider.get('warning'):
                warnings.insert(0, insider['warning'])

            if not fund['data_ok']:
                val_s = qual_s = safe_s = align_s = comp_s = 0.0
                dd_questions = data_notes
            else:
                comp_s, val_s, qual_s, safe_s, align_s = compute_scores(m, red_flags, warnings, insider)
                dd_questions = build_due_diligence(symbol, m, insider)

        fcf_y = m.get('owner_fcf_yield') or 0.0
        conv = m.get('cash_conversion') or 1.0
        rev_g = m.get('rev_cagr') or 0.0
        div_y = m.get('dividend_yield') or 0.0
        pe = (conv / fcf_y) if (fcf_y > 0 and conv > 0) else None
        is_pegy = div_y > 0.002
        peg_type = 'PEGY' if is_pegy else 'PEG'
        tot_g = rev_g + div_y

        peg_val = None
        peg_display = 'N/A'
        peg_rating = 'Negative / Zero Earnings' if not pe else 'Negative Growth'
        peg_cls = 'c-muted' if not pe else 'c-neg'

        if pe and tot_g > 0.005:
            val = pe / (tot_g * 100)
            peg_val = round(val, 2)
            peg_display = f"{val:.2f}"
            if val < 1.0:
                peg_rating = 'Undervalued < 1.0'
                peg_cls = 'c-pos'
            elif val <= 2.0:
                peg_rating = 'Fair Value 1.0–2.0'
                peg_cls = 'c-prime'
            else:
                peg_rating = 'Expensive > 2.0'
                peg_cls = 'c-neg'
        elif pe and tot_g <= 0.005:
            peg_display = 'Contraction'

        return {
            'ticker': symbol,
            'company': name,
            'sector': sector,
            'data_ok': fund['data_ok'],
            'in_basket': False,
            'position_weight_pct': 0.0,
            'tier': 'U',
            'composite_score': comp_s,
            'val_score': val_s,
            'qual_score': qual_s,
            'safe_score': safe_s,
            'align_score': align_s,
            'pe_ratio': round(pe, 1) if pe else None,
            'peg_type': peg_type,
            'peg_value': peg_val,
            'peg_display': peg_display,
            'peg_rating': peg_rating,
            'peg_cls': peg_cls,
            'price': m.get('price'),
            'market_cap': m.get('market_cap'),
            'fair_value': m.get('fair_value'),
            'fair_value_mos': m.get('fair_value_mos'),
            'owner_fcf_yield': m.get('owner_fcf_yield'),
            'ebit_ev': m.get('ebit_ev'),
            'implied_growth': m.get('implied_growth'),
            'rev_cagr': m.get('rev_cagr'),
            'growth_gap': m.get('growth_gap'),
            'roic': m.get('roic'),
            'gross_margin': m.get('gross_margin'),
            'op_margin': m.get('op_margin'),
            'op_margin_change': m.get('op_margin_change'),
            'piotroski': m.get('piotroski'),
            'cash_conversion': m.get('cash_conversion'),
            'gross_profitability': m.get('gross_profitability'),
            'cash_op_profitability': m.get('cash_op_profitability'),
            'asset_growth': m.get('asset_growth'),
            'pleasing_signals': m.get('pleasing_signals', []),
            'throw_offs': m.get('throw_offs', []),
            'pleasing_count': m.get('pleasing_count', 0),
            'throwoff_count': m.get('throwoff_count', 0),
            'owner_fcf_ps_cagr': m.get('owner_fcf_ps_cagr'),
            'share_cagr': m.get('share_cagr'),
            'net_debt_ebitda': m.get('net_debt_ebitda'),
            'interest_coverage': m.get('interest_coverage'),
            'altman_z': m.get('altman_z'),
            'beneish_m': m.get('beneish_m'),
            'dividend_yield': m.get('dividend_yield'),
            'drawdown': m.get('drawdown'),
            'eps_expected_change': m.get('eps_expected_change'),
            'headline_risk': headline_risk,
            'insider_signal': insider['signal'],
            'insider_buyers': insider['unique_buyers'],
            'insider_sellers': insider['unique_sellers'],
            'insider_buy_value': insider['buy_value'],
            'insider_sell_value': insider['sell_value'],
            'insider_buy_ratio': insider['buy_sell_ratio'],
            'insider_score_adj': insider['score_adj'],
            'insider_summary': insider['summary'],
            'insider_details': insider['details'],
            'red_flags': red_flags,
            'warnings': warnings + data_notes,
            'due_diligence': dd_questions,
            'trends': fund['trends'],
        }
    except Exception as exc:
        print(f"[!] Exception analyzing ticker {symbol}: {exc}", flush=True)
        return None


def audit_single_ticker_live(symbol):
    """
    On-demand full forensic, Reverse-DCF, OpenInsider, and SEC EDGAR deep dive
    for any single ticker (inside or outside the S&P 500) in ~3 seconds.
    """
    sym = str(symbol or '').strip().upper().replace('.', '-')
    if not sym:
        return None
    res = analyze_single_ticker(sym, force_full=True)
    if not res:
        return None

    if not res['data_ok']:
        res['tier'] = 'U'
    elif res['red_flags']:
        res['tier'] = 'D'
    elif res['composite_score'] >= 60.0:
        res['tier'] = 'A'
    elif res['composite_score'] >= 48.0:
        res['tier'] = 'B'
    else:
        res['tier'] = 'C'

    enrich_single_stock_with_research(res)
    return res


def assign_tiers_and_basket(rows):
    """
    Selects the diversified Top Basket (max 15 stocks, max 3 per sector) from
    zero-red-flag candidates that meet strict floor criteria AND do not suffer
    from heavy insider / C-suite selling, then assigns tiers.
    """
    for r in rows:
        r['in_basket'] = False
        r['position_weight_pct'] = 0.0

    eligible = [
        r for r in rows
        if r['data_ok']
        and len(r['red_flags']) == 0
        and r.get('insider_signal') not in ('C-SUITE DUMPING', 'HEAVY SELLING')
        and not r.get('needs_full_audit')
        and (r.get('eps_expected_change') is None or r['eps_expected_change'] >= -0.30)
        and (r.get('owner_fcf_yield') or 0) >= 0.04
        and (r.get('roic') or 0) >= 0.09
        and (r.get('piotroski') or 0) >= 5.5
        and r['composite_score'] >= 60.0
    ]
    eligible.sort(key=lambda x: x['composite_score'], reverse=True)

    sector_counts = {}
    basket = []
    for r in eligible:
        sec = r['sector']
        if sector_counts.get(sec, 0) < BASKET_MAX_PER_SECTOR and len(basket) < BASKET_MAX_STOCKS:
            r['in_basket'] = True
            sector_counts[sec] = sector_counts.get(sec, 0) + 1
            basket.append(r)

    wt = round(100.0 / len(basket), 1) if basket else 0.0
    for r in basket:
        r['position_weight_pct'] = wt

    for r in rows:
        if not r['data_ok']:
            r['tier'] = 'U'
        elif r['red_flags']:
            r['tier'] = 'D'
        elif r['in_basket']:
            r['tier'] = 'S'
        elif r['composite_score'] >= 60.0:
            r['tier'] = 'A'
        elif r['composite_score'] >= 48.0:
            r['tier'] = 'B'
        else:
            r['tier'] = 'C'

    return basket


def load_existing_database():
    """Loads existing stocks, cohorts, and watchlists from OUTPUT_HTML."""
    if not os.path.exists(OUTPUT_HTML):
        return [], [], []
    try:
        with open(OUTPUT_HTML, 'r', encoding='utf-8') as f:
            for line in f:
                if 'PAYLOAD = {' in line:
                    raw = line.split('PAYLOAD = ', 1)[1].strip().rstrip(';')
                    data = json.loads(raw)
                    return data.get('stocks', []), data.get('cohorts', []), data.get('watchlists', [])
    except Exception:
        pass
    return [], [], []


def save_database_to_disk(results, cohorts_eval, watchlists=None):
    """Saves the full merged database (including shared watchlists) to CSV and HTML."""
    if watchlists is None:
        _, _, watchlists = load_existing_database()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_rows = []
    for r in results:
        res_doc = r.get('research') or {}
        csv_rows.append({
            'Ticker': r['ticker'],
            'Company': r['company'],
            'Sector': r['sector'],
            'Tier': r['tier'],
            'In Basket': r['in_basket'],
            'Position Weight (%)': r['position_weight_pct'],
            'Research Verdict': res_doc.get('verdict', ''),
            'Moat Rating': res_doc.get('moat_rating', ''),
            'Next Earnings Date': res_doc.get('earnings_date', ''),
            'Composite Score': r['composite_score'],
            'Price ($)': round(r['price'], 2) if r['price'] else None,
            'DCF Fair Value ($)': round(r['fair_value'], 2) if r['fair_value'] else None,
            'DCF Upside (%)': round(r['fair_value_mos'] * 100, 1) if r['fair_value_mos'] is not None else None,
            'Owner FCF Yield (%)': round(r['owner_fcf_yield'] * 100, 2) if r['owner_fcf_yield'] is not None else None,
            'Implied 10Y Growth (%)': round(r['implied_growth'] * 100, 1) if r['implied_growth'] is not None else None,
            '3Y Rev CAGR (%)': round(r['rev_cagr'] * 100, 1) if r['rev_cagr'] is not None else None,
            '3Y Avg ROIC (%)': round(r['roic'] * 100, 1) if r['roic'] is not None else None,
            'Piotroski F-Score': r['piotroski'],
            'Altman Z-Score': round(r['altman_z'], 2) if r['altman_z'] is not None else None,
            'Beneish M-Score': round(r['beneish_m'], 2) if r['beneish_m'] is not None else None,
            '3Y Share Count CAGR (%)': round(r['share_cagr'] * 100, 2) if r['share_cagr'] is not None else None,
            'Net Debt / EBITDA': round(r['net_debt_ebitda'], 2) if r['net_debt_ebitda'] is not None else None,
            'Dividend Yield (%)': round((r['dividend_yield'] or 0) * 100, 2),
            'OpenInsider Signal': r['insider_signal'],
            'Insider Buyers (6m)': r['insider_buyers'],
            'Insider Buy Value ($)': round(r['insider_buy_value'], 0),
            'Red Flags': ' | '.join(r['red_flags']),
            'Warnings': ' | '.join(r['warnings']),
        })
    pd.DataFrame(csv_rows).to_csv(OUTPUT_CSV, index=False)
    html = build_html_dashboard(results, cohorts_eval, watchlists)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)


def run_screener(max_stocks=None, progress_callback=None, mode='full_universe', custom_tickers=None):
    existing_stocks, existing_cohorts, existing_watchlists = load_existing_database()
    existing_map = {s['ticker'].upper(): s for s in existing_stocks if s.get('ticker')}

    is_watchlist_scan = (mode == 'watchlist' and custom_tickers)
    if is_watchlist_scan:
        tickers = [str(t).strip().upper().replace('.', '-') for t in custom_tickers if str(t).strip()]
    elif mode == 'current_db' and existing_map:
        tickers = sorted(existing_map.keys())
    else:
        sp_tickers = get_sp500_tickers()
        if max_stocks is not None:
            sp_tickers = sp_tickers[:max_stocks]
        sp_set = set(t.upper() for t in sp_tickers)
        extra_tickers = [t for t in existing_map.keys() if t not in sp_set]
        tickers = sp_tickers + sorted(extra_tickers)

    total = len(tickers)

    print("\n" + "=" * 88)
    print(" S&P 500 & CUSTOM DATABASE MULTI-YEAR FORENSIC, REVERSE-DCF & OPENINSIDER ENGINE")
    print(" 1. 4-Yr Annual Statement Audit (Owner FCF ex-Stock Comp, ROIC, Margins, Share Count)")
    print(" 2. Forensic Accounting Guards (Piotroski F-Score, Altman Z-Score, Beneish M-Score)")
    print(" 3. Reverse DCF Valuation (Market-Implied Growth vs 3Y Historical CAGR)")
    print(" 4. OpenInsider.com 6-Month Open-Market Purchase & Cluster-Buy Scanner")
    print(f" 5. Diversified Basket Construction (Top {BASKET_MAX_STOCKS} Stocks, Max {BASKET_MAX_PER_SECTOR} Per Sector)")
    print("=" * 88 + "\n")

    scanned_map = {}
    completed = 0
    clean_count = 0
    flagged_count = 0
    insider_count = 0

    if progress_callback:
        progress_callback({
            'stage': 'scanning',
            'completed': 0,
            'total': total,
            'ticker': 'INIT',
            'status': f'Starting parallel forensic audit across {total} securities...',
            'clean_count': 0,
            'flagged_count': 0,
            'insider_count': 0,
        })

    with ThreadPoolExecutor(max_workers=6) as pool:
        future_map = {pool.submit(analyze_single_ticker, sym, is_watchlist_scan): sym for sym in tickers}
        for fut in as_completed(future_map):
            completed += 1
            sym = future_map[fut]
            res = fut.result()
            if res:
                prev = existing_map.get(sym.upper())
                if prev and prev.get('research') and not res.get('research'):
                    res['research'] = prev['research']
                scanned_map[sym.upper()] = res
                if not res['data_ok']:
                    status = "UNRATED (Incomplete Data)"
                elif res['red_flags']:
                    flagged_count += 1
                    status = f"RED FLAG ({res['red_flags'][0][:42]}...)"
                else:
                    clean_count += 1
                    if res.get('insider_signal') in ('CLUSTER BUY', 'CEO/CFO BUY', 'INSIDER BUY'):
                        insider_count += 1
                    ins_tag = f" | [{res['insider_signal']}]" if res['insider_signal'] != 'NEUTRAL' else ""
                    fcf_y = (res['owner_fcf_yield'] or 0) * 100
                    roic_v = (res['roic'] or 0) * 100
                    status = f"Score: {res['composite_score']:5.1f} | Owner FCF Yld: {fcf_y:5.1f}% | ROIC: {roic_v:5.1f}%{ins_tag}"
                print(f"[{completed:3d}/{total}] {sym:5} -> {status}", flush=True)
            else:
                status = "[skip: no response]"
                print(f"[{completed:3d}/{total}] {sym:5} -> {status}", flush=True)

            if progress_callback:
                progress_callback({
                    'stage': 'scanning',
                    'completed': completed,
                    'total': total,
                    'ticker': sym,
                    'status': status,
                    'clean_count': clean_count,
                    'flagged_count': flagged_count,
                    'insider_count': insider_count,
                })

    # Merge with any previously saved database stocks so the database never loses entries
    merged_map = dict(existing_map)
    merged_map.update(scanned_map)
    results = list(merged_map.values())

    basket = assign_tiers_and_basket(results)
    results.sort(key=lambda x: (x['in_basket'], x['composite_score']), reverse=True)

    if progress_callback:
        progress_callback({
            'stage': 'researching',
            'completed': total,
            'total': total,
            'ticker': 'SEC EDGAR',
            'status': 'Running Autonomous Research Agent (10-K/10-Q filings, news & moats)...',
            'clean_count': clean_count,
            'flagged_count': flagged_count,
            'insider_count': insider_count,
        })

    if is_watchlist_scan:
        # For a Watchlist scan, run Deep Research Dossier on EVERY stock in the watchlist!
        for sym_u, row_obj in scanned_map.items():
            enrich_single_stock_with_research(row_obj)
        cohorts_eval = existing_cohorts
    else:
        enrich_top_stocks_with_research(results, max_research=18)
        live_px = {r['ticker']: r['price'] for r in results if r.get('price')}
        cohorts_eval = record_and_evaluate(basket, current_prices=live_px)

    # Save CSV & HTML
    save_database_to_disk(results, cohorts_eval, existing_watchlists)
    print(f"\n[CSV] Saved {len(results)} database stocks to: {OUTPUT_CSV}")
    print(f"[HTML] Interactive workstation saved to: {OUTPUT_HTML}")

    return {'stocks': results, 'cohorts': cohorts_eval, 'watchlists': existing_watchlists}


if __name__ == '__main__':
    run_screener(max_stocks=None)
