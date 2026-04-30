# Lecture 2 — Implied volatility

> **Module**: [packages/analytics/src/basis_analytics/iv.py](../../packages/analytics/src/basis_analytics/iv.py)

## 2.1 What "implied" means

Black-76 takes $\sigma$ in and produces a price. **Implied volatility**
is the inverse: given the price quoted in the market, find the $\sigma$
that the formula needs to produce that price. Formally we solve

$$
\text{Black76}(F, K, T, \sigma) = P_\text{market}
$$

for $\sigma$. The IV is *the* number traders quote and chart, because
prices are noisy and apples-to-oranges across strikes/expiries while IV
is comparable.

## 2.2 Why this is easy: vega is positive

The derivative of the option price with respect to $\sigma$ is **vega**:

$$
\nu = \frac{\partial P}{\partial \sigma} = df \cdot F \cdot \varphi(d_1) \cdot \sqrt{T}
$$

This is **always non-negative** — and strictly positive for any
non-degenerate option. So the price is a strictly increasing function
of $\sigma$, which means:

* The IV is **unique** when it exists.
* Any reasonable bracket-based root finder will converge.

## 2.3 Why we use Brent's method

Newton's method would converge fast (it has the analytic vega for free),
but it's brittle near the boundaries — at very deep OTM strikes the
function is almost flat and a Newton step can overshoot. **Brent's
method** combines bisection (always safe) with secant/IQI steps when
they're well-behaved, so it's both robust and efficient.

`scipy.optimize.brentq` requires:

* A bracket $[\sigma_\text{lo}, \sigma_\text{hi}]$ where the function
  changes sign.
* The function to evaluate.

We use the bracket `[1e-4, 5.0]`. Five hundred percent annualized vol is
above anything seen on liquid crypto options — even meme-coin tail
strikes don't break this bracket.

## 2.4 No-arbitrage bounds

Before solving, we check the price is feasible. For a call with our
conventions:

$$
df \cdot \max(F - K, 0) \;\le\; P \;\le\; df \cdot F
$$

Outside that interval, no $\sigma$ can produce $P$ — the bracket
won't change sign, and Brent will raise. We prefer to return `NaN`
rather than swallow a stack trace, because a market data feed can
genuinely send one stale tick that violates the bound.

## 2.5 Validation against Deribit

[`validation.py`](../../packages/analytics/src/basis_analytics/validation.py)
does the round-trip:

1. Pull every BTC option's mark price (in coin) and `mark_iv` from
   Deribit's public `get_book_summary_by_currency`.
2. Pull every BTC future's mark price; build `forwards_by_expiry`.
3. For each option: convert mark price to USD via `mark_price * F`,
   compute $T$ in years, solve our IV.
4. Compare against `mark_iv / 100`.

A real run produces something like:

```
expiry                           count  mean_abs_err  p95_abs_err  max_abs_err
2026-05-29 08:00:00+00:00           94       0.00059      0.00272      0.00670
2026-12-25 08:00:00+00:00          110       0.00041      0.00261      0.00789
2027-03-26 08:00:00+00:00           90       0.00009      0.00034      0.00130
```

Errors are in vol points (0.001 = 10 bps of IV). Liquid expiries are
**well under 1 vol point of error**; same-day expiries can be much
worse because mark prices are dominated by intrinsic + bid/ask noise
and a small price perturbation maps to a large vol perturbation when
$T$ is tiny — that's the math, not a bug.

## 2.6 Vectorized solves

Brent doesn't vectorize natively. We expose `implied_vol_array` which
loops in pure Python — for an entire BTC chain (~1000 options) the
total wall time is a few hundred milliseconds. For our use case
(periodic snapshots, not tick-level recomputation) this is fine. If we
ever need faster, the path is `numba.njit` over a hand-rolled Brent —
but don't pre-optimize.

## 2.7 Common gotchas

| Symptom | Cause |
|---|---|
| IV solve always returns NaN | Forgot to multiply coin-price by `F` (lecture 1.3). |
| IV solve returns the bracket endpoint | Price is exactly the bracket's lower/upper bound; widen `lo`/`hi` only if the value is actually plausible. |
| Solver is slow on large batches | Calling `implied_vol_black76` from a pandas `apply` is O(n) Python — use `implied_vol_array` with NumPy arrays instead. |

> **Next lecture**: the Greeks, and why analytic forms tie out with finite differences to 1 part in 10⁴.
