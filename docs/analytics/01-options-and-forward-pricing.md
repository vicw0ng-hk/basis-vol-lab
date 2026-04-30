# Lecture 1 — Options and forward pricing

> **Module**: [packages/analytics/src/basis_analytics/pricing.py](../../packages/analytics/src/basis_analytics/pricing.py)

## 1.1 What an option is

A **European option** is a contract that pays, at a fixed expiry $T$, the
larger of zero and a fixed function of the underlying price $S_T$:

* **Call** payoff: $\max(S_T - K, 0)$
* **Put** payoff: $\max(K - S_T, 0)$

$K$ is the **strike**. Before $T$ the option has a price greater than its
intrinsic value $\max(S_t - K, 0)$ because future moves still might push
it deeper in the money — this excess is the **time value**, and it's
where volatility shows up.

## 1.2 Why we use Black-76, not Black-Scholes-Merton

Most textbooks introduce **Black-Scholes-Merton (BSM)**, which prices an
option directly in terms of the spot $S$ under a risk-neutral
geometric-Brownian-motion model with constant rate $r$ and dividend yield
$q$. BSM is fine when you can borrow and lend in the underlying and you
know $r$ and $q$.

In crypto we don't have a clean risk-free rate, but we do have a
**liquid futures market**. The natural reference is therefore the
**forward price** $F$ implied by the futures, not the spot. Black (1976)
showed that if you reformulate the same option around a forward $F$, you
get a particularly clean formula — no $r - q$ messiness, just $F$ and a
discount factor $df$:

$$
\begin{aligned}
C &= df \cdot \big[F\,\Phi(d_1) - K\,\Phi(d_2)\big] \\
P &= df \cdot \big[K\,\Phi(-d_2) - F\,\Phi(-d_1)\big] \\
d_1 &= \frac{\ln(F/K) + \tfrac{1}{2}\sigma^2 T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}.
\end{aligned}
$$

This is **Black-76**. It's what every options venue we care about
(Deribit included) actually uses to mark its books.

## 1.3 Deribit's quoting conventions

Two crypto-specific wrinkles change *how* we use Black-76, but not the
formula itself.

**(a) The option premium is paid in coin, not USD.** A BTC call
quoted at `0.05` is `0.05 BTC`, not `0.05 USD`. To get a USD-style
Black-76 input you multiply by the matching future's mark price:

$$
\text{premium}_\text{USD} = \text{premium}_\text{coin} \cdot F
$$

This is exactly what
[`validation.validate_iv`](../../packages/analytics/src/basis_analytics/validation.py)
does before the IV solve.

**(b) The discount factor is effectively 1.** Inverse options settle
the premium and the payoff in the same currency at expiry against a
synthetic future, so there's no separate discounting to apply. Setting
`df = 1.0` in our pricer reproduces Deribit's `mark_iv` to within
numerical tolerance — that's the empirical proof in lecture 2.

## 1.4 Edge cases the code has to handle

* **At expiry** ($T = 0$). $d_1$ becomes $\pm\infty$, the formula
  evaluates to the intrinsic value, and most numerical libraries throw
  warnings. We special-case this branch and return $\max(F-K, 0)$ /
  $\max(K-F, 0)$ directly.
* **Zero vol** ($\sigma = 0$ with $T > 0$). Same intrinsic-value branch.
* **Vectorization**. Every input may be a scalar or an array; we use
  `np.broadcast_arrays` so a single call can price an entire option
  chain in one shot.

## 1.5 Where this lives in the code

[pricing.py](../../packages/analytics/src/basis_analytics/pricing.py)
implements exactly the formula above. Look at `_d1_d2` for the closed
form and `black76_price` for the broadcasting boilerplate. The function
returns a NumPy array, which composes directly with pandas — you can
pass a `Series.values` in, get an array out, and assign it back to a
column.

## 1.6 Common gotchas

| Symptom | Cause |
|---|---|
| IV solve returns NaN for short-dated ATM options | `T` is in **years**, not days. Convert with `T = days / 365.0`. |
| Calls and puts both negative | You broadcast `is_call` as a Python `bool`; passing an array of bools lets each strike pick its own side. |
| Prices bigger than `F` for very deep ITM calls | Discount factor mistake; the upper bound is `df * F`, not `F`. |
| Different IV than Deribit by exactly a factor of 100 | Deribit's `mark_iv` is in **percent** (e.g. `65.4` = 65.4 %). Divide by 100 before comparing. |

> **Next lecture**: solving for $\sigma$ given a quoted price.
