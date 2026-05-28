# Implied Volatility

Black-76 takes volatility in and returns a price. Implied volatility (IV) is
the inverse: the volatility that makes the model match the market quote.

$$
\text{Black76}(F, K, T, \sigma) = P_{market}
$$

IV is the common language for options because it is comparable across strikes
and expiries in a way raw prices are not.

## Solver

Option price is monotone in volatility because vega is non-negative:

$$
\nu = df \cdot F \cdot \varphi(d_1) \cdot \sqrt{T}
$$

That makes the solution unique when the price is inside no-arbitrage bounds.
The implementation uses Brent's method with a `[1e-4, 5.0]` volatility bracket
because it is robust near deep ITM/OTM strikes.

## Bounds

For a call under this convention:

$$
df \cdot \max(F-K,0) \le P \le df \cdot F
$$

If a feed sends a stale price outside the feasible range, the solver returns
`NaN` instead of inventing a volatility.

## Deribit Validation

The validation flow pulls option mark prices and matching futures marks,
converts coin premiums to USD with `mark_price * F`, solves IV, and compares
against `mark_iv / 100`. Liquid expiries typically land well below one vol
point of error; same-day expiries are noisier because tiny price moves map to
large IV moves.
