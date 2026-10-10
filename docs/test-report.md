# Test report

## Automated validation

| Area | Result | Command |
| --- | --- | --- |
| Alert engine | Passed | `python -m pytest server/tests/test_alert_engine.py -q --basetemp=.pytest_tmp` |
| API endpoints | Passed | `python -m pytest server/tests/test_api.py -q --basetemp=.pytest_tmp` |
| Full backend suite | Passed | `python -m pytest server/tests -q --basetemp=.pytest_tmp` |

## Summary

The backend includes a pure threshold evaluator and a Flask service layer that validates incoming sensor payloads, stores readings, and maintains modelled alert lifecycle state. All tests pass under the current configuration.

## Known limitations

| Limitation | Impact |
| --- | --- |
| MQ-135 is relative gas trend detection, not absolute ppm measurement | Gas thresholding is trend-based and should be treated as a qualitative indicator |
| Simulator replaces physical hardware | Demo data does not capture true enclosure thermal delay or bad sensor drift |
| SQLite is local-lab infrastructure | The project is designed for a prototype environment, not a large multi-node distributed telemetry platform |
| No physical hardware validation was performed in this environment | EEPROM, load-cell calibration, and real WiFi throughput remain to be validated on-device |
