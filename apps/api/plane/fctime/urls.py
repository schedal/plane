# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.fctime.views import (
    IssueTimeEntryAPIEndpoint,
    IssueTimeEntryDetailAPIEndpoint,
    IssueTimeEstimateAPIEndpoint,
    IssueTimeSummaryAPIEndpoint,
    WorkspaceTimeEntriesAPIEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/time-estimate/",
        IssueTimeEstimateAPIEndpoint.as_view(),
        name="issue-time-estimate",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/time-entries/",
        IssueTimeEntryAPIEndpoint.as_view(),
        name="issue-time-entries",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/time-entries/<uuid:pk>/",
        IssueTimeEntryDetailAPIEndpoint.as_view(),
        name="issue-time-entry-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/time-summary/",
        IssueTimeSummaryAPIEndpoint.as_view(),
        name="issues-time-summary",
    ),
    path(
        "workspaces/<str:slug>/time-entries/",
        WorkspaceTimeEntriesAPIEndpoint.as_view(),
        name="workspace-time-entries",
    ),
]
