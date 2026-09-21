/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// i18n
import { useTranslation } from "@plane/i18n";
// types
import type { IIssueDisplayProperties } from "@plane/types";
// helpers
import { shouldRenderColumn } from "@/helpers/issue-filter.helper";
import { formatMinutesAsHours } from "@/helpers/time.helper";
// hooks
import { useTimeTracking } from "@/hooks/store/use-time";

type Props = {
  issueIds: string[];
  displayProperties: IIssueDisplayProperties;
  spreadsheetColumnsList: (keyof IIssueDisplayProperties)[];
};

/**
 * Sticky totals row for the spreadsheet layout: client-side sums of the
 * time estimate and time spent over the currently visible (filtered) issues.
 * Reads the same time-summary data as the columns, so it updates live when
 * the visible issue set changes.
 */
export const SpreadsheetTotalsRow = observer(function SpreadsheetTotalsRow(props: Props) {
  const { issueIds, displayProperties, spreadsheetColumnsList } = props;
  // i18n
  const { t } = useTranslation();
  // store hooks
  const { timeSummaryMap } = useTimeTracking();

  let totalEstimateMinutes = 0;
  let totalSpentMinutes = 0;
  let hasAnyEstimate = false;
  for (const issueId of issueIds) {
    const summary = timeSummaryMap[issueId];
    if (!summary) continue;
    if (summary.estimate_minutes !== null) {
      totalEstimateMinutes += summary.estimate_minutes;
      hasAnyEstimate = true;
    }
    totalSpentMinutes += summary.spent_minutes;
  }

  return (
    <tr className="border-t border-subtle">
      {/* sticky first column, aligned with the work-item column above */}
      <td className="left-0 z-[11] h-11 min-w-60 border-r-[0.5px] border-subtle bg-layer-1 px-page-x text-13 font-medium text-secondary md:sticky">
        {t("common.time_tracking")}
      </td>
      {spreadsheetColumnsList.map((property) => {
        if (!displayProperties[property] || !shouldRenderColumn(property)) return null;

        let content: string | null = null;
        if (property === "time_estimate") content = hasAnyEstimate ? formatMinutesAsHours(totalEstimateMinutes) : null;
        else if (property === "time_spent") content = formatMinutesAsHours(totalSpentMinutes);

        return (
          <td
            key={property}
            className="h-11 min-w-36 border-r-[1px] border-subtle bg-layer-1 px-page-x text-13 font-medium text-secondary"
          >
            {content}
          </td>
        );
      })}
    </tr>
  );
});
