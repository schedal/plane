/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import set from "lodash-es/set";
import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type {
  TIssueTimeEntry,
  TIssueTimeEntryPayload,
  TIssueTimeEstimatePayload,
  TIssueTimeSummaryValue,
} from "@plane/types";
// services
import { IssueTimeService } from "@/services/issue";
// store
import type { CoreRootStore } from "./root.store";

/** Max issue ids per time-summary request (keeps URLs well under length limits). */
const TIME_SUMMARY_CHUNK_SIZE = 100;

export type TIssueTimeSummaryFetchInput = {
  id: string;
  project_id: string | null | undefined;
};

export interface ITimeStore {
  // observables
  /** Per-issue { estimate_minutes, spent_minutes }, keyed by issue id. */
  timeSummaryMap: Record<string, TIssueTimeSummaryValue>;
  /** Issues whose summary has been fetched (or is in flight) — guards duplicate requests. */
  summaryRequestedMap: Record<string, boolean>;
  /** Per-issue time entry lists, keyed by issue id. */
  timeEntriesMap: Record<string, TIssueTimeEntry[]>;
  entriesFetchedMap: Record<string, boolean>;
  // computed fns
  getTimeSummaryByIssueId: (issueId: string) => TIssueTimeSummaryValue | undefined;
  getTimeEntriesByIssueId: (issueId: string) => TIssueTimeEntry[] | undefined;
  // fetch actions
  fetchTimeSummary: (workspaceSlug: string, issues: TIssueTimeSummaryFetchInput[]) => Promise<void>;
  fetchTimeEntries: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TIssueTimeEntry[]>;
  // crud actions
  updateTimeEstimate: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEstimatePayload
  ) => Promise<number | null>;
  createTimeEntry: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEntryPayload
  ) => Promise<TIssueTimeEntry>;
  deleteTimeEntry: (workspaceSlug: string, projectId: string, issueId: string, entryId: string) => Promise<void>;
}

export class TimeStore implements ITimeStore {
  // root store
  rootStore;
  // observables
  timeSummaryMap: Record<string, TIssueTimeSummaryValue> = {};
  summaryRequestedMap: Record<string, boolean> = {};
  timeEntriesMap: Record<string, TIssueTimeEntry[]> = {};
  entriesFetchedMap: Record<string, boolean> = {};
  // services
  issueTimeService;

  constructor(_rootStore: CoreRootStore) {
    makeObservable(this, {
      timeSummaryMap: observable,
      summaryRequestedMap: observable,
      timeEntriesMap: observable,
      entriesFetchedMap: observable,
      // actions
      fetchTimeSummary: action,
      fetchTimeEntries: action,
      updateTimeEstimate: action,
      createTimeEntry: action,
      deleteTimeEntry: action,
    });

    // root store
    this.rootStore = _rootStore;
    // services
    this.issueTimeService = new IssueTimeService();
  }

  getTimeSummaryByIssueId = computedFn(
    (issueId: string): TIssueTimeSummaryValue | undefined => this.timeSummaryMap[issueId]
  );

  getTimeEntriesByIssueId = computedFn(
    (issueId: string): TIssueTimeEntry[] | undefined => this.timeEntriesMap[issueId]
  );

  /**
   * Bulk-fetch estimate/spent summary for a set of issues. Groups ids by
   * project (the endpoint is project-scoped) and chunks requests. Ids that
   * have already been fetched/requested are skipped, so this is safe to call
   * on every render of an issue list.
   */
  fetchTimeSummary = async (workspaceSlug: string, issues: TIssueTimeSummaryFetchInput[]): Promise<void> => {
    // group the ids that still need fetching by project
    const idsByProject: Record<string, string[]> = {};
    const pendingIds: string[] = [];
    for (const issue of issues) {
      if (!issue.id || !issue.project_id) continue;
      if (this.summaryRequestedMap[issue.id]) continue;
      set(idsByProject, [issue.project_id], [...(idsByProject[issue.project_id] ?? []), issue.id]);
      pendingIds.push(issue.id);
    }
    if (pendingIds.length === 0) return;

    // mark as requested up-front to dedupe concurrent calls
    runInAction(() => {
      for (const id of pendingIds) set(this.summaryRequestedMap, id, true);
    });

    try {
      await Promise.all(
        Object.entries(idsByProject).map(async ([projectId, projectIssueIds]) => {
          // sequential chunks per project keep the request rate modest on
          // very long issue lists
          for (let i = 0; i < projectIssueIds.length; i += TIME_SUMMARY_CHUNK_SIZE) {
            // eslint-disable-next-line no-await-in-loop
            const summary = await this.issueTimeService.fetchTimeSummary(
              workspaceSlug,
              projectId,
              projectIssueIds.slice(i, i + TIME_SUMMARY_CHUNK_SIZE)
            );
            const chunk = projectIssueIds.slice(i, i + TIME_SUMMARY_CHUNK_SIZE);
            runInAction(() => {
              for (const issueId of chunk) {
                set(this.timeSummaryMap, issueId, summary[issueId] ?? { estimate_minutes: null, spent_minutes: 0 });
              }
            });
          }
        })
      );
    } catch (error) {
      // allow retries on the next render cycle
      runInAction(() => {
        for (const id of pendingIds) set(this.summaryRequestedMap, id, false);
      });
      throw error;
    }
  };

  fetchTimeEntries = async (workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueTimeEntry[]> => {
    const entries = await this.issueTimeService.fetchTimeEntries(workspaceSlug, projectId, issueId);
    runInAction(() => {
      set(this.timeEntriesMap, issueId, entries);
      set(this.entriesFetchedMap, issueId, true);
    });
    return entries;
  };

  /**
   * Upsert the issue's time estimate. Returns the stored minutes (null when
   * the response carries no estimate). Throws on 400 (invalid duration string)
   * so callers can surface the server error message.
   */
  updateTimeEstimate = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEstimatePayload
  ): Promise<number | null> => {
    const response = await this.issueTimeService.updateTimeEstimate(workspaceSlug, projectId, issueId, payload);
    const estimateMinutes = "estimate_minutes" in response ? response.estimate_minutes : null;
    runInAction(() => {
      const current = this.timeSummaryMap[issueId] ?? { estimate_minutes: null, spent_minutes: 0 };
      set(this.timeSummaryMap, issueId, { ...current, estimate_minutes: estimateMinutes });
      set(this.summaryRequestedMap, issueId, true);
    });
    return estimateMinutes;
  };

  createTimeEntry = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEntryPayload
  ): Promise<TIssueTimeEntry> => {
    const entry = await this.issueTimeService.createTimeEntry(workspaceSlug, projectId, issueId, payload);
    runInAction(() => {
      if (this.entriesFetchedMap[issueId]) {
        set(this.timeEntriesMap, issueId, [entry, ...(this.timeEntriesMap[issueId] ?? [])]);
      }
      const current = this.timeSummaryMap[issueId] ?? { estimate_minutes: null, spent_minutes: 0 };
      set(this.timeSummaryMap, issueId, { ...current, spent_minutes: current.spent_minutes + entry.minutes });
      set(this.summaryRequestedMap, issueId, true);
    });
    return entry;
  };

  deleteTimeEntry = async (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    entryId: string
  ): Promise<void> => {
    const deletedEntry = (this.timeEntriesMap[issueId] ?? []).find((entry) => entry.id === entryId);
    await this.issueTimeService.deleteTimeEntry(workspaceSlug, projectId, issueId, entryId);
    runInAction(() => {
      if (this.entriesFetchedMap[issueId]) {
        set(
          this.timeEntriesMap,
          issueId,
          (this.timeEntriesMap[issueId] ?? []).filter((entry) => entry.id !== entryId)
        );
      }
      if (deletedEntry) {
        const current = this.timeSummaryMap[issueId];
        if (current) {
          set(this.timeSummaryMap, issueId, {
            ...current,
            spent_minutes: Math.max(0, current.spent_minutes - deletedEntry.minutes),
          });
        }
      }
    });
  };
}
