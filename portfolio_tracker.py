"""
portfolio_tracker.py - Forward performance log & benchmark comparison vs SPY.

Because free financial APIs do not provide point-in-time historical fundamental
statements without survivorship bias, the only intellectually honest way to
verify a stock-picking engine is a forward out-of-sample audit trail:
  1. Every scan records the date, the SPY price, and the entry price of each
     selected basket stock in `picks_history.json`.
  2. On every subsequent run (or when launched directly), this module fetches
     current prices and computes each cohort's equal-weight return vs SPY.
"""
import os
import json
from datetime import datetime
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, 'picks_history.json')


def _get_spy_price():
    try:
        spy = yf.Ticker('SPY')
        info = spy.info or {}
        p = info.get('currentPrice') or info.get('regularMarketPrice')
        if p:
            return float(p)
        hist = spy.history(period='5d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return None


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {'cohorts': []}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'cohorts' in data:
                return data
    except Exception:
        pass
    return {'cohorts': []}


def record_and_evaluate(basket_rows, current_prices=None):
    """
    1. Logs today's basket snapshot (replacing today's entry if run twice on
       the same calendar day).
    2. Evaluates all stored cohorts against current live prices and SPY.
    Returns a summary list ready to embed in the HTML dashboard.
    """
    current_prices = current_prices or {}
    today_str = datetime.now().strftime('%Y-%m-%d')
    spy_now = _get_spy_price()

    history = load_history()
    cohorts = history.get('cohorts', [])

    if basket_rows:
        picks_payload = []
        for r in basket_rows:
            sym = r.get('ticker')
            px = r.get('price')
            if sym and px and px > 0:
                picks_payload.append({
                    'ticker': sym,
                    'company': r.get('company', sym),
                    'sector': r.get('sector', ''),
                    'entry_price': round(float(px), 2),
                    'composite_score': round(float(r.get('composite_score', 0)), 1),
                    'fair_value': round(float(r['fair_value']), 2) if r.get('fair_value') else None,
                })
        if picks_payload:
            cohorts = [c for c in cohorts if c.get('date') != today_str]
            cohorts.append({
                'date': today_str,
                'spy_entry': round(spy_now, 2) if spy_now else None,
                'picks': picks_payload,
            })
            history['cohorts'] = cohorts
            try:
                with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2)
            except Exception:
                pass

    evaluated = []
    for c in reversed(cohorts):
        c_date = c.get('date', '')
        spy_entry = c.get('spy_entry')
        spy_ret = ((spy_now / spy_entry - 1) * 100) if (spy_now and spy_entry and spy_entry > 0) else 0.0

        pick_results = []
        returns = []
        beat_spy_count = 0

        for p in c.get('picks', []):
            sym = p['ticker']
            entry = p.get('entry_price')
            now_px = current_prices.get(sym)
            if now_px is None:
                try:
                    t = yf.Ticker(sym)
                    inf = t.info or {}
                    now_px = inf.get('currentPrice') or inf.get('regularMarketPrice')
                except Exception:
                    now_px = entry
            now_px = float(now_px) if now_px else entry
            ret = ((now_px / entry - 1) * 100) if (entry and entry > 0 and now_px) else 0.0
            returns.append(ret)
            if ret >= spy_ret:
                beat_spy_count += 1
            pick_results.append({
                'ticker': sym,
                'company': p.get('company', sym),
                'entry_price': entry,
                'current_price': round(now_px, 2) if now_px else entry,
                'return_pct': round(ret, 2),
                'alpha_pct': round(ret - spy_ret, 2),
            })

        basket_ret = sum(returns) / len(returns) if returns else 0.0
        evaluated.append({
            'date': c_date,
            'count': len(pick_results),
            'spy_entry': spy_entry,
            'spy_current': round(spy_now, 2) if spy_now else None,
            'spy_return_pct': round(spy_ret, 2),
            'basket_return_pct': round(basket_ret, 2),
            'alpha_pct': round(basket_ret - spy_ret, 2),
            'win_rate_vs_spy': round(beat_spy_count / len(pick_results) * 100, 1) if pick_results else 0.0,
            'picks': pick_results,
        })

    return evaluated


if __name__ == '__main__':
    print("=" * 75)
    print(" S&P 500 QUANT BASKET — FORWARD PERFORMANCE TRACKER vs SPY")
    print("=" * 75)
    ev = record_and_evaluate(basket_rows=None)
    if not ev:
        print("No historical cohorts logged yet. Run sp500_peg_screener.py first!")
    else:
        for cohort in ev:
            print(f"\nCohort Date: {cohort['date']} ({cohort['count']} stocks)")
            print(f"  Basket Return: {cohort['basket_return_pct']:+.2f}% | "
                  f"SPY Return: {cohort['spy_return_pct']:+.2f}% | "
                  f"Alpha: {cohort['alpha_pct']:+.2f}% | "
                  f"Beat SPY: {cohort['win_rate_vs_spy']:.0f}%")
            print("-" * 65)
            for p in cohort['picks']:
                print(f"  {p['ticker']:6} Entry: ${p['entry_price']:<8.2f} "
                      f"Now: ${p['current_price']:<8.2f} "
                      f"Ret: {p['return_pct']:+6.2f}% (vs SPY: {p['alpha_pct']:+6.2f}%)")
