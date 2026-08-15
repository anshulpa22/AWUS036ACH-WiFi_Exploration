# Lab 00 — AWUS036ACH Hardware Overview

## Objective

Identify the Alfa AWUS036ACH at the USB, kernel and Linux wireless layers and
establish its baseline capabilities before changing drivers or configuration.

## Test Environment

| Item | Observed value |
|---|---|
| Operating system | Ubuntu Linux |
| Kernel | 6.17.0-40-generic |
| Adapter | Alfa Network AWUS036ACH |
| USB ID | 0bda:8812 |
| Chipset | Realtek RTL8812AU |
| USB negotiated speed | 5000M |
| Kernel driver | rtw88_8812au |
| Driver transport module | rtw88_usb |
| Chip-specific module | rtw88_8812a |
| Wireless interface | wlx00c0caXXXXXX |
| Initial PHY | Dynamic; observed as phy8 and later phy10 |
| Initial interface mode | Managed |
| Reported TX-power setting | 20 dBm |

The interface and MAC address are partially anonymized because this is a public
repository.

## USB Identification

The adapter was identified using:

```bash
lsusb

Output
ID 0bda:8812 Realtek Semiconductor Corp. RTL8812AU
802.11a/b/g/n/ac 2T2R DB WLAN Adapter

## USB Link Speed

lsusb -t

Driver=rtw88_8812au, 5000M

## Driver Identification

The active driver was inspected with:

ethtool -i <interface>
modinfo rtw88_8812au

Observed driver:

driver: rtw88_8812au
version: 6.17.0-40-generic
firmware-version: N/A

The system is using the in-kernel rtw88_8812au driver. No third-party DKMS
driver was installed during this lab.

## Wireless Interface Identification

Commands:

iw dev
ip -brief link

Two Wi-Fi interfaces were present:

The internal Intel adapter was connected to the existing WLAN.
The Alfa adapter was present in managed mode but was not associated.

A PHY number such as phy8 or phy10 is not permanent. It can change after a
USB reconnection or driver reload.

A PHY should therefore be obtained dynamically:

ALFA_IF=<alfa-interface>
ALFA_PHY=$(iw dev "$ALFA_IF" info | awk '/wiphy/ {print "phy"$2}')
echo "$ALFA_PHY"
5. Supported Interface Modes

The current driver advertised:

IBSS
Managed
AP
AP/VLAN
Monitor

The driver did not advertise mesh point mode. Native 802.11s operation cannot
therefore be assumed to work with this driver. This will be investigated before
the 802.11s lab.

## Frequency Bands

The adapter exposed both:

2.4 GHz channels
5 GHz channels

Channel availability, transmit power and the ability to initiate transmission
depend on the regulatory domain, driver and device capabilities.

## UAE Regulatory Domain

Initially, the global regulatory domain was:

country 00: DFS-UNSET

The internal Intel adapter used a self-managed UAE domain, while the Alfa
adapter followed the global world domain.

Because the experiment is being performed in the UAE, the global domain was
temporarily set using:

sudo iw reg set AE

Verification:

iw reg get

The resulting global domain was:

country AE: DFS-FCC

This command applies legal UAE regulatory rules; it is not a mechanism for
bypassing channel or transmit-power restrictions.

The Alfa adapter continued to report 20 dBm as its maximum setting. Several
5 GHz channels also retained no IR restrictions, indicating an additional
driver or device limitation that requires further investigation.

## Key Findings
The AWUS036ACH was detected as a Realtek RTL8812AU device.
It operated at USB 3.x SuperSpeed (5000M).
Ubuntu used the in-kernel rtw88_8812au driver.
Managed, AP and monitor modes were advertised.
Native 802.11s mesh-point mode was not advertised.
PHY numbers changed after re-enumeration and must not be hard-coded.
The adapter followed the global regulatory domain rather than the internal
Intel adapter's self-managed domain.
Regulatory and device limits must be respected during all RF experiments.
