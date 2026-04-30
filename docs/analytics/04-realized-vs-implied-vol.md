# Lecture 4 — Realized vs implied volatility

> **Module**: [packages/analytics/src/basis_analytics/realized_vol.py](../../packages/analytics/src/basis_analytics/realized_vol.py)

## 4.1 The two flavours of vol

* **Implied volatility (IV)** is forward-looking: what the option market
  *thinks* future vol will be, extracted from quotes (lectures 1–3).
* **Realized volatility (RV)** is backward-looking: how much the price
  *actually* moved over some past window.

Their *difference* is one of the most-watched signals in derivatives
trading. Persistently `IV > RV` means the options market is
"expensive" — you can sell vol and statistically come out ahead.
Persistently `IV < RV` means options are cheap relative to recent
moves. Either regime is interview-explainable in one sentence.

## 4.2 Close-to-close estimator

Given a price series $P_0, P_1, \dots, P_n$ sampled at uniform intervals
$\Delta t$, the canonical estimator is the standard deviation of log
returns, annualized:

$$
\hat\sigma_\text{cc} = \sqrt{\frac{1}{n - 1} \sum_{i=1}^n r_i^2 \cdot \text{annualization}}, \quad r_i = \ln\frac{P_i}{P_{i-1}}
$$

Annualization for daily bars is $\sqrt{365}$ (crypto, 24/7) or
$\sqrt{252}$ (traditional markets). We default to **365** because the
project is crypto-only.

This estimator is **unbiased under iid returns** — but it's noisy. With
$n$ daily observations its standard error is roughly $\sigma /
\sqrt{2n}$, so a 30-day estimate has ~13 % relative noise on its own
realization.

## 4.3 Parkinson estimator

[Parkinson (1980)](https://www.jstor.org/stable/2352357) noticed that
each bar's high/low range carries information about intra-bar volatility
the close-to-close estimator throws away. Under geometric Brownian
motion with zero drift and continuous observation:

$$
\hat\sigma^2_\text{P}(\text{bar}) = \frac{1}{4 \ln 2} \left(\ln\frac{H}{L}\right)^2
$$

Averaging this over a window and annualizing gives an estimator that's
**~5x more efficient** than close-to-close (i.e., needs 5x fewer bars
for the same standard error). In crypto markets where we have clean
high/low tape, this is a meaningful win.

The trade-off:

* Assumes no jumps. Crypto has jumps.
* Assumes high/low is continuously observed within the bar. Real bars
  miss the true high/low slightly, biasing the estimator down.

In practice we report **both** and compare. Big disagreement = the bar
has a jump or a gap.

## 4.4 Bar-frequency sanity check

If you build the series from intra-day bars (e.g. 1-minute), the
annualization factor must reflect bars-per-year, not days. Our code
inspects the median sampling interval and computes
`bars_per_day = 86400 / median_dt_seconds` automatically. Concretely,
for 1-minute bars, `bars_per_day = 1440` and the annualization factor
is `365 * 1440`. The unit tests confirm a constant-return series gives
zero RV regardless of bar frequency.

## 4.5 The IV-RV spread as a signal

In step 5 the spread enters the **carry-vol divergence** signal
(lecture 6). Two computational notes:

* **Match the tenor.** Don't compare 7-day RV to a 30-day ATM IV. Pick
  one tenor (we use 30D) and use it everywhere downstream.
* **Use the same annualization on both legs.** RV from
  `close_to_close_rv(annualize=365)` and IV from Deribit are both in
  the same units (decimal annualized vol), so subtracting is direct.

## 4.6 Common gotchas

| Symptom | Cause |
|---|---|
| RV is `0.0` everywhere | Series isn't log-returns; it's already a return series. Pass *prices*, not returns. |
| RV is much smaller than IV in calm regimes | That's the normal "vol risk premium", not a bug — IV embeds an option-buyer's risk premium and is typically a few vol points above RV. |
| RV spikes only on the day of a known event | Window includes the event day. Try a shorter window or exponentially weighted RV. |
| TypeError "must have a DatetimeIndex" | Pass a `Series` with a UTC-aware `pd.DatetimeIndex`, not a default RangeIndex. |

> **Next lecture**: carry — the other input to the carry-vol divergence signal.
