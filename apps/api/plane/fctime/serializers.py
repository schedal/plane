# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Module imports
from plane.app.serializers import BaseSerializer
from plane.fctime.models import FcTimeEntry, FcTimeEstimate


class FcTimeEstimateSerializer(BaseSerializer):
    class Meta:
        model = FcTimeEstimate
        fields = [
            "id",
            "issue",
            "project",
            "workspace",
            "estimate_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FcTimeEntrySerializer(BaseSerializer):
    class Meta:
        model = FcTimeEntry
        fields = [
            "id",
            "issue",
            "project",
            "workspace",
            "user",
            "minutes",
            "note",
            "entry_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
