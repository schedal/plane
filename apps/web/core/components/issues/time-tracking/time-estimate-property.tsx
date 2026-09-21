/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Timer } from "lucide-react";
// i18n
import { useTranslation } from "@plane/i18n";
// ui
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input } from "@plane/ui";
// helpers
import { formatMinutesAsHours } from "@/helpers/time.helper";
// hooks
import { useTimeTracking } from "@/hooks/store/use-time";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

/**
 * Editable per-issue time estimate property. Sends the raw user input to the
 * server as `{ estimate: <string> }` — the fctime duration parser accepts
 * decimal hours ("1.5"), clock format ("0:30") and shorthand ("2h 30m").
 * Stored values are displayed as decimal hours.
 */
export const IssueTimeEstimateProperty = observer(function IssueTimeEstimateProperty(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { getTimeSummaryByIssueId, summaryRequestedMap, fetchTimeSummary, updateTimeEstimate } = useTimeTracking();
  // states
  const [inputValue, setInputValue] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  const summary = getTimeSummaryByIssueId(issueId);
  const estimateMinutes = summary?.estimate_minutes ?? null;
  const displayValue = formatMinutesAsHours(estimateMinutes);

  // fetch the estimate lazily (issues opened outside a list view have no summary yet)
  useEffect(() => {
    if (summary !== undefined || summaryRequestedMap[issueId]) return;
    fetchTimeSummary(workspaceSlug, [{ id: issueId, project_id: projectId }]).catch(() => {});
  }, [summary, summaryRequestedMap, issueId, workspaceSlug, projectId, fetchTimeSummary]);

  const handleSave = async () => {
    const value = (inputValue ?? "").trim();
    setInputValue(null);
    if (!value || value === displayValue) return;

    setIsUpdating(true);
    try {
      await updateTimeEstimate(workspaceSlug, projectId, issueId, { estimate: value });
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.time_estimate"),
        message: error?.response?.data?.error ?? error?.message,
      });
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <SidebarPropertyListItem icon={Timer} label={t("common.time_estimate")}>
      {disabled ? (
        <span className={`text-body-xs-medium ${displayValue ? "" : "text-placeholder"}`}>
          {displayValue || t("common.none")}
        </span>
      ) : (
        <Input
          type="text"
          mode="transparent"
          inputSize="xs"
          value={inputValue ?? displayValue}
          onChange={(e) => setInputValue(e.target.value)}
          onBlur={handleSave}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              e.currentTarget.blur();
            } else if (e.key === "Escape") {
              setInputValue(null);
              e.currentTarget.blur();
            }
          }}
          placeholder={t("common.none")}
          disabled={isUpdating}
          className="h-7.5 w-full text-body-xs-medium text-primary"
        />
      )}
    </SidebarPropertyListItem>
  );
});
