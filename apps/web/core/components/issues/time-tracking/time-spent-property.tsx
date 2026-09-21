/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Clock, Trash2 } from "lucide-react";
// i18n
import { useTranslation } from "@plane/i18n";
// ui
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomMenu, Input, TextArea } from "@plane/ui";
// helpers
import { formatMinutesAsHours, getTodayISODate } from "@/helpers/time.helper";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useTimeTracking } from "@/hooks/store/use-time";
import { useUser } from "@/hooks/store/user";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

/**
 * Read-only total time spent on the issue, with a "Log time" popover to add
 * entries (time string, optional date defaulting to today, optional note) and
 * to review/delete the current user's own entries.
 */
export const IssueTimeSpentProperty = observer(function IssueTimeSpentProperty(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const {
    getTimeSummaryByIssueId,
    getTimeEntriesByIssueId,
    entriesFetchedMap,
    summaryRequestedMap,
    fetchTimeSummary,
    fetchTimeEntries,
    createTimeEntry,
    deleteTimeEntry,
  } = useTimeTracking();
  const { data: currentUser } = useUser();
  const { getUserDetails } = useMember();
  // states
  const [timeInput, setTimeInput] = useState("");
  const [entryDate, setEntryDate] = useState(getTodayISODate());
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const summary = getTimeSummaryByIssueId(issueId);
  const spentMinutes = summary?.spent_minutes ?? 0;
  const entries = getTimeEntriesByIssueId(issueId);

  const handleMenuOpen = () => {
    if (summary === undefined && !summaryRequestedMap[issueId]) {
      fetchTimeSummary(workspaceSlug, [{ id: issueId, project_id: projectId }]).catch(() => {});
    }
    if (!entriesFetchedMap[issueId]) {
      fetchTimeEntries(workspaceSlug, projectId, issueId).catch(() => {});
    }
  };

  const resetForm = () => {
    setTimeInput("");
    setEntryDate(getTodayISODate());
    setNote("");
  };

  const handleSubmit = async () => {
    const time = timeInput.trim();
    if (!time || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await createTimeEntry(workspaceSlug, projectId, issueId, {
        time,
        entry_date: entryDate || undefined,
        note: note.trim() || undefined,
      });
      resetForm();
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.log_time"),
        message: error?.response?.data?.error ?? error?.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (entryId: string) => {
    try {
      await deleteTimeEntry(workspaceSlug, projectId, issueId, entryId);
    } catch (error: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.time_entries"),
        message: error?.response?.data?.error ?? error?.message,
      });
    }
  };

  return (
    <SidebarPropertyListItem icon={Clock} label={t("common.time_spent")}>
      <div className="flex w-full items-center justify-between gap-2">
        <span className={`text-body-xs-medium ${spentMinutes > 0 ? "" : "text-placeholder"}`}>
          {spentMinutes > 0 ? formatMinutesAsHours(spentMinutes) : t("common.none")}
        </span>
        {!disabled && (
          <CustomMenu
            customButton={
              <button
                type="button"
                className="rounded-sm px-2 py-0.5 text-11 text-accent-primary hover:bg-accent-primary/10"
              >
                {t("common.log_time")}
              </button>
            }
            menuButtonOnClick={handleMenuOpen}
            menuItemsClassName="w-72"
            placement="bottom-end"
            closeOnSelect={false}
          >
            <div className="flex flex-col gap-2 p-2">
              <div className="flex items-center gap-2">
                <Input
                  type="text"
                  inputSize="xs"
                  value={timeInput}
                  onChange={(e) => setTimeInput(e.target.value)}
                  placeholder="1.5, 0:30, 2h 30m"
                  className="w-full"
                />
                <Input
                  type="date"
                  inputSize="xs"
                  value={entryDate}
                  onChange={(e) => setEntryDate(e.target.value)}
                  className="w-full"
                />
              </div>
              <TextArea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t("common.description")}
                rows={2}
                className="w-full resize-none"
              />
              <button
                type="button"
                disabled={!timeInput.trim() || isSubmitting}
                onClick={handleSubmit}
                className="rounded-sm bg-accent-primary px-2 py-1 text-11 font-medium text-on-color disabled:opacity-50"
              >
                {t("common.log_time")}
              </button>

              {entries && entries.length > 0 && (
                <div className="mt-1 flex max-h-48 flex-col gap-1 overflow-y-auto border-t border-subtle pt-2">
                  {entries.map((entry) => {
                    const entryUser = getUserDetails(entry.user);
                    const canDelete = !!currentUser?.id && entry.user === currentUser.id;
                    return (
                      <div key={entry.id} className="group flex items-center justify-between gap-2 text-11">
                        <div className="flex min-w-0 flex-col">
                          <span className="text-secondary">
                            {formatMinutesAsHours(entry.minutes)}h · {entry.entry_date}
                            {entryUser ? ` · ${entryUser.display_name}` : ""}
                          </span>
                          {entry.note && <span className="truncate text-tertiary">{entry.note}</span>}
                        </div>
                        {canDelete && (
                          <button
                            type="button"
                            onClick={() => handleDelete(entry.id)}
                            className="shrink-0 rounded-sm p-0.5 text-placeholder hover:bg-danger-subtle hover:text-danger-primary"
                            aria-label={t("common.delete")}
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </CustomMenu>
        )}
      </div>
    </SidebarPropertyListItem>
  );
});
