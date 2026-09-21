/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Types for the fctime app (per-issue time estimate and time entries).
 * Mirrors the plane.fctime Django app's API responses.
 */

export type TIssueTimeEstimate = {
  id: string;
  issue: string;
  project: string;
  workspace: string;
  estimate_minutes: number;
  created_at: string;
  updated_at: string;
};

/** GET time-estimate returns this shape when no estimate has been set yet. */
export type TIssueTimeEstimateResponse = TIssueTimeEstimate | { estimate_minutes: null };

export type TIssueTimeEstimatePayload = {
  estimate?: string;
  estimate_minutes?: number;
};

export type TIssueTimeEntry = {
  id: string;
  issue: string;
  project: string;
  workspace: string;
  user: string;
  minutes: number;
  note: string;
  entry_date: string;
  created_at: string;
  updated_at: string;
};

export type TIssueTimeEntryPayload = {
  minutes?: number;
  time?: string;
  note?: string;
  entry_date?: string;
};

export type TIssueTimeSummaryValue = {
  estimate_minutes: number | null;
  spent_minutes: number;
};

/** Keyed by issue id. */
export type TIssueTimeSummary = Record<string, TIssueTimeSummaryValue>;

export type TWorkspaceTimeEntriesFilters = {
  project_id?: string;
  user_id?: string;
  from?: string;
  to?: string;
};
