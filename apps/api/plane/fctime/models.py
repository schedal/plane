# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from plane.db.models import ProjectBaseModel


class FcTimeEstimate(ProjectBaseModel):
    """Per-issue time estimate (one-to-one with the issue)."""

    issue = models.OneToOneField("db.Issue", on_delete=models.CASCADE, related_name="fctime_estimate")
    estimate_minutes = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Fc Time Estimate"
        verbose_name_plural = "Fc Time Estimates"
        db_table = "fctime_estimates"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.issue_id} {self.estimate_minutes}m"


class FcTimeEntry(ProjectBaseModel):
    """A single logged-time entry against an issue."""

    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="fctime_entries")
    user = models.ForeignKey("db.User", on_delete=models.CASCADE, related_name="fctime_entries")
    minutes = models.PositiveIntegerField()
    note = models.TextField(blank=True, default="")
    entry_date = models.DateField()

    class Meta:
        verbose_name = "Fc Time Entry"
        verbose_name_plural = "Fc Time Entries"
        db_table = "fctime_entries"
        ordering = ("-entry_date", "-created_at")

    def __str__(self):
        return f"{self.issue_id} {self.user_id} {self.minutes}m"
