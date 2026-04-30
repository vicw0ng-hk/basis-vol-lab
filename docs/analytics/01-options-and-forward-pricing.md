# Options and Forward Pricing

An option pays at expiry. A call pays $\max(S_T - K, 0)$; a put pays
$\max(K - S_T, 0)$. Before expiry the option is worth more than intrinsic
value because future moves still matter. That extra value is where volatility
enters.

## Why Black-76

The dashboard prices options against the forward/futures mark $F$, not spot
$S$. Crypto has deep futures markets and no clean risk-free curve, so Black-76
is the natural model:

$$
\begin{aligned}
C &= df \cdot [F\Phi(d_1) - K\Phi(d_2)] \\
P &= df \cdot [K\Phi(-d_2) - F\Phi(-d_1)] \\
d_1 &= \frac{\ln(F/K) + \tfrac{1}{2}\sigma^2T}{\sigma\sqrt{T}},\quad
d_2 = d_1 - \sigma\sqrt{T}.
\end{aligned}
$$

For Deribit inverse options we use `df = 1`. The premium is quoted in coin, so
a `0.05 BTC` option premium becomes a USD-style model input by multiplying by
the matching futures mark:

$$
\text{premium}_{USD} = \text{premium}_{coin} \cdot F
$$

## Practical Edges

- At expiry or zero volatility, price is intrinsic value.
- Time is ACT/365 years, not calendar days.
- Deribit's `mark_iv` is a percent value, so divide by 100 before comparing.
- Vectorized NumPy inputs let one pricing call cover a full option chain.
