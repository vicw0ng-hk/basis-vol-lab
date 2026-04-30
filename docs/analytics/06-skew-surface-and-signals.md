# Lecture 6 — Skew, surface, and the headline signals

> **Modules**:
> [`surface.py`](../../packages/analytics/src/basis_analytics/surface.py),
> [`signals.py`](../../packages/analytics/src/basis_analytics/signals.py)

This is the last lecture and the most product-flavoured. We bring
everything together to produce three signals interview-ready and
dashboard-ready.

## 6.1 The volatility surface, in one diagram

Plot every option's IV against its strike (x-axis) and expiry (y-axis).
You get a **vol surface**: a 2-D function that's smooth in expiry and
roughly U-shaped in strike (the "smile").

Two slices of the surface dominate trader conversation:

* **Smile** — fix the expiry, look across strikes. Crypto smiles
  usually tilt: BTC tends to be **call-skewed** (calls richer than
  puts) in bull markets and **put-skewed** in selloffs.
* **Term structure** — fix the moneyness (usually ATM), look across
  expiries. A flat term structure says "the market expects the same
  vol at all horizons"; a steep curve says "today is calmer than
  later."

`atm_term_structure(snapshot_df)` extracts the term structure: per
expiry, the option whose strike is closest to the forward, its IV.
That's the natural time axis of the surface.

## 6.2 Smile interpolation with PCHIP

For numerical work we often need IV at strikes that aren't quoted.
Naive cubic-spline interpolation **overshoots** between observed
points: a spline through three smoothly-decreasing nodes can wiggle
*up* between them, producing nonsense IVs.

PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) is **monotone
preserving**: where input data is monotone, the interpolant is too. The
output is smooth (continuous first derivative) without bow-tie
oscillations. SciPy ships it as `scipy.interpolate.PchipInterpolator`.

`smile_interp(strikes, ivs)` wraps it and adds a flat-extrapolation
guard (return the nearest endpoint IV outside the observed strike
range). For the MVP this is sufficient; SVI / SABR can come later if
we want a parametric surface.

## 6.3 Risk reversal and butterfly

Two scalar summary statistics of the smile:

* **25Δ risk reversal**:
  $\text{RR}_{25} = \sigma_{25\Delta\,\text{call}} - \sigma_{25\Delta\,\text{put}}$
  Positive = call-skewed, negative = put-skewed. This is the
  market's *directional fear/greed* indicator.

* **25Δ butterfly**:
  $\text{BF}_{25} = \tfrac{1}{2}(\sigma_{25\Delta\,\text{call}} + \sigma_{25\Delta\,\text{put}}) - \sigma_\text{ATM}$
  Always positive in equilibrium. Measures *smile convexity* — how
  much extra vol the wings carry over the ATM. High BF = the market
  is pricing in fat tails.

Both feed the **skew stress** signal below. We compute them in step 6
when we wire up the dashboard; the smile interpolator is the
underlying primitive.

## 6.4 The three headline signals

All three are explicit, transparent formulas on **percentile-ranked**
inputs. Percentile rank converts any noisy time series into a
$[0, 1]$ score that's stationary by construction — the median is
always 0.5, the all-time-high is 1.0. That's the only sensible way to
combine apples (vol, in vol points) and oranges (carry, in % per year)
on the same axis.

### (a) Carry-vol divergence

```
carry_vol_divergence = pctile(carry) - pctile(IV - RV)
```

* **Positive** = carry is rich relative to the IV-RV spread; vol
  sellers are getting paid less than carry would suggest.
* **Negative** = carry is cheap; vol is rich relative to historical RV.

Both extremes are interesting; mean-reverting trade ideas live at
both ends. Range: $[-1, 1]$.

### (b) Skew stress

```
skew_stress = (pctile(|RR_25Δ|) + pctile(OI concentration)) / 2
```

* `|RR_25Δ|` because both extreme call-skew and extreme put-skew are
  stress indicators.
* OI concentration is the share of total option open interest in the
  top-N strikes; a concentrated book = a few big positions that move
  the market when they unwind.

Range: $[0, 1]$.

### (c) Regime-change alert

```
alert(t) = carry_pct(t) ≥ τ AND skew_pct(t) ≥ τ AND oi_pct(t) ≥ τ
```

A boolean Series. Default threshold $\tau = 0.8$ → all three
signals in their top 20 % of the trailing year. The conjunction is
the point: any one of these in the top quintile is unremarkable, but
all three at once is genuinely a regime.

## 6.5 Building the percentile rank

`percentile_rank(s, window="365D")` returns a rolling-window rank in
$[0, 1]$. For each timestamp $t$, the value is the fraction of
observations in the trailing window with value $\le s_t$. Implementation
note: pandas' built-in `rolling.rank` is faster but less explicit;
our `apply` version makes the meaning transparent at the cost of
performance. For the MVP that's the right trade-off.

## 6.6 What lives in `signals.py` and what doesn't

The package contains the **formulas**. It does **not** contain:

* The data plumbing that builds a long-history series of carry,
  IV-RV, RR_25Δ, and OI concentration. That's step 6 (orchestration).
* Backtests. The plan defers backtesting; the signals are
  interpretable on inspection without a backtest, which is the
  interview-friendly framing.
* Real-time alerting (notifications, email, etc.). That's a
  product-shell concern.

## 6.7 Common gotchas

| Symptom | Cause |
|---|---|
| Percentile rank is `NaN` for the first 364 points | Window not full yet. Either accept it or use `.expanding()` instead until enough data accumulates. |
| Smile interp throws `ValueError: x must be increasing` | Input strikes aren't sorted. `smile_interp` already handles this; if you call PCHIP directly, sort first. |
| Regime alert never fires | Threshold too high, or the three series aren't on a UTC `DatetimeIndex` and don't align. Check `series.index.equals(...)`. |
| RR percentile spikes on a single quote | The RR uses interpolated 25Δ vols; if you pulled raw quote IVs without interpolation you can hit holes when 25Δ strikes move between expiries. Always interpolate. |

## 6.8 Where to go from here

* **Step 6** wires this package into the API layer and dashboard.
* **Cloud rollout** publishes signal artifacts to R2 and serves them
  through a Lambda endpoint.
* **Future research**: SVI fits, term-structure of skew, vol-of-vol
  signals.

That closes the analytics course. Read the source, run the validation
CLI, and make changes — the package is small enough to hold in your
head, and the tests will catch you when you break it.
