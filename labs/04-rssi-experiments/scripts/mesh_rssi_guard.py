#!/usr/bin/env python3

"""Monitor per-neighbour RSSI on a Linux wireless or mesh interface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Optional, Sequence, TextIO


STATION_RE = re.compile(r"^Station\s+([0-9a-fA-F:]{17})\s+\(on\s+[^)]+\)")
SIGNAL_RE = re.compile(r"^\s*signal:\s*(-?\d+)")


@dataclass
class PeerState:
    history: Deque[int]
    calibration: list[int] = field(default_factory=list)
    baseline: Optional[float] = None
    deviation_hits: int = 0
    deviation_active: bool = False
    flatline_active: bool = False


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor per-neighbour RSSI using 'iw station dump' and raise "
            "baseline-deviation and possible Sybil-correlation alarms."
        )
    )
    parser.add_argument("--interface", required=True, help="Wireless/mesh interface")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--window", type=int, default=10)
    parser.add_argument("--calibration-samples", type=int, default=20)
    parser.add_argument("--deviation-threshold", type=float, default=4.0)
    parser.add_argument("--deviation-consecutive", type=int, default=3)
    parser.add_argument(
        "--flatline-samples",
        type=int,
        default=0,
        help="Optional single-peer flatline window; 0 disables it (default: 0)",
    )
    parser.add_argument("--flatline-tolerance", type=float, default=0.0)
    parser.add_argument("--sybil-window", type=int, default=8)
    parser.add_argument(
        "--sybil-tolerance",
        type=float,
        default=0.0,
        help="Allowed per-sample difference; 0 requires exact matches",
    )
    parser.add_argument("--sybil-consecutive", type=int, default=3)
    parser.add_argument("--csv", default="/tmp/mesh-rssi-samples.csv")
    parser.add_argument("--alerts", default="/tmp/mesh-rssi-alerts.jsonl")
    parser.add_argument("--anonymize", action="store_true")
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> None:
    positive_integer_fields = (
        "window",
        "calibration_samples",
        "deviation_consecutive",
        "sybil_window",
        "sybil_consecutive",
    )
    if args.interval <= 0:
        raise ValueError("--interval must be greater than zero")
    for field_name in positive_integer_fields:
        if getattr(args, field_name) <= 0:
            raise ValueError(f"--{field_name.replace('_', '-')} must be positive")
    if args.flatline_samples < 0:
        raise ValueError("--flatline-samples cannot be negative")
    if args.deviation_threshold < 0:
        raise ValueError("--deviation-threshold cannot be negative")
    if args.flatline_tolerance < 0 or args.sybil_tolerance < 0:
        raise ValueError("tolerance values cannot be negative")


def validate_interface(interface: str) -> None:
    result = subprocess.run(
        ["iw", "dev", interface, "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "interface not found"
        raise RuntimeError(f"'{interface}' is not usable: {message}")


def read_station_signals(interface: str) -> dict[str, int]:
    result = subprocess.run(
        ["iw", "dev", interface, "station", "dump"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "iw station dump failed")

    signals: dict[str, int] = {}
    current_mac: Optional[str] = None
    for line in result.stdout.splitlines():
        station_match = STATION_RE.match(line)
        if station_match:
            current_mac = station_match.group(1).lower()
            continue
        signal_match = SIGNAL_RE.match(line)
        if current_mac is not None and signal_match:
            signals[current_mac] = int(signal_match.group(1))
            current_mac = None
    return signals


def rolling_mean(history: Deque[int], window: int) -> Optional[float]:
    if len(history) < window:
        return None
    values = list(history)[-window:]
    return sum(values) / len(values)


def update_deviation_alarm_state(
    state: PeerState,
    deviation: float,
    threshold: float,
    required_matches: int,
) -> bool:
    """Update deviation state and return True only for a new alarm."""

    if deviation >= threshold:
        state.deviation_hits += 1
    else:
        state.deviation_hits = 0
        state.deviation_active = False
        return False

    if (
        state.deviation_hits >= required_matches
        and not state.deviation_active
    ):
        state.deviation_active = True
        return True

    return False



def sequences_match(
    first: Sequence[int],
    second: Sequence[int],
    window: int,
    tolerance: float,
) -> bool:
    """Return whether two time-aligned RSSI windows match."""

    if len(first) < window or len(second) < window:
        return False

    first_values = list(first)[-window:]
    second_values = list(second)[-window:]

    return all(
        abs(a - b) <= tolerance
        for a, b in zip(first_values, second_values)
    )


def update_pair_alarm_state(
    pair: tuple[str, str],
    similar: bool,
    required_matches: int,
    pair_hits: dict[tuple[str, str], int],
    pair_active: set[tuple[str, str]],
) -> bool:
    """Update pair state and return True only for a new alarm."""

    if similar:
        pair_hits[pair] = pair_hits.get(pair, 0) + 1
    else:
        pair_hits[pair] = 0
        pair_active.discard(pair)
        return False

    if (
        pair_hits[pair] >= required_matches
        and pair not in pair_active
    ):
        pair_active.add(pair)
        return True

    return False



def peer_label(mac: str, anonymize: bool) -> str:
    if not anonymize:
        return mac
    digest = hashlib.sha256(mac.encode("utf-8")).hexdigest()[:10]
    return f"peer-{digest}"


def emit_alert(
    alert_file: TextIO,
    kind: str,
    peers: list[str],
    message: str,
    anonymize: bool,
) -> None:
    labels = [peer_label(peer, anonymize) for peer in peers]
    event = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "type": kind,
        "peers": labels,
        "message": message,
    }
    print(f"ALARM [{kind}] {', '.join(labels)}: {message}", file=sys.stderr)
    alert_file.write(json.dumps(event) + "\n")
    alert_file.flush()


def ensure_parent_directory(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def main() -> int:
    args = parse_arguments()
    try:
        validate_arguments(args)
        validate_interface(args.interface)
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    max_history = max(args.window, args.flatline_samples, args.sybil_window)
    states: dict[str, PeerState] = {}
    pair_hits: dict[tuple[str, str], int] = {}
    pair_active: set[tuple[str, str]] = set()

    ensure_parent_directory(args.csv)
    ensure_parent_directory(args.alerts)
    csv_exists = os.path.exists(args.csv) and os.path.getsize(args.csv) > 0

    print("Mesh RSSI guard started")
    print(f"Interface: {args.interface}")
    print(f"Polling interval: {args.interval} seconds")
    print(f"Rolling window: {args.window} samples")
    print(f"Calibration: {args.calibration_samples} samples")
    print(f"Deviation threshold: {args.deviation_threshold} dB")
    print(f"Cross-neighbour match tolerance: {args.sybil_tolerance} dB")
    print(
        "Single-neighbour flatline detection: disabled"
        if args.flatline_samples == 0
        else f"Single-neighbour flatline detection: {args.flatline_samples} samples"
    )
    print("Press Ctrl+C to stop")

    try:
        with open(args.csv, "a", newline="", encoding="utf-8", buffering=1) as csv_file, open(
            args.alerts, "a", encoding="utf-8", buffering=1
        ) as alert_file:
            fieldnames = [
                "timestamp",
                "peer",
                "rssi_dbm",
                "rolling_mean_dbm",
                "baseline_dbm",
                "deviation_db",
                "state",
            ]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()

            while True:
                timestamp = datetime.now().astimezone().isoformat()
                try:
                    signals = read_station_signals(args.interface)
                except RuntimeError as error:
                    print(f"Warning: {error}", file=sys.stderr)
                    time.sleep(args.interval)
                    continue

                if not signals:
                    print(f"{timestamp} no connected stations found", flush=True)
                    time.sleep(args.interval)
                    continue

                # Clearing a missing peer's history prevents comparisons of
                # sequences collected during different polling rounds.
                for mac, state in states.items():
                    if mac not in signals:
                        state.history.clear()
                        state.deviation_hits = 0
                        state.deviation_active = False
                        state.flatline_active = False

                for mac, rssi in sorted(signals.items()):
                    if mac not in states:
                        states[mac] = PeerState(history=deque(maxlen=max_history))
                        print(f"{timestamp} discovered {peer_label(mac, args.anonymize)}")

                    state = states[mac]
                    state.history.append(rssi)

                    if state.baseline is None:
                        state.calibration.append(rssi)
                        if len(state.calibration) >= args.calibration_samples:
                            state.baseline = sum(state.calibration) / len(state.calibration)
                            print(
                                f"{timestamp} baseline established for "
                                f"{peer_label(mac, args.anonymize)}: "
                                f"{state.baseline:.2f} dBm"
                            )

                    mean = rolling_mean(state.history, args.window)
                    deviation: Optional[float] = None

                    if mean is not None and state.baseline is not None:
                        deviation = abs(mean - state.baseline)
                        new_deviation_alarm = (
                            update_deviation_alarm_state(
                                state,
                                deviation,
                                args.deviation_threshold,
                                args.deviation_consecutive,
                            )
                        )

                        if new_deviation_alarm:
                            emit_alert(
                                alert_file,
                                "RSSI_DEVIATION",
                                [mac],
                                (
                                    f"rolling mean {mean:.2f} dBm differs from "
                                    f"baseline {state.baseline:.2f} dBm by "
                                    f"{deviation:.2f} dB"
                                ),
                                args.anonymize,
                            )
                            

                    if (
                        args.flatline_samples > 0
                        and len(state.history) >= args.flatline_samples
                    ):
                        recent = list(state.history)[-args.flatline_samples:]
                        spread = max(recent) - min(recent)
                        is_flat = spread <= args.flatline_tolerance
                        if is_flat and not state.flatline_active:
                            emit_alert(
                                alert_file,
                                "RSSI_FLATLINE",
                                [mac],
                                (
                                    f"last {args.flatline_samples} samples "
                                    f"have spread {spread:.2f} dB"
                                ),
                                args.anonymize,
                            )
                            state.flatline_active = True
                        elif not is_flat:
                            state.flatline_active = False

                    active_states: list[str] = []
                    if state.deviation_active:
                        active_states.append("deviation")
                    if state.flatline_active:
                        active_states.append("flatline")

                    writer.writerow(
                        {
                            "timestamp": timestamp,
                            "peer": peer_label(mac, args.anonymize),
                            "rssi_dbm": rssi,
                            "rolling_mean_dbm": f"{mean:.2f}" if mean is not None else "",
                            "baseline_dbm": (
                                f"{state.baseline:.2f}" if state.baseline is not None else ""
                            ),
                            "deviation_db": (
                                f"{deviation:.2f}" if deviation is not None else ""
                            ),
                            "state": ",".join(active_states) or "normal",
                        }
                    )

                eligible = [
                    mac
                    for mac, state in states.items()
                    if mac in signals and len(state.history) >= args.sybil_window
                ]
                observed_pairs: set[tuple[str, str]] = set()

                for first, second in itertools.combinations(sorted(eligible), 2):
                    pair = (first, second)
                    observed_pairs.add(pair)
                    similar = sequences_match(
                        states[first].history,
                        states[second].history,
                        args.sybil_window,
                        args.sybil_tolerance,
                    )
                    


                    new_pair_alarm = update_pair_alarm_state(
                        pair,
                        similar,
                        args.sybil_consecutive,
                        pair_hits,
                        pair_active,
                    )

                    if new_pair_alarm:
                        
                        emit_alert(
                            alert_file,
                            "POSSIBLE_SYBIL_CORRELATION",
                            [first, second],
                            (
                                f"RSSI sequences matched within "
                                f"{args.sybil_tolerance:.2f} dB over "
                                f"{args.sybil_window} samples"
                            ),
                            args.anonymize,
                        )
                        # pair_active is updated by update_pair_alarm_state()

                for pair in list(pair_hits):
                    if pair not in observed_pairs:
                        pair_hits[pair] = 0
                        pair_active.discard(pair)

                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nMesh RSSI guard stopped")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())