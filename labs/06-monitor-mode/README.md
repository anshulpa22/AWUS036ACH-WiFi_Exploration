# Lab 06 — IEEE 802.11 Monitor Mode

## 1. Purpose

This lab demonstrates how to place the Alfa Network AWUS036ACH USB Wi-Fi
adapter into monitor mode, passively observe IEEE 802.11 management frames,
extract privacy-safe metadata and restore the adapter to normal managed mode.

The experiment uses one laptop with two wireless adapters:

- the internal Wi-Fi adapter maintains normal network connectivity;
- the AWUS036ACH performs passive monitor-mode observation.

The lab does not perform packet injection, deauthentication, password
collection or payload inspection.

Only monitor networks and radio channels that you are authorized to observe.

## 2. Learning Objectives

After completing this lab, the learner should be able to:

- distinguish managed mode from monitor mode;
- explain why a monitor interface normally has no IP address;
- identify IEEE 802.11 management-frame subtypes;
- explain the purpose of radiotap metadata;
- configure a legal channel under the active regulatory domain;
- capture privacy-safe frame metadata with `tshark`;
- interpret beacon timing and RSSI measurements;
- understand the limitations of passive frame capture;
- restore the adapter safely to NetworkManager control;
- automate monitor-mode setup, capture and cleanup.

## 3. Managed Mode and Monitor Mode

### 3.1 Managed Mode

Managed mode is the normal operating mode for a Wi-Fi client.

In managed mode, the interface:

1. scans for access points;
2. authenticates and associates with an access point;
3. negotiates Wi-Fi capabilities;
4. obtains an IP address;
5. sends and receives traffic through the associated network.

The interface normally processes only frames relevant to its connection.

### 3.2 Monitor Mode

Monitor mode exposes raw IEEE 802.11 frames received on the configured radio
channel.

A monitor interface:

- does not need to associate with an access point;
- normally has no IP address;
- remains fixed to a selected channel unless channel hopping is implemented;
- can observe management, control and data frames;
- receives radiotap metadata supplied by the driver.

Monitor mode does not automatically decrypt encrypted Wi-Fi traffic. Receiving
a frame is not equivalent to understanding its encrypted payload.

## 4. Test Architecture

The laptop used two independent wireless PHYs:

| Adapter | Role | Mode |
|---|---|---|
| Internal Wi-Fi adapter | Normal network connectivity | Managed |
| AWUS036ACH | Passive frame observation | Monitor |

The internal adapter remained connected while the AWUS036ACH was temporarily
removed from NetworkManager control.

## 5. Regulatory Requirements

The active regulatory domain was checked with:

```bash
iw reg get
