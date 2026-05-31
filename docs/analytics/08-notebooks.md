# Lecture 8 — Notebooks & Practical Analysis

The Jupyter notebooks in `notebooks/` apply the pricing, volatility,
and carry analytics from the lecture series to real market data. Each
notebook is self-contained and can be re-run against fresh snapshots.

## Notebook Index

| # | Notebook | Focus |
|---|---------|-------|
| 1 | [IV & Greek Validation](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/01_iv_greek_validation.ipynb) | Round-trip IV solve accuracy, Greek cross-checks |
| 2 | [Carry Regime Explorer](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/02_carry_regime_explorer.ipynb) | Rolling carry / vol divergence, regime transitions |
| 3 | [Surface Dynamics](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/03_surface_dynamics.ipynb) | 3-D IV surface, ATM term structure, smile skew |
| 4 | [RV Estimators](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/04_rv_estimators_comparison.ipynb) | Close-to-close vs Parkinson vs Yang-Zhang RV |
| 5 | [Concurrency Patterns](https://github.com/vicw0ng-hk/basis-vol-lab/blob/master/notebooks/05_concurrency_patterns.ipynb) | asyncio, threading, multiprocessing, GIL |

## Key Findings

### IV & Greek Validation (Notebook 1)

Compares our Brent-method IV solver against Deribit's published mark IV
across all active BTC options.

- **Median absolute error**: < 0.3 vol points across the full chain
- Largest deviations cluster in deep OTM puts with very short tenors
  where both bid–ask width and numerical sensitivity are highest
- Greeks (delta, gamma, vega, theta) pass finite-difference cross-checks

### Carry Regime Explorer (Notebook 2)

Loads accumulated Deribit Parquet history and computes rolling
carry / vol divergence.

- Visualises basis-carry vs implied-vol regimes over time
- Identifies divergence windows where basis carry and IV move in
  opposite directions — potential regime shift signals
- Uses the same carry decomposition (basis, funding, total) as the
  dashboard Carry page

### Surface Dynamics (Notebook 3)

Animates how the BTC IV surface evolves using accumulated snapshots.

- 3-D surface plots (strike × tenor × IV) for individual snapshots
- ATM term-structure slope tracker — monitors the term-structure
  gradient that signals contango/backwardation in vol
- Smile skew metrics: 25-delta risk-reversal and butterfly spreads
  across expiries
- Multi-expiry smile panels for visual comparison

### RV Estimators (Notebook 4)

Compares three realised-volatility estimators on BTC data sourced from
Binance hourly candles and local Deribit snapshots.

- **Close-to-close**: simplest, uses only closing prices
- **Parkinson**: uses high-low range, roughly 5× more efficient
- **Yang-Zhang**: uses open-high-low-close, most efficient for drift
- Side-by-side time-series and distribution plots show estimator
  agreement and divergence under different volatility regimes

### Concurrency Patterns (Notebook 5)

Benchmarks Python concurrency primitives on the project's own IV solver
and REST fetchers.

- **asyncio.gather** delivers 3–4× speedup on concurrent REST calls by
  overlapping network wait on a single thread
- **Threading** gives zero speedup for CPU-bound Brent IV solves — the
  GIL serialises pure-Python bytecode
- **ProcessPoolExecutor** achieves true parallelism by bypassing the GIL
  but only pays off for large chains (≥ 1 000 options) due to
  serialisation overhead
- **NumPy vectorization** outperforms all Python-level strategies for
  array math by running in GIL-released C extensions
- Production choice: asyncio for I/O + NumPy for compute; process pools
  reserved for batch sizes beyond typical crypto option chains

## Running the Notebooks

```bash
# Make sure dependencies are installed
uv sync

# Launch JupyterLab
uv run jupyter lab notebooks/
```

The notebooks expect Parquet data in `data/deribit/` (accumulated by the
scheduled pipeline). Notebook 4 also fetches live Binance candle data
via the public REST API.
