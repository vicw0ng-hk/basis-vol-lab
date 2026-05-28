# Analytics Notes

These notes explain the math behind the dashboard in plain language. Read them
in order for the full flow, or jump to the topic behind a specific card.

| # | Topic | Covers |
| --- | --- | --- |
| 1 | [Options and forward pricing](01-options-and-forward-pricing.md) | Payoffs, Black-76, and Deribit's inverse premium convention. |
| 2 | [Implied volatility](02-implied-volatility.md) | IV inversion, Brent's method, and Deribit validation. |
| 3 | [Greeks](03-greeks.md) | Delta, gamma, vega, theta, and units under inverse quoting. |
| 4 | [Realized vs implied volatility](04-realized-vs-implied-vol.md) | RV estimators and the IV-RV spread. |
| 5 | [Carry, basis, and funding](05-carry-basis-funding.md) | Dated-futures carry and perpetual funding. |
| 6 | [Skew, surface, and signals](06-skew-surface-and-signals.md) | Smile interpolation, term structure, and headline regime scores. |

## Notation

| Symbol | Meaning |
| --- | --- |
| $S$ | Spot price |
| $F$ | Forward or futures mark price |
| $K$ | Strike |
| $T$ | Time to expiry in years |
| $\sigma$ | Annualized volatility |
| $\Phi, \varphi$ | Standard normal CDF and PDF |

Crypto trades continuously, so annualization uses 365 days unless noted.
