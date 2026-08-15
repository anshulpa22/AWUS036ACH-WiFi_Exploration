# Learning Progress

This page tracks the completion and key outcomes of the AWUS036ACH Wi-Fi
exploration labs.

## Progress Summary

- Total labs: 13
- Completed: 2
- In progress: 0
- Overall progress: 15%

## Lab Tracker

| Lab | Topic | Status | Completion Date | Key Outcome |
|---|---|---|---|---|
| 00 | Hardware overview | Completed | 2026-08-15 | Identified RTL8812AU, USB 3.x link, rtw88 driver and supported modes |
| 01 | Driver installation | Completed | 2026-08-15 | Verified in-kernel driver stack, firmware, USB binding and clean module reload |
| 02 | Interface management | Not started | — | — |
| 03 | Channel scanning | Not started | — | — |
| 04 | RSSI experiments | Not started | — | — |
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
