# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import uuid
from datetime import date

# Django imports
from django.db.models import Sum
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.views import BaseAPIView
from plane.db.models import Issue
from plane.fctime.models import FcTimeEntry, FcTimeEstimate
from plane.fctime.parsers import DurationParseError, parse_duration_to_minutes
from plane.fctime.serializers import FcTimeEntrySerializer, FcTimeEstimateSerializer


def _parse_positive_minutes(value):
    """Validate a raw minutes integer payload. Returns int minutes or None."""
    if isinstance(value, bool):
        return None
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return None
    if minutes <= 0:
        return None
    return minutes


def _resolve_minutes(data, string_field, int_field):
    """Extract a positive minute count from the payload.

    Accepts either `<int_field>` (integer minutes) or `<string_field>`
    (duration string parsed by parse_duration_to_minutes). Returns
    (minutes, error_response).
    """
    if data.get(int_field) is not None:
        minutes = _parse_positive_minutes(data.get(int_field))
        if minutes is None:
            return None, Response(
                {"error": f"'{int_field}' must be a positive integer (minutes)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return minutes, None
    if data.get(string_field) is not None:
        try:
            return parse_duration_to_minutes(data.get(string_field)), None
        except DurationParseError as e:
            return None, Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return None, Response(
        {"error": f"Either '{int_field}' (integer minutes) or '{string_field}' (duration string) is required."},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _parse_iso_date(value, field_name):
    """Parse an ISO date string. Returns (date, error_response)."""
    try:
        return date.fromisoformat(str(value)), None
    except ValueError:
        return None, Response(
            {"error": f"'{field_name}' must be a valid ISO date (YYYY-MM-DD)."},
            status=status.HTTP_400_BAD_REQUEST,
        )


def _get_scoped_issue(slug, project_id, issue_id):
    return Issue.objects.filter(workspace__slug=slug, project_id=project_id, pk=issue_id).first()


class IssueTimeEstimateAPIEndpoint(BaseAPIView):
    """Read/upsert the per-issue time estimate."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id):
        issue = _get_scoped_issue(slug, project_id, issue_id)
        if issue is None:
            return Response({"error": "The required object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        estimate = FcTimeEstimate.objects.filter(issue_id=issue.id).first()
        if estimate is None:
            return Response({"estimate_minutes": None}, status=status.HTTP_200_OK)
        return Response(FcTimeEstimateSerializer(estimate).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def put(self, request, slug, project_id, issue_id):
        issue = _get_scoped_issue(slug, project_id, issue_id)
        if issue is None:
            return Response({"error": "The required object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        minutes, error = _resolve_minutes(request.data, string_field="estimate", int_field="estimate_minutes")
        if error is not None:
            return error

        # Use all_objects so a previously soft-deleted estimate is revived
        # instead of violating the one-to-one constraint.
        estimate = FcTimeEstimate.all_objects.filter(issue_id=issue.id).first()
        if estimate is None:
            estimate = FcTimeEstimate(
                issue_id=issue.id,
                project_id=issue.project_id,
                estimate_minutes=minutes,
            )
        else:
            estimate.estimate_minutes = minutes
            estimate.deleted_at = None
        estimate.save()

        return Response(FcTimeEstimateSerializer(estimate).data, status=status.HTTP_200_OK)


class IssueTimeEntryAPIEndpoint(BaseAPIView):
    """List and create time entries for an issue."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id):
        issue = _get_scoped_issue(slug, project_id, issue_id)
        if issue is None:
            return Response({"error": "The required object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        entries = FcTimeEntry.objects.filter(issue_id=issue.id)
        return Response(FcTimeEntrySerializer(entries, many=True).data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, issue_id):
        issue = _get_scoped_issue(slug, project_id, issue_id)
        if issue is None:
            return Response({"error": "The required object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        minutes, error = _resolve_minutes(request.data, string_field="time", int_field="minutes")
        if error is not None:
            return error

        entry_date_raw = request.data.get("entry_date")
        if entry_date_raw:
            entry_date, error = _parse_iso_date(entry_date_raw, "entry_date")
            if error is not None:
                return error
        else:
            entry_date = timezone.localdate()

        note = request.data.get("note", "")
        if not isinstance(note, str):
            return Response(
                {"error": "'note' must be a string."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entry = FcTimeEntry.objects.create(
            issue_id=issue.id,
            project_id=issue.project_id,
            user=request.user,
            minutes=minutes,
            note=note,
            entry_date=entry_date,
        )
        return Response(FcTimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class IssueTimeEntryDetailAPIEndpoint(BaseAPIView):
    """Soft-delete a single time entry. Allowed for project admins and the
    entry's creator."""

    @allow_permission(allowed_roles=[ROLE.ADMIN], creator=True, model=FcTimeEntry)
    def delete(self, request, slug, project_id, issue_id, pk):
        entry = FcTimeEntry.objects.filter(
            workspace__slug=slug,
            project_id=project_id,
            issue_id=issue_id,
            pk=pk,
        ).first()
        if entry is None:
            return Response({"error": "The required object does not exist."}, status=status.HTTP_404_NOT_FOUND)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssueTimeSummaryAPIEndpoint(BaseAPIView):
    """Bulk per-issue time summary for list-view column rendering."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        raw_ids = request.GET.get("issue_ids", "").strip()
        if not raw_ids:
            return Response({}, status=status.HTTP_200_OK)

        try:
            issue_ids = [uuid.UUID(raw_id.strip()) for raw_id in raw_ids.split(",") if raw_id.strip()]
        except ValueError:
            return Response(
                {"error": "'issue_ids' must be a comma-separated list of UUIDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not issue_ids:
            return Response({}, status=status.HTTP_200_OK)

        estimates = FcTimeEstimate.objects.filter(
            workspace__slug=slug,
            project_id=project_id,
            issue_id__in=issue_ids,
        ).values("issue_id", "estimate_minutes")
        estimate_map = {str(row["issue_id"]): row["estimate_minutes"] for row in estimates}

        spent = (
            FcTimeEntry.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                issue_id__in=issue_ids,
            )
            .values("issue_id")
            .annotate(spent_minutes=Sum("minutes"))
        )
        spent_map = {str(row["issue_id"]): row["spent_minutes"] for row in spent}

        summary = {
            str(issue_id): {
                "estimate_minutes": estimate_map.get(str(issue_id)),
                "spent_minutes": spent_map.get(str(issue_id), 0),
            }
            for issue_id in issue_ids
        }
        return Response(summary, status=status.HTTP_200_OK)


class WorkspaceTimeEntriesAPIEndpoint(BaseAPIView):
    """Workspace-level time-entry reporting feed with optional filters."""

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        queryset = FcTimeEntry.objects.filter(workspace__slug=slug).select_related(
            "issue", "project", "workspace", "user"
        )

        project_id = request.GET.get("project_id")
        if project_id:
            try:
                uuid.UUID(project_id)
            except ValueError:
                return Response(
                    {"error": "'project_id' must be a valid UUID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(project_id=project_id)

        user_id = request.GET.get("user_id")
        if user_id:
            try:
                uuid.UUID(user_id)
            except ValueError:
                return Response(
                    {"error": "'user_id' must be a valid UUID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(user_id=user_id)

        from_date = request.GET.get("from")
        if from_date:
            from_date, error = _parse_iso_date(from_date, "from")
            if error is not None:
                return error
            queryset = queryset.filter(entry_date__gte=from_date)

        to_date = request.GET.get("to")
        if to_date:
            to_date, error = _parse_iso_date(to_date, "to")
            if error is not None:
                return error
            queryset = queryset.filter(entry_date__lte=to_date)

        return self.paginate(
            request=request,
            queryset=queryset,
            order_by="-entry_date",
            on_results=lambda entries: FcTimeEntrySerializer(entries, many=True).data,
        )
