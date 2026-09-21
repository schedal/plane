# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the plane.fctime app endpoints (time estimates and
time entries)."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)
from plane.fctime.models import FcTimeEntry, FcTimeEstimate


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="FcTime Project",
        identifier="FCT",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def state(db, workspace, project):
    return State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)


@pytest.fixture
def issue(db, workspace, project, state, create_user):
    return Issue.objects.create(
        name="FcTime Issue",
        workspace=workspace,
        project=project,
        state=state,
        created_by=create_user,
    )


@pytest.fixture
def other_issue(db, workspace, project, state, create_user):
    return Issue.objects.create(
        name="Other Issue",
        workspace=workspace,
        project=project,
        state=state,
        created_by=create_user,
    )


@pytest.fixture
def other_project(db, workspace, create_user):
    """A second project in the same workspace that the admin user belongs to —
    used to prove view-level scoping returns 404 (not 403) when the issue in
    the path belongs to a different project."""
    project = Project.objects.create(
        name="FcTime Other Project",
        identifier="FCT2",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def outsider_client(db):
    """Session client for a user with no membership anywhere."""
    uid = uuid4().hex[:8]
    outsider = User.objects.create(
        email=f"outsider-{uid}@plane.so",
        username=f"outsider_{uid}",
        first_name="Out",
        last_name="Sider",
    )
    outsider.set_password("test-password")
    outsider.save()
    client = APIClient()
    client.force_authenticate(user=outsider)
    return client


@pytest.fixture
def member_user(db, workspace, project):
    """A project MEMBER (role 15), distinct from the admin fixture user."""
    uid = uuid4().hex[:8]
    member = User.objects.create(
        email=f"member-{uid}@plane.so",
        username=f"member_{uid}",
        first_name="Mem",
        last_name="Ber",
    )
    member.set_password("test-password")
    member.save()
    WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
    ProjectMember.objects.create(project=project, member=member, role=15, is_active=True)
    return member


@pytest.fixture
def member_client(db, member_user):
    client = APIClient()
    client.force_authenticate(user=member_user)
    return client


def estimate_url(slug, project_id, issue_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-estimate/"


def entries_url(slug, project_id, issue_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-entries/"


def entry_detail_url(slug, project_id, issue_id, pk):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/time-entries/{pk}/"


def summary_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/time-summary/"


def workspace_entries_url(slug):
    return f"/api/workspaces/{slug}/time-entries/"


@pytest.mark.contract
class TestIssueTimeEstimate:
    @pytest.mark.django_db
    def test_get_unset_estimate_returns_null(self, session_client, workspace, project, issue):
        response = session_client.get(estimate_url(workspace.slug, project.id, issue.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"estimate_minutes": None}

    @pytest.mark.django_db
    def test_put_estimate_with_duration_string(self, session_client, workspace, project, issue):
        url = estimate_url(workspace.slug, project.id, issue.id)
        response = session_client.put(url, {"estimate": "0:30"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estimate_minutes"] == 30
        assert FcTimeEstimate.objects.get(issue_id=issue.id).estimate_minutes == 30

    @pytest.mark.django_db
    def test_put_estimate_with_minutes_int(self, session_client, workspace, project, issue):
        url = estimate_url(workspace.slug, project.id, issue.id)
        response = session_client.put(url, {"estimate_minutes": 45}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estimate_minutes"] == 45

    @pytest.mark.django_db
    def test_put_estimate_upserts_existing(self, session_client, workspace, project, issue):
        url = estimate_url(workspace.slug, project.id, issue.id)
        session_client.put(url, {"estimate": "1h"}, format="json")
        response = session_client.put(url, {"estimate": "2h 30m"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["estimate_minutes"] == 150
        assert FcTimeEstimate.all_objects.filter(issue_id=issue.id).count() == 1

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "payload",
        [
            {"estimate": "garbage"},
            {"estimate": "1:75"},
            {"estimate_minutes": 0},
            {"estimate_minutes": -5},
            {"estimate_minutes": "abc"},
            {},
        ],
    )
    def test_put_estimate_bad_input_returns_400(self, session_client, workspace, project, issue, payload):
        url = estimate_url(workspace.slug, project.id, issue.id)
        response = session_client.put(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    @pytest.mark.django_db
    def test_estimate_cross_project_issue_returns_404(self, session_client, workspace, other_project, issue):
        # The caller is a member of `other_project`, but the issue in the path
        # belongs to a different project — the scoped lookup must 404.
        response = session_client.get(estimate_url(workspace.slug, other_project.id, issue.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_estimate_permission_denied_for_outsider(self, outsider_client, workspace, project, issue):
        url = estimate_url(workspace.slug, project.id, issue.id)
        assert outsider_client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert outsider_client.put(url, {"estimate": "1h"}, format="json").status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_estimate_unauthenticated(self, api_client, workspace, project, issue):
        response = api_client.get(estimate_url(workspace.slug, project.id, issue.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.contract
class TestIssueTimeEntries:
    @pytest.mark.django_db
    def test_create_entry_with_minutes(self, session_client, workspace, project, issue, create_user):
        url = entries_url(workspace.slug, project.id, issue.id)
        response = session_client.post(url, {"minutes": 60, "note": "work"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["minutes"] == 60
        assert response.data["note"] == "work"
        assert response.data["entry_date"] == date.today().isoformat()
        assert response.data["user"] == create_user.id

    @pytest.mark.django_db
    def test_create_entry_with_time_string_and_date(self, session_client, workspace, project, issue):
        url = entries_url(workspace.slug, project.id, issue.id)
        response = session_client.post(
            url,
            {"time": "1h30m", "entry_date": "2026-09-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["minutes"] == 90
        assert response.data["entry_date"] == "2026-09-01"
        assert response.data["note"] == ""

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "payload",
        [
            {"minutes": 0},
            {"minutes": -10},
            {"time": "nonsense"},
            {"minutes": 30, "entry_date": "not-a-date"},
            {"note": "no time given"},
        ],
    )
    def test_create_entry_bad_input_returns_400(self, session_client, workspace, project, issue, payload):
        url = entries_url(workspace.slug, project.id, issue.id)
        response = session_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    @pytest.mark.django_db
    def test_list_entries(self, session_client, workspace, project, issue):
        url = entries_url(workspace.slug, project.id, issue.id)
        session_client.post(url, {"minutes": 30, "entry_date": "2026-09-01"}, format="json")
        session_client.post(url, {"minutes": 45, "entry_date": "2026-09-02"}, format="json")

        response = session_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        # Ordered by -entry_date
        assert response.data[0]["entry_date"] == "2026-09-02"
        assert {entry["minutes"] for entry in response.data} == {30, 45}

    @pytest.mark.django_db
    def test_entries_permission_denied_for_outsider(self, outsider_client, workspace, project, issue):
        url = entries_url(workspace.slug, project.id, issue.id)
        assert outsider_client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert outsider_client.post(url, {"minutes": 30}, format="json").status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_delete_entry_soft_deletes(self, session_client, workspace, project, issue):
        create_response = session_client.post(
            entries_url(workspace.slug, project.id, issue.id), {"minutes": 30}, format="json"
        )
        entry_id = create_response.data["id"]

        response = session_client.delete(entry_detail_url(workspace.slug, project.id, issue.id, entry_id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Row still exists but is soft-deleted and hidden from the default manager
        assert not FcTimeEntry.objects.filter(pk=entry_id).exists()
        assert FcTimeEntry.all_objects.get(pk=entry_id).deleted_at is not None

        # Hidden from the list endpoint
        list_response = session_client.get(entries_url(workspace.slug, project.id, issue.id))
        assert list_response.data == []

    @pytest.mark.django_db
    def test_delete_entry_by_creator_member(self, member_client, workspace, project, issue, member_user):
        # A plain MEMBER logs their own entry
        create_response = member_client.post(
            entries_url(workspace.slug, project.id, issue.id), {"minutes": 25}, format="json"
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        entry_id = create_response.data["id"]

        # The creator (a plain MEMBER) can delete their own entry
        response = member_client.delete(entry_detail_url(workspace.slug, project.id, issue.id, entry_id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_delete_entry_forbidden_for_non_creator_member(
        self, session_client, member_client, workspace, project, issue
    ):
        # Admin (session_client) logs the entry
        create_response = session_client.post(
            entries_url(workspace.slug, project.id, issue.id), {"minutes": 25}, format="json"
        )
        entry_id = create_response.data["id"]

        # A non-admin member who did not create the entry cannot delete it
        response = member_client.delete(entry_detail_url(workspace.slug, project.id, issue.id, entry_id))
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert FcTimeEntry.objects.filter(pk=entry_id).exists()

    @pytest.mark.django_db
    def test_delete_entry_cross_project_returns_404(
        self, session_client, workspace, project, other_project, issue, create_user
    ):
        entry = FcTimeEntry.objects.create(
            issue_id=issue.id,
            project_id=project.id,
            user=create_user,
            minutes=30,
            entry_date=date.today(),
        )
        # Entry referenced through a different (but accessible) project → 404,
        # and the entry must remain untouched.
        response = session_client.delete(entry_detail_url(workspace.slug, other_project.id, issue.id, entry.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert FcTimeEntry.objects.filter(pk=entry.id).exists()


@pytest.mark.contract
class TestIssueTimeSummary:
    @pytest.mark.django_db
    def test_summary_aggregation(self, session_client, workspace, project, issue, other_issue, create_user):
        FcTimeEstimate.objects.create(issue_id=issue.id, project_id=project.id, estimate_minutes=120)
        FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=30, entry_date=date.today()
        )
        FcTimeEntry.objects.create(
            issue_id=issue.id,
            project_id=project.id,
            user=create_user,
            minutes=60,
            entry_date=date.today() - timedelta(days=1),
        )
        # Soft-deleted entries must not count towards the total
        deleted_entry = FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=999, entry_date=date.today()
        )
        deleted_entry.delete()
        FcTimeEntry.objects.create(
            issue_id=other_issue.id, project_id=project.id, user=create_user, minutes=15, entry_date=date.today()
        )

        url = summary_url(workspace.slug, project.id)
        response = session_client.get(url, {"issue_ids": f"{issue.id},{other_issue.id}"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data[str(issue.id)] == {"estimate_minutes": 120, "spent_minutes": 90}
        assert response.data[str(other_issue.id)] == {"estimate_minutes": None, "spent_minutes": 15}

    @pytest.mark.django_db
    def test_summary_unknown_issue_returns_nulls(self, session_client, workspace, project):
        unknown_id = uuid4()
        response = session_client.get(summary_url(workspace.slug, project.id), {"issue_ids": str(unknown_id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data[str(unknown_id)] == {"estimate_minutes": None, "spent_minutes": 0}

    @pytest.mark.django_db
    def test_summary_invalid_issue_ids_returns_400(self, session_client, workspace, project):
        response = session_client.get(summary_url(workspace.slug, project.id), {"issue_ids": "not-a-uuid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_summary_permission_denied_for_outsider(self, outsider_client, workspace, project):
        response = outsider_client.get(summary_url(workspace.slug, project.id), {"issue_ids": str(uuid4())})
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
class TestWorkspaceTimeEntries:
    @pytest.mark.django_db
    def test_workspace_feed_lists_entries_paginated(self, session_client, workspace, project, issue, create_user):
        FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=30, entry_date=date(2026, 9, 1)
        )
        FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=45, entry_date=date(2026, 9, 10)
        )

        response = session_client.get(workspace_entries_url(workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_results"] == 2
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["entry_date"] == "2026-09-10"

    @pytest.mark.django_db
    def test_workspace_feed_filters(
        self, session_client, workspace, project, issue, create_user, member_user
    ):
        FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=30, entry_date=date(2026, 9, 1)
        )
        FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=member_user, minutes=45, entry_date=date(2026, 9, 10)
        )

        base = workspace_entries_url(workspace.slug)

        response = session_client.get(base, {"project_id": str(project.id)})
        assert response.data["total_results"] == 2

        response = session_client.get(base, {"user_id": str(member_user.id)})
        assert response.data["total_results"] == 1
        assert response.data["results"][0]["user"] == member_user.id

        response = session_client.get(base, {"from": "2026-09-05", "to": "2026-09-30"})
        assert response.data["total_results"] == 1
        assert response.data["results"][0]["minutes"] == 45

    @pytest.mark.django_db
    def test_workspace_feed_bad_filters_return_400(self, session_client, workspace):
        base = workspace_entries_url(workspace.slug)
        assert session_client.get(base, {"project_id": "nope"}).status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.get(base, {"user_id": "nope"}).status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.get(base, {"from": "nope"}).status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.get(base, {"to": "nope"}).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_workspace_feed_excludes_soft_deleted(self, session_client, workspace, project, issue, create_user):
        entry = FcTimeEntry.objects.create(
            issue_id=issue.id, project_id=project.id, user=create_user, minutes=30, entry_date=date.today()
        )
        entry.delete()
        response = session_client.get(workspace_entries_url(workspace.slug))
        assert response.data["total_results"] == 0

    @pytest.mark.django_db
    def test_workspace_feed_permission_denied_for_outsider(self, outsider_client, workspace):
        response = outsider_client.get(workspace_entries_url(workspace.slug))
        assert response.status_code == status.HTTP_403_FORBIDDEN
