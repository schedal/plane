/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// types
import type { TIssue } from "@plane/types";
// helpers
import { formatMinutesAsHours } from "@/helpers/time.helper";
// hooks
import { useTimeTracking } from "@/hooks/store/use-time";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

/**
 * Shared cell body for the time-tracking spreadsheet columns. Lazily fetches
 * the per-issue time summary (e.g. for expanded sub-issues that were not part
 * of the list's bulk summary fetch).
 */
const TimeSummaryCell = observer(function TimeSummaryCell(props: { issue: TIssue; field: "estimate" | "spent" }) {
  const { issue, field } = props;
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { getTimeSummaryByIssueId, summaryRequestedMap, fetchTimeSummary } = useTimeTracking();

  const summary = getTimeSummaryByIssueId(issue.id);

  useEffect(() => {
    if (summary !== undefined || summaryRequestedMap[issue.id] || !workspaceSlug || !issue.project_id) return;
    fetchTimeSummary(workspaceSlug.toString(), [{ id: issue.id, project_id: issue.project_id }]).catch(() => {});
  }, [summary, summaryRequestedMap, issue.id, issue.project_id, workspaceSlug, fetchTimeSummary]);

  const minutes = field === "estimate" ? summary?.estimate_minutes : summary?.spent_minutes;
  const displayValue =
    field === "estimate" ? formatMinutesAsHours(minutes) : minutes ? formatMinutesAsHours(minutes) : "";

  return (
    <div className="flex h-11 items-center border-b-[0.5px] border-subtle px-page-x text-13 text-secondary">
      {summary === undefined ? (
        <span className="text-placeholder">…</span>
      ) : (
        <span className={displayValue ? "" : "text-placeholder"}>{displayValue || "—"}</span>
      )}
    </div>
  );
});

export const SpreadsheetTimeEstimateColumn = observer(function SpreadsheetTimeEstimateColumn(props: Props) {
  const { issue } = props;
  return <TimeSummaryCell issue={issue} field="estimate" />;
});

export const SpreadsheetTimeSpentColumn = observer(function SpreadsheetTimeSpentColumn(props: Props) {
  const { issue } = props;
  return <TimeSummaryCell issue={issue} field="spent" />;
});
