# Wiring and pin map

Use the ESP32 DevKit V1 (30-pin) pin assignments below. Disconnect USB power while changing wiring.

| Function | ESP32 pin | Connection / notes |
| --- | --- | --- |
| DS18B20 DATA | GPIO4 | 4.7 kΩ pull-up from DATA to 3.3 V |
| MQ-135 AO | GPIO34 | ADC1 input; reduce AO to 3.3 V or less with a suitable divider; readings are raw 0–4095 ADC counts |
| Reed switch | GPIO27 | `INPUT_PULLUP`; firmware reports status as **SENSOR UNVERIFIED** until magnet and polarity are checked |
| TTP223 OUT | GPIO14 | Assumed HIGH on touch; verify your module's output mode |
| RC522 SDA/SS | GPIO5 | 3.3 V only |
| RC522 SCK | GPIO18 | SPI clock |
| RC522 MOSI | GPIO23 | SPI MOSI |
| RC522 MISO | GPIO19 | SPI MISO |
| RC522 RST | GPIO22 | Reset |
| RC522 supply | 3.3 V | Do not power the RC522 from 5 V; connect GND to ESP32 GND |
| Fan control | GPIO26 | BC547 base through 1 kΩ; fan switched on 5 V supply, not from ESP32 GPIO |
| Active buzzer | GPIO13 | Use a transistor driver if the buzzer current exceeds GPIO capability |
| Red LED | GPIO15 | 220 Ω series resistor; GPIO15 is a boot-strapping pin, move it if boot issues occur |
| Green LED | GPIO21 | 220 Ω series resistor |

## Electrical and behavior notes

- Join ESP32 ground and external fan-supply ground. Add suitable transient protection for the fan, and verify the BC547 current rating against the fan's start-up current.
- Do not connect 5 V directly to GPIO34. ESP32 inputs are not 5 V tolerant.
- MQ-135 readings are for relative trend only; they are not calibrated ppm, food spoilage detection, or a safety assessment.
- Door alarms remain disabled in firmware until the magnet is installed and GPIO27's open/closed polarity has been verified.
- A TTP223 touch edge mutes the buzzer for 30 seconds; the red LED and fan remain commanded on while the temperature alarm persists.
- The dashboard reports firmware-commanded outputs. The current hardware has no actuator feedback sensors, so it cannot verify that a fan, LED, or buzzer physically operated.
- Load cell/HX711 and humidity are excluded from this firmware.

At boot, the serial monitor prints the pin map and RC522 version register. The firmware recognizes `0x88`, `0x90`, `0x91`, and `0x92`; `0x00`, `0xFF`, or any other value (including `0x82`) is reported as unrecognized and does not mark the reader healthy. Check 3.3 V, common ground, and the five SPI/control connections above, especially if temporary headers are being used. A recognized version confirms register communication only; test a compatible 13.56 MHz card and look for its UID log. Each two-second sensor log includes temperature, raw gas ADC, reed switch level, touch state, buzzer, fan, and LED commands.
