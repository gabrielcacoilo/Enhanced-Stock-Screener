"""
dashboard_builder.py - Builds the modern institutional HTML application from the
multi-year fundamental + OpenInsider + Reverse DCF + Track Record payload.

Uses a raw template string with .replace("__PAYLOAD_JSON__", payload_json) so
Python f-string brace collisions can never occur.
"""
import json

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>S&P 500 Quantitative Valuation & Forensic Terminal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-canvas: #06080d;
      --bg-panel: rgba(15, 19, 28, 0.85);
      --bg-panel-solid: #0f131c;
      --bg-card: linear-gradient(180deg, rgba(22, 27, 38, 0.88) 0%, rgba(14, 17, 25, 0.96) 100%);
      --bg-card-hover: linear-gradient(180deg, rgba(28, 35, 49, 0.94) 0%, rgba(18, 22, 32, 0.98) 100%);
      --bg-subtle: rgba(10, 13, 19, 0.75);
      --bg-elevated: #1c2230;
      --border-dim: rgba(255, 255, 255, 0.07);
      --border-mid: rgba(255, 255, 255, 0.12);
      --border-strong: rgba(255, 255, 255, 0.22);
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --green-text: #34d399;
      --green-bg: rgba(16, 185, 129, 0.10);
      --green-border: rgba(52, 211, 153, 0.28);
      --amber-text: #fbbf24;
      --amber-bg: rgba(245, 158, 11, 0.10);
      --amber-border: rgba(251, 191, 36, 0.28);
      --red-text: #f87171;
      --red-bg: rgba(239, 68, 68, 0.10);
      --red-border: rgba(248, 113, 113, 0.28);
      --blue-text: #60a5fa;
      --blue-bg: rgba(59, 130, 246, 0.10);
      --blue-border: rgba(96, 165, 250, 0.28);
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, monospace;
      --shadow-card: inset 0 1px 0 0 rgba(255, 255, 255, 0.06), 0 8px 24px -4px rgba(0, 0, 0, 0.5);
      --shadow-hover: inset 0 1px 0 0 rgba(255, 255, 255, 0.12), 0 14px 32px -4px rgba(0, 0, 0, 0.65);
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }

    html {
      overflow-x: hidden;
      width: 100%;
      max-width: 100vw;
    }

    body {
      background-color: var(--bg-canvas);
      background-image:
        radial-gradient(1100px circle at 50% -260px, rgba(56, 189, 248, 0.11), rgba(16, 185, 129, 0.04) 45%, transparent 80%);
      background-attachment: fixed;
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 13px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      padding: 0;
      margin: 0;
      width: 100%;
      max-width: 100vw;
      overflow-x: hidden;
    }

    .num {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
    }

    /* TOP FROSTED GLASS MASTHEAD */
    .masthead {
      background: rgba(9, 12, 18, 0.78);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-dim);
      padding: 14px 32px;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .masthead-inner {
      max-width: 1580px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .brand-group {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .brand-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-mark {
      width: 10px;
      height: 28px;
      border-radius: 3px;
      background: linear-gradient(180deg, #34d399 0%, #3b82f6 100%);
      box-shadow: 0 0 14px rgba(52, 211, 153, 0.35);
      flex-shrink: 0;
    }
    .brand-title {
      font-size: 16px;
      font-weight: 600;
      letter-spacing: -0.025em;
      color: var(--text-primary);
    }
    .brand-sub {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 1px;
      font-family: var(--font-mono);
      letter-spacing: -0.01em;
    }
    .mobile-only-actions {
      display: none !important;
    }
    .mobile-title {
      display: none;
    }

    /* PROMINENT TICKER SEARCH BAR */
    .search-command {
      display: flex;
      align-items: center;
      background: rgba(15, 20, 30, 0.85);
      border: 1px solid var(--border-mid);
      border-radius: 8px;
      padding: 0 12px;
      min-width: 300px;
      flex: 1;
      max-width: 420px;
      box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.35);
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .search-command:focus-within {
      border-color: var(--blue-text);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
    }
    .search-prefix {
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      padding-right: 10px;
      border-right: 1px solid var(--border-dim);
      user-select: none;
    }
    .search-command input {
      background: transparent;
      border: none;
      color: var(--text-primary);
      font-family: var(--font-mono);
      font-size: 12.5px;
      padding: 8px 10px;
      width: 100%;
      outline: none;
    }
    .search-command input::placeholder {
      color: var(--text-muted);
      font-family: var(--font-sans);
    }
    .search-clear {
      background: rgba(255, 255, 255, 0.06);
      border: none;
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      cursor: pointer;
      padding: 3px 7px;
      border-radius: 4px;
      display: none;
    }
    .search-clear:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.12);
    }
    .search-audit-btn {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.20) 0%, rgba(59, 130, 246, 0.22) 100%);
      border: 1px solid rgba(52, 211, 153, 0.45);
      color: #6ee7b7;
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 5px;
      margin-right: 5px;
      white-space: nowrap;
      display: none;
      transition: all 0.14s;
    }
    .search-audit-btn:hover {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(59, 130, 246, 0.35) 100%);
      border-color: #34d399;
      color: #ffffff;
    }
    .search-kbd {
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-dim);
      padding: 2px 6px;
      border-radius: 4px;
      user-select: none;
    }

    /* NAV ACTIONS & TELEMETRY */
    .nav-right {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .telemetry-strip {
      display: flex;
      border: 1px solid var(--border-dim);
      background: rgba(12, 16, 24, 0.7);
      border-radius: 8px;
      overflow: hidden;
    }
    .telemetry-cell {
      padding: 5px 14px;
      border-right: 1px solid var(--border-dim);
      min-width: 88px;
    }
    .telemetry-cell:last-child { border-right: none; }
    .telemetry-cell .lbl {
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      font-weight: 600;
    }
    .telemetry-cell .val {
      font-family: var(--font-mono);
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      font-variant-numeric: tabular-nums;
    }

    .header-btn-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .mobile-only-actions {
      display: none !important;
    }
    .desktop-only-actions {
      display: flex !important;
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-mid);
      color: var(--text-primary);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 500;
      padding: 8px 14px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.09);
      border-color: var(--border-strong);
    }

    .btn-primary {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      border: 1px solid rgba(52, 211, 153, 0.4);
      color: #04130d;
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 2px 12px rgba(16, 185, 129, 0.25);
      transition: all 0.15s ease;
    }
    .btn-primary:hover {
      filter: brightness(1.08);
      box-shadow: 0 4px 18px rgba(16, 185, 129, 0.38);
      transform: translateY(-1px);
    }
    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #04130d;
      display: inline-block;
    }

    /* MAIN CONTAINER */
    .container {
      max-width: 1580px;
      margin: 0 auto;
      padding: 24px 32px 64px;
    }

    /* BENCHMARK TRACKER BAR */
    .benchmark-bar {
      background: var(--bg-panel);
      border: 1px solid var(--border-dim);
      border-radius: 10px;
      padding: 12px 20px;
      margin-bottom: 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      box-shadow: var(--shadow-card);
    }
    .benchmark-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-secondary);
    }
    .cohort-list {
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      font-family: var(--font-mono);
      font-size: 12px;
    }
    .cohort-item {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      color: var(--text-secondary);
    }
    .cohort-item strong {
      color: var(--text-primary);
      font-weight: 600;
    }

    /* SECTOR MOMENTUM & ROTATION HEATMAP BAR */
    .sector-bar-wrap {
      background: var(--bg-panel);
      border: 1px solid var(--border-dim);
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-card);
    }
    .sector-bar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 8px;
    }
    .sector-bar-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-primary);
    }
    .sector-bar-subtitle {
      font-size: 11px;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }
    .sector-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
      gap: 8px;
    }
    .sector-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border-dim);
      border-radius: 6px;
      padding: 8px 10px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .sector-card:hover {
      border-color: var(--text-secondary);
      background: rgba(255, 255, 255, 0.04);
    }
    .sector-card.active {
      border-color: #3b82f6;
      background: rgba(59, 130, 246, 0.12);
    }
    .sector-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .sector-card-name {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sector-card-regime {
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 1px 4px;
      border-radius: 3px;
      font-family: var(--font-mono);
    }
    .regime-leading {
      color: #34d399;
      background: rgba(16, 185, 129, 0.15);
    }
    .regime-headwind {
      color: #f87171;
      background: rgba(239, 68, 68, 0.15);
    }
    .regime-neutral {
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.05);
    }
    .sector-card-metrics {
      display: flex;
      justify-content: space-between;
      font-size: 10.5px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }
    .sector-card-bottom {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 3px;
      padding-top: 4px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    .sector-tv-link {
      font-size: 9.5px;
      font-weight: 600;
      font-family: var(--font-mono);
      color: #60a5fa;
      text-decoration: none;
      padding: 1px 5px;
      border-radius: 3px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.25);
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 2px;
      white-space: nowrap;
    }
    .sector-tv-link:hover {
      background: rgba(59, 130, 246, 0.25);
      border-color: #60a5fa;
      color: #93c5fd;
      text-decoration: none;
    }

    /* SECTION HEADERS */
    .section-block {
      margin-bottom: 36px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .section-title-group {
      display: flex;
      align-items: baseline;
      gap: 14px;
      flex-wrap: wrap;
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--text-primary);
    }
    .section-desc {
      font-size: 12.5px;
      color: var(--text-muted);
    }
    .section-meta {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      color: var(--green-text);
      background: var(--green-bg);
      border: 1px solid var(--green-border);
      padding: 4px 12px;
      border-radius: 999px;
    }

    /* CONTROLS TOOLBAR */
    .toolbar {
      background: var(--bg-panel);
      border: 1px solid var(--border-dim);
      border-radius: 10px;
      padding: 10px 14px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      box-shadow: var(--shadow-card);
    }
    .seg-group {
      display: flex;
      background: rgba(8, 10, 15, 0.75);
      border: 1px solid var(--border-dim);
      border-radius: 8px;
      padding: 3px;
      gap: 2px;
      flex-wrap: wrap;
    }
    .seg-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 500;
      padding: 6px 13px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.14s ease;
    }
    .seg-btn:hover {
      color: var(--text-primary);
    }
    .seg-btn.active {
      background: var(--bg-elevated);
      color: var(--text-primary);
      font-weight: 600;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
    }

    .filter-Right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .ctrl-group {
      display: flex;
      align-items: center;
      gap: 7px;
    }
    .ctrl-group label {
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-weight: 600;
    }
    .toolbar select {
      background: rgba(10, 13, 19, 0.85);
      border: 1px solid var(--border-mid);
      color: var(--text-primary);
      padding: 6px 11px;
      border-radius: 7px;
      font-size: 12px;
      font-family: var(--font-sans);
      outline: none;
      cursor: pointer;
    }
    .toolbar select:focus {
      border-color: var(--border-strong);
    }

    /* SEARCH BANNER STATUS */
    .search-status-bar {
      display: none;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-panel);
      border: 1px solid var(--blue-border);
      padding: 12px 18px;
      margin-bottom: 20px;
      border-radius: 10px;
      font-family: var(--font-mono);
      font-size: 12px;
    }

    /* SHARED WATCHLISTS BAR & PANEL */
    .watchlist-wrap {
      background: var(--bg-panel);
      border: 1px solid var(--border-dim);
      border-radius: 10px;
      padding: 12px 16px;
      margin-bottom: 14px;
      box-shadow: var(--shadow-card);
    }
    .watchlist-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .watchlist-pills {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .watchlist-label {
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-right: 6px;
    }
    .wl-pill {
      background: rgba(10, 13, 19, 0.85);
      border: 1px solid var(--border-mid);
      color: var(--text-secondary);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 500;
      padding: 5px 12px;
      border-radius: 7px;
      cursor: pointer;
      transition: all 0.14s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .wl-pill:hover {
      color: var(--text-primary);
      border-color: var(--border-strong);
      background: rgba(255, 255, 255, 0.05);
    }
    .wl-pill.active {
      background: var(--blue-bg);
      color: var(--text-primary);
      border-color: var(--blue-border);
      font-weight: 600;
    }
    .wl-pill-count {
      font-family: var(--font-mono);
      font-size: 10.5px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.05);
      padding: 1px 6px;
      border-radius: 999px;
    }
    .wl-pill.active .wl-pill-count {
      color: var(--blue-text);
      background: rgba(59, 130, 246, 0.18);
    }
    .wl-new-btn {
      background: rgba(16, 185, 129, 0.08);
      border: 1px dashed var(--green-border);
      color: var(--green-text);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 600;
      padding: 5px 11px;
      border-radius: 7px;
      cursor: pointer;
      transition: all 0.14s ease;
    }
    .wl-new-btn:hover {
      background: rgba(16, 185, 129, 0.15);
      color: #ffffff;
    }
    .wl-active-panel {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--border-dim);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .wl-panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }
    .wl-chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }
    .wl-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(8, 11, 16, 0.85);
      border: 1px solid var(--border-mid);
      padding: 4px 9px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: var(--text-primary);
      cursor: pointer;
      transition: border-color 0.12s;
    }
    .wl-chip:hover {
      border-color: var(--border-strong);
      background: rgba(255, 255, 255, 0.05);
    }
    .wl-chip-del {
      color: var(--text-muted);
      font-size: 12px;
      padding: 0 2px;
      cursor: pointer;
      line-height: 1;
    }
    .wl-chip-del:hover {
      color: var(--red-text);
    }
    .wl-input {
      background: rgba(8, 11, 16, 0.9);
      border: 1px solid var(--border-mid);
      color: var(--text-primary);
      font-family: var(--font-mono);
      font-size: 12px;
      padding: 6px 11px;
      border-radius: 6px;
      outline: none;
    }
    .wl-input:focus {
      border-color: var(--blue-border);
    }

    /* GRIDS */
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 14px;
    }

    /* TIER CONTAINERS */
    .tier-block {
      margin-bottom: 32px;
    }
    .tier-bar {
      background: var(--bg-panel);
      border: 1px solid var(--border-dim);
      border-left-width: 3px;
      padding: 12px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      border-radius: 8px;
    }
    .tier-S .tier-bar { border-left-color: #10b981; }
    .tier-A .tier-bar { border-left-color: #3b82f6; }
    .tier-B .tier-bar { border-left-color: #8b5cf6; }
    .tier-C .tier-bar { border-left-color: #f59e0b; }
    .tier-D .tier-bar { border-left-color: #ef4444; }
    .tier-U .tier-bar { border-left-color: #4b5563; }

    .tier-name {
      font-size: 12.5px;
      font-weight: 600;
      letter-spacing: -0.01em;
      color: var(--text-primary);
    }
    .tier-count {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-muted);
      margin-left: 8px;
      font-weight: 400;
      background: rgba(255, 255, 255, 0.04);
      padding: 2px 7px;
      border-radius: 999px;
    }
    .tier-sub {
      font-size: 12px;
      color: var(--text-muted);
    }

    /* MODERN STOCK CARD */
    .stock-card {
      background: var(--bg-card);
      border: 1px solid var(--border-dim);
      border-radius: 12px;
      padding: 18px;
      cursor: pointer;
      box-shadow: var(--shadow-card);
      transition: transform 0.16s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.16s ease, box-shadow 0.16s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      overflow: hidden;
    }
    .stock-card:hover {
      background: var(--bg-card-hover);
      border-color: var(--border-strong);
      box-shadow: var(--shadow-hover);
      transform: translateY(-2px);
    }
    .stock-card.in-basket {
      border-color: rgba(52, 211, 153, 0.25);
    }
    .stock-card.in-basket::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, #10b981, #3b82f6);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .id-group {
      min-width: 0;
    }
    .ticker-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .ticker {
      font-family: var(--font-mono);
      font-size: 17px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }
    .sector-tag {
      font-size: 11px;
      color: var(--text-muted);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-dim);
      padding: 1px 7px;
      border-radius: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sector-tag.tag-headwind {
      color: #f87171;
      border-color: rgba(239, 68, 68, 0.35);
      background: rgba(239, 68, 68, 0.08);
      font-weight: 600;
    }
    .sector-tag.tag-leading {
      color: #34d399;
      border-color: rgba(16, 185, 129, 0.35);
      background: rgba(16, 185, 129, 0.08);
      font-weight: 600;
    }
    .company-name {
      font-size: 12.5px;
      color: var(--text-secondary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
      margin-top: 2px;
    }

    /* SCORE + MINI PILLAR BAR */
    .score-box {
      text-align: right;
      flex-shrink: 0;
      min-width: 68px;
    }
    .score-num {
      font-family: var(--font-mono);
      font-size: 17px;
      font-weight: 700;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }
    .pillar-mini-bar {
      display: flex;
      height: 3px;
      width: 64px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 2px;
      overflow: hidden;
      margin-top: 5px;
      margin-left: auto;
      gap: 1px;
    }
    .pillar-mini-seg {
      height: 100%;
      border-radius: 1px;
    }

    /* TAG STRIP */
    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin-bottom: 14px;
    }
    .tag {
      font-family: var(--font-mono);
      font-size: 10px;
      font-weight: 600;
      padding: 2.5px 7px;
      border-radius: 5px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border: 1px solid var(--border-dim);
      color: var(--text-secondary);
      background: rgba(255, 255, 255, 0.03);
    }
    .tag-green { color: var(--green-text); background: var(--green-bg); border-color: var(--green-border); }
    .tag-amber { color: var(--amber-text); background: var(--amber-bg); border-color: var(--amber-border); }
    .tag-red   { color: var(--red-text);   background: var(--red-bg);   border-color: var(--red-border); }
    .tag-blue  { color: var(--blue-text);  background: var(--blue-bg);  border-color: var(--blue-border); }
    .tag-light { color: var(--text-primary); border-color: var(--border-strong); background: rgba(255, 255, 255, 0.08); }

    /* PRIMARY VALUATION BOX WITH VISUAL METER */
    .val-box {
      background: rgba(8, 11, 16, 0.65);
      border: 1px solid var(--border-dim);
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 12px;
    }
    .val-strip {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr 0.95fr 0.95fr;
      gap: 6px;
    }
    .val-cell .k {
      font-size: 9.5px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 500;
    }
    .val-cell .v {
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 600;
      margin-top: 2px;
      font-variant-numeric: tabular-nums;
    }
    .mos-meter-track {
      height: 3px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 2px;
      overflow: hidden;
      margin-top: 8px;
    }
    .mos-meter-fill {
      height: 100%;
      border-radius: 2px;
    }

    /* COMPACT METRICS TABLE */
    .kv-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 18px;
      font-size: 11.5px;
      padding: 0 2px;
    }
    .kv-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }
    .kv-item .k {
      color: var(--text-muted);
    }
    .kv-item .v {
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      font-weight: 500;
      color: var(--text-secondary);
    }

    /* CARD FOOTER */
    .card-footer {
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid var(--border-dim);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      font-size: 11px;
    }
    .verdict-text {
      font-family: var(--font-mono);
      font-size: 10.5px;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .source-count {
      font-size: 10.5px;
      color: var(--text-muted);
      flex-shrink: 0;
    }

    /* TABLE VIEW */
    .data-table-wrap {
      overflow-x: auto;
      border: 1px solid var(--border-dim);
      border-radius: 12px;
      background: var(--bg-panel);
      box-shadow: var(--shadow-card);
    }
    table.inst-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    table.inst-table th {
      background: rgba(10, 13, 19, 0.9);
      color: var(--text-muted);
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 12px 14px;
      text-align: right;
      border-bottom: 1px solid var(--border-dim);
      white-space: nowrap;
    }
    table.inst-table th:nth-child(1),
    table.inst-table th:nth-child(2),
    table.inst-table th:nth-child(3),
    table.inst-table th:nth-child(12) {
      text-align: left;
    }
    table.inst-table td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-dim);
      text-align: right;
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      color: var(--text-secondary);
      white-space: nowrap;
    }
    table.inst-table td:nth-child(1),
    table.inst-table td:nth-child(2),
    table.inst-table td:nth-child(3),
    table.inst-table td:nth-child(12) {
      text-align: left;
      font-family: var(--font-sans);
    }
    table.inst-table tr {
      cursor: pointer;
      transition: background 0.1s;
    }
    table.inst-table tbody tr:hover {
      background: rgba(255, 255, 255, 0.04);
    }

    /* SEMANTIC TEXT COLORS */
    .c-pos   { color: var(--green-text) !important; }
    .c-warn  { color: var(--amber-text) !important; }
    .c-neg   { color: var(--red-text) !important; }
    .c-prime { color: var(--text-primary) !important; }
    .c-muted { color: var(--text-muted) !important; }

    /* MODAL */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(3, 5, 9, 0.80);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      display: none;
      justify-content: center;
      align-items: center;
      z-index: 1000;
      padding: 24px;
    }
    .modal {
      background: #0d1119;
      border: 1px solid var(--border-mid);
      border-radius: 16px;
      max-width: 1000px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      padding: 28px 32px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 28px 72px rgba(0, 0, 0, 0.85);
    }
    .modal-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid var(--border-dim);
      padding-bottom: 18px;
      margin-bottom: 22px;
      gap: 16px;
    }
    .modal-ticker {
      font-family: var(--font-mono);
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }
    .modal-company {
      font-size: 15px;
      color: var(--text-secondary);
      font-weight: 400;
      margin-left: 10px;
    }
    .modal-pillars {
      display: flex;
      gap: 18px;
      margin-top: 8px;
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: var(--text-secondary);
      flex-wrap: wrap;
    }
    .modal-pillars span strong {
      color: var(--text-primary);
    }
    .close-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border-mid);
      color: var(--text-secondary);
      font-family: var(--font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 7px 14px;
      border-radius: 7px;
      cursor: pointer;
      transition: all 0.12s;
    }
    .close-btn:hover {
      color: var(--text-primary);
      background: rgba(255, 255, 255, 0.1);
      border-color: var(--border-strong);
    }

    .m-section {
      margin-bottom: 24px;
    }
    .m-heading {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-dim);
      padding-bottom: 6px;
      margin-bottom: 12px;
    }

    .verdict-panel {
      background: rgba(16, 21, 31, 0.85);
      border: 1px solid var(--border-mid);
      border-left: 3px solid #10b981;
      padding: 16px 20px;
      border-radius: 10px;
      margin-bottom: 22px;
    }
    .verdict-panel.v-green {
      border-left-color: #10b981;
      background: linear-gradient(90deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 21, 31, 0.88) 45%);
    }
    .verdict-panel.v-green .verdict-headline {
      color: var(--green-text);
    }
    .verdict-panel.v-red {
      border-left-color: #ef4444;
      border-color: rgba(239, 68, 68, 0.28);
      border-left-width: 3px;
      background: linear-gradient(90deg, rgba(239, 68, 68, 0.10) 0%, rgba(16, 21, 31, 0.88) 45%);
    }
    .verdict-panel.v-red .verdict-headline {
      color: var(--red-text);
    }
    .verdict-panel.v-amber {
      border-left-color: #f59e0b;
      border-color: rgba(245, 158, 11, 0.25);
      border-left-width: 3px;
      background: linear-gradient(90deg, rgba(245, 158, 11, 0.09) 0%, rgba(16, 21, 31, 0.88) 45%);
    }
    .verdict-panel.v-amber .verdict-headline {
      color: var(--amber-text);
    }
    .verdict-panel.v-mid {
      border-left-color: #94a3b8;
      background: rgba(16, 21, 31, 0.85);
    }
    .verdict-panel.v-mid .verdict-headline {
      color: var(--text-primary);
    }
    .verdict-headline {
      font-family: var(--font-mono);
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 6px;
    }
    .verdict-body {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.55;
    }
    .verdict-meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--border-dim);
      font-family: var(--font-mono);
      font-size: 11.5px;
    }
    .verdict-meta-grid .k {
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-muted);
      display: block;
    }
    .verdict-meta-grid .v {
      color: var(--text-primary);
      font-weight: 500;
    }

    .thesis-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    @media (max-width: 760px) {
      .thesis-grid { grid-template-columns: 1fr; }
    }
    .thesis-box {
      background: rgba(15, 19, 28, 0.75);
      border: 1px solid var(--border-dim);
      border-top-width: 2px;
      padding: 14px 16px;
      border-radius: 8px;
      font-size: 12.5px;
    }
    .thesis-box.bear { border-top-color: #ef4444; }
    .thesis-box.bull { border-top-color: #10b981; }
    .thesis-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }
    .thesis-list {
      list-style: none;
    }
    .thesis-list li {
      position: relative;
      padding-left: 12px;
      margin-bottom: 6px;
      color: var(--text-secondary);
    }
    .thesis-list li::before {
      content: "—";
      position: absolute;
      left: 0;
      color: var(--text-muted);
    }

    table.audit-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--font-mono);
      font-size: 12px;
      border: 1px solid var(--border-dim);
      border-radius: 8px;
      overflow: hidden;
    }
    table.audit-table th, table.audit-table td {
      padding: 9px 12px;
      border-bottom: 1px solid var(--border-dim);
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    table.audit-table th:first-child, table.audit-table td:first-child {
      text-align: left;
      font-family: var(--font-sans);
      color: var(--text-secondary);
    }
    table.audit-table th {
      background: rgba(10, 13, 19, 0.9);
      color: var(--text-muted);
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .clean-list {
      list-style: none;
    }
    .clean-list li {
      background: rgba(15, 19, 28, 0.65);
      border: 1px solid var(--border-dim);
      padding: 9px 14px;
      margin-bottom: 6px;
      font-size: 12px;
      color: var(--text-secondary);
      border-radius: 7px;
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }
    .clean-list a {
      color: var(--text-primary);
      text-decoration: none;
      font-weight: 500;
    }
    .clean-list a:hover {
      color: var(--blue-text);
    }
    .portal-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }
    .portal-btn {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-mid);
      color: var(--text-secondary);
      padding: 6px 12px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 11px;
      text-decoration: none;
      transition: all 0.12s;
    }
    .portal-btn:hover {
      color: var(--text-primary);
      border-color: var(--border-strong);
      background: rgba(255, 255, 255, 0.08);
    }
    .alert-row {
      padding: 9px 14px;
      margin-bottom: 6px;
      font-size: 12px;
      border-radius: 7px;
      border: 1px solid var(--border-dim);
      border-left-width: 3px;
      background: rgba(15, 19, 28, 0.7);
    }
    .alert-row.red { border-left-color: #ef4444; color: var(--red-text); }
    .alert-row.amber { border-left-color: #f59e0b; color: var(--amber-text); }

    /* METHODOLOGY / INFO MODAL GRID */
    .doc-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 16px;
    }
    @media (max-width: 760px) {
      .doc-grid { grid-template-columns: 1fr; }
    }
    .doc-card {
      background: rgba(15, 19, 28, 0.7);
      border: 1px solid var(--border-dim);
      padding: 16px 18px;
      border-radius: 10px;
    }
    .doc-card h4 {
      font-family: var(--font-mono);
      font-size: 11.5px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--text-primary);
      margin-bottom: 8px;
    }
    .bullet-point {
      margin-bottom: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.55;
    }
    .bullet-point:last-child {
      margin-bottom: 0;
    }
    .bullet-point strong, .clean-list strong, .verdict-body strong {
      color: #ffffff;
      font-weight: 600;
    }

    /* MATHEMATICAL FORMULA BLOCKS */
    .formula-display {
      background: rgba(8, 11, 16, 0.85);
      border: 1px solid var(--border-mid);
      border-left: 3px solid var(--blue-text);
      padding: 9px 13px;
      margin: 9px 0 11px;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 10px;
      overflow-x: auto;
      white-space: nowrap;
    }
    .f-name { font-weight: 600; color: var(--text-primary); }
    .f-eq { color: var(--text-muted); user-select: none; }
    .f-frac {
      display: inline-flex;
      flex-direction: column;
      vertical-align: middle;
      text-align: center;
      padding: 0 4px;
    }
    .f-num {
      border-bottom: 1px solid var(--border-strong);
      padding-bottom: 2px;
      color: var(--text-primary);
      font-weight: 500;
    }
    .f-den {
      padding-top: 2px;
      color: var(--text-secondary);
      font-size: 11px;
    }
    .f-var { font-style: italic; color: var(--blue-text); }
    .f-sup { font-size: 9.5px; vertical-align: super; color: var(--amber-text); }
    .f-sub { font-size: 9.5px; vertical-align: sub; color: var(--text-muted); }

    /* LIVE SCANNER PROGRESS MODAL */
    .scan-progress-wrap {
      background: rgba(8, 11, 16, 0.85);
      border: 1px solid var(--border-mid);
      border-radius: 12px;
      padding: 20px;
      margin: 16px 0;
    }
    .scan-bar-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 10px;
    }
    .scan-pct {
      font-family: var(--font-mono);
      font-size: 28px;
      font-weight: 700;
      color: var(--green-text);
      letter-spacing: -0.03em;
    }
    .scan-stage-label {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-secondary);
    }
    .scan-track {
      width: 100%;
      height: 10px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 999px;
      overflow: hidden;
      margin-bottom: 16px;
    }
    .scan-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
      border-radius: 999px;
      transition: width 0.25s ease;
      box-shadow: 0 0 16px rgba(16, 185, 129, 0.45);
    }
    .scan-log-feed {
      background: #06080c;
      border: 1px solid var(--border-dim);
      border-radius: 8px;
      padding: 12px 14px;
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: var(--text-secondary);
      height: 175px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    /* MOBILE SMARTPHONE & TABLET RESPONSIVENESS */
    @media (max-width: 860px) {
      *, *::before, *::after {
        max-width: 100%;
      }
      .desktop-only-actions {
        display: none !important;
      }
      .mobile-only-actions {
        display: flex !important;
      }
      .desktop-title {
        display: none !important;
      }
      .mobile-title {
        display: inline-block !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em !important;
        color: var(--text-primary) !important;
        white-space: nowrap !important;
      }
      .masthead {
        padding: 5px 8px !important;
        position: static !important;
        width: 100% !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
      }
      .masthead-inner {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 4px !important;
        width: 100% !important;
      }
      .brand-group {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
      }
      .brand-title-wrap {
        display: flex !important;
        align-items: center !important;
        gap: 7px !important;
        min-width: 0 !important;
      }
      .brand-mark {
        width: 5px !important;
        height: 18px !important;
      }
      .brand-title {
        font-size: 13px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
      }
      .brand-sub {
        display: none !important;
      }
      .header-btn-group.mobile-only-actions {
        display: flex !important;
        gap: 4px !important;
        align-items: center !important;
        flex-shrink: 0 !important;
      }
      .header-btn-group.mobile-only-actions .btn-secondary,
      .header-btn-group.mobile-only-actions .btn-primary {
        padding: 3px 8px !important;
        font-size: 10px !important;
        height: 25px !important;
        border-radius: 5px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
      }
      .pulse-dot {
        width: 5px !important;
        height: 5px !important;
      }
      .search-command {
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        padding: 0 8px !important;
        height: 32px !important;
        border-radius: 6px !important;
        box-sizing: border-box !important;
      }
      .search-prefix {
        display: none !important;
      }
      .search-command input {
        font-size: 12.5px !important;
        padding: 4px 2px !important;
        width: 100% !important;
        min-width: 0 !important;
      }
      .search-kbd {
        display: none !important;
      }
      .search-audit-btn {
        padding: 2px 6px !important;
        font-size: 9px !important;
      }
      .mobile-stats-row {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        width: 100% !important;
        background: rgba(12, 16, 24, 0.85);
        border: 1px solid var(--border-dim);
        border-radius: 6px;
        padding: 2px 8px !important;
        font-family: var(--font-mono);
        font-size: 9.5px !important;
        color: var(--text-secondary);
        box-sizing: border-box;
        height: 22px !important;
      }
      .mobile-stats-row span strong {
        color: var(--text-primary);
      }
      .container {
        padding: 6px 8px 48px !important;
        width: 100% !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
      }
      .benchmark-bar {
        padding: 5px 8px !important;
        margin-bottom: 6px !important;
        width: 100% !important;
        box-sizing: border-box !important;
      }
      .benchmark-label {
        font-size: 8.5px !important;
        margin-bottom: 2px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
      }
      .cohort-list {
        width: 100% !important;
        gap: 3px !important;
      }
      .cohort-item {
        width: 100% !important;
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 2px 6px !important;
        font-size: 9.5px !important;
        line-height: 1.3 !important;
      }
      .watchlist-wrap {
        padding: 6px 8px !important;
        margin-bottom: 6px !important;
        width: 100% !important;
        box-sizing: border-box !important;
      }
      .watchlist-top {
        flex-direction: column !important;
        align-items: stretch !important;
        width: 100% !important;
      }
      .watchlist-label {
        font-size: 8.5px !important;
        margin-bottom: 2px !important;
      }
      .watchlist-pills {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        padding-bottom: 3px !important;
        flex-wrap: nowrap !important;
        width: 100% !important;
        gap: 4px !important;
      }
      .wl-pill, .wl-new-btn {
        flex-shrink: 0 !important;
        white-space: nowrap !important;
        padding: 3px 8px !important;
        font-size: 10px !important;
        height: 24px !important;
      }
      .wl-active-panel {
        width: 100% !important;
        margin-top: 5px !important;
        padding-top: 5px !important;
      }
      .wl-panel-header {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 4px !important;
        width: 100% !important;
      }
      .wl-panel-header .btn-primary,
      .wl-panel-header .btn-secondary {
        width: 100% !important;
        text-align: center !important;
        justify-content: center !important;
        padding: 5px 8px !important;
        font-size: 10.5px !important;
      }
      .wl-input {
        width: 100% !important;
        min-width: 0 !important;
        box-sizing: border-box !important;
        font-size: 11.5px !important;
        padding: 5px 8px !important;
      }
      .toolbar {
        padding: 6px 8px !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 5px !important;
        width: 100% !important;
        margin-bottom: 6px !important;
        box-sizing: border-box !important;
      }
      .seg-group {
        width: 100% !important;
        display: flex !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        padding: 2px !important;
        gap: 4px !important;
      }
      .seg-btn {
        flex-shrink: 0 !important;
        white-space: nowrap !important;
        padding: 4px 8px !important;
        font-size: 10px !important;
        height: 25px !important;
      }
      .filter-Right {
        width: 100% !important;
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 5px !important;
      }
      .ctrl-group {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 2px !important;
      }
      .ctrl-group label {
        font-size: 8px !important;
        text-transform: uppercase !important;
      }
      .toolbar select {
        width: 100% !important;
        font-size: 10.5px !important;
        padding: 3px 6px !important;
        height: 26px !important;
      }
      .filter-Right > .seg-group {
        grid-column: span 2 !important;
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
      }
      .filter-Right > .seg-group .seg-btn {
        width: 100% !important;
        text-align: center !important;
      }
      .section-block {
        margin-bottom: 12px !important;
      }
      .section-header {
        margin-bottom: 5px !important;
      }
      .section-title {
        font-size: 13px !important;
      }
      .section-desc {
        display: none !important;
      }
      .section-meta {
        font-size: 8.5px !important;
        padding: 2px 6px !important;
      }
      .cards-grid {
        grid-template-columns: 1fr !important;
        gap: 8px !important;
        width: 100% !important;
      }
      .stock-card {
        padding: 9px 11px !important;
        width: 100% !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
      }
      .ticker {
        font-size: 15px !important;
      }
      .company-name {
        font-size: 10.5px !important;
        max-width: 160px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
      }
      .sector-tag {
        font-size: 9px !important;
        padding: 1px 4px !important;
      }
      .score-num {
        font-size: 15px !important;
      }
      .tag-row {
        gap: 4px !important;
        margin: 5px 0 6px !important;
        flex-wrap: wrap !important;
      }
      .tag {
        font-size: 9px !important;
        padding: 2px 5px !important;
      }
      .val-box {
        padding: 5px 7px !important;
        margin-bottom: 5px !important;
      }
      .val-strip {
        grid-template-columns: 1fr 1fr 1fr !important;
        gap: 4px !important;
      }
      .val-cell .k {
        font-size: 7.5px !important;
      }
      .val-cell .v {
        font-size: 10.5px !important;
      }
      .kv-grid {
        grid-template-columns: 1fr 1fr !important;
        gap: 2px 6px !important;
        font-size: 9.5px !important;
      }
      .card-footer {
        margin-top: 5px !important;
        padding-top: 5px !important;
        font-size: 9.5px !important;
      }
      .tier-block {
        margin-bottom: 12px !important;
      }
      .tier-bar {
        padding: 6px 8px !important;
        margin-bottom: 6px !important;
      }
      .tier-name {
        font-size: 11px !important;
      }
      .tier-sub {
        font-size: 9.5px !important;
      }
      .modal-backdrop {
        padding: 4px !important;
      }
      .modal {
        padding: 10px 10px !important;
        max-height: 94vh !important;
        border-radius: 8px !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
      }
      .modal-top {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 5px !important;
      }
      .modal-top > div:last-child {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 5px !important;
        width: 100% !important;
      }
      .modal-top > div:last-child button {
        width: 100% !important;
        text-align: center !important;
        justify-content: center !important;
        padding: 6px 6px !important;
        font-size: 10.5px !important;
      }
      .modal-ticker {
        font-size: 15px !important;
      }
      .modal-company {
        display: block !important;
        margin-left: 0 !important;
        margin-top: 2px !important;
        font-size: 11px !important;
      }
      .modal-pillars {
        font-size: 9px !important;
        gap: 4px !important;
        flex-wrap: wrap !important;
      }
      .verdict-meta-grid {
        grid-template-columns: 1fr 1fr !important;
        gap: 4px !important;
        padding: 8px 10px !important;
      }
      .verdict-meta-grid > div .k {
        font-size: 8px !important;
      }
      .verdict-meta-grid > div .v {
        font-size: 11px !important;
      }
      .thesis-grid {
        grid-template-columns: 1fr !important;
      }
      .doc-grid {
        grid-template-columns: 1fr !important;
      }
      .audit-table {
        font-size: 9.5px !important;
        display: block !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        width: 100% !important;
      }
      .formula-display {
        font-size: 9.5px !important;
        padding: 4px 6px !important;
      }
    }
  </style>
</head>
<body>

  <!-- MASTHEAD -->
  <header class="masthead">
    <div class="masthead-inner">
      <div class="brand-group">
        <div class="brand-title-wrap">
          <div class="brand-mark"></div>
          <div>
            <div class="brand-title">
              <span class="desktop-title">S&amp;P 500 Quantitative Valuation &amp; Forensic Terminal</span>
              <span class="mobile-title">S&amp;P 500 Terminal</span>
            </div>
            <div class="brand-sub">4-Year 10-K Audit  /  Owner FCF ex-SBC  /  Piotroski, Altman Z, Beneish M  /  Reverse DCF  /  OpenInsider</div>
          </div>
        </div>
        <div class="header-btn-group mobile-only-actions">
          <button class="btn-secondary" onclick="openInfoModal()">Info</button>
          <button class="btn-primary" onclick="openScannerModal()"><span class="pulse-dot"></span>Run Screener</button>
        </div>
      </div>

      <!-- PROMINENT TICKER SEARCH BAR -->
      <div class="search-command">
        <span class="search-prefix">Ticker / Audit</span>
        <input type="text" id="search-box" placeholder="Search or audit any ticker (e.g. APTV, SOFI, NVDA)..." oninput="onSearchInput()" onkeydown="onSearchKey(event)">
        <button class="search-audit-btn" id="search-audit-btn" onclick="auditFromSearchBox()">Audit</button>
        <button class="search-clear" id="search-clear-btn" onclick="clearSearch()">Clear</button>
        <span class="search-kbd" id="search-kbd-hint">/</span>
      </div>

      <div class="nav-right desktop-only-actions">
        <div class="telemetry-strip" id="stats-row"></div>
        <div class="header-btn-group">
          <button class="btn-secondary" onclick="openInfoModal()">Methodology</button>
          <button class="btn-primary" onclick="openScannerModal()"><span class="pulse-dot"></span>Run Screener</button>
        </div>
      </div>
      <div class="mobile-stats-row mobile-only-actions" id="mobile-stats-row"></div>
    </div>
  </header>

  <main class="container">
    <!-- SECTOR MOMENTUM & ROTATION HEATMAP BAR -->
    <div class="sector-bar-wrap" id="sector-bar-container"></div>

    <!-- SHARED WATCHLISTS BAR & ACTIVE WATCHLIST WORKSPACE -->
    <div class="watchlist-wrap" id="watchlist-container"></div>

    <!-- FILTER & VIEW TOOLBAR -->
    <div class="toolbar">
      <div class="seg-group" id="segment-tabs">
        <button class="seg-btn active" data-filter="ALL" onclick="setSegment('ALL')">All Universe</button>
        <button class="seg-btn" data-filter="BASKET_ONLY" onclick="setSegment('BASKET_ONLY')">Portfolio Basket</button>
        <button class="seg-btn" data-filter="ZERO_FLAGS" onclick="setSegment('ZERO_FLAGS')">Clean 10-K (Zero Flags)</button>
        <button class="seg-btn" data-filter="HIGH_CASH" onclick="setSegment('HIGH_CASH')">High Cash Yield (&ge;5%)</button>
        <button class="seg-btn" data-filter="INSIDER_BUY" onclick="setSegment('INSIDER_BUY')">Net Insider Buying</button>
      </div>

      <div class="filter-Right">
        <div class="ctrl-group">
          <label>Sector</label>
          <select id="sector-filter" onchange="render()"><option value="ALL">All Sectors</option></select>
        </div>
        <div class="ctrl-group">
          <label>Sort</label>
          <select id="sort-mode" onchange="render()">
            <option value="score">Economic Score</option>
            <option value="fcfYield">Owner Cash Yield</option>
            <option value="pleasing">Most Pleasing Signals</option>
            <option value="roic">3Y Avg ROIC</option>
            <option value="gpAssets">Gross Profit / Assets</option>
            <option value="piotroski">Piotroski F-Score</option>
            <option value="insider">Insider Conviction</option>
          </select>
        </div>
        <div class="seg-group">
          <button class="seg-btn active" id="btn-view-grid" onclick="setViewMode('GRID')">Grid</button>
          <button class="seg-btn" id="btn-view-table" onclick="setViewMode('TABLE')">Table</button>
        </div>
      </div>
    </div>

    <!-- ACTIVE SEARCH STATUS BAR -->
    <div class="search-status-bar" id="search-status-bar">
      <span id="search-status-text"></span>
      <span class="c-muted">Press [Enter] to open top match or [Esc] to clear search</span>
    </div>

    <!-- TOP DIVERSIFIED PORTFOLIO BASKET -->
    <section class="section-block" id="basket-section">
      <div class="section-header">
        <div class="section-title-group">
          <h2 class="section-title">Selected Portfolio Basket</h2>
          <span class="section-desc">Zero forensic red flags across 4-year statements, positive DCF margin of safety, capped at 3 positions per sector</span>
        </div>
        <span class="section-meta" id="basket-badge">0 POSITIONS</span>
      </div>
      <div class="cards-grid" id="basket-grid"></div>
    </section>

    <!-- UNIVERSE OUTPUT -->
    <div id="dashboard"></div>
  </main>

  <!-- RESEARCH DOSSIER / INFO / SCANNER MODAL -->
  <div class="modal-backdrop" id="modal-backdrop" onclick="if(event.target===this)closeModal()">
    <div class="modal" id="modal-content"></div>
  </div>

<script>
let PAYLOAD = __PAYLOAD_JSON__;
let allStocks = PAYLOAD.stocks || [];
let cohorts = PAYLOAD.cohorts || [];
let watchlists = PAYLOAD.watchlists || [];
try {
  if ((!watchlists || watchlists.length === 0) && window.localStorage) {
    const cachedWls = localStorage.getItem('sp500_shared_watchlists');
    if (cachedWls) watchlists = JSON.parse(cachedWls) || [];
  }
} catch (e) {}

let activeSegment = 'ALL';
let activeWatchlistId = null;
let showNewWatchlistForm = false;
let viewMode = 'GRID';
let currentFiltered = [];
let scanPollTimer = null;

async function syncWatchlistsToServer() {
  PAYLOAD.watchlists = watchlists;
  try {
    if (window.localStorage) {
      localStorage.setItem('sp500_shared_watchlists', JSON.stringify(watchlists));
    }
  } catch (e) {}
  try {
    const res = await fetch('/api/watchlists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ watchlists })
    });
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.watchlists)) {
        watchlists = data.watchlists;
        PAYLOAD.watchlists = watchlists;
      }
    }
  } catch (e) {}
}

function selectWatchlist(wid) {
  activeWatchlistId = (wid === activeWatchlistId) ? null : wid;
  showNewWatchlistForm = false;
  render();
}

function toggleNewWatchlistForm() {
  showNewWatchlistForm = !showNewWatchlistForm;
  renderWatchlistsBar();
  if (showNewWatchlistForm) {
    const inp = document.getElementById('new-wl-name');
    if (inp) inp.focus();
  }
}

async function createWatchlistFromForm() {
  const nameEl = document.getElementById('new-wl-name');
  const tickersEl = document.getElementById('new-wl-tickers');
  const name = (nameEl ? nameEl.value : '').trim();
  if (!name) {
    if (nameEl) nameEl.focus();
    return;
  }
  const rawTickers = (tickersEl ? tickersEl.value : '').toUpperCase().split(/[\s,;]+/).map(t => t.trim()).filter(Boolean);
  const uniqueTickers = [...new Set(rawTickers)];
  const newId = 'wl_' + Date.now();
  watchlists.push({ id: newId, name, tickers: uniqueTickers });
  activeWatchlistId = newId;
  showNewWatchlistForm = false;
  render();
  await syncWatchlistsToServer();
}

async function addTickersToWatchlist(wid) {
  const wl = watchlists.find(w => w.id === wid);
  if (!wl) return;
  const inp = document.getElementById('add-wl-tickers-input');
  if (!inp) return;
  const raw = inp.value.toUpperCase().split(/[\s,;]+/).map(t => t.trim()).filter(Boolean);
  if (raw.length === 0) return;
  raw.forEach(t => {
    if (!wl.tickers.includes(t)) wl.tickers.push(t);
  });
  inp.value = '';
  render();
  await syncWatchlistsToServer();
}

async function removeTickerFromWatchlist(wid, ticker, ev) {
  if (ev) ev.stopPropagation();
  const wl = watchlists.find(w => w.id === wid);
  if (!wl) return;
  wl.tickers = wl.tickers.filter(t => t.toUpperCase() !== ticker.toUpperCase());
  render();
  await syncWatchlistsToServer();
}

async function toggleTickerInWatchlist(wid, ticker) {
  const wl = watchlists.find(w => w.id === wid);
  if (!wl) return;
  const up = ticker.toUpperCase();
  if (wl.tickers.includes(up)) {
    wl.tickers = wl.tickers.filter(t => t !== up);
  } else {
    wl.tickers.push(up);
  }
  await syncWatchlistsToServer();
  renderWatchlistsBar();
  openModal(ticker);
}

async function deleteWatchlist(wid) {
  const wl = watchlists.find(w => w.id === wid);
  if (!wl) return;
  watchlists = watchlists.filter(w => w.id !== wid);
  if (activeWatchlistId === wid) activeWatchlistId = null;
  render();
  await syncWatchlistsToServer();
}

function runWatchlistAnalysis(wid) {
  const wl = watchlists.find(w => w.id === wid);
  if (!wl || !wl.tickers || wl.tickers.length === 0) return;
  openScannerModal();
  triggerLiveScan('watchlist', wl.tickers, wl.name);
}

function renderWatchlistsBar() {
  const container = document.getElementById('watchlist-container');
  if (!container) return;

  const allPillCls = activeWatchlistId === null ? 'wl-pill active' : 'wl-pill';
  const pillsHTML = [
    `<button class="${allPillCls}" onclick="selectWatchlist(null)">All Shared Database <span class="wl-pill-count">${allStocks.length}</span></button>`,
    ...watchlists.map(w => {
      const cls = activeWatchlistId === w.id ? 'wl-pill active' : 'wl-pill';
      return `<button class="${cls}" onclick="selectWatchlist('${w.id}')">${w.name} <span class="wl-pill-count">${(w.tickers || []).length}</span></button>`;
    }),
    `<button class="wl-new-btn" onclick="toggleNewWatchlistForm()">+ New Watchlist</button>`
  ].join('');

  let formHTML = '';
  if (showNewWatchlistForm) {
    formHTML = `
      <div class="wl-active-panel">
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
          <span class="watchlist-label" style="color:var(--green-text);">Create Shared Watchlist</span>
          <input type="text" id="new-wl-name" class="wl-input" placeholder="Watchlist Name (e.g. AI Infrastructure, Compounders)..." onkeydown="if(event.key==='Enter')createWatchlistFromForm()">
          <input type="text" id="new-wl-tickers" class="wl-input" placeholder="Optional initial tickers (e.g. NVDA, AVGO, ANET)..." style="flex:1;" onkeydown="if(event.key==='Enter')createWatchlistFromForm()">
          <button class="btn-primary" onclick="createWatchlistFromForm()">Save Shared Watchlist</button>
          <button class="btn-secondary" onclick="toggleNewWatchlistForm()">Cancel</button>
        </div>
      </div>
    `;
  }

  let activePanelHTML = '';
  if (activeWatchlistId) {
    const wl = watchlists.find(w => w.id === activeWatchlistId);
    if (wl) {
      const tickers = wl.tickers || [];
      const inDbCount = tickers.filter(t => allStocks.some(s => s.ticker.toUpperCase() === t.toUpperCase())).length;
      const unscannedCount = tickers.length - inDbCount;

      const chips = tickers.length > 0
        ? tickers.map(t => {
            const st = allStocks.find(s => s.ticker.toUpperCase() === t.toUpperCase());
            let metaBadge = '<span class="c-warn" style="font-size:10px;">Unscanned</span>';
            if (st) {
              const hasFlags = st.red_flags && st.red_flags.length > 0;
              const sCls = (!hasFlags && st.composite_score >= 60) ? 'c-pos' : (hasFlags || st.composite_score < 45 ? 'c-neg' : 'c-prime');
              metaBadge = `<span class="${sCls}" style="font-size:10.5px;">${st.data_ok ? st.composite_score.toFixed(0) : 'N/A'}</span>`;
            }
            const clickAct = st ? `openModal('${st.ticker}')` : `auditSingleTicker('${t}')`;
            return `
              <span class="wl-chip" onclick="${clickAct}" title="${st ? st.company + ' — Click to inspect dossier' : 'Not yet in database — Click to audit ' + t}">
                <strong>${t}</strong>
                ${metaBadge}
                <span class="wl-chip-del" onclick="removeTickerFromWatchlist('${wl.id}', '${t}', event)" title="Remove ${t} from watchlist">&times;</span>
              </span>
            `;
          }).join('')
        : '<span class="c-muted" style="font-size:12px;">No companies in this watchlist yet. Add tickers below or from inside any stock dossier.</span>';

      activePanelHTML = `
        <div class="wl-active-panel">
          <div class="wl-panel-header">
            <div>
              <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${wl.name}</span>
              <span class="c-muted" style="font-family:var(--font-mono);font-size:11.5px;margin-left:10px;">
                ${tickers.length} Companies (${inDbCount} audited in DB${unscannedCount > 0 ? `, <strong class="c-warn">${unscannedCount} pending initial audit</strong>` : ''})
              </span>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              ${tickers.length > 0 ? `<button class="btn-primary" onclick="runWatchlistAnalysis('${wl.id}')"><span class="pulse-dot"></span>Analyze This Watchlist Alone (${tickers.length} Stocks)</button>` : ''}
              <button class="btn-secondary" onclick="selectWatchlist(null)">Show All Database</button>
              <button class="btn-secondary" style="color:var(--red-text);border-color:rgba(239,68,68,0.28);" onclick="deleteWatchlist('${wl.id}')">Delete Watchlist</button>
            </div>
          </div>

          <div class="wl-chip-list">${chips}</div>

          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:2px;">
            <input type="text" id="add-wl-tickers-input" class="wl-input" placeholder="Add tickers to ${wl.name} (e.g. AAPL, MSFT, RDDT, SOFI)..." style="flex:1;" onkeydown="if(event.key==='Enter')addTickersToWatchlist('${wl.id}')">
            <button class="btn-secondary" onclick="addTickersToWatchlist('${wl.id}')">+ Add Companies</button>
            <span class="c-muted" style="font-size:11px;font-family:var(--font-mono);">Clicking "Analyze This Watchlist Alone" runs the full 4-Year 10-K + SEC EDGAR + OpenInsider audit on these ${tickers.length} companies and updates the shared database.</span>
          </div>
        </div>
      `;
    }
  }

  container.innerHTML = `
    <div class="watchlist-top">
      <div class="watchlist-pills">
        <span class="watchlist-label">Shared Watchlists</span>
        ${pillsHTML}
      </div>
    </div>
    ${formHTML}
    ${activePanelHTML}
  `;
}

const tierOrder = ['S', 'A', 'B', 'C', 'D', 'U'];
const tierMeta = {
  'S': { css: 'tier-S', label: 'Tier S — Selected Portfolio Basket', desc: 'Cleared all multi-year forensic gates; highest composite valuation and quality scores (max 3 per sector)' },
  'A': { css: 'tier-A', label: 'Tier A — High-Conviction Watchlist', desc: 'Zero hard forensic red flags; strong fundamentals but either fuller valuation or sector-capped' },
  'B': { css: 'tier-B', label: 'Tier B — Quality Compounders at Fair Value', desc: 'Clean financial statements and positive cash generation, priced near intrinsic growth expectations' },
  'C': { css: 'tier-C', label: 'Tier C — Mixed Fundamentals / Caution', desc: 'Modest composite score or operational warnings requiring manual verification' },
  'D': { css: 'tier-D', label: 'Tier D — Disqualified / Hard Red Flags', desc: 'Excluded due to negative Owner FCF, share dilution, high leverage, distress Z-Score, or severe contraction' },
  'U': { css: 'tier-U', label: 'Unrated — Incomplete Financial Data', desc: 'Fewer than 3 aligned annual statements or non-USD reporting mismatch' }
};

const sectorETFs = {
  'Technology': 'XLK',
  'Financial Services': 'XLF',
  'Energy': 'XLE',
  'Healthcare': 'XLV',
  'Consumer Cyclical': 'XLY',
  'Consumer Defensive': 'XLP',
  'Industrials': 'XLI',
  'Basic Materials': 'XLB',
  'Communication Services': 'XLC',
  'Real Estate': 'XLRE',
  'Utilities': 'XLU'
};

function renderSectorBar() {
  const container = document.getElementById('sector-bar-container');
  if (!container) return;

  const sectors = {};
  allStocks.forEach(s => {
    const sec = s.sector || 'Other';
    if (!sectors[sec]) sectors[sec] = [];
    sectors[sec].push(s);
  });

  const secList = Object.keys(sectors).map(sec => {
    const slist = sectors[sec];
    const dds = slist.map(s => s.drawdown).filter(d => d != null);
    const avgDD = dds.length ? (dds.reduce((a, b) => a + b, 0) / dds.length) : 0;
    const corrCount = dds.filter(d => d <= -0.20).length;
    const corrPct = dds.length ? (corrCount / dds.length * 100) : 0;
    const fcfs = slist.map(s => s.owner_fcf_yield).filter(y => y != null).sort((a, b) => a - b);
    const medFCF = fcfs.length ? fcfs[Math.floor(fcfs.length / 2)] : 0;

    let regime = 'NEUTRAL';
    if (avgDD > -0.12) regime = 'LEADING';
    else if (avgDD <= -0.18) regime = 'HEADWIND';

    return {
      name: sec,
      count: slist.length,
      avgDD,
      corrPct,
      medFCF,
      regime
    };
  });

  // Sort sectors by relative strength (least drawdown first)
  secList.sort((a, b) => b.avgDD - a.avgDD);

  const activeSector = document.getElementById('sector-filter') ? document.getElementById('sector-filter').value : 'ALL';

  const cardsHTML = secList.map(sec => {
    const isActive = activeSector === sec.name;
    const regCls = sec.regime === 'LEADING' ? 'regime-leading' : (sec.regime === 'HEADWIND' ? 'regime-headwind' : 'regime-neutral');
    const ddCls = sec.avgDD > -0.12 ? 'c-pos' : (sec.avgDD <= -0.18 ? 'c-neg' : 'c-prime');
    const etf = sectorETFs[sec.name] || '';

    return `
      <div class="sector-card ${isActive ? 'active' : ''}" onclick="selectSectorFromBar('${sec.name.replace(/'/g, "\\'")}')" title="${sec.name}: Avg constituent drawdown ${fmtPct(sec.avgDD, 1)}, ${sec.corrPct.toFixed(0)}% of stocks in correction. Click card to filter.">
        <div class="sector-card-top">
          <span class="sector-card-name">${sec.name}</span>
          <span class="sector-card-regime ${regCls}">${sec.regime}</span>
        </div>
        <div class="sector-card-metrics">
          <span>Avg DD: <strong class="${ddCls}">${fmtPct(sec.avgDD, 1)}</strong></span>
          <span>Cash: <strong>${fmtPct(sec.medFCF, 1)}</strong></span>
        </div>
        <div class="sector-card-bottom">
          <span class="c-muted" style="font-size:9.5px;font-family:var(--font-mono);">${sec.count} stocks</span>
          ${etf ? `<a href="https://www.tradingview.com/chart/?symbol=AMEX%3A${etf}" target="_blank" rel="noopener" class="sector-tv-link" onclick="event.stopPropagation()" title="Open ${sec.name} (${etf}) chart on TradingView">${etf} &nearr;</a>` : ''}
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="sector-bar-header">
      <div>
        <div class="sector-bar-title">S&amp;P 500 Sector Momentum &amp; Capital Rotation (Moskowitz &amp; Grinblatt 1999)</div>
        <div class="sector-bar-subtitle">Ranked by Relative Strength (Least Drawdown &bull; Click card to filter &bull; TradingView ETF charts)</div>
      </div>
      <div>
        <a href="https://www.tradingview.com/heatmap/stock/#%7B%22dataset%22%3A%22SPX500%22%2C%22group%22%3A%22sector%22%7D" target="_blank" rel="noopener" class="portal-btn" style="padding:4px 9px;font-size:11px;" title="Open live visual S&P 500 sector heatmap on TradingView">TradingView Heatmap &nearr;</a>
      </div>
    </div>
    <div class="sector-grid">
      ${cardsHTML}
    </div>
  `;
}

function selectSectorFromBar(secName) {
  const sel = document.getElementById('sector-filter');
  if (!sel) return;
  if (sel.value === secName) {
    sel.value = 'ALL';
  } else {
    sel.value = secName;
  }
  render();
}

function populateSectorFilter() {
  const sectors = [...new Set(allStocks.map(s => s.sector).filter(s => s && s !== 'N/A'))].sort();
  const sectorSel = document.getElementById('sector-filter');
  const prev = sectorSel.value || 'ALL';
  sectorSel.innerHTML = '<option value="ALL">All Sectors</option>';
  sectors.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; sectorSel.appendChild(o); });
  sectorSel.value = prev;
}
populateSectorFilter();

function setSegment(seg) {
  activeSegment = seg;
  document.querySelectorAll('#segment-tabs .seg-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-filter') === seg);
  });
  render();
}

function setViewMode(mode) {
  viewMode = mode;
  document.getElementById('btn-view-grid').classList.toggle('active', mode === 'GRID');
  document.getElementById('btn-view-table').classList.toggle('active', mode === 'TABLE');
  render();
}

function onSearchInput() {
  const val = document.getElementById('search-box').value.trim();
  const auditBtn = document.getElementById('search-audit-btn');
  const isTickerLike = /^[A-Za-z.-]{1,7}$/.test(val);
  if (auditBtn) {
    auditBtn.style.display = isTickerLike ? 'inline-block' : 'none';
    if (isTickerLike) auditBtn.textContent = `Audit ${val.toUpperCase()}`;
  }
  document.getElementById('search-clear-btn').style.display = val.length > 0 ? 'inline-block' : 'none';
  document.getElementById('search-kbd-hint').style.display = val.length > 0 ? 'none' : 'inline-block';
  render();
}

function clearSearch() {
  const box = document.getElementById('search-box');
  box.value = '';
  onSearchInput();
  box.focus();
}

function auditFromSearchBox() {
  const q = document.getElementById('search-box').value.trim().toUpperCase();
  if (q) auditSingleTicker(q);
}

function onSearchKey(e) {
  if (e.key === 'Escape') {
    clearSearch();
    document.getElementById('search-box').blur();
  } else if (e.key === 'Enter') {
    const q = document.getElementById('search-box').value.trim().toUpperCase();
    if (!q) return;
    if (e.shiftKey) {
      auditSingleTicker(q);
      return;
    }
    const exact = allStocks.find(s => s.ticker.toUpperCase() === q);
    if (exact) {
      openModal(exact.ticker);
    } else if (currentFiltered.length > 0) {
      openModal(currentFiltered[0].ticker);
    } else if (/^[A-Z.-]{1,7}$/.test(q)) {
      auditSingleTicker(q);
    }
  }
}

async function auditSingleTicker(rawSymbol) {
  const sym = (rawSymbol || '').trim().toUpperCase();
  if (!sym) return;
  document.getElementById('modal-content').innerHTML = `
    <div class="modal-top">
      <div>
        <div>
          <span class="modal-ticker">Live Single-Stock Forensic Audit: ${sym}</span>
        </div>
        <div class="modal-pillars">
          <span>4-Year 10-K Statements</span>
          <span>Reverse DCF</span>
          <span>OpenInsider 12M Ledger</span>
          <span>SEC EDGAR &amp; News Synthesis</span>
        </div>
      </div>
      <button class="close-btn" onclick="closeModal()">Close [ESC]</button>
    </div>
    <div class="verdict-panel" id="single-audit-panel">
      <div class="verdict-headline" id="single-audit-title">Running Full Quantitative &amp; SEC EDGAR Audit on ${sym}...</div>
      <div class="verdict-body" id="single-audit-sub">
        Fetching 4-year audited Income, Balance Sheet &amp; Cash Flow statements, computing Owner FCF ex-SBC, Piotroski F, Altman Z, Beneish M, scanning 12 months of OpenInsider filings, and building the SEC EDGAR / News catalyst dossier (~3 seconds).
      </div>
      <div class="progress-track" style="margin-top:16px;">
        <div class="progress-fill" id="single-audit-bar" style="width: 45%; transition: width 0.5s ease;"></div>
      </div>
    </div>
  `;
  document.getElementById('modal-backdrop').style.display = 'flex';

  const barTimer = setTimeout(() => {
    const b = document.getElementById('single-audit-bar');
    if (b) b.style.width = '82%';
  }, 900);

  try {
    const res = await fetch('/api/audit/ticker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: sym })
    });
    clearTimeout(barTimer);
    const data = await res.json();
    if (!res.ok || !data.ok || !data.stock) {
      const errText = (data && data.error) ? data.error : `Could not retrieve financial statements for '${sym}'. Verify the ticker symbol.`;
      document.getElementById('single-audit-title').className = 'verdict-headline c-neg';
      document.getElementById('single-audit-title').textContent = `Audit Failed for ${sym}`;
      document.getElementById('single-audit-sub').textContent = errText;
      const b = document.getElementById('single-audit-bar');
      if (b) b.style.width = '0%';
      return;
    }

    const stock = data.stock;
    if (data.stocks && Array.isArray(data.stocks)) {
      allStocks = data.stocks;
      PAYLOAD.stocks = allStocks;
    } else {
      const idx = allStocks.findIndex(s => s.ticker.toUpperCase() === stock.ticker.toUpperCase());
      if (idx >= 0) {
        allStocks[idx] = stock;
      } else {
        allStocks.push(stock);
      }
    }
    populateSectorFilter();
    render();
    openModal(stock.ticker);
  } catch (err) {
    clearTimeout(barTimer);
    const titleEl = document.getElementById('single-audit-title');
    const subEl = document.getElementById('single-audit-sub');
    if (titleEl) {
      titleEl.className = 'verdict-headline c-warn';
      titleEl.textContent = 'Local Python Engine Required for Live Ticker Audits';
    }
    if (subEl) {
      subEl.innerHTML = 'You are viewing the static HTML file directly. Double-click <strong>launch_app.bat</strong> in the project folder to start the live local engine and audit any ticker on demand.';
    }
  }
}

function fmtPct(v, dec=1, plus=false) {
  if (v === null || v === undefined || isNaN(v)) return '—';
  const p = (v * 100).toFixed(dec);
  return (plus && v > 0 ? '+' : '') + p + '%';
}
function fmtNum(v, dec=1) {
  if (v === null || v === undefined || isNaN(v)) return '—';
  return Number(v).toFixed(dec);
}
function fmtMoneyB(v) {
  if (v === null || v === undefined || isNaN(v)) return '—';
  return '$' + (v / 1e9).toFixed(2) + 'B';
}

function renderTracker() {
  return;
}

function insiderTagHTML(s) {
  const sig = s.insider_signal || 'NEUTRAL';
  if (sig === 'CLUSTER BUY') return `<span class="tag tag-green">Cluster Buy (${s.insider_buyers}B)</span>`;
  if (sig === 'CEO/CFO BUY') return `<span class="tag tag-green">C-Suite Buy</span>`;
  if (sig === 'INSIDER BUY') return `<span class="tag tag-blue">Net Insider Buy</span>`;
  if (sig === 'LONE BUY / HEAVY SELLS') return `<span class="tag tag-amber">1 Buy / ${s.insider_sellers || 'Mult'} Sells</span>`;
  if (sig === 'C-SUITE DUMPING') return `<span class="tag tag-red">C-Suite Selling</span>`;
  if (sig === 'HEAVY SELLING') return `<span class="tag tag-red">Insider Selling</span>`;
  return '';
}

function verdictTone(s, rdoc) {
  const vText = (rdoc && rdoc.verdict) ? rdoc.verdict.toUpperCase() : '';
  const vCol = (rdoc && rdoc.verdict_color) ? rdoc.verdict_color : '';
  if ((s.red_flags && s.red_flags.length > 0) || vCol === 'b-red' || vText.includes('DISQUALIFIED') || vText.includes('AVOID')) {
    return { panelCls: 'v-red', textCls: 'c-neg' };
  }
  if (vCol === 'b-amber' || vText.includes('WAIT FOR EARNINGS') || vText.includes('DUMPING') || vText.includes('HEAVY SELLING')) {
    return { panelCls: 'v-amber', textCls: 'c-warn' };
  }
  if (vCol === 'b-slate' || vCol === 'b-blue' || vText.includes('WATCHLIST') || vText.includes('HOLD') || vText.includes('UNRATED') || vText.includes('CAUTIOUS')) {
    return { panelCls: 'v-mid', textCls: 'c-prime' };
  }
  return { panelCls: 'v-green', textCls: 'c-pos' };
}

function colorizeDesc(text, s) {
  if (!text) return '';
  let out = String(text);

  // 1. Score X/100
  out = out.replace(/(\b\d+(?:\.\d+)?)\s*\/\s*100\b/g, (m, v) => {
    const num = parseFloat(v);
    const cls = (num >= 60 && (!s || !s.red_flags || !s.red_flags.length)) ? 'c-pos' : (num < 45 || (s && s.red_flags && s.red_flags.length) ? 'c-neg' : 'c-prime');
    return `<strong class="${cls}">${v}/100</strong>`;
  });

  // 2. Piotroski X/9
  out = out.replace(/(\b\d+(?:\.\d+)?)\s*\/\s*9\b/g, (m, v) => {
    const num = parseFloat(v);
    const cls = num >= 7 ? 'c-pos' : (num <= 4 ? 'c-neg' : 'c-prime');
    return `<strong class="${cls}">${v}/9</strong>`;
  });

  // 3. ROIC percentages
  out = out.replace(/(ROIC(?:\s+is|\s+of)?\s+)([+-]?\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    const num = parseFloat(pct);
    const cls = num >= 15 ? 'c-pos' : (num < 8 ? 'c-neg' : 'c-prime');
    return `${pre}<strong class="${cls}">${pct}</strong>`;
  });

  // 4. Operating margin percentages
  out = out.replace(/(operating margin of\s+)([+-]?\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    const num = parseFloat(pct);
    const cls = num >= 18 ? 'c-pos' : (num < 8 ? 'c-neg' : 'c-prime');
    return `${pre}<strong class="${cls}">${pct}</strong>`;
  });
  out = out.replace(/([+-]?\d+(?:\.\d+)?%)(\s+operating margin)/gi, (m, pct, post) => {
    const num = parseFloat(pct);
    const cls = num >= 18 ? 'c-pos' : (num < 8 ? 'c-neg' : 'c-prime');
    return `<strong class="${cls}">${pct}</strong>${post}`;
  });
  out = out.replace(/(compresses below\s+)([+-]?\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    return `${pre}<strong class="c-neg">${pct}</strong>`;
  });

  // 5. Margin change pts over 3Y: (+2.1 pts over 3Y)
  out = out.replace(/\(([+-]?\d+(?:\.\d+)?\s*pts\s+over\s+3Y)\)/gi, (m, inner) => {
    const num = parseFloat(inner);
    const cls = num >= 1.0 ? 'c-pos' : (num <= -1.0 ? 'c-neg' : 'c-prime');
    return `(<strong class="${cls}">${inner}</strong>)`;
  });

  // 6. Owner FCF yield / cash yield
  out = out.replace(/([+-]?\d+(?:\.\d+)?%)(\s+(?:true\s+|negative\s+)?Owner FCF yield)/gi, (m, pct, post) => {
    const num = parseFloat(pct);
    const cls = num >= 5.0 ? 'c-pos' : (num < 2.5 ? 'c-neg' : 'c-prime');
    return `<strong class="${cls}">${pct}</strong>${post}`;
  });
  out = out.replace(/(Owner FCF yield:\s*|cash yield\s*\()([+-]?\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    const num = parseFloat(pct);
    const cls = num >= 5.0 ? 'c-pos' : (num < 2.5 ? 'c-neg' : 'c-prime');
    return `${pre}<strong class="${cls}">${pct}</strong>`;
  });

  out = out.replace(/(Thin\s+)([+-]?\d+(?:\.\d+)?%)(\s+Owner FCF yield)/gi, (m, pre, pct, post) => {
    return `${pre}<strong class="c-neg">${pct}</strong>${post}`;
  });
  out = out.replace(/(Price is\s+)(\d+(?:\.\d+)?%)(\s+above conservative DCF fair value)/gi, (m, pre, pct, post) => {
    return `${pre}<strong class="c-neg">${pct}</strong>${post}`;
  });
  out = out.replace(/(implying\s+)(\d+(?:\.\d+)?%)(\s+downside)/gi, (m, pre, pct, post) => {
    return `${pre}<strong class="c-neg">${pct}</strong>${post}`;
  });
  out = out.replace(/(Trades at\s+)(\+\d+(?:\.\d+)?%)(\s+upside)/gi, (m, pre, pct, post) => {
    return `${pre}<strong class="c-pos">${pct}</strong>${post}`;
  });

  // 7. DCF upside / margin of safety / premium
  out = out.replace(/([+-]?\d+(?:\.\d+)?%)(\s+(?:DCF\s+)?(?:upside|margin of safety|premium))/gi, (m, pct, post) => {
    const num = parseFloat(pct);
    const isPrem = /premium/i.test(post);
    const cls = (!isPrem && num >= 10) ? 'c-pos' : ((isPrem || num <= -5) ? 'c-neg' : 'c-prime');
    return `<strong class="${cls}">${pct}</strong>${post}`;
  });

  // 8. Drawdown from 52-week high: down -48%
  out = out.replace(/(down\s+)(-\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    const num = parseFloat(pct);
    const cls = num <= -20 ? 'c-neg' : 'c-prime';
    return `${pre}<strong class="${cls}">${pct}</strong>`;
  });

  // 9. Short interest stands at X%
  out = out.replace(/(Short interest stands at\s+)(\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    const num = parseFloat(pct);
    const cls = num > 8.0 ? 'c-neg' : (num < 3.0 ? 'c-pos' : 'c-prime');
    return `${pre}<strong class="${cls}">${pct}</strong>`;
  });

  // 10. Share buybacks vs dilution
  out = out.replace(/(retiring\s+)(\d+(?:\.\d+)?%)/gi, (m, pre, pct) => {
    return `${pre}<strong class="c-pos">${pct}</strong>`;
  });
  out = out.replace(/([+-]?\d+(?:\.\d+)?%\/yr)(\s+share count dilution)/gi, (m, pct, post) => {
    return `<strong class="c-neg">${pct}</strong>${post}`;
  });

  // 11. Implied growth vs 3Y historical revenue growth
  out = out.replace(/(pricing in a\s+)([+-]?\d+(?:\.\d+)?%\/yr\s+permanent contraction)/gi, (m, pre, val) => {
    return `${pre}<strong class="c-warn">${val}</strong>`;
  });
  out = out.replace(/(prices in\s+)([+-]?\d+(?:\.\d+)?%\/yr)(\s+FCF growth vs\s+)([+-]?\d+(?:\.\d+)?%\/yr)(\s+historical 3Y revenue growth)/gi, (m, p1, impPct, p2, revPct, p3) => {
    const impN = parseFloat(impPct);
    const revN = parseFloat(revPct);
    const impCls = (revN - impN >= 2.0) ? 'c-pos' : (impN - revN >= 4.0 ? 'c-neg' : 'c-prime');
    const revCls = revN >= 6.0 ? 'c-pos' : (revN < 0 ? 'c-neg' : 'c-prime');
    return `${p1}<strong class="${impCls}">${impPct}</strong>${p2}<strong class="${revCls}">${revPct}</strong>${p3}`;
  });

  // 12. Negative in X of the last Y years
  out = out.replace(/(negative in\s+\d+\s+of\s+the\s+last\s+\d+\s+years)/gi, '<strong class="c-neg">$1</strong>');

  return out;
}

function createCardHTML(s) {
  const hasFlags = s.red_flags && s.red_flags.length > 0;
  const scoreCls = (!hasFlags && s.composite_score >= 60) ? 'c-pos' : (hasFlags || s.composite_score < 45 ? 'c-neg' : 'c-prime');
  const mos = s.fair_value_mos;
  const mosCls = mos != null ? (mos >= 0.10 ? 'c-pos' : (mos > -0.05 ? 'c-prime' : 'c-neg')) : 'c-muted';
  const fcfCls = s.owner_fcf_yield != null ? (s.owner_fcf_yield >= 0.05 ? 'c-pos' : (s.owner_fcf_yield >= 0.025 ? 'c-prime' : 'c-neg')) : 'c-muted';
  const roicCls = s.roic != null ? (s.roic >= 0.15 ? 'c-pos' : (s.roic >= 0.08 ? 'c-prime' : 'c-neg')) : 'c-muted';
  const shCls = s.share_cagr != null ? (s.share_cagr <= -0.01 ? 'c-pos' : (s.share_cagr <= 0.015 ? 'c-prime' : 'c-neg')) : 'c-muted';
  const pioCls = s.piotroski != null ? (s.piotroski >= 7 ? 'c-pos' : (s.piotroski <= 4 ? 'c-neg' : 'c-prime')) : 'c-muted';
  const gapCls = s.growth_gap != null ? (s.growth_gap >= 0.02 ? 'c-pos' : (s.growth_gap <= -0.03 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const debtCls = s.net_debt_ebitda != null ? (s.net_debt_ebitda <= 1.5 ? 'c-pos' : (s.net_debt_ebitda >= 3.5 ? 'c-neg' : 'c-prime')) : 'c-muted';
  const altzCls = s.altman_z != null ? (s.altman_z >= 2.99 ? 'c-pos' : (s.altman_z < 1.80 ? 'c-neg' : 'c-prime')) : 'c-muted';

  const rdoc = s.research || null;
  let moatTag = '';
  let earnTag = '';
  if (rdoc) {
    const mShort = (rdoc.moat_rating || '').startsWith('WIDE') ? 'Wide Moat' : ((rdoc.moat_rating || '').startsWith('NARROW') ? 'Narrow Moat' : 'Cyclical');
    const mCls = mShort === 'Wide Moat' ? 'tag-green' : (mShort === 'Cyclical' && (s.roic || 0) < 0.08 ? 'tag-red' : '');
    moatTag = `<span class="tag ${mCls}">${mShort}</span>`;
    if (rdoc.earnings_date) {
      const d = rdoc.days_to_earnings;
      const eCls = (d !== null && d >= 0 && d <= 7) ? 'tag-red' : '';
      earnTag = `<span class="tag ${eCls}">Earn ${rdoc.earnings_date}${d !== null && d >= 0 ? ' ('+d+'d)' : ''}</span>`;
    }
  }

  let footerLeft = '';
  let footerRight = 'Inspect Dossier';
  if (rdoc) {
    const tone = verdictTone(s, rdoc);
    footerLeft = `<span class="verdict-text ${tone.textCls}">${rdoc.verdict}</span>`;
    const nSec = (rdoc.sec_filings || []).length;
    const nNews = (rdoc.news_sources || []).length;
    footerRight = `${nSec} Filings · ${nNews} News`;
  } else if (s.red_flags && s.red_flags.length > 0) {
    footerLeft = `<span class="verdict-text c-neg" title="${s.red_flags[0]}">${s.red_flags[0]}</span>`;
    footerRight = 'Audit';
  } else if (s.warnings && s.warnings.length > 0) {
    footerLeft = `<span class="verdict-text c-warn" title="${s.warnings[0]}">${s.warnings[0]}</span>`;
    footerRight = 'Audit';
  } else {
    footerLeft = `<span class="verdict-text c-muted">4-Year 10-K Statement Audit</span>`;
  }

  // Visual 4-pillar fill widths
  const wVal = Math.max(4, ((s.val_score || 0) / 30) * 30);
  const wQual = Math.max(4, ((s.qual_score || 0) / 30) * 30);
  const wSafe = Math.max(4, ((s.safe_score || 0) / 20) * 20);
  const wAlign = Math.max(4, ((s.align_score || 0) / 20) * 20);

  // Visual Economic Health Meter
  const pleasingCount = s.pleasing_count != null ? s.pleasing_count : 0;
  const throwCount = s.throwoff_count != null ? s.throwoff_count : 0;
  const healthMeterWidth = Math.max(12, Math.min(100, (pleasingCount / 6) * 100));
  const healthMeterColor = throwCount > 0 ? '#f87171' : (pleasingCount >= 4 ? '#10b981' : '#e2e8f0');

  const headwindSectors = ['Technology', 'Consumer Cyclical', 'Basic Materials', 'Communication Services'];
  const leadingSectors = ['Energy', 'Financial Services', 'Healthcare'];
  const secRegimeCls = headwindSectors.includes(s.sector) ? 'tag-headwind' : (leadingSectors.includes(s.sector) ? 'tag-leading' : '');
  const secBadge = headwindSectors.includes(s.sector) ? ' · Headwind' : (leadingSectors.includes(s.sector) ? ' · Leading' : '');

  const cFcfY = s.owner_fcf_yield || 0;
  const cConv = s.cash_conversion || 1.0;
  const cRevG = s.rev_cagr || 0;
  const cDivY = s.dividend_yield || 0;
  const cPe = (cFcfY > 0 && cConv > 0) ? (cConv / cFcfY) : null;
  const cIsPegy = cDivY > 0.002;
  const pegyType = cIsPegy ? 'PEGY' : 'PEG';
  const cTotG = cRevG + cDivY;

  let pegyDisp = 'N/A';
  let pegyCls = 'c-muted';

  if (cPe && cTotG > 0.005) {
    const rawVal = cPe / (cTotG * 100);
    pegyDisp = rawVal.toFixed(2);
    pegyCls = rawVal < 1.0 ? 'c-pos' : (rawVal <= 2.0 ? 'c-prime' : 'c-neg');
  } else if (cPe && cTotG <= 0.005) {
    pegyDisp = '<0 Growth';
    pegyCls = 'c-neg';
  }

  return `
    <div class="stock-card ${s.in_basket ? 'in-basket' : ''}" onclick="openModal('${s.ticker}')">
      <div>
        <div class="card-header">
          <div class="id-group">
            <div class="ticker-row">
              <span class="ticker">${s.ticker}</span>
              <span class="sector-tag ${secRegimeCls}">${s.sector}${secBadge}</span>
            </div>
            <div class="company-name" title="${s.company}">${s.company}</div>
          </div>
          <div class="score-box" title="Composite Score: Cash & Yield (${(s.val_score||0).toFixed(0)}/30) + ROIC & Profitability (${(s.qual_score||0).toFixed(0)}/30) + Safety (${(s.safe_score||0).toFixed(0)}/20) + Capital Discipline (${(s.align_score||0).toFixed(0)}/20)">
            <div class="score-num ${scoreCls}">${s.data_ok ? s.composite_score.toFixed(1) : 'N/A'}</div>
            <div class="pillar-mini-bar">
              <div class="pillar-mini-seg" style="width:${wVal}%;background:#10b981;"></div>
              <div class="pillar-mini-seg" style="width:${wQual}%;background:#3b82f6;"></div>
              <div class="pillar-mini-seg" style="width:${wSafe}%;background:#8b5cf6;"></div>
              <div class="pillar-mini-seg" style="width:${wAlign}%;background:#fbbf24;"></div>
            </div>
          </div>
        </div>

        <div class="tag-row">
          ${s.in_basket ? `<span class="tag tag-light">Alloc ${s.position_weight_pct}%</span>` : `<span class="tag">Tier ${s.tier}</span>`}
          ${insiderTagHTML(s)}
          ${moatTag}
          ${earnTag}
          ${s.headline_risk ? `<span class="tag tag-red">Headline Risk</span>` : ''}
        </div>

        <div class="val-box">
          <div class="val-strip">
            <div class="val-cell">
              <div class="k" title="Verified Economic Fortress Signals: real cash generation, compounding ROIC, high asset productivity, share buybacks, fortress balance sheet">Pleasing Signals</div>
              <div class="v c-pos">${pleasingCount} <span class="c-muted">/ 6</span></div>
            </div>
            <div class="val-cell">
              <div class="k" title="Dealbreaker Throw-Offs: cash burn, dilution, excessive debt leverage, margin decay, forensic red flags">Throw-Offs</div>
              <div class="v ${throwCount > 0 ? 'c-neg' : 'c-prime'}">${throwCount} ${throwCount === 1 ? 'Flag' : 'Flags'}</div>
            </div>
            <div class="val-cell">
              <div class="k" title="Owner Free Cash Flow Yield: (Operating Cash Flow - CapEx - Stock-Based Comp) / Market Cap">Cash Yield</div>
              <div class="v ${fcfCls}">${fmtPct(s.owner_fcf_yield, 1)}</div>
            </div>
            <div class="val-cell">
              <div class="k" title="Peter Lynch ${pegyType}: Trailing P/E divided by (3Y Growth + Dividend Yield). Below 1.0 = Undervalued, 1.0-2.0 = Fair Value, Above 2.0 = Expensive">3Y Lynch ${pegyType}</div>
              <div class="v ${pegyCls}">${pegyDisp}</div>
            </div>
          </div>
          <div class="mos-meter-track">
            <div class="mos-meter-fill" style="width:${healthMeterWidth}%;background:${healthMeterColor};"></div>
          </div>
        </div>

        <div class="kv-grid">
          <div class="kv-item"><span class="k" title="Return on Invested Capital: Compounding efficiency of capital (target > 18%)">3Y ROIC</span><span class="v ${roicCls}">${fmtPct(s.roic, 1)}</span></div>
          <div class="kv-item"><span class="k" title="Novy-Marx Gross Profitability: Gross Profit / Total Assets (clean asset productivity, benchmark > 28%)">GP / Assets</span><span class="v ${s.gross_profitability != null && s.gross_profitability >= 0.28 ? 'c-pos' : (s.gross_profitability != null && s.gross_profitability < 0.15 ? 'c-neg' : 'c-prime')}">${s.gross_profitability != null ? fmtPct(s.gross_profitability, 1) : '—'}</span></div>
          <div class="kv-item"><span class="k" title="Piotroski F-Score (0-9): 9 accounting checks testing financial improvement">Piotroski F</span><span class="v ${pioCls}">${s.piotroski != null ? s.piotroski.toFixed(0)+'/9' : '—'}</span></div>
          <div class="kv-item"><span class="k" title="3Y Diluted Share Count CAGR: Negative % means share buybacks; positive % means dilution">3Y Shares</span><span class="v ${shCls}">${fmtPct(s.share_cagr, 1, true)}/yr</span></div>
          <div class="kv-item"><span class="k" title="Net Debt / EBITDA: Number of years of cash earnings needed to repay net debt (Limit < 3.0x)">Net Debt/EBITDA</span><span class="v ${debtCls}">${s.net_debt_ebitda != null ? fmtNum(s.net_debt_ebitda, 1)+'x' : (s.net_debt != null && s.net_debt <= 0 ? 'Net Cash' : '—')}</span></div>
          <div class="kv-item"><span class="k" title="Altman Z-Score: Probability of bankruptcy (Safe > 2.99, Grey 1.80-2.99, Distress < 1.80)">Altman Z</span><span class="v ${altzCls}">${s.altman_z != null ? fmtNum(s.altman_z, 2) : '—'}</span></div>
        </div>
      </div>

      <div class="card-footer">
        ${footerLeft}
        <span class="source-count">${footerRight}</span>
      </div>
    </div>
  `;
}

function createTableHTML(stocks) {
  const rows = stocks.map(s => {
    const mosCls = s.fair_value_mos != null ? (s.fair_value_mos >= 0.15 ? 'c-pos' : (s.fair_value_mos < -0.05 ? 'c-neg' : '')) : '';
    const fcfCls = s.owner_fcf_yield != null ? (s.owner_fcf_yield >= 0.06 ? 'c-pos' : (s.owner_fcf_yield < 0.03 ? 'c-neg' : '')) : '';
    const roicCls = s.roic != null ? (s.roic >= 0.18 ? 'c-pos' : (s.roic < 0.10 ? 'c-neg' : '')) : '';
    const debtCls = s.net_debt_ebitda != null ? (s.net_debt_ebitda <= 1.5 ? 'c-pos' : (s.net_debt_ebitda >= 3.5 ? 'c-neg' : '')) : '';
    const shCls = s.share_cagr != null ? (s.share_cagr <= -0.01 ? 'c-pos' : (s.share_cagr > 0.015 ? 'c-neg' : '')) : '';
    const statusText = s.research ? s.research.verdict : (s.red_flags && s.red_flags.length ? s.red_flags[0] : (s.insider_signal !== 'NEUTRAL' ? s.insider_signal : 'Clean 10-K'));
    const statusCls = s.red_flags && s.red_flags.length ? 'c-neg' : (s.in_basket ? 'c-pos' : 'c-muted');
    const pleasingCnt = s.pleasing_count != null ? s.pleasing_count : 0;
    const throwCnt = s.throwoff_count != null ? s.throwoff_count : 0;

    const tFcfY = s.owner_fcf_yield || 0;
    const tConv = s.cash_conversion || 1.0;
    const tRevG = s.rev_cagr || 0;
    const tDivY = s.dividend_yield || 0;
    const tPe = (tFcfY > 0 && tConv > 0) ? (tConv / tFcfY) : null;
    const tTotG = tRevG + tDivY;
    const tPegyType = s.peg_type || ((tDivY > 0.002) ? 'PEGY' : 'PEG');
    let tPegDisp = s.peg_display || null;
    let tPegCls = s.peg_cls || 'c-muted';
    if (!tPegDisp && tPe) {
      if (tTotG > 0.005) {
        const raw = tPe / (tTotG * 100);
        tPegDisp = raw.toFixed(2);
        tPegCls = raw < 1.0 ? 'c-pos' : (raw <= 2.0 ? 'c-prime' : 'c-neg');
      } else {
        tPegDisp = 'Contraction';
        tPegCls = 'c-neg';
      }
    }

    return `
      <tr onclick="openModal('${s.ticker}')">
        <td class="num c-prime" style="font-weight:600;">${s.ticker}</td>
        <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;">${s.company}</td>
        <td class="c-muted">${s.sector}</td>
        <td class="c-prime" style="font-weight:600;">${s.data_ok ? s.composite_score.toFixed(1) : '—'}</td>
        <td>$${fmtNum(s.price, 2)}</td>
        <td class="${throwCnt > 0 ? 'c-neg' : 'c-pos'}" style="font-weight:600;">${pleasingCnt}/6 Pleasing <span class="c-muted">(${throwCnt} Flags)</span></td>
        <td class="${fcfCls}">${fmtPct(s.owner_fcf_yield, 1)}</td>
        <td class="${tPegCls}" style="font-weight:600;font-family:var(--font-mono);">${tPegDisp ? `${tPegyType} ${tPegDisp}` : '—'}</td>
        <td class="${roicCls}">${fmtPct(s.roic, 1)}</td>
        <td>${s.gross_profitability != null ? fmtPct(s.gross_profitability, 1) : '—'}</td>
        <td class="${debtCls}">${s.net_debt_ebitda != null ? fmtNum(s.net_debt_ebitda, 1)+'x' : (s.net_debt != null && s.net_debt <= 0 ? 'Net Cash' : '—')}</td>
        <td class="${shCls}">${fmtPct(s.share_cagr, 1, true)}/yr</td>
        <td class="${statusCls}" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;">${statusText}</td>
      </tr>
    `;
  }).join('');

  return `
    <div class="data-table-wrap">
      <table class="inst-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Company</th>
            <th>Sector</th>
            <th title="Composite Quant Score (0-100)">Score</th>
            <th>Price</th>
            <th title="Objective Economic Profile: verified pleasing signals vs fatal throw-off flags">Economic Profile</th>
            <th title="Owner Free Cash Flow Yield: (Operating Cash Flow - CapEx - Stock-Based Comp) / Market Cap">Cash Yield</th>
            <th title="Peter Lynch PEG / PEGY: P/E divided by (Growth Rate + Dividend Yield). Below 1.0 = Undervalued, 1.0-2.0 = Fair Value, Above 2.0 = Expensive">3Y PEG / PEGY</th>
            <th title="3-Year Average Return on Invested Capital (compounding power)">3Y ROIC</th>
            <th title="Novy-Marx Gross Profitability: Gross Profit / Total Assets (clean asset productivity)">GP / Assets</th>
            <th title="Net Debt / EBITDA: balance sheet leverage (lower is safer; < 0 = net cash)">Net Debt / EBITDA</th>
            <th title="3Y Diluted Share Count CAGR: negative % means active share retirement (buybacks)">3Y Shares</th>
            <th>Thesis / Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

/* LIVE SCREENER ENGINE MODAL */
function openScannerModal() {
  const savedCount = allStocks.length;
  const currentDbBtn = (savedCount > 0 && savedCount < 480)
    ? `<button class="btn-secondary" id="btn-start-db" onclick="triggerLiveScan('current_db')">Re-Analyze Current Saved List (${savedCount} Stocks)</button>`
    : '';

  const wlButtonsHTML = (watchlists && watchlists.length > 0)
    ? `
      <div class="verdict-panel v-mid" style="margin-bottom:16px;">
        <div class="verdict-headline">2. Analyze a Shared Watchlist Alone</div>
        <div class="verdict-body" style="margin-bottom:12px;">
          <strong>Targeted Watchlist Audit:</strong> Runs the full 4-Year 10-K, Reverse DCF, OpenInsider &amp; SEC EDGAR catalyst audit on <strong>only the companies in your selected watchlist</strong> and updates the shared database.
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          ${watchlists.map(w => (w.tickers && w.tickers.length > 0)
            ? `<button class="btn-primary" onclick="triggerLiveScan('watchlist', ${JSON.stringify(w.tickers).replace(/"/g, '&quot;')}, '${w.name.replace(/'/g, "\\'")}')"><span class="pulse-dot"></span>Analyze "${w.name}" (${w.tickers.length} Stocks)</button>`
            : `<span class="c-muted" style="font-size:11.5px;font-family:var(--font-mono);">${w.name} (0 stocks)</span>`
          ).join('')}
        </div>
      </div>
    `
    : '';

  const fullSectionNum = (watchlists && watchlists.length > 0) ? '3' : '2';

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-top">
      <div>
        <div>
          <span class="modal-ticker">Live Quantitative Screener &amp; Shared Database Engine</span>
        </div>
        <div class="modal-pillars">
          <span>Shared Persistent Database (<strong class="c-prime">${savedCount} Stocks Saved</strong>)</span>
          <span>Parallel 6-Worker Pipeline</span>
          <span>Live OpenInsider &amp; SEC EDGAR Synthesis</span>
        </div>
      </div>
      <button class="close-btn" onclick="closeModal()">Close [ESC]</button>
    </div>

    <div class="verdict-panel v-mid" style="margin-bottom:16px;">
      <div class="verdict-headline">1. Analyze &amp; Add 1 Single Stock (~3 Seconds)</div>
      <div class="verdict-body" style="margin-bottom:12px;">
        <strong>Additive single-stock deep dive:</strong> Audits any US ticker (inside or outside the S&amp;P 500) and <strong>adds it directly to the shared database without resetting the list</strong>. Automatically re-ranks Tiers and Top Basket eligibility.
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
        <input type="text" id="scanner-single-input" placeholder="Enter ticker symbol (e.g. RDDT, SOFI, NVDA)..." onkeydown="if(event.key==='Enter'){const v=this.value.trim();if(v)auditSingleTicker(v);}" style="background:rgba(10,13,19,0.9);border:1px solid var(--border-mid);color:var(--text-primary);font-family:var(--font-mono);font-size:12.5px;padding:8px 14px;border-radius:7px;max-width:320px;width:100%;flex:1;outline:none;box-sizing:border-box;">
        <button class="btn-primary" onclick="const v=document.getElementById('scanner-single-input').value.trim();if(v)auditSingleTicker(v);"><span class="pulse-dot"></span>Analyze &amp; Add Single Stock</button>
      </div>
    </div>

    ${wlButtonsHTML}

    <div class="verdict-panel v-green" id="scan-config-panel">
      <div class="verdict-headline">${fullSectionNum}. Analyze Whole Database (Full S&amp;P 500 + All Added Stocks)</div>
      <div class="verdict-body" style="margin-bottom:14px;">
        <strong>Full universe &amp; custom database audit:</strong> Audits all ~503 S&amp;P 500 companies <strong>plus every custom stock added</strong> to the shared database, updating 4-year 10-K statements, Reverse DCF valuations, OpenInsider signals, and Top Portfolio Basket weights.
      </div>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
        <button class="btn-primary" id="btn-start-full" onclick="triggerLiveScan('full_universe')"><span class="pulse-dot"></span>Analyze Whole Database (~500+ Stocks)</button>
        ${currentDbBtn}
        <span id="scan-server-msg" class="c-muted" style="font-size:11.5px;font-family:var(--font-mono);"></span>
      </div>
    </div>

    <div class="scan-progress-wrap" id="scan-progress-wrap" style="display:none;">
      <div class="scan-bar-header">
        <div>
          <span class="scan-pct" id="scan-pct">0%</span>
          <span class="scan-stage-label" id="scan-stage-label" style="margin-left:12px;">Initializing pipeline...</span>
        </div>
        <div class="num c-muted" id="scan-eta-label" style="font-size:12px;">0 / 0</div>
      </div>

      <div class="scan-track">
        <div class="scan-fill" id="scan-fill"></div>
      </div>

      <div class="verdict-meta-grid" style="margin-top:0;margin-bottom:14px;padding-top:4px;border-top:none;">
        <div><span class="k">Audited Securities</span><span class="v" id="sc-done">0 / 0</span></div>
        <div><span class="k">Clean 10-K Passed</span><span class="v c-pos" id="sc-clean">0</span></div>
        <div><span class="k">Hard Red Flagged</span><span class="v c-neg" id="sc-flagged">0</span></div>
        <div><span class="k">Net Insider Buys</span><span class="v c-prime" id="sc-insider">0</span></div>
      </div>

      <div class="m-heading" style="margin-bottom:8px;">Live Audit Stream</div>
      <div class="scan-log-feed" id="scan-log-feed"></div>
    </div>
  `;
  document.getElementById('modal-backdrop').style.display = 'flex';
  checkActiveScanStatus();
}

async function checkActiveScanStatus() {
  try {
    const res = await fetch('/api/scan/status');
    if (!res.ok) return;
    const st = await res.json();
    if (st.running) {
      document.getElementById('scan-progress-wrap').style.display = 'block';
      const bf = document.getElementById('btn-start-full');
      const bd = document.getElementById('btn-start-db');
      if (bf) bf.disabled = true;
      if (bd) bd.disabled = true;
      startPollingScan();
    }
  } catch (err) {
    const msg = document.getElementById('scan-server-msg');
    if (msg) {
      msg.innerHTML = 'Static file mode active &mdash; double-click <strong>launch_app.bat</strong> to enable in-app live scanning.';
    }
  }
}

async function triggerLiveScan(mode, customTickers=null, wlName=null) {
  const msg = document.getElementById('scan-server-msg');
  try {
    const bodyObj = { max_stocks: null, mode: mode || 'full_universe' };
    if (Array.isArray(customTickers) && customTickers.length > 0) {
      bodyObj.custom_tickers = customTickers;
    }
    const res = await fetch('/api/scan/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyObj)
    });
    if (!res.ok) throw new Error('Server error');
    const wrap = document.getElementById('scan-progress-wrap');
    if (wrap) {
      wrap.style.display = 'block';
      wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (wlName) {
      const lbl = document.getElementById('scan-stage-label');
      if (lbl) lbl.textContent = `Auditing Watchlist "${wlName}" (${customTickers.length} stocks)...`;
    }
    const bf = document.getElementById('btn-start-full');
    const bd = document.getElementById('btn-start-db');
    if (bf) bf.disabled = true;
    if (bd) bd.disabled = true;
    if (msg) msg.textContent = '';
    startPollingScan();
  } catch (err) {
    if (msg) {
      msg.className = 'c-warn';
      msg.innerHTML = 'To run live scans from the UI, open the app via <strong>launch_app.bat</strong> (starts the local Python engine).';
    }
  }
}

function startPollingScan() {
  if (scanPollTimer) clearInterval(scanPollTimer);
  scanPollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/scan/status');
      if (!res.ok) return;
      const st = await res.json();
      const wrap = document.getElementById('scan-progress-wrap');
      if (!wrap) {
        clearInterval(scanPollTimer);
        return;
      }
      const pct = st.total > 0 ? Math.min(100, Math.round((st.completed / st.total) * 100)) : 0;
      document.getElementById('scan-pct').textContent = pct + '%';
      document.getElementById('scan-fill').style.width = pct + '%';
      document.getElementById('scan-stage-label').textContent =
        st.stage === 'researching'
          ? 'Synthesizing SEC EDGAR 10-K/10-Q filings & news catalysts...'
          : (st.stage === 'done' ? 'Scan complete! Updating shared database...' : `Auditing ${st.ticker || ''}...`);
      document.getElementById('scan-eta-label').textContent = `Elapsed: ${st.elapsed_sec || 0}s`;
      document.getElementById('sc-done').textContent = `${st.completed} / ${st.total}`;
      document.getElementById('sc-clean').textContent = st.clean_count || 0;
      document.getElementById('sc-flagged').textContent = st.flagged_count || 0;
      document.getElementById('sc-insider').textContent = st.insider_count || 0;

      const feed = document.getElementById('scan-log-feed');
      if (feed && st.recent_logs) {
        feed.innerHTML = st.recent_logs.map(l => `<div>${l}</div>`).join('');
        feed.scrollTop = feed.scrollHeight;
      }

      if (!st.running && st.stage === 'done') {
        clearInterval(scanPollTimer);
        scanPollTimer = null;
        const pRes = await fetch('/api/payload');
        if (pRes.ok) {
          PAYLOAD = await pRes.json();
          allStocks = PAYLOAD.stocks || [];
          cohorts = PAYLOAD.cohorts || [];
          if (Array.isArray(PAYLOAD.watchlists)) {
            watchlists = PAYLOAD.watchlists;
          }
          populateSectorFilter();
          renderTracker();
          render();
          setTimeout(() => closeModal(), 900);
        }
      }
    } catch (e) {
      clearInterval(scanPollTimer);
    }
  }, 600);
}

function openInfoModal() {
  document.getElementById('modal-content').innerHTML = `
    <div class="modal-top">
      <div>
        <div>
          <span class="modal-ticker">System Methodology &amp; Quantitative Architecture</span>
        </div>
        <div class="modal-pillars">
          <span>S&amp;P 500 Universe</span>
          <span>4-Year 10-K Statement Audit</span>
          <span>Forensic Accounting Guards</span>
          <span>Reverse DCF</span>
          <span>OpenInsider 12M Ledger</span>
        </div>
      </div>
      <button class="close-btn" onclick="closeModal()">Close [ESC]</button>
    </div>

    <div class="verdict-panel">
      <div class="verdict-headline">Core Investment Philosophy</div>
      <div class="verdict-body" style="display:flex;flex-direction:column;gap:8px;">
        <div><strong>Single-day valuation ratios fail:</strong> Trailing P/E and PEG ratios mask equity dilution, debt burdens, and one-off accounting distortions.</div>
        <div><strong>4-Year statement trends reveal durability:</strong> We audit 10-Ks across 3 to 4 years to track cash flow consistency, ROIC, and share count changes.</div>
        <div><strong>Deduct stock-based compensation:</strong> Reported Free Cash Flow hides heavy option dilution. Owner FCF (FCF minus Stock-Based Comp) measures real cash generated for shareholders.</div>
        <div><strong>Reverse DCF measures market expectations:</strong> Solves for the exact 10-year growth rate baked into today's price to find asymmetric mispricings.</div>
        <div><strong>Verify genuine insider skin-in-the-game:</strong> Tracks 12 months of OpenInsider open-market transactions, exposing fake token buys surrounded by C-suite dumping.</div>
      </div>
    </div>

    <div class="m-section">
      <div class="m-heading">1. The 4-Pillar Composite Scoring Engine (0 – 100 Points)</div>
      <div class="doc-grid">
        <div class="doc-card">
          <h4>Pillar I: Valuation &amp; Expectations (30 Pts)</h4>
          <div class="bullet-point"><strong>Owner FCF Yield (0–12 pts):</strong> Rewards companies generating 5% to 9%+ of their market cap in cash every year.</div>
          <div class="bullet-point"><strong>Probabilistic DCF Margin of Safety (0–8 pts):</strong> Measures discount to Base DCF fair value with Arturo Cifuentes confidence bands (Bear to Bull).</div>
          <div class="bullet-point"><strong>Mauboussin Expectations Gap (0–10 pts):</strong> Rewards setups where the market prices in low or negative growth while fundamentals compound faster.</div>
        </div>
        <div class="doc-card">
          <h4>Pillar II: Economic Profitability &amp; Quality (30 Pts)</h4>
          <div class="bullet-point"><strong>Economic ROIC (0–10 pts):</strong> Capital compounding efficiency (&ge;15% ROIC) creating positive spread over 9% WACC cost of capital.</div>
          <div class="bullet-point"><strong>Novy-Marx Gross Profitability (0–8 pts):</strong> Gross Profit / Total Assets (JFE 2013) measures clean asset productivity and moats.</div>
          <div class="bullet-point"><strong>Ball Cash Operating Profitability (0–6 pts):</strong> Operating Cash Flow / Assets (JFE 2016) strips non-cash accrual pollution.</div>
          <div class="bullet-point"><strong>Piotroski F-Score (0–6 pts):</strong> 9 strict accounting tests across profitability, liquidity, and operational efficiency.</div>
        </div>
        <div class="doc-card">
          <h4>Pillar III: Financial Safety &amp; Forensics (20 Pts)</h4>
          <div class="bullet-point"><strong>Low Debt Leverage (0–8 pts):</strong> Net Debt / EBITDA under 2.5x ensures the business easily survives recessions and high interest rates.</div>
          <div class="bullet-point"><strong>Altman Z-Score (0–6 pts):</strong> Distance from bankruptcy (Safe &gt; 2.99; distress line is 1.80).</div>
          <div class="bullet-point"><strong>Beneish M-Score (0–6 pts):</strong> Flags aggressive accruals and earnings manipulation (M-Score &gt; -1.78 incurs penalty).</div>
        </div>
        <div class="doc-card">
          <h4>Pillar IV: Capital Discipline &amp; Alignment (20 Pts)</h4>
          <div class="bullet-point"><strong>Share Count Reduction (0–6 pts):</strong> Rewards aggressive buybacks retiring &ge;2.5% of outstanding float per year.</div>
          <div class="bullet-point"><strong>Hou-Xue-Zhang Asset Growth (0–6 pts):</strong> Rewards conservative balance sheet growth (&le;10%/yr; RFS 2015) and penalizes empire-building.</div>
          <div class="bullet-point"><strong>Cash Conversion Ratio (0–4 pts):</strong> Verifies that Owner FCF consistently matches or exceeds reported Net Income.</div>
          <div class="bullet-point"><strong>OpenInsider Cluster Buying (up to +4 pts):</strong> Net open-market purchases by multiple corporate executives.</div>
        </div>
      </div>
    </div>

    <div class="m-section">
      <div class="m-heading">2. Hard Disqualification Gates (Tier D Exclusions — Score Capped at 39.0)</div>
      <ul class="clean-list">
        <li><span><strong>Negative Owner Cash Flow:</strong> Disqualified if FCF minus Stock-Based Compensation was negative last year or in 2 of the past 3 years.</span></li>
        <li><span><strong>Excessive Debt Burden:</strong> Disqualified if Net Debt / EBITDA exceeds 4.0x or Interest Coverage (EBIT / Interest) is below 2.0x.</span></li>
        <li><span><strong>Bankruptcy Distress Zone:</strong> Disqualified if Altman Z-Score is below 1.80 for non-financials.</span></li>
        <li><span><strong>Structural Business Contraction:</strong> Disqualified if both 3-year revenue and operating income are shrinking &gt; 2.5%/yr.</span></li>
        <li><span><strong>Shareholder Dilution:</strong> Disqualified if diluted share count expands &gt; 2.5%/yr from excessive stock issuance.</span></li>
        <li><span><strong>Incomplete or Non-USD Statements:</strong> Placed into Unrated (Tier U) &mdash; missing data is never automatically passed.</span></li>
        <li><span class="c-muted"><em>Note: Forward EPS consensus drops are treated as scored operational warnings (Valuation penalty) rather than forensic disqualifications, preventing false alarms from GAAP one-offs or market cycle shifts.</em></span></li>
      </ul>
    </div>

    <div class="m-section">
      <div class="m-heading">3. OpenInsider: Real Conviction vs. The Lone-Buy Trap</div>
      <div class="doc-grid">
        <div class="doc-card">
          <h4>Genuine Conviction (Cluster &amp; C-Suite Buys)</h4>
          <div class="bullet-point"><strong>Open-market cash purchases only (P - Purchase):</strong> We ignore automatic option exercises, stock grants, and corporate buybacks.</div>
          <div class="bullet-point"><strong>Cluster Buys require multiple buyers:</strong> 3+ distinct insiders purchasing &ge;$150k total with &ge;60% buy-to-sell dollar ratio.</div>
          <div class="bullet-point"><strong>No selling after the buy:</strong> Confirms leadership is aligned and not front-running upcoming negative reports.</div>
        </div>
        <div class="doc-card">
          <h4>The "Lone Buy Surrounded by Sells" Trap</h4>
          <div class="bullet-point"><strong>One lone buy does not offset heavy selling:</strong> A $200k purchase by a director does not make up for $10M+ in executive dumping.</div>
          <div class="bullet-point"><strong>Chronological order check:</strong> Flags stocks where a token purchase was followed by consecutive executive sales.</div>
          <div class="bullet-point"><strong>Stake liquidation (% &Delta;Own):</strong> Penalizes companies where senior executives cut 25% to 75% of their personal shareholdings.</div>
        </div>
      </div>
    </div>

    <div class="m-section">
      <div class="m-heading">4. Moskowitz &amp; Grinblatt (1999) Sector Momentum &amp; Capital Rotation</div>
      <div class="verdict-panel" style="margin-bottom:12px;">
        <div class="verdict-headline" style="font-size:14px;">Why Individual Stock Quality Fails Inside Out-of-Favor Sectors</div>
        <div class="verdict-body" style="font-size:12.5px;color:var(--text-secondary);line-height:1.6;">
          Academic research by Moskowitz &amp; Grinblatt (<em>Journal of Finance</em>, 1999) titled <em>"Do Industries Explain Momentum?"</em> established that industry-level momentum accounts for the vast majority of individual stock price momentum. When institutional asset managers rotate out of a sector, correlated outflows create persistent selling pressure across all constituent stocks—even those with immaculate balance sheets.
        </div>
      </div>
      <div class="doc-grid">
        <div class="doc-card">
          <h4>Sector Momentum Regimes</h4>
          <div class="bullet-point"><strong>HEADWIND (Correction &gt; 18% avg DD):</strong> Sectors where constituent stocks face pervasive institutional liquidation (e.g. Technology, Consumer Cyclical). Value multiple compression persists longer than expected.</div>
          <div class="bullet-point"><strong>NEUTRAL (12% to 18% avg DD):</strong> Sectors tracking broader market indexes with balanced institutional capital flow.</div>
          <div class="bullet-point"><strong>LEADING (Drawdown &lt; 12%):</strong> Sectors demonstrating strong relative strength and institutional capital accumulation (e.g. Energy, Financial Services).</div>
        </div>
        <div class="doc-card">
          <h4>Portfolio Protection Rules</h4>
          <div class="bullet-point"><strong>Avoid the "Cheap Tech" Trap:</strong> Never buy a stock purely because its P/E fell if the broader sector has &gt;40% of its members in correction territory.</div>
          <div class="bullet-point"><strong>Sector Max Capped at 3 Positions:</strong> The 15-stock Top Basket strictly limits exposure to 3 stocks per sector (maximum 20% sector allocation) to guarantee resilience against sector-specific drawdowns.</div>
          <div class="bullet-point"><strong>Macro Trend Alignment:</strong> Prioritize high-quality companies operating in leading or neutral sectors before catching falling knives in headwind sectors.</div>
        </div>
      </div>
    </div>

    <div class="m-section">
      <div class="m-heading">5. Portfolio Construction &amp; 2-Tranche Execution Protocol</div>
      <ul class="clean-list">
        <li><span><strong>Diversified Top Basket (Max 15 positions, Max 3/Sector):</strong> Enforces strict sector diversification and equal weighting (~6.7% to 8.3% each) so no single sector or stock dominates.</span></li>
        <li><span><strong>Mandatory Earnings Gate:</strong> If earnings report is within 7 days, the verdict automatically switches to <strong>WAIT FOR EARNINGS</strong> to prevent gambling on binary quarterly prints.</span></li>
        <li><span><strong>2-Tranche Entry Strategy:</strong> For deep-value stocks down &ge;35%, deploy Tranche 1 (50% size) now, and add Tranche 2 (50% size) only after post-earnings stability.</span></li>
        <li><span><strong>Out-of-Sample Forward Tracking:</strong> Every basket cohort is permanently recorded in <code>picks_history.json</code> and benchmarked live against the S&amp;P 500 (<code>SPY</code>).</span></li>
      </ul>
    </div>

    <div class="m-section">
      <div class="m-heading">6. Financial Glossary &amp; Core Metric Formulas</div>
      <div class="doc-grid">
        <div class="doc-card">
          <h4>ROIC &mdash; Return on Invested Capital</h4>
          <div class="formula-display">
            <span class="f-name">ROIC</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">NOPAT</span>
              <span class="f-den">Invested Capital</span>
            </div>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">EBIT &times; (1 &minus; <span class="f-var">t</span>)</span>
              <span class="f-den">Total Debt + Equity &minus; Cash</span>
            </div>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> Measures how efficiently a company allocates capital to generate net operating profit.</div>
          <div class="bullet-point"><strong>Why it matters:</strong> Consistent ROIC &ge; 15% proves the company has an economic moat that competitors cannot duplicate. When ROIC is below the cost of capital (~9%), business growth destroys shareholder value.</div>
        </div>

        <div class="doc-card">
          <h4>Owner FCF &amp; FCF Yield &mdash; Real Shareholder Cash</h4>
          <div class="formula-display">
            <span class="f-name">Owner FCF</span>
            <span class="f-eq">=</span>
            <span>Operating Cash Flow &minus; CapEx &minus; Stock-Based Comp</span>
          </div>
          <div class="formula-display">
            <span class="f-name">Owner FCF Yield</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">Owner Free Cash Flow</span>
              <span class="f-den">Market Capitalization</span>
            </div>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> The actual cash an owner could pocket every year without shrinking the business.</div>
          <div class="bullet-point"><strong>Why standard FCF is flawed:</strong> Companies frequently report positive Free Cash Flow by paying executives billions in stock options instead of cash. Deducting SBC treats dilution as a real expense.</div>
        </div>

        <div class="doc-card">
          <h4>Peter Lynch PEG &amp; PEGY &mdash; Valuation vs. Compounding Trajectory</h4>
          <div class="formula-display">
            <span class="f-name">PEG</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">Trailing P/E</span>
              <span class="f-den">3Y Revenue Growth Rate (%)</span>
            </div>
          </div>
          <div class="formula-display">
            <span class="f-name">PEGY</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">Trailing P/E</span>
              <span class="f-den">Growth Rate (%) + Dividend Yield (%)</span>
            </div>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> Popularized by legendary investor Peter Lynch (<em>One Up on Wall Street</em>). Measures how much you pay per 1% of growth and shareholder cash yield.</div>
          <div class="bullet-point"><strong>Peter Lynch Benchmarks:</strong> <strong>Below 1.0</strong> indicates a high-growth bargain where fundamentals outgrow the price multiple; <strong>1.0 to 2.0</strong> is fair value; <strong>Above 2.0</strong> indicates an expensive multiple vulnerable to severe valuation compressions if growth slows down.</div>
          <div class="bullet-point"><strong>Why PEGY for Dividend Payers:</strong> For cash-distributing businesses, capital returned to owners as cash dividends is added to top-line growth to measure Total Shareholder Return.</div>
        </div>

        <div class="doc-card">
          <h4>DCF &amp; Reverse DCF &mdash; Valuation Expectations</h4>
          <div class="formula-display">
            <span class="f-name">Stock Price</span>
            <span class="f-eq">=</span>
            <span>&sum;</span>
            <div class="f-frac">
              <span class="f-num">FCF<sub>0</sub> &times; (1 + <span class="f-var">g</span><sub>implied</sub>)<span class="f-sup">t</span></span>
              <span class="f-den">(1 + <span class="f-var">r</span>)<span class="f-sup">t</span></span>
            </div>
            <span>+</span>
            <div class="f-frac">
              <span class="f-num">Terminal Value</span>
              <span class="f-den">(1 + <span class="f-var">r</span>)<span class="f-sup">10</span></span>
            </div>
          </div>
          <div class="formula-display">
            <span class="f-name">DCF Margin of Safety</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">DCF Fair Value &minus; Current Price</span>
              <span class="f-den">Current Price</span>
            </div>
          </div>
          <div class="bullet-point"><strong>Reverse DCF (The core engine metric):</strong> Instead of guessing the future, it solves backwards for the exact annual growth rate the market price implies.</div>
          <div class="bullet-point"><strong>Why it finds bargains:</strong> If the market prices in a <code>-2.2%/yr permanent contraction</code> for a company whose revenue is growing at <code>+5.3%/yr</code>, the stock has an asymmetric margin of safety.</div>
        </div>

        <div class="doc-card">
          <h4>Piotroski F-Score (0 – 9 Scale) &mdash; Fundamental Health</h4>
          <div class="formula-display">
            <span class="f-name">F-Score</span>
            <span class="f-eq">=</span>
            <span>&sum;<span class="f-sub">i=1..9</span> Test<sub><span class="f-var">i</span></sub> &isin; {0, 1}</span>
            <span class="f-eq">&rArr;</span>
            <span style="font-size:11px;color:var(--text-secondary);">4 Profitability + 3 Leverage + 2 Efficiency</span>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> A 9-point accounting checklist designed by Stanford Professor Joseph Piotroski to separate winning value stocks from value traps.</div>
          <div class="bullet-point"><strong>Score interpretation:</strong> <strong>7 to 9</strong> indicates robust, improving fundamental health. <strong>Below 4</strong> indicates deteriorating operations.</div>
        </div>

        <div class="doc-card">
          <h4>Altman Z-Score &mdash; Bankruptcy Distance</h4>
          <div class="formula-display">
            <span class="f-name">Z-Score</span>
            <span class="f-eq">=</span>
            <span>1.2&middot;<span class="f-var">X</span><sub>1</sub> + 1.4&middot;<span class="f-var">X</span><sub>2</sub> + 3.3&middot;<span class="f-var">X</span><sub>3</sub> + 0.6&middot;<span class="f-var">X</span><sub>4</sub> + 0.999&middot;<span class="f-var">X</span><sub>5</sub></span>
          </div>
          <div style="font-size:10.5px;color:var(--text-muted);font-family:var(--font-mono);margin-bottom:8px;line-height:1.4;">
            <span class="f-var">X</span><sub>1</sub> = Working Capital/Assets &bull; <span class="f-var">X</span><sub>2</sub> = Retained Earnings/Assets &bull; <span class="f-var">X</span><sub>3</sub> = EBIT/Assets &bull; <span class="f-var">X</span><sub>4</sub> = Market Cap/Liabilities &bull; <span class="f-var">X</span><sub>5</sub> = Sales/Assets
          </div>
          <div class="bullet-point"><strong>The Thresholds:</strong> <strong>Z &gt; 2.99</strong> is the Safe Zone. <strong>1.80 to 2.99</strong> is the Grey Caution Zone. <strong>Z &lt; 1.80</strong> is the Distress Zone (triggers automatic disqualification in our terminal).</div>
        </div>

        <div class="doc-card">
          <h4>Beneish M-Score &mdash; Forensic Accounting / Fraud Guard</h4>
          <div class="formula-display">
            <span class="f-name">M-Score</span>
            <span class="f-eq">=</span>
            <span>&minus;4.84 + 0.92&middot;DSRI + 0.528&middot;GMI + 0.404&middot;AQI + 0.892&middot;SGI + 0.115&middot;DEPI &minus; 0.172&middot;SGAI + 4.679&middot;TATA &minus; 0.327&middot;LVGI</span>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> A mathematical model created by Professor Messod Beneish using 8 financial ratios to detect earnings manipulation before the SEC catches it.</div>
          <div class="bullet-point"><strong>The Threshold:</strong> A score <strong>more negative than -1.78</strong> (e.g. -2.88) indicates pristine, honest accounting. A score <strong>greater than -1.78</strong> (e.g. -1.10) indicates high probability of manipulated earnings.</div>
        </div>

        <div class="doc-card">
          <h4>Net Debt / EBITDA &mdash; Solvency &amp; Leverage</h4>
          <div class="formula-display">
            <span class="f-name">Net Debt / EBITDA</span>
            <span class="f-eq">=</span>
            <div class="f-frac">
              <span class="f-num">Total Debt &minus; Cash &amp; Equivalents</span>
              <span class="f-den">EBITDA</span>
            </div>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> Measures how many years of cash operating earnings it would take to pay off all debt.</div>
          <div class="bullet-point"><strong>Thresholds:</strong> <strong>Below 0.0x</strong> means net cash (cash exceeds all debt). <strong>Under 2.5x</strong> is conservative. <strong>Above 4.0x</strong> is dangerous debt and triggers automatic disqualification.</div>
        </div>

        <div class="doc-card">
          <h4>CAGR &mdash; Compound Annual Growth Rate</h4>
          <div class="formula-display">
            <span class="f-name">CAGR</span>
            <span class="f-eq">=</span>
            <span>(</span>
            <div class="f-frac">
              <span class="f-num">Ending Value</span>
              <span class="f-den">Beginning Value</span>
            </div>
            <span>)<span class="f-sup">1 / <span class="f-var">n</span></span> &minus; 1</span>
          </div>
          <div class="bullet-point"><strong>What it is:</strong> The annualized geometric growth rate over a 3 or 4 year multi-year window, smoothing out single-year volatility.</div>
          <div class="bullet-point"><strong>Share Count CAGR:</strong> Negative % means aggressive share buybacks (increasing your ownership stake); positive % means shareholder dilution.</div>
        </div>
      </div>
    </div>
  `;
  document.getElementById('modal-backdrop').style.display = 'flex';
}

function openModal(ticker) {
  const s = allStocks.find(x => x.ticker === ticker);
  if (!s) return;
  const t = s.trends || {};
  const yrs = t.years || [];
  const rdoc = s.research || null;
  const hasFlags = s.red_flags && s.red_flags.length > 0;

  let researchHTML = '';
  if (rdoc) {
    const tone = verdictTone(s, rdoc);
    const bullItems = (rdoc.bull_thesis || []).map(b => `<li>${colorizeDesc(b, s)}</li>`).join('');
    const secLinks = (rdoc.sec_filings || []).map(f => `
      <li>
        <a href="${f.url}" target="_blank" rel="noopener">[${f.form}] ${f.title}</a>
        <span class="num c-muted" style="font-size:11px;">Filed ${f.date} &nearr;</span>
      </li>
    `).join('');

    const secEtf = sectorETFs[s.sector] || '';
    let links = [...(rdoc.external_links || [])];
    if (!links.some(l => (l.label || '').includes('TradingView') && !(l.label || '').includes('Sector'))) {
      links.unshift({
        label: `${s.ticker} on TradingView Chart`,
        url: `https://www.tradingview.com/chart/?symbol=${s.ticker}`
      });
    }
    if (secEtf && !links.some(l => (l.label || '').includes(secEtf))) {
      links.splice(1, 0, {
        label: `${secEtf} Sector ETF on TradingView (${s.sector})`,
        url: `https://www.tradingview.com/chart/?symbol=AMEX%3A${secEtf}`
      });
    }

    const extLinks = links.map(l => `
      <a href="${l.url}" target="_blank" rel="noopener" class="portal-btn">${l.label} &nearr;</a>
    `).join('');
    const newsLinks = (rdoc.news_sources || []).length
      ? rdoc.news_sources.map(n => `
          <li>
            <a href="${n.url}" target="_blank" rel="noopener">${n.title}</a>
            <span class="c-muted" style="font-size:11px;white-space:nowrap;">${n.publisher} · ${n.date} &nearr;</span>
          </li>
        `).join('')
      : '<li><span class="c-muted">No recent news items returned.</span></li>';
    const analystHTML = (rdoc.analyst_actions && rdoc.analyst_actions.length)
      ? `<div style="margin-top:10px;font-size:11.5px;color:var(--text-muted);font-family:var(--font-mono);">Recent Institutional Ratings: ${rdoc.analyst_actions.join('  /  ')}</div>`
      : '';

    const moatCls = (rdoc.moat_rating || '').startsWith('WIDE') ? 'c-pos' : ((rdoc.moat_rating || '').startsWith('NARROW') ? 'c-prime' : ((s.roic || 0) < 0.08 ? 'c-neg' : 'c-prime'));
    const dEarn = rdoc.days_to_earnings;
    const earnCls = (dEarn !== null && dEarn !== undefined) ? (dEarn >= 0 && dEarn <= 7 ? 'c-neg' : (dEarn > 14 ? 'c-pos' : 'c-prime')) : 'c-prime';
    const sfNum = rdoc.short_float ? parseFloat(rdoc.short_float) : null;
    const sfCls = (sfNum !== null && !isNaN(sfNum)) ? (sfNum > 8.0 ? 'c-neg' : (sfNum < 3.0 ? 'c-pos' : 'c-prime')) : 'c-prime';
    const ioNum = rdoc.inst_own ? parseFloat(rdoc.inst_own) : null;
    const ioCls = (ioNum !== null && !isNaN(ioNum)) ? (ioNum >= 65.0 ? 'c-pos' : (ioNum < 30.0 ? 'c-neg' : 'c-prime')) : 'c-prime';

    researchHTML = `
      <div class="verdict-panel ${tone.panelCls}">
        <div class="verdict-headline">${rdoc.verdict}</div>
        <div class="verdict-body">${colorizeDesc(rdoc.action_plan, s)}</div>
        <div class="verdict-meta-grid">
          <div><span class="k">Moat Classification</span><span class="v ${moatCls}">${rdoc.moat_rating}</span></div>
          <div><span class="k">Next Earnings Release</span><span class="v ${earnCls}">${rdoc.earnings_date || 'Unscheduled'} ${rdoc.days_to_earnings != null ? '('+rdoc.days_to_earnings+'d)' : ''}</span></div>
          <div><span class="k">Short Interest Float</span><span class="v ${sfCls}">${rdoc.short_float || 'N/A'}</span></div>
          <div><span class="k">Institutional Ownership</span><span class="v ${ioCls}">${rdoc.inst_own || 'N/A'}</span></div>
        </div>
        <div style="font-size:12px;color:var(--text-secondary);margin-top:12px;">${colorizeDesc(rdoc.moat_desc, s)}</div>
        ${rdoc.business_summary ? `<div style="font-size:12px;color:var(--text-muted);margin-top:8px;padding-top:8px;border-top:1px solid var(--border-dim);">${rdoc.business_summary}</div>` : ''}
      </div>

      <div class="m-section">
        <div class="m-heading">Market Pricing Narrative vs. Quantitative Counter-Thesis</div>
        <div class="thesis-grid">
          <div class="thesis-box bear">
            <div class="thesis-title c-neg">Market Concern (Priced-In Bear Case)</div>
            <div style="color:var(--text-secondary);line-height:1.55;">${colorizeDesc(rdoc.bear_narrative || 'No structural bear discount identified; trading near consensus growth trajectory.', s)}</div>
          </div>
          <div class="thesis-box bull">
            <div class="thesis-title c-pos">Audited Quantitative &amp; Insider Counter-Thesis</div>
            <ul class="thesis-list">${bullItems}</ul>
          </div>
        </div>
        ${analystHTML}
      </div>

      <div class="m-section">
        <div class="m-heading">Official SEC EDGAR Filings &amp; Direct Research Portals</div>
        <div class="portal-links">${extLinks}</div>
        <ul class="clean-list">${secLinks}</ul>
      </div>

      <div class="m-section">
        <div class="m-heading">Recent News &amp; Catalyst Sources</div>
        <ul class="clean-list">${newsLinks}</ul>
      </div>
    `;
  } else {
    const emptyTone = hasFlags ? 'v-red' : 'v-mid';
    const secEtf = sectorETFs[s.sector] || '';
    researchHTML = `
      <div class="verdict-panel ${emptyTone}" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">
        <div>
          <div class="verdict-headline">On-Demand SEC EDGAR &amp; Catalyst Research Dossier</div>
          <div class="verdict-body">Run a 3-second live deep audit on <strong>${s.ticker}</strong> to synthesize SEC 10-K/10-Q links, Finviz short interest, 12-month OpenInsider transactions, and the Bear-vs-Bull verdict.</div>
        </div>
        <button class="btn-primary" onclick="auditSingleTicker('${s.ticker}')"><span class="pulse-dot"></span>Run Live Deep Audit on ${s.ticker}</button>
      </div>
      <div class="m-section">
        <div class="m-heading">Official SEC EDGAR Filings &amp; Direct Research Portals</div>
        <div class="portal-links">
          <a href="https://www.tradingview.com/chart/?symbol=${s.ticker}" target="_blank" rel="noopener" class="portal-btn">${s.ticker} on TradingView Chart &nearr;</a>
          ${secEtf ? `<a href="https://www.tradingview.com/chart/?symbol=AMEX%3A${secEtf}" target="_blank" rel="noopener" class="portal-btn">${secEtf} Sector ETF on TradingView (${s.sector}) &nearr;</a>` : ''}
          <a href="http://openinsider.com/screener?s=${s.ticker}&fd=365" target="_blank" rel="noopener" class="portal-btn">${s.ticker} on OpenInsider.com &nearr;</a>
          <a href="https://www.sec.gov/edgar/searchedgar/companysearch?cik=${s.ticker}" target="_blank" rel="noopener" class="portal-btn">${s.ticker} SEC EDGAR Filings &nearr;</a>
          <a href="https://finance.yahoo.com/quote/${s.ticker}/financials/" target="_blank" rel="noopener" class="portal-btn">${s.ticker} Yahoo Finance &nearr;</a>
          <a href="https://finviz.com/quote.ashx?t=${s.ticker}" target="_blank" rel="noopener" class="portal-btn">${s.ticker} Finviz Chart &nearr;</a>
        </div>
      </div>
    `;
  }

  const mFcfY = s.owner_fcf_yield || 0;
  const mConv = s.cash_conversion || 1.0;
  const mRevG = s.rev_cagr || 0;
  const mDivY = s.dividend_yield || 0;
  const mPe = (mFcfY > 0 && mConv > 0) ? (mConv / mFcfY) : null;
  const mIsPegy = mDivY > 0.002;
  const pegyType = mIsPegy ? 'PEGY' : 'PEG';
  const mTotG = mRevG + mDivY;

  let pegyDisp = 'N/A';
  let pegyRating = 'N/A';
  let pegyCls = 'c-muted';

  if (!mPe) {
    pegyDisp = 'N/A';
    pegyRating = 'Negative Cash Flow';
    pegyCls = 'c-muted';
  } else if (mTotG <= 0.005) {
    pegyDisp = 'Contraction';
    pegyRating = 'Negative Growth';
    pegyCls = 'c-neg';
  } else {
    const rawVal = mPe / (mTotG * 100);
    pegyDisp = rawVal.toFixed(2);
    if (rawVal < 1.0) {
      pegyRating = 'Undervalued < 1.0';
      pegyCls = 'c-pos';
    } else if (rawVal <= 2.0) {
      pegyRating = 'Fair Value 1.0–2.0';
      pegyCls = 'c-prime';
    } else {
      pegyRating = 'Expensive > 2.0';
      pegyCls = 'c-neg';
    }
  }

  const revs = t.revenue || [];

  const revGrowthCells = revs.map((currR, idx) => {
    if (idx === 0) return { txt: '— (Base)', cls: 'c-muted' };
    const prevR = revs[idx - 1];
    const rg = (prevR && prevR > 0) ? ((currR - prevR) / prevR) : 0;
    const cls = rg >= 0.10 ? 'c-pos' : (rg >= 0.02 ? 'c-prime' : 'c-neg');
    return { txt: (rg >= 0 ? '+' : '') + (rg * 100).toFixed(1) + '%', cls: cls };
  });

  const pegRowCells = revs.map((currR, idx) => {
    if (idx === 0) return { txt: '— (Base)', cls: 'c-muted' };
    const prevR = revs[idx - 1];
    const rg = (prevR && prevR > 0) ? ((currR - prevR) / prevR) : 0;
    const totG = rg + mDivY;
    if (!mPe) {
      return { txt: 'N/A', cls: 'c-muted' };
    }
    if (totG <= 0.005) {
      return { txt: 'Contraction', cls: 'c-neg' };
    }
    const val = mPe / (totG * 100);
    const cls = val < 1.0 ? 'c-pos' : (val <= 2.0 ? 'c-prime' : 'c-neg');
    return { txt: val.toFixed(2), cls: cls };
  });

  const rowsHTML = [
    ['Revenue ($B)', (t.revenue || []).map(v => ({ txt: fmtMoneyB(v), cls: 'c-prime' }))],
    ['YoY Top-Line Growth', revGrowthCells],
    ['Operating Margin', (t.op_margin || []).map(v => ({ txt: fmtPct(v, 1), cls: v == null ? 'c-muted' : (v >= 0.18 ? 'c-pos' : (v < 0.08 ? 'c-neg' : 'c-prime')) }))],
    ['Owner FCF ex-SBC ($B)', (t.owner_fcf || []).map(v => ({ txt: fmtMoneyB(v), cls: v == null ? 'c-muted' : (v > 0 ? 'c-pos' : 'c-neg') }))],
    ['Return on Invested Capital (ROIC)', (t.roic || []).map(v => ({ txt: fmtPct(v, 1), cls: v == null ? 'c-muted' : (v >= 0.15 ? 'c-pos' : (v < 0.08 ? 'c-neg' : 'c-prime')) }))],
    ['Diluted Shares (M)', (t.shares || []).map(v => ({ txt: v ? (v/1e6).toFixed(1)+'M' : '—', cls: 'c-prime' }))],
    [`Peter Lynch ${pegyType} (Valuation / Growth)`, pegRowCells]
  ].map(([label, cells]) => `
    <tr>
      <td>${label}</td>
      ${cells.map(c => `<td class="${c.cls}">${c.txt}</td>`).join('')}
    </tr>
  `).join('');

  const rfHTML = (s.red_flags && s.red_flags.length)
    ? s.red_flags.map(f => `<div class="alert-row red">Disqualification: ${colorizeDesc(f, s)}</div>`).join('')
    : '<div style="color:var(--green-text);font-size:12px;margin-bottom:8px;">Passed all multi-year balance sheet, cash conversion, and dilution gates.</div>';

  const wnHTML = (s.warnings && s.warnings.length)
    ? s.warnings.map(w => `<div class="alert-row amber">Caution: ${colorizeDesc(w, s)}</div>`).join('')
    : '';

  const pleasingHTML = (s.pleasing_signals && s.pleasing_signals.length)
    ? `<div class="verdict-panel v-bull" style="margin-bottom:12px;">
        <div class="verdict-headline" style="color:var(--c-pos);font-size:12px;font-weight:700;letter-spacing:0.04em;">VERIFIED PLEASING ECONOMIC SIGNALS (${s.pleasing_signals.length} Passed)</div>
        <ul class="clean-list" style="margin-top:6px;">${s.pleasing_signals.map(p => `<li><span class="c-pos">&bull; ${p}</span></li>`).join('')}</ul>
       </div>`
    : '';

  const throwoffsHTML = (s.throw_offs && s.throw_offs.length)
    ? `<div class="verdict-panel v-bear" style="margin-bottom:12px;">
        <div class="verdict-headline" style="color:var(--c-neg);font-size:12px;font-weight:700;letter-spacing:0.04em;">THROW-OFFS &amp; DEALBREAKERS (${s.throw_offs.length} Detected)</div>
        <ul class="clean-list" style="margin-top:6px;">${s.throw_offs.map(t => `<li><span class="c-neg">&bull; ${t}</span></li>`).join('')}</ul>
       </div>`
    : `<div class="verdict-panel v-bull" style="margin-bottom:12px;padding:10px 14px;">
        <div style="color:var(--c-pos);font-size:12px;font-weight:600;">ZERO THROW-OFFS DETECTED &mdash; Pristine Balance Sheet &amp; Cash Profile</div>
       </div>`;

  const insDetails = (s.insider_details && s.insider_details.length)
    ? s.insider_details.map(d => {
        const dCls = /Purchase|Buy/i.test(d) ? 'c-pos' : (/Sale|Sell/i.test(d) ? 'c-neg' : 'c-prime');
        return `<li><span class="${dCls}">${d}</span></li>`;
      }).join('')
    : `<li><span>${s.insider_summary || 'No open-market insider transactions recorded in the past 6 months.'}</span></li>`;

  const ddHTML = (s.due_diligence && s.due_diligence.length)
    ? s.due_diligence.map(q => `<li><span>${colorizeDesc(q, s)}</span></li>`).join('')
    : '';

  const pCompCls = (!hasFlags && s.composite_score >= 60) ? 'c-pos' : (hasFlags || s.composite_score < 45 ? 'c-neg' : 'c-prime');
  const pValCls  = s.val_score >= 18 ? 'c-pos' : (s.val_score < 10 ? 'c-neg' : 'c-prime');
  const pQualCls = s.qual_score >= 18 ? 'c-pos' : (s.qual_score < 10 ? 'c-neg' : 'c-prime');
  const pSafeCls = s.safe_score >= 13 ? 'c-pos' : (s.safe_score < 8 ? 'c-neg' : 'c-prime');
  const pAlnCls  = s.align_score >= 11 ? 'c-pos' : (s.align_score < 5 ? 'c-neg' : 'c-prime');

  const dMosCls = s.fair_value_mos != null ? (s.fair_value_mos >= 0.10 ? 'c-pos' : (s.fair_value_mos <= -0.05 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dFcfCls = s.owner_fcf_yield != null ? (s.owner_fcf_yield >= 0.05 ? 'c-pos' : (s.owner_fcf_yield < 0.025 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dImpCls = (s.implied_growth != null && s.rev_cagr != null) ? ((s.rev_cagr - s.implied_growth >= 0.02) ? 'c-pos' : (s.implied_growth - s.rev_cagr >= 0.04 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dRevCls = s.rev_cagr != null ? (s.rev_cagr >= 0.06 ? 'c-pos' : (s.rev_cagr < 0 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dGpCls  = s.gross_profitability != null ? (s.gross_profitability >= 0.30 ? 'c-pos' : (s.gross_profitability < 0.15 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dCfoCls = s.cash_op_profitability != null ? (s.cash_op_profitability >= 0.12 ? 'c-pos' : (s.cash_op_profitability < 0.05 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dAgCls  = s.asset_growth != null ? (s.asset_growth <= 0.10 ? 'c-pos' : (s.asset_growth > 0.22 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dPioCls = s.piotroski != null ? (s.piotroski >= 7 ? 'c-pos' : (s.piotroski <= 4 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dAltCls = s.altman_z != null ? (s.altman_z >= 2.99 ? 'c-pos' : (s.altman_z < 1.80 ? 'c-neg' : 'c-prime')) : 'c-prime';
  const dBenCls = s.beneish_m != null ? (s.beneish_m <= -2.00 ? 'c-pos' : (s.beneish_m > -1.78 ? 'c-neg' : 'c-prime')) : 'c-prime';

  const modalWatchlistRow = (watchlists && watchlists.length > 0)
    ? `<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:10px;">
        <span class="watchlist-label" style="margin-right:2px;">Watchlists:</span>
        ${watchlists.map(w => {
          const inWl = (w.tickers || []).some(t => t.toUpperCase() === s.ticker.toUpperCase());
          const pillCls = inWl ? 'wl-pill active' : 'wl-pill';
          const prefix = inWl ? 'In ' : '+ ';
          return `<button class="${pillCls}" style="padding:3px 9px;font-size:11px;" onclick="toggleTickerInWatchlist('${w.id}', '${s.ticker}')">${prefix}${w.name}</button>`;
        }).join('')}
      </div>`
    : '';

  const headwindSectors = ['Technology', 'Consumer Cyclical', 'Basic Materials', 'Communication Services'];
  const leadingSectors = ['Energy', 'Financial Services', 'Healthcare'];
  const isHeadwind = headwindSectors.includes(s.sector);
  const isLeading = leadingSectors.includes(s.sector);
  const secRegimeBadge = isHeadwind 
    ? '<span class="sector-tag tag-headwind" style="margin-left:8px;vertical-align:middle;font-size:11px;">Sector Headwind (Outflow/Correction)</span>' 
    : (isLeading ? '<span class="sector-tag tag-leading" style="margin-left:8px;vertical-align:middle;font-size:11px;">Sector Leading (Relative Strength)</span>' : '');

  document.getElementById('modal-content').innerHTML = `
    <div class="modal-top">
      <div>
        <div>
          <span class="modal-ticker">${s.ticker}</span>
          <span class="modal-company">${s.company} · ${s.sector}${secRegimeBadge}</span>
        </div>
        <div class="modal-pillars">
          <span>Composite: <strong class="${pCompCls}">${s.composite_score.toFixed(1)} / 100</strong></span>
          <span>Valuation: <strong class="${pValCls}">${s.val_score.toFixed(1)} / 30</strong></span>
          <span>Quality: <strong class="${pQualCls}">${s.qual_score.toFixed(1)} / 30</strong></span>
          <span>Safety: <strong class="${pSafeCls}">${s.safe_score.toFixed(1)} / 20</strong></span>
          <span>Alignment: <strong class="${pAlnCls}">${s.align_score.toFixed(1)} / 20</strong></span>
        </div>
        ${modalWatchlistRow}
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button class="btn-secondary" onclick="auditSingleTicker('${s.ticker}')">Live Re-Audit</button>
        <button class="close-btn" onclick="closeModal()">Close [ESC]</button>
      </div>
    </div>

    ${researchHTML}

    <div class="m-section">
      <div class="m-heading">Multi-Year Audited Financial Statements (${yrs.length} Fiscal Years)</div>
      ${yrs.length ? `
        <table class="audit-table">
          <thead><tr><th>Line Item</th>${yrs.map(y => `<th>FY ${y}</th>`).join('')}</tr></thead>
          <tbody>${rowsHTML}</tbody>
        </table>
      ` : '<div class="c-muted">Annual statement series unavailable.</div>'}
    </div>

    <div class="m-section">
      <div class="m-heading">Objective Economic Scorecard (Pleasing Signals vs. Throw-Offs)</div>
      ${pleasingHTML}
      ${throwoffsHTML}
      <div class="verdict-meta-grid" style="background:rgba(15,19,28,0.7);border:1px solid var(--border-dim);padding:14px 18px;border-radius:8px;margin-top:8px;">
        <div><span class="k">Economic Health Verdict</span><span class="v ${s.throwoff_count > 0 ? 'c-neg' : 'c-pos'}">${s.pleasing_count != null ? s.pleasing_count : 0} / 6 Pleasing <span class="c-muted">(${s.throwoff_count || 0} Flags)</span></span></div>
        <div><span class="k" title="Moskowitz &amp; Grinblatt (1999 JF) Industry Momentum: intermediate 6-12M industry performance explains individual stock momentum">Sector Momentum Regime</span><span class="v ${isHeadwind ? 'c-neg' : (isLeading ? 'c-pos' : 'c-prime')}">${s.sector || 'N/A'}: ${isHeadwind ? 'HEADWIND' : (isLeading ? 'LEADING' : 'NEUTRAL')}${sectorETFs[s.sector] ? ` <a href="https://www.tradingview.com/chart/?symbol=AMEX%3A${sectorETFs[s.sector]}" target="_blank" rel="noopener" class="sector-tv-link" style="margin-left:6px;vertical-align:middle;">${sectorETFs[s.sector]} Chart &nearr;</a>` : ''}</span></div>
        <div><span class="k">Owner Cash Yield (ex-SBC)</span><span class="v ${dFcfCls}">${fmtPct(s.owner_fcf_yield, 2)}</span></div>
        <div><span class="k" title="Peter Lynch ${pegyType}: Trailing P/E divided by (3Y Revenue Growth + Dividend Yield). Below 1.0 = Undervalued, 1.0–2.0 = Fair Value, Above 2.0 = Expensive multiple relative to growth">3Y Peter Lynch ${pegyType}</span><span class="v ${pegyCls}">${pegyDisp} <span class="c-muted">(${pegyRating})</span></span></div>
        <div><span class="k">3Y ROIC (Compounding Power)</span><span class="v ${s.roic != null && s.roic >= 0.18 ? 'c-pos' : (s.roic != null && s.roic < 0.10 ? 'c-neg' : 'c-prime')}">${fmtPct(s.roic, 1)}</span></div>
        <div><span class="k" title="Novy-Marx (2013 JFE) Gross Profit / Assets: raw asset productivity (benchmark &gt; 28%)">Novy-Marx Gross Profitability</span><span class="v ${dGpCls}">${s.gross_profitability != null ? fmtPct(s.gross_profitability, 1) : 'N/A'}</span></div>
        <div><span class="k" title="Ball et al. (2016 JFE) Cash Operating Profitability: CFO / Assets (benchmark &gt; 10%)">Ball Cash-Op Profitability</span><span class="v ${dCfoCls}">${s.cash_op_profitability != null ? fmtPct(s.cash_op_profitability, 1) : 'N/A'}</span></div>
        <div><span class="k" title="Hou-Xue-Zhang (2015 RFS) Capital Discipline: YoY Asset Growth Rate (low &lt; 10% = disciplined)">Hou-Xue-Zhang Asset Growth</span><span class="v ${dAgCls}">${s.asset_growth != null ? fmtPct(s.asset_growth, 1, true) : 'N/A'}</span></div>
        <div><span class="k">3Y Diluted Share Trajectory</span><span class="v ${s.share_cagr != null && s.share_cagr <= -0.01 ? 'c-pos' : (s.share_cagr != null && s.share_cagr > 0.015 ? 'c-neg' : 'c-prime')}">${fmtPct(s.share_cagr, 1, true)}/yr</span></div>
        <div><span class="k">Net Debt / EBITDA</span><span class="v ${s.net_debt_ebitda != null && s.net_debt_ebitda <= 1.5 ? 'c-pos' : (s.net_debt_ebitda != null && s.net_debt_ebitda >= 3.5 ? 'c-neg' : 'c-prime')}">${s.net_debt_ebitda != null ? fmtNum(s.net_debt_ebitda, 1)+'x' : (s.net_debt != null && s.net_debt <= 0 ? 'Net Cash' : 'N/A')}</span></div>
        <div><span class="k">Altman Z-Score</span><span class="v ${dAltCls}">${fmtNum(s.altman_z, 2)} <span class="c-muted">(Safe &gt; 2.99)</span></span></div>
        <div><span class="k">Beneish M-Score</span><span class="v ${dBenCls}">${fmtNum(s.beneish_m, 2)} <span class="c-muted">(Limit -1.78)</span></span></div>
      </div>
    </div>

    <div class="m-section">
      <div class="m-heading">OpenInsider Transaction Ledger (12-Month Open-Market P/S)</div>
      <ul class="clean-list">${insDetails}</ul>
    </div>

    <div class="m-section">
      <div class="m-heading">Analytical Due-Diligence Protocol</div>
      <ul class="clean-list">${ddHTML}</ul>
    </div>
  `;
  document.getElementById('modal-backdrop').style.display = 'flex';
}

function closeModal() {
  if (scanPollTimer) {
    clearInterval(scanPollTimer);
    scanPollTimer = null;
  }
  document.getElementById('modal-backdrop').style.display = 'none';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (document.getElementById('modal-backdrop').style.display === 'flex') {
      closeModal();
    } else if (document.getElementById('search-box').value) {
      clearSearch();
    }
  } else if (e.key === '/' && document.activeElement !== document.getElementById('search-box')) {
    e.preventDefault();
    document.getElementById('search-box').focus();
    document.getElementById('search-box').select();
  }
});

function render() {
  renderWatchlistsBar();
  renderSectorBar();

  const sectorFilter = document.getElementById('sector-filter').value;
  const searchTerm = document.getElementById('search-box').value.trim().toUpperCase();
  const sortMode = document.getElementById('sort-mode').value;

  const activeWl = activeWatchlistId ? watchlists.find(w => w.id === activeWatchlistId) : null;
  const wlTickerSet = activeWl ? new Set((activeWl.tickers || []).map(t => t.toUpperCase())) : null;

  const basketSec = document.getElementById('basket-section');
  basketSec.style.display = (searchTerm.length > 0 || activeWl) ? 'none' : 'block';

  const basketStocks = allStocks.filter(s => s.in_basket).sort((a, b) => b.composite_score - a.composite_score);
  document.getElementById('basket-badge').textContent = `${basketStocks.length} POSITIONS · MAX 3 / SECTOR`;
  const bGrid = document.getElementById('basket-grid');
  if (basketStocks.length === 0) {
    bGrid.innerHTML = '<div class="c-muted">No stocks currently clear all gates. Inspect Tier A below.</div>';
  } else {
    bGrid.innerHTML = basketStocks.map(s => createCardHTML(s)).join('');
  }

  let filtered = allStocks.filter(s => {
    if (wlTickerSet && !wlTickerSet.has(s.ticker.toUpperCase())) return false;
    if (sectorFilter !== 'ALL' && s.sector !== sectorFilter) return false;
    if (searchTerm && !s.ticker.toUpperCase().includes(searchTerm) && !s.company.toUpperCase().includes(searchTerm) && !(s.sector || '').toUpperCase().includes(searchTerm)) return false;
    if (activeSegment === 'BASKET_ONLY' && !s.in_basket) return false;
    if (activeSegment === 'ZERO_FLAGS' && (!s.data_ok || (s.red_flags && s.red_flags.length > 0))) return false;
    if (activeSegment === 'HIGH_CASH' && (s.owner_fcf_yield == null || s.owner_fcf_yield < 0.05)) return false;
    if (activeSegment === 'INSIDER_BUY' && !['CLUSTER BUY', 'CEO/CFO BUY', 'INSIDER BUY'].includes(s.insider_signal)) return false;
    return true;
  });

  const sortFn = {
    'score': (a, b) => (b.composite_score || 0) - (a.composite_score || 0),
    'fcfYield': (a, b) => (b.owner_fcf_yield ?? -99) - (a.owner_fcf_yield ?? -99),
    'pleasing': (a, b) => (b.pleasing_count ?? 0) - (a.pleasing_count ?? 0) || (a.throwoff_count ?? 99) - (b.throwoff_count ?? 99),
    'roic': (a, b) => (b.roic ?? -99) - (a.roic ?? -99),
    'gpAssets': (a, b) => (b.gross_profitability ?? -99) - (a.gross_profitability ?? -99),
    'piotroski': (a, b) => (b.piotroski ?? -1) - (a.piotroski ?? -1),
    'insider': (a, b) => (b.insider_score_adj ?? -99) - (a.insider_score_adj ?? -99) || (b.composite_score || 0) - (a.composite_score || 0),
  }[sortMode];

  if (searchTerm) {
    filtered.sort((a, b) => {
      const aExact = a.ticker.toUpperCase() === searchTerm ? 2 : (a.ticker.toUpperCase().startsWith(searchTerm) ? 1 : 0);
      const bExact = b.ticker.toUpperCase() === searchTerm ? 2 : (b.ticker.toUpperCase().startsWith(searchTerm) ? 1 : 0);
      if (aExact !== bExact) return bExact - aExact;
      return sortFn(a, b);
    });
  } else {
    filtered.sort(sortFn);
  }

  currentFiltered = filtered;

  const statusBar = document.getElementById('search-status-bar');
  if (searchTerm.length > 0) {
    statusBar.style.display = 'flex';
    const topMatch = filtered.length > 0 ? `${filtered[0].ticker} (${filtered[0].company})` : 'Not in current S&P 500 cache';
    document.getElementById('search-status-text').innerHTML = `Search Filter: <strong>"${searchTerm}"</strong> &mdash; ${filtered.length} matching securities. Top match: <strong>${topMatch}</strong>`;
  } else {
    statusBar.style.display = 'none';
  }

  const statsRow = document.getElementById('stats-row');
  if (statsRow) {
    statsRow.innerHTML = `
      <div class="telemetry-cell"><div class="lbl">Universe</div><div class="val">${filtered.length}</div></div>
      <div class="telemetry-cell"><div class="lbl">Basket</div><div class="val">${filtered.filter(s=>s.in_basket).length}</div></div>
      <div class="telemetry-cell"><div class="lbl">Clean 10-K</div><div class="val c-pos">${filtered.filter(s=>s.data_ok && (!s.red_flags || s.red_flags.length===0)).length}</div></div>
      <div class="telemetry-cell"><div class="lbl">Insider Buy</div><div class="val">${filtered.filter(s=>['CLUSTER BUY','CEO/CFO BUY','INSIDER BUY'].includes(s.insider_signal)).length}</div></div>
      <div class="telemetry-cell"><div class="lbl">Disqualified</div><div class="val c-neg">${filtered.filter(s=>s.red_flags && s.red_flags.length>0).length}</div></div>
    `;
  }
  const mobStats = document.getElementById('mobile-stats-row');
  if (mobStats) {
    mobStats.innerHTML = `
      <span><strong>${filtered.length}</strong> Univ</span>
      <span><strong>${filtered.filter(s=>s.in_basket).length}</strong> Basket</span>
      <span class="c-pos"><strong>${filtered.filter(s=>s.data_ok && (!s.red_flags || s.red_flags.length===0)).length}</strong> Clean</span>
      <span class="c-prime"><strong>${filtered.filter(s=>['CLUSTER BUY','CEO/CFO BUY','INSIDER BUY'].includes(s.insider_signal)).length}</strong> Buy</span>
      <span class="c-neg"><strong>${filtered.filter(s=>s.red_flags && s.red_flags.length>0).length}</strong> Disq</span>
    `;
  }

  const dashboard = document.getElementById('dashboard');
  dashboard.innerHTML = '';

  if (viewMode === 'TABLE' || searchTerm.length > 0) {
    if (viewMode === 'TABLE' && filtered.length > 0) {
      dashboard.innerHTML = createTableHTML(filtered);
      return;
    }
    dashboard.innerHTML = filtered.length
      ? `<div class="cards-grid">${filtered.map(s => createCardHTML(s)).join('')}</div>`
      : `<div class="verdict-panel" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-top:8px;">
          <div>
            <div class="verdict-headline">"${searchTerm}" is not in the cached S&amp;P 500 list</div>
            <div class="verdict-body">Press <strong>[Enter]</strong> or click the button to run a live 4-Year 10-K, Reverse DCF, OpenInsider &amp; SEC EDGAR audit on <strong>${searchTerm}</strong> right now (~3 seconds).</div>
          </div>
          <button class="btn-primary" onclick="auditSingleTicker('${searchTerm}')"><span class="pulse-dot"></span>Run Live Audit on ${searchTerm}</button>
        </div>`;
    return;
  }

  if (activeWl && filtered.length === 0) {
    const hasTickers = activeWl.tickers && activeWl.tickers.length > 0;
    dashboard.innerHTML = `
      <div class="verdict-panel v-mid" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-top:8px;">
        <div>
          <div class="verdict-headline">${hasTickers ? `Companies in "${activeWl.name}" Have Not Been Audited Yet` : `Watchlist "${activeWl.name}" Is Empty`}</div>
          <div class="verdict-body">${hasTickers ? `Click <strong>Analyze This Watchlist Alone</strong> to run the 4-Year 10-K, Reverse DCF, OpenInsider &amp; SEC EDGAR audit on all ${activeWl.tickers.length} companies and add them to the shared database.` : `Add ticker symbols in the watchlist bar above (or from inside any stock dossier) to populate this watchlist.`}</div>
        </div>
        ${hasTickers ? `<button class="btn-primary" onclick="runWatchlistAnalysis('${activeWl.id}')"><span class="pulse-dot"></span>Analyze This Watchlist Alone (${activeWl.tickers.length} Stocks)</button>` : ''}
      </div>
    `;
    return;
  }

  tierOrder.forEach(tier => {
    const meta = tierMeta[tier];
    const stocks = filtered.filter(s => s.tier === tier).sort(sortFn);
    if (stocks.length === 0 && (activeSegment !== 'ALL' || activeWl)) return;

    const sec = document.createElement('div');
    sec.className = `tier-block ${meta.css}`;
    sec.innerHTML = `
      <div class="tier-bar">
        <div class="tier-name">${meta.label} <span class="tier-count">${stocks.length}</span></div>
        <div class="tier-sub">${meta.desc}</div>
      </div>
      ${stocks.length ? `<div class="cards-grid">${stocks.map(s => createCardHTML(s)).join('')}</div>` : '<div class="c-muted" style="font-size:12px;padding:8px 0;">No securities in this tier match current criteria.</div>'}
    `;
    dashboard.appendChild(sec);
  });
}

renderTracker();
render();
</script>
</body>
</html>"""


def build_html_dashboard(stocks_payload, cohorts_payload, watchlists_payload=None):
    payload = {
        'stocks': stocks_payload,
        'cohorts': cohorts_payload,
        'watchlists': watchlists_payload if watchlists_payload is not None else [],
    }
    json_str = json.dumps(payload)
    return HTML_TEMPLATE.replace("__PAYLOAD_JSON__", json_str)
