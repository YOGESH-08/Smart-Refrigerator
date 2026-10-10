# Wiring and pin map

The ESP32 DevKit V1 connects as follows:

| Function | ESP32 Pin | Notes |
| --- | --- | --- |
| DS18B20 data | GPIO4 | 4.7k pull-up resistor required |
| MQ-135 analog output | GPIO35 | Use a voltage divider if the board uses a 5V ADC range |
| Reed switch | GPIO27 | Door state; active when magnet is far away |
| HX711 DT | GPIO16 | Load-cell interface |
| HX711 SCK | GPIO17 | Clock for load-cell amplifier |
| TTP223 touch input | GPIO32 | Use to silence the buzzer |
| Fan transistor | GPIO25 | NPN transistor driver |
| Buzzer | GPIO26 | Active alarm output |
| Red LED | GPIO18 | Warning/alert indicator |
| Green LED | GPIO19 | Healthy state indicator |

## Notes

- The DS18B20 requires a pull-up resistor between the data line and the 3.3V rail.
- The MQ-135 is not a calibrated ppm sensor; it should be used as a relative trend indicator for gas rise.
- The load-cell module must be tared before use to remove the empty shelf weight.
- Keep the fan transistor circuit isolated from the ESP32 GPIO input with a base resistor.
