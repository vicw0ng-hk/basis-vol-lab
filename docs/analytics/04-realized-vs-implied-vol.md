# Realized vs Implied Volatility

Implied volatility (IV) is what option prices imply about future movement.
Realized volatility (RV) is what the underlying actually did over a past
window. Their spread is a core derivatives signal: persistent `IV > RV` means
options are expensive versus recent movement; `IV < RV` means they are cheap.

## Close-to-Close RV

For prices $P_0, P_1, \dots, P_n$, compute log returns and annualize their
standard deviation:

$$
\hat\sigma_{cc} = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n} r_i^2 \cdot annualization},
\quad r_i = \ln(P_i/P_{i-1})
$$

Crypto uses 365-day annualization because it trades continuously.

## Parkinson RV

Parkinson's estimator uses each bar's high/low range:

$$
\hat\sigma_P^2 = \frac{1}{4\ln2}\left(\ln\frac{H}{L}\right)^2
$$

It is more efficient than close-to-close under smooth price paths, but jumps
and missed intrabar extremes can bias it. The dashboard keeps both views.

## Using the Spread

Compare IV and RV on the same tenor. A 30-day ATM IV should be paired with a
30-day RV estimate, and both should use the same annualization convention.
