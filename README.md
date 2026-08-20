# Alfa AWUS036ACH Wi-Fi Exploration

A hands-on learning repository for exploring Linux Wi-Fi, RF measurements,
network performance, monitor mode, mesh networking and wireless security using
the Alfa Network AWUS036ACH USB Wi-Fi adapter.

## Objectives

- Understand the AWUS036ACH hardware and Linux driver architecture.
- Learn Linux wireless-interface configuration and troubleshooting.
- Measure RSSI, latency, packet loss and network throughput.
- Explore 2.4 GHz and 5 GHz Wi-Fi channels.
- Perform authorized passive wireless packet capture.
- Build 802.11s and BATMAN-adv mesh networks.
- Automate wireless measurements using shell and Python.
- Document reproducible experiments and results.

## Hardware

- Alfa Network AWUS036ACH
- USB 3.0 interface
- Dual-band 2.4 GHz and 5 GHz operation
- Two external antennas
- Linux computer running Ubuntu
- Additional Wi-Fi node or access point for selected experiments

## Learning Roadmap

| Lab | Topic | Status |
|---|---|---|
| 00 | Hardware overview | Completed |
| 01 | Driver installation and verification | Completed |
| 02 | Linux Wi-Fi interface management | Completed |
| 03 | Channel scanning and network discovery | Completed |
| 04 | RSSI measurement experiments | Completed |
| 05 | TCP and UDP throughput testing | Not started |
| 06 | Monitor mode and passive capture | Completed |
| 07 | 802.11s mesh networking | Not started |
| 08 | BATMAN-adv Layer-2 mesh | Not started |
| 09 | Long-range Wi-Fi testing | Not started |
| 10 | Wi-Fi security analysis | Not started |
| 11 | Python measurement automation | Not started |
| 12 | Final mesh testbed project | Not started |

## Repository Structure

```text
.
├── docs/       # Progress, troubleshooting and supporting documentation
├── labs/       # Individual hands-on learning exercises
├── scripts/    # Reusable shell and Python utilities
└── results/    # Sanitized sample measurements
