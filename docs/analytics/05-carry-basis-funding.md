# Lecture 5 — Carry, basis, and funding

> **Module**: [packages/analytics/src/basis_analytics/carry.py](../../packages/analytics/src/basis_analytics/carry.py)

## 5.1 What "carry" means in a derivatives book

**Carry** is the annualized return you'd earn from holding a position
to expiry, assuming the underlying stays flat. In a futures-vs-spot
arbitrage:

* Buy spot at $S$, sell future at $F$ for delivery in $\tau$ days.
* At expiry, $F - S$ flows in (assuming the future converges to spot).
* Annualize: $(F - S)/S \cdot 365 / \tau$.

That's exactly `annualized_carry(S, F, τ)` in our package. Positive
carry = **contango** (futures rich vs spot); negative = **backwardation**
(futures cheap vs spot).

## 5.2 The basis curve

For a single underlying we can have several listed futures (Deribit
typically has weekly + monthly + quarterly contracts). Their carries
form a **basis curve** — annualized carry as a function of expiry.

`basis_curve(prices, expiries, spot=…, asof=…)` produces this curve as
a DataFrame indexed by expiry, with columns `[future, days,
annualized_carry]`. Curve shape carries information:

* **Steep contango** (carry rising with expiry) = strong demand to
  hold long exposure later, often a sign of leveraged-long
  positioning.
* **Inverted curve** = backwardation in the front, contango further
  out, often a sign of immediate sell pressure with longer-term bullish
  bias.

## 5.3 Perpetual funding as the limit of carry

A **perpetual** has no expiry. To keep its mark price tethered to the
spot index, the venue pays / charges holders a periodic **funding
rate** $r_\text{8h}$ — currently every 8 hours on both Deribit and
Binance.

Conceptually a perpetual is a future whose expiry is "now + funding
interval", repeatedly. The annualized carry implied by funding is
therefore

$$
r_\text{ann} = (1 + r_\text{8h})^{3 \cdot 365} - 1
$$

`annualized_funding(funding_rate_8h)` computes this. Note we
**compound**, not multiply by 1095. For tiny rates (under 0.01 %) the
two are indistinguishable, but compounding is the right primitive when
funding briefly spikes to 1 %+.

## 5.4 Stitching futures and perp into one number

In the dashboard we want a single "carry" series per underlying. The
construction is:

1. Pull the perp's funding history (Binance backfill + ongoing).
2. Pull the front-month future's annualized carry over time.
3. Take a tenor-weighted average — the perp anchors the very-front
   end, the future anchors ~30-90D out, and we report a 30D-equivalent.

This stitching lives in the dashboard layer (step 6+), not in
`carry.py`. The package gives you the primitives; the orchestration
glues them.

## 5.5 Why we annualize compounded, not simple

A common mistake is reporting `funding_8h * 1095` as "annualized". It's
fine for headline numbers but breaks down when funding goes negative or
when you backtest. Compounding is the only formulation that:

* Returns 0 if the rate is 0.
* Inverts cleanly: $(1 + r_\text{ann})^{1/1095} - 1$ recovers the 8h
  rate.
* Aggregates correctly across periods of different rates.

For interview defensibility, always show both formulas and explain
the gap.

## 5.6 Common gotchas

| Symptom | Cause |
|---|---|
| Annualized carry is huge (>1.0) for near-expiry futures | Time-decay scaling: $(F-S)/S \cdot 365 / \tau$ blows up as $\tau \to 0$. Filter `days > 1`. |
| Funding annualization gives `nan` | Rate column has stale `inf` values from a 0-spot day. Drop / clip before compounding. |
| Curve looks inverted but Deribit's "basis" page disagrees | Some venues quote basis in *USD* (just $F - S$) rather than annualized. Match conventions explicitly. |
| Backtest shows free money in a steep contango | You forgot the cost of borrowing the coin to short the spot. In crypto, lending rates can dwarf the basis. |

> **Next lecture**: the volatility surface and how it feeds the three headline signals.
