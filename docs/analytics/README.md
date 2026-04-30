# Analytics Course — `basis_analytics`

This is the math-and-product companion to the `basis_analytics` package.
The audience is an engineer who is comfortable with Python and pandas and
has *some* exposure to options (you've heard of Black-Scholes, you know
what a future is) but isn't a derivatives specialist. Each lecture stands
alone; together they walk from "what is an option" to "how do I build a
regime-change signal".

| # | Lecture | What you'll learn |
|---|---|---|
| 1 | [Options and forward pricing](01-options-and-forward-pricing.md) | The option payoff, why we price under Black-76 (not Black-Scholes-Merton), the inverse-quoting convention crypto uses, and where this lives in [packages/analytics/src/basis_analytics/pricing.py](../../packages/analytics/src/basis_analytics/pricing.py). |
| 2 | [Implied volatility](02-implied-volatility.md) | Why IV is monotone in vega, why we use Brent, how to handle no-arbitrage bounds. Module: [iv.py](../../packages/analytics/src/basis_analytics/iv.py). |
| 3 | [Greeks](03-greeks.md) | Analytic delta/gamma/vega/theta under Black-76 and how we validate them with finite differences. Module: [greeks.py](../../packages/analytics/src/basis_analytics/greeks.py). |
| 4 | [Realized vs implied volatility](04-realized-vs-implied-vol.md) | Close-to-close, Parkinson, the IV-RV spread, and why crypto needs `annualize=365`. Module: [realized_vol.py](../../packages/analytics/src/basis_analytics/realized_vol.py). |
| 5 | [Carry, basis, and funding](05-carry-basis-funding.md) | Annualized basis on dated futures, perpetual funding, and how to put them on the same axis. Module: [carry.py](../../packages/analytics/src/basis_analytics/carry.py). |
| 6 | [Skew, surface, and the headline signals](06-skew-surface-and-signals.md) | Smile interpolation, ATM term structure, and the three composite signals (carry-vol divergence, skew stress, regime-change alert). Modules: [surface.py](../../packages/analytics/src/basis_analytics/surface.py), [signals.py](../../packages/analytics/src/basis_analytics/signals.py). |

## How to use this course

* **Read top-down** if you want the full picture before touching the code.
* **Jump straight to a lecture** if you're trying to understand one
  specific module — every lecture maps to a real source file.
* **Run the validation CLI** at any point to see the math working
  against live Deribit data:

  ```bash
  uv run python -m basis_analytics.validate --currency BTC
  ```

  No API credentials required; the script uses Deribit's public REST
  endpoint.

## Notation used throughout

| Symbol | Meaning |
|---|---|
| $S$ | Spot price of the underlying (e.g. BTC/USD) |
| $F$ | Forward (or futures mark) price for some expiry |
| $K$ | Option strike |
| $T$ | Time to expiry, in years (ACT/365) |
| $\sigma$ | Annualized lognormal volatility |
| $r$ | Risk-free rate (we set it to 0 for crypto inverse options) |
| $\Phi(\cdot), \varphi(\cdot)$ | Standard normal CDF and PDF |

All time series are pandas with a UTC `DatetimeIndex` unless noted.
