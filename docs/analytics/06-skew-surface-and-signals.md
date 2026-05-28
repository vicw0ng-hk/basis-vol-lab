# Skew, Surface, and Signals

A volatility surface plots IV by strike and expiry. The dashboard focuses on
two slices: the smile across strikes for one expiry, and the ATM term
structure across expiries.

## Smile Interpolation

Quoted strikes are discrete, but signals often need values between them. The
app uses PCHIP interpolation because it is smooth while preserving monotone
input shapes. Outside the quoted strike range, IV is held flat at the nearest
endpoint.

## Smile Summary

- **25-delta risk reversal**:
  $RR_{25} = \sigma_{25\Delta call} - \sigma_{25\Delta put}$. Positive values
  indicate call skew; negative values indicate put skew.
- **25-delta butterfly**:
  $BF_{25} = 0.5(\sigma_{25\Delta call}+\sigma_{25\Delta put})-\sigma_{ATM}$.
  Higher values mean richer wings and more priced tail risk.

## Headline Signals

Signals combine percentile-ranked inputs so carry, vol, skew, and open
interest can share one scale.

```text
carry_vol_divergence = pctile(carry) - pctile(IV - RV)
skew_stress = (pctile(abs(RR_25)) + pctile(OI concentration)) / 2
regime_alert = carry_pct >= threshold and skew_pct >= threshold and oi_pct >= threshold
```

Interpretation:

- Positive carry-vol divergence means carry is rich relative to the IV-RV
  spread; negative means vol is rich relative to carry.
- Skew stress rises when risk reversal extremes and concentrated option open
  interest rise together.
- A regime alert requires multiple dimensions to be extreme at the same time.

Rolling percentiles become more useful as the snapshot history grows.
