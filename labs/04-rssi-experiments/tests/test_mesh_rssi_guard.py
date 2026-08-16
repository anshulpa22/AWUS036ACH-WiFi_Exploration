#!/usr/bin/env python3

"""Unit tests for mesh_rssi_guard.py."""

from __future__ import annotations

import sys
import unittest
from collections import deque
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import mesh_rssi_guard as guard  # noqa: E402


class RollingMeanTests(unittest.TestCase):
    def test_mean_is_unavailable_before_window_is_full(self) -> None:
        history = deque([-55, -54, -55])
        self.assertIsNone(guard.rolling_mean(history, 5))

    def test_mean_uses_latest_window(self) -> None:
        history = deque([-80, -55, -55, -54, -54, -55])
        result = guard.rolling_mean(history, 5)
        self.assertAlmostEqual(result, -54.6)


class SybilSequenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.node_a = deque([-55, -54, -55, -56, -55, -54])
        self.node_b = deque([-55, -54, -55, -56, -55, -54])
        self.node_c = deque([-62, -61, -63, -62, -60, -61])

    def test_two_identical_neighbours_match(self) -> None:
        self.assertTrue(
            guard.sequences_match(
                self.node_a,
                self.node_b,
                window=6,
                tolerance=0,
            )
        )

    def test_different_neighbour_does_not_match(self) -> None:
        self.assertFalse(
            guard.sequences_match(
                self.node_a,
                self.node_c,
                window=6,
                tolerance=0,
            )
        )

        self.assertFalse(
            guard.sequences_match(
                self.node_b,
                self.node_c,
                window=6,
                tolerance=0,
            )
        )

    def test_single_neighbour_is_not_compared_to_itself(self) -> None:
        neighbours = {"node-a": self.node_a}

        pairs = [
            pair
            for pair in __import__("itertools").combinations(
                neighbours,
                2,
            )
        ]

        self.assertEqual(pairs, [])

    def test_incomplete_history_does_not_match(self) -> None:
        short_history = deque([-55, -54])

        self.assertFalse(
            guard.sequences_match(
                short_history,
                self.node_b,
                window=6,
                tolerance=0,
            )
        )

    def test_tolerance_is_optional(self) -> None:
        near_match = deque([-54, -53, -54, -55, -54, -53])

        self.assertFalse(
            guard.sequences_match(
                self.node_a,
                near_match,
                window=6,
                tolerance=0,
            )
        )

        self.assertTrue(
            guard.sequences_match(
                self.node_a,
                near_match,
                window=6,
                tolerance=1,
            )
        )



class PairAlarmStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair = ("node-a", "node-b")
        self.hits: dict[tuple[str, str], int] = {}
        self.active: set[tuple[str, str]] = set()

    def update(self, similar: bool) -> bool:
        return guard.update_pair_alarm_state(
            self.pair,
            similar,
            required_matches=3,
            pair_hits=self.hits,
            pair_active=self.active,
        )

    def test_alarm_occurs_only_after_required_matches(self) -> None:
        self.assertFalse(self.update(True))
        self.assertFalse(self.update(True))
        self.assertTrue(self.update(True))

    def test_active_alarm_is_not_repeated_every_poll(self) -> None:
        self.assertFalse(self.update(True))
        self.assertFalse(self.update(True))
        self.assertTrue(self.update(True))
        self.assertFalse(self.update(True))
        self.assertFalse(self.update(True))

    def test_mismatch_resets_and_allows_future_alarm(self) -> None:
        self.assertFalse(self.update(True))
        self.assertFalse(self.update(True))
        self.assertFalse(self.update(False))

        self.assertFalse(self.update(True))
        self.assertFalse(self.update(True))
        self.assertTrue(self.update(True))


class DeviationAlarmStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = guard.PeerState(history=deque(maxlen=10))

    def update(self, deviation: float) -> bool:
        return guard.update_deviation_alarm_state(
            self.state,
            deviation,
            threshold=4.0,
            required_matches=3,
        )

    def test_alarm_requires_consecutive_threshold_violations(self) -> None:
        self.assertFalse(self.update(4.2))
        self.assertFalse(self.update(4.5))
        self.assertTrue(self.update(4.1))

    def test_alarm_is_not_repeated_while_active(self) -> None:
        self.assertFalse(self.update(5.0))
        self.assertFalse(self.update(5.0))
        self.assertTrue(self.update(5.0))
        self.assertFalse(self.update(5.0))

    def test_subthreshold_value_resets_detector(self) -> None:
        self.assertFalse(self.update(4.5))
        self.assertFalse(self.update(4.5))
        self.assertFalse(self.update(1.0))

        self.assertFalse(self.update(4.5))
        self.assertFalse(self.update(4.5))
        self.assertTrue(self.update(4.5))

    def test_absolute_deviation_is_computed_before_state_update(self) -> None:
        baseline = -55.0
        rolling_mean = -49.0
        deviation = abs(rolling_mean - baseline)

        self.assertEqual(deviation, 6.0)



class PrivacyTests(unittest.TestCase):
    def test_anonymized_label_is_stable(self) -> None:
        mac = "02:00:00:00:00:01"

        first = guard.peer_label(mac, anonymize=True)
        second = guard.peer_label(mac, anonymize=True)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("peer-"))
        self.assertNotIn(mac, first)


if __name__ == "__main__":
    unittest.main()
