/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Format a minute count as decimal hours for display.
 * 30 -> "0.5", 90 -> "1.5", 120 -> "2". Returns "" for null/undefined.
 */
export const formatMinutesAsHours = (minutes: number | null | undefined): string => {
  if (minutes === null || minutes === undefined) return "";
  return `${parseFloat((minutes / 60).toFixed(2))}`;
};

/** Local date (YYYY-MM-DD) for defaulting time-entry dates. */
export const getTodayISODate = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
};
