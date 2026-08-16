# Anonymized Wi-Fi Scan Summary

- Timestamp: `2026-08-17T00:03:55+04:00`
- Interface: `<anonymized-wireless-interface>`
- PHY at scan time: `phy262`
- Regulatory country: `AE`
- BSS entries: `7`

SSIDs and BSSIDs are intentionally excluded.

| AP | Band | Channel | Frequency | Signal | Width | Secondary | Center segment | Security | SSID status |
|---|---|---:|---:|---:|---|---|---:|---|---|
| AP-01 | 2.4 GHz | 6 | 2437.0 MHz | -44.00 dBm | 20 MHz | no secondary | — | RSN present | Redacted |
| AP-02 | 2.4 GHz | 11 | 2462.0 MHz | -30.00 dBm | 20 MHz | no secondary | — | RSN present | Redacted |
| AP-03 | 5 GHz | 64 | 5320.0 MHz | -36.00 dBm | 80 MHz | below | 58 | RSN present | Redacted |
| AP-04 | 5 GHz | 64 | 5320.0 MHz | -38.00 dBm | 80 MHz | below | 58 | RSN present | Not advertised |
| AP-05 | 2.4 GHz | 1 | 2412.0 MHz | -38.00 dBm | 40 MHz | above | — | RSN present | Redacted |
| AP-06 | 2.4 GHz | 11 | 2462.0 MHz | -30.00 dBm | 20 MHz | no secondary | — | RSN present | Not advertised |
| AP-07 | 5 GHz | 36 | 5180.0 MHz | -72.00 dBm | 80 MHz | above | 42 | RSN present | Redacted |

## Notes

- Signal values come from the driver through `iw`.
- Advertised PHY rate is not application throughput.
- Width is inferred from HT/VHT operation information.
- A missing SSID line is recorded as `Not advertised`.
- The report does not determine whether a non-advertised SSID is intentionally hidden.
