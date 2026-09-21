# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Duration string parser for the fctime app.

Accepted input forms (all whitespace-tolerant):
  - Decimal hours:   "1.5"  -> 90 minutes, "2" -> 120 minutes
  - Clock format:    "0:30" -> 30 minutes, "2:15" -> 135 minutes
  - Shorthand:       "90m" -> 90, "2h" -> 120, "2h 30m" / "1h30m" -> 150
"""

import re

# Bare number: interpreted as (decimal) hours
_DECIMAL_HOURS_RE = re.compile(r"^\d+(?:\.\d+)?$")
# Clock format H:MM (minutes component must be < 60)
_CLOCK_RE = re.compile(r"^(\d+):([0-5]?\d)$")
# Shorthand tokens: optional hours part and/or minutes part
_SHORTHAND_RE = re.compile(r"^(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+(?:\.\d+)?)\s*m)?$", re.IGNORECASE)

INVALID_DURATION_MESSAGE = (
    "Invalid duration format. Use decimal hours (e.g. '1.5'), clock format (e.g. '2:15'), "
    "or shorthand (e.g. '90m', '2h', '2h 30m')."
)


class DurationParseError(ValueError):
    """Raised when a duration string cannot be parsed."""


def parse_duration_to_minutes(value):
    """Parse a duration string into a positive number of minutes.

    Raises DurationParseError on any unparseable or non-positive input.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        raise DurationParseError(INVALID_DURATION_MESSAGE)

    text = value.strip()
    if not text:
        raise DurationParseError(INVALID_DURATION_MESSAGE)

    minutes = None

    if _DECIMAL_HOURS_RE.match(text):
        minutes = round(float(text) * 60)
    else:
        clock_match = _CLOCK_RE.match(text)
        if clock_match:
            hours, mins = int(clock_match.group(1)), int(clock_match.group(2))
            minutes = hours * 60 + mins
        else:
            shorthand_match = _SHORTHAND_RE.match(text)
            if shorthand_match and shorthand_match.group(0).strip():
                hours_part, minutes_part = shorthand_match.groups()
                if hours_part is None and minutes_part is None:
                    raise DurationParseError(INVALID_DURATION_MESSAGE)
                total = 0.0
                if hours_part is not None:
                    total += float(hours_part) * 60
                if minutes_part is not None:
                    total += float(minutes_part)
                minutes = round(total)

    if minutes is None or minutes <= 0:
        raise DurationParseError(INVALID_DURATION_MESSAGE)

    return int(minutes)
