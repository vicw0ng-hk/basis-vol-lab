# Greeks

Greeks are option-price sensitivities. They make a portfolio's exposure
legible without repricing every scenario from scratch.

| Greek | Definition | Meaning |
| --- | --- | --- |
| Delta $\Delta$ | $\partial P / \partial F$ | Hedge ratio versus the forward. |
| Gamma $\Gamma$ | $\partial^2 P / \partial F^2$ | How quickly delta changes. |
| Vega $\nu$ | $\partial P / \partial \sigma$ | Price change per 1.00 vol shift. |
| Theta $\Theta$ | $\partial P / \partial T$ | Value of more time to expiry. |
| Rho $\rho$ | $\partial P / \partial r$ | Rate sensitivity; zero in this app's convention. |

## Black-76 Forms

$$
\begin{aligned}
\Delta_{call} &= df \cdot \Phi(d_1) \\
\Delta_{put} &= df \cdot (\Phi(d_1)-1) \\
\Gamma &= \frac{df \cdot \varphi(d_1)}{F\sigma\sqrt{T}} \\
\nu &= df \cdot F \cdot \varphi(d_1) \cdot \sqrt{T} \\
\Theta &= \frac{df \cdot F \cdot \varphi(d_1) \cdot \sigma}{2\sqrt{T}}
\end{aligned}
$$

Vega and gamma are the same for calls and puts. Delta carries the call/put
direction.

## Units

The implementation returns forward-denominated Greeks. Deribit publishes
coin-denominated Greeks, so compare units before comparing numbers:

- Coin delta is approximately forward delta divided by $F$.
- Coin vega is approximately forward vega divided by $F$.
- Theta sign conventions differ by venue; this app reports
  $\partial P / \partial T$.

Finite-difference tests check delta, gamma, and vega against the pricer.
