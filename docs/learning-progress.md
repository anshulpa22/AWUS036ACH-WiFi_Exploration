# Learning Progress

This page tracks the completion and key outcomes of the AWUS036ACH Wi-Fi
exploration labs.

## Progress Summary

- Total labs: 13
- Completed: 5
- In progress: 0
- Overall progress: 38%

## Lab Tracker

| Lab | Topic | Status | Completion Date | Key Outcome |
|---|---|---|---|---|
| 00 | Hardware overview | Completed | 2026-08-15 | Identified RTL8812AU, USB 3.x link, rtw88 driver and supported modes |
| 01 | Driver installation | Completed | 2026-08-15 | Verified in-kernel driver stack, firmware, USB binding and clean module reload |
| 02 | Interface management | Completed | 2026-08-16 | Compared Linux Wi-Fi management layers and diagnosed an RF-kill-related re-enumeration sequence |
| 03 | Channel scanning | Completed | 2026-08-17 | Compared NetworkManager and `iw` scans and created an anonymized reporting script |
| 04 | RSSI experiments | Not started | 2026-08-17 | Developed and tested per-neighbour RSSI deviation and possible Sybil-correlation monitoring |
| 05 | Throughput testing | Not started | — | — |
| 06 | Monitor mode | Not started | — | — |
| 07 | 802.11s mesh | Not started | — | — |
| 08 | BATMAN-adv | Not started | — | — |
| 09 | Long-range testing | Not started | — | — |
| 10 | Wi-Fi security | Not started | — | — |
| 11 | Python automation | Not started | — | — |
| 12 | Final project | Not started | — | — |

## Status Definitions

- **Not started:** No experimental work has begun.
- **In progress:** Theory or experimentation is underway.
- **Completed:** Procedure, results and conclusions are documented.
- **Blocked:** Progress depends on unresolved hardware or software issues.

## Learning Journal

Important findings, unexpected behaviour and decisions will be summarized here
as the labs progress.

### 2026-08-15 — Lab 00

The AWUS036ACH was detected as USB device `0bda:8812` and negotiated a 5000M
USB link. Ubuntu loaded the in-kernel `rtw88_8812au` driver. Managed, AP and
monitor modes were advertised, but mesh-point mode was not. The adapter follows
the global regulatory domain, which was temporarily changed from the world
domain to the UAE `AE` domain for compliant local testing.

### 2026-08-15 — Lab 01

The in-kernel `rtw88_8812au` driver was verified from USB modalias matching
through firmware initialization. No conflicting Realtek DKMS module was
installed. Firmware `52.14.0` initialized successfully, USB runtime autosuspend
was disabled and the driver completed a controlled unload/reload test without
affecting the internal Wi-Fi interface.

### 2026-08-16 — Lab 02

The Linux USB, driver, PHY, interface, NetworkManager, RF-kill and IP-routing
layers were studied using the AWUS036ACH and the internal Intel adapter.
Administrative state was shown to be independent of Wi-Fi association and
NetworkManager ownership. A targeted RF-kill experiment was followed by
repeated USB re-enumeration; the adapter subsequently recovered and passed a
timestamped 60-second stability observation. The internal adapter also
demonstrated an intentional hybrid configuration containing an additional
static IPv4 address alongside a DHCP address.

### 2026-08-17 — Lab 03

The AWUS036ACH completed high-level NetworkManager scans and lower-level `iw`
scans without USB resets. The experiment examined active and passive discovery,
SSID/BSSID roles, 2.4 GHz overlap, DFS channels, signal measurements and
20/40/80 MHz operation. A reusable Bash script was developed to create
anonymized Markdown reports. Testing identified and corrected an RF-kill
substring bug, an AWK portability issue and a channel-width interpretation
issue. Timestamped reports are ignored while one reviewed sample is retained.


### 2026-08-17 — Lab 04

Developed a tutorial and Python monitoring tool for collecting RSSI measurements
from every wireless neighbour reported by `iw station dump`. The tool maintains
a rolling mean and calibration baseline independently for each neighbour and
raises an anomaly when the mean deviation exceeds a configured threshold for
multiple consecutive observations.

The experiment also investigates a possible Sybil indicator by comparing
time-aligned RSSI sequences belonging to different neighbour identities. An
alert is raised only when two neighbours produce matching sequences across
multiple consecutive windows. This is a heuristic rather than proof of an
attack, because co-located devices, quantized RSSI readings and stable radio
conditions can also create similar observations.

Single-neighbour constant RSSI values are not treated as a Sybil indicator.
The optional flatline detector is disabled by default. Fifteen unit tests
verified the rolling-mean, deviation-alarm, anonymization, sequence-comparison
and alarm-state logic.
