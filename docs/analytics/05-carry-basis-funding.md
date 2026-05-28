# Carry, Basis, and Funding

Carry is the annualized return implied by holding a derivatives position to
expiry if the underlying price stays flat. For a spot/futures basis trade:

$$
carry = \frac{F-S}{S}\cdot\frac{365}{days\ to\ expiry}
$$

Positive carry means contango: futures are rich to spot. Negative carry means
backwardation: futures are cheap to spot.

## Basis Curve

Each dated futures expiry has its own carry. Plotting carry by expiry gives a
basis curve. Steep contango can point to leveraged-long demand; inversion can
point to near-term sell pressure or funding stress.

## Perpetual Funding

A perpetual has no expiry, so exchanges use periodic funding to keep it near
the spot index. If the 8-hour funding rate is $r_{8h}$, annualized funding is:

$$
r_{ann} = (1 + r_{8h})^{3\cdot365} - 1
$$

Compounding matters when rates spike or go negative. Simple multiplication is
fine for a quick headline, but compounding is the defensible series.

## Dashboard Use

The Carry page shows perp funding beside dated-futures basis so the front end
of the curve and the 30-90 day futures market can be read together.

Common checks:

- Filter near-expiry futures; annualization explodes as days to expiry goes
  to zero.
- Match quote conventions before comparing venue basis values.
- Remember that borrow costs can erase apparent basis profits.
