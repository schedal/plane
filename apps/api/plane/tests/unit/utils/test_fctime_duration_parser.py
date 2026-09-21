# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.fctime.parsers import DurationParseError, parse_duration_to_minutes


@pytest.mark.unit
class TestParseDurationToMinutes:
    @pytest.mark.parametrize(
        "value,expected",
        [
            # Decimal hours
            ("1.5", 90),
            ("2", 120),
            ("0.25", 15),
            ("0.5", 30),
            # Clock format
            ("0:30", 30),
            ("2:15", 135),
            ("1:00", 60),
            ("10:05", 605),
            # Shorthand
            ("90m", 90),
            ("2h", 120),
            ("2h 30m", 150),
            ("1h30m", 90),
            ("1.5h", 90),
            ("45m", 45),
            (" 2h ", 120),
        ],
    )
    def test_valid_durations(self, value, expected):
        assert parse_duration_to_minutes(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "   ",
            "abc",
            "2h30",  # missing unit on trailing number
            "1:75",  # clock minutes >= 60
            "1:2:3",  # malformed clock
            "h",
            "m",
            "-30m",
            "2x",
            "1,5",  # comma decimal separator not supported
            "0",  # zero duration
            "0:00",
            "0m",
            "-1.5",
            None,
            30,  # non-string input
            True,
        ],
    )
    def test_invalid_durations_raise(self, value):
        with pytest.raises(DurationParseError):
            parse_duration_to_minutes(value)

    def test_error_message_is_clear(self):
        with pytest.raises(DurationParseError, match="Invalid duration format"):
            parse_duration_to_minutes("garbage")
