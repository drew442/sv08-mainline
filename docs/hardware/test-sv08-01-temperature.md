# Test printer 01: cold hotend reporting about 120°C

## Post-repair check: ambient anomaly no longer observed

After the owner reported repairing the thermistor, three read-only samples on
2026-09-05 at 05:58:18–05:58:38 UTC showed hotend **29.42–29.44°C** and bed
**29.40–29.42°C**. Both heater targets were zero throughout; the printer reported
ready/standby, with no configuration warnings.

The extruder, custom hotend thermistor and bed heater configuration fields are
identical to the earlier API capture: hotend `my_thermistor_e` with configured
11,500Ω pull-up. The previous approximately 120°C ambient reading is no longer
present. No sensor setting change was needed for this recheck.

This verifies plausible ambient readings and short-term stability, not sensor
part number or accuracy at printing temperatures. Repair details remain
unspecified. No heaters, motors, restart or configuration changes were commanded.
See the [post-repair record](../../profiles/test-sv08-01/observations/2026-09-05-post-repair.json).

## Original observation and diagnostic calculation

Date: 2026-09-05. The owner reports **28°C measured with an external instrument**,
while Klipper reports approximately 120°C with a zero heater target. Instrument
type, accuracy and measurement point have not been recorded. This establishes an
owner-observed discrepancy; the installed sensor type remains unknown.

## Does a PT1000 explain the reading?

A PT1000 is a platinum resistance sensor, distinct from the NTC thermistor model
currently configured. At 28°C, the Callendar–Van Dusen coefficients used by
[Klipper's PT1000 model](../../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/adc_temperature.py)
give approximately **1,108.98 ohms**.

The active configuration instead uses `my_thermistor_e`, defined by
25°C/110000Ω, 100°C/7008Ω and 220°C/435Ω, with `pullup_resistor: 11500` and no
inline resistor. Using the exact
[vendor thermistor conversion](../../upstream/sovol-sv08/home/sovol/klipper/klippy/extras/thermistor.py)
and an ideal sensor-to-ground divider gives:

| Assumed effective physical pull-up | PT1000 actual temperature | Predicted display under the current NTC configuration |
| --- | --- | --- |
| 11,500Ω | 28°C | 172.34°C |
| 4,700Ω | 28°C | 134.26°C |
| 3,225.57Ω | 28°C | 120.00°C |

The first two rows are scenarios, not measurements of the board. The third row
is the value required by the assumed circuit to fit the observed temperatures;
it is **not a recommended configuration value**.

Therefore a PT1000 in an NTC configuration can produce a large false temperature,
but the specific 28°C -> 120°C observation does not identify a PT1000 by itself.
The effective circuit, sensor/wiring condition or deployed ADC behavior would
need to explain the difference. Do not tune a pull-up value to fit one room
temperature reading or simply switch sensor types on that evidence.

Under the present NTC conversion, a displayed 120°C corresponds to an inferred
normalized ADC fraction of 0.255846 and an apparent resistance of 3,953.80Ω
when interpreted with the configured 11,500Ω pull-up. These are computed from
the reported temperature, not raw ADC or resistance measurements.

The inspected installed source matched the pinned vendor `thermistor.py`,
`adc_temperature.py`, `src/adccmds.c` and `src/stm32/adc.c`; the latter returns
the ADC register value directly. This does not prove the separately built,
dirty toolhead firmware matches those on-disk sources.

## Reproduce the calculation offline

From the repository root (no printer connection or settings change):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import sys
sys.path.insert(0, 'upstream/sovol-sv08/home/sovol/klipper/klippy')
from extras.thermistor import Thermistor

ntc = Thermistor(11500, 0)
ntc.setup_coefficients(25, 110000, 100, 7008, 220, 435)
t = 28.0
r_pt1000 = 1000 * (1 + 3.9083e-3*t - 5.775e-7*t*t)
adc_at_120 = ntc.calc_adc(120.0)
print('PT1000 resistance:', r_pt1000)
for pullup in (11500, 4700):
    adc = r_pt1000 / (pullup + r_pt1000)
    print('Assumed pull-up / displayed temperature:', pullup, ntc.calc_temp(adc))
print('Inferred ADC fraction at displayed 120C:', adc_at_120)
print('Pull-up required to fit 28C -> 120C:',
      r_pt1000 * (1-adc_at_120) / adc_at_120)
PY
```

## Sensor identification guidance from the original investigation

With the printer powered off and the sensor disconnected from its board input,
measure resistance across the sensor leads. Around 1.11 kΩ at 28°C supports a
PT1000 identification; it does not verify the board pull-up or operation across
the temperature range. An open/intermittent sensor or a substantially different
resistance needs investigation before selecting settings. Do not measure
resistance on a powered or connected input.

Confirm the exact installed sensor/kit, connection and board circuit next.
The [Trianglelab CHCB-SV08 listing](https://trianglelab.net/products/chcb-sv08-hotend-hot-side)
offers NTC and PT1000 options, so the hotend family name is insufficient.
[Klipper's configuration reference](https://www.klipper3d.org/Config_Reference.html#directly-connected-pt1000-sensor)
requires the appropriate sensor model and pull-up; both sources checked 2026-09-05.

Do not command heat or printing until sensor identity and temperature conversion
are verified. No live sensor configuration, PID values or heater settings were
changed during this analysis.
