# korad_powersupply

Driver for the Korad KC3405P four channel power supply (Ethernet / UDP),
prepared for inclusion in [pymeasure](https://github.com/pymeasure/pymeasure).

The repository mirrors the layout of the pymeasure source tree, so every file sits where
it belongs in pymeasure:

| File | Purpose |
| --- | --- |
| `pymeasure/instruments/korad/kc3405p.py` | `KC3405P` instrument and `KC3405PChannel` |
| `pymeasure/instruments/korad/__init__.py` | exports `KC3405P` |
| `pymeasure/adapters/udp.py` | new generic `UDPAdapter` (the KC3405P is UDP only, which VISA cannot do) |
| `tests/instruments/korad/test_kc3405p.py` | protocol tests using `expected_protocol` |
| `tests/adapters/test_udp.py` | `UDPAdapter` tests against a local UDP socket |
| `docs/api/instruments/korad/` | Sphinx documentation |

## Usage

```python
from pymeasure.instruments.korad import KC3405P

psu = KC3405P("192.168.1.100")      # or KC3405P(adapter_instance)
psu.ch_1.voltage_setpoint = 5       # plain numbers are taken as V
psu.ch_1.current_setpoint = 0.5     # ... and A
psu.ch_1.output_enabled = True
print(psu.ch_1.voltage, psu.ch_1.current, psu.ch_1.mode)
psu.shutdown()                      # all outputs off
```

Voltages and currents (measurements, setpoints, protection thresholds) are
[pint](https://pint.readthedocs.io) quantities from `pymeasure.units.ureg`.
Setpoints also accept quantities in any compatible unit:

```python
from pymeasure.units import ureg

psu.ch_1.voltage_setpoint = 500 * ureg.mV
psu.ch_1.current_setpoint = 250 * ureg.mA
psu.ch_1.voltage.to("mV")           # <Quantity(5000.0, 'millivolt')>
psu.ch_1.voltage.magnitude          # 5.0
psu.ch_1.voltage_setpoint = 1 * ureg.A   # pint.DimensionalityError
```

Channels are `psu.ch_1` ... `psu.ch_4` (also `psu.channels`). See the docs for all properties
(protection thresholds, external trigger/switch/compensation, button lock, device info).

## Adding it to pymeasure

```sh
git clone https://github.com/pymeasure/pymeasure
scripts/add_to_pymeasure.sh path/to/pymeasure
```

The script copies the files above and registers `UDPAdapter` in
`pymeasure/adapters/__init__.py`. Then, by hand:

- add `korad/index` to the toctree in `docs/api/instruments/index.rst`,
- add an entry to `CHANGES.rst` (new instrument: Korad KC3405P, new `UDPAdapter`),
- run `pytest tests/instruments/korad tests/adapters/test_udp.py` and `flake8`.

## Changes compared to the previous standalone `korad.py`

- Now a pymeasure `Instrument` with `Channel`s, properties instead of get/set methods.
- Fixed channel range checks (`1 > channel > 4` was never true), inverted OCP/OVP
  verification, and a wrong read-back (OCP/OVP checked the voltage/current setpoint).
- Device info parsing splits at the first `:` only, so values containing colons survive.
- Setters no longer read back and compare; values are range-validated before sending instead.
- Not implemented (documented in the device manual): voltage/current auto-stepping,
  manual stepping and the LIST commands.
