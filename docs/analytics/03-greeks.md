# Lecture 3 — Greeks

> **Module**: [packages/analytics/src/basis_analytics/greeks.py](../../packages/analytics/src/basis_analytics/greeks.py)

## 3.1 What a Greek is

A **Greek** is a partial derivative of the option price with respect to
some input — moneyness, vol, time, or rate. Traders use them to quickly
estimate how a portfolio's mark moves under hypothetical shocks. The
five most-used:

| Greek | Definition | Interpretation |
|---|---|---|
| Delta $\Delta$ | $\partial P / \partial F$ | Hedge ratio: how many forward contracts hedge the option. |
| Gamma $\Gamma$ | $\partial^2 P / \partial F^2$ | How fast delta changes as $F$ moves. |
| Vega $\nu$ | $\partial P / \partial \sigma$ | P/L per 1.00 of vol shift. |
| Theta $\Theta$ | $\partial P / \partial T$ | Time decay (we return $\partial / \partial T$, not $\partial / \partial t$). |
| Rho $\rho$ | $\partial P / \partial r$ | Rate sensitivity. Zero in our zero-rate convention. |

## 3.2 Closed-form Black-76 Greeks

Differentiating the Black-76 formula and grinding through the algebra:

$$
\begin{aligned}
\Delta_\text{call} &= df \cdot \Phi(d_1) \\
\Delta_\text{put} &= -df \cdot \Phi(-d_1) = df \cdot (\Phi(d_1) - 1) \\
\Gamma &= \frac{df \cdot \varphi(d_1)}{F \, \sigma \sqrt{T}} \\
\nu &= df \cdot F \cdot \varphi(d_1) \cdot \sqrt{T} \\
\Theta &= \frac{df \cdot F \cdot \varphi(d_1) \cdot \sigma}{2\sqrt{T}} \quad\text{(both call and put, with $df$ constant)}
\end{aligned}
$$

Two things to notice:

* **Vega and gamma are the same for calls and puts.** That's a
  consequence of put-call parity — both sides of the parity equation are
  linear in $F$, so the second derivative and the vol derivative don't
  see the call-vs-put split.
* **Forward delta has a sign**. Our $\Delta$ is per unit of *forward*,
  not per unit of *coin*. If you want Deribit's coin-quoted delta you
  rescale: `delta_coin ≈ delta_forward / F` (with df = 1).

## 3.3 Validating Greeks with finite differences

Analytic Greeks are easy to get wrong by a sign or factor. The cheapest
guard is to compare them against **central finite differences** of the
pricer:

$$
\Delta_\text{FD} \approx \frac{P(F+h) - P(F-h)}{2h}
$$

If your $\Delta$ matches $\Delta_\text{FD}$ to ~1e-4 relative for a
range of $F, K, T, \sigma$, your derivation is right. The tests in
[tests/test_greeks.py](../../tests/test_greeks.py) do exactly this for
delta, gamma, and vega across both calls and puts.

This is the discipline that separates "I copy-pasted a formula" from
"I shipped a pricer". For an interview narrative: the FD-vs-analytic
test is also what proves your derivation, *not* a literature reference.

## 3.4 Why theta is signed strangely

Different shops sign theta differently. Some report
$-\partial P / \partial t$ ("how much I lose per day if nothing moves").
We report $\partial P / \partial T$, which is positive (more time =
more value). To convert to "decay per calendar day", do
$\Theta_\text{per-day} = -\Theta / 365$.

## 3.5 Greeks under inverse quoting

Deribit publishes `delta`, `gamma`, etc. in coin terms. Our forward
Greeks are in forward (USD) terms. The mapping is purely a units
conversion through the matching future's mark $F$:

* Coin-delta $\approx$ forward-delta $/ F$ (per 1 coin of underlying).
* Coin-vega $\approx$ forward-vega $/ F$.

The validation report in step 5 deliberately compares **only IV**, not
Greeks, because IV is the natural invariant — once IV agrees, Greek
mismatches are just unit conversions you can do downstream. We can add
a Greek-validation panel later if needed.

## 3.6 Common gotchas

| Symptom | Cause |
|---|---|
| Vega bigger than Deribit's by exactly $F$ | You're comparing forward-vega to coin-vega. Divide by `F`. |
| Theta has wrong sign | Convention mismatch — we return $+\partial / \partial T$; Deribit displays $-\partial / \partial t$. |
| FD test fails for tiny $h$ | Floating-point cancellation. Use $h \approx 10^{-4} \cdot F$ for delta, $h \approx 10^{-4}$ for vega. |
| Gamma is `inf` at expiry | Division by $\sigma\sqrt{T} \to 0$. We return zero on the degenerate branch. |

> **Next lecture**: realized volatility, which is the second leg of the IV-RV signal.
