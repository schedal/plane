/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* eslint-disable no-useless-catch */

// types
import { API_BASE_URL } from "@plane/constants";
import type {
  TIssueTimeEntry,
  TIssueTimeEntryPayload,
  TIssueTimeEstimatePayload,
  TIssueTimeEstimateResponse,
  TIssueTimeSummary,
  TWorkspaceTimeEntriesFilters,
} from "@plane/types";
// services
import { APIService } from "@/services/api.service";

/**
 * Service for the fctime app endpoints (per-issue time estimates and time entries).
 */
export class IssueTimeService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async fetchTimeEstimate(
    workspaceSlug: string,
    projectId: string,
    issueId: string
  ): Promise<TIssueTimeEstimateResponse> {
    try {
      const { data } = await this.get(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/time-estimate/`
      );
      return data;
    } catch (error) {
      throw error;
    }
  }

  async updateTimeEstimate(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEstimatePayload
  ): Promise<TIssueTimeEstimateResponse> {
    try {
      const { data } = await this.put(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/time-estimate/`,
        payload
      );
      return data;
    } catch (error) {
      throw error;
    }
  }

  async fetchTimeEntries(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueTimeEntry[]> {
    try {
      const { data } = await this.get(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/time-entries/`
      );
      return data;
    } catch (error) {
      throw error;
    }
  }

  async createTimeEntry(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueTimeEntryPayload
  ): Promise<TIssueTimeEntry> {
    try {
      const { data } = await this.post(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/time-entries/`,
        payload
      );
      return data;
    } catch (error) {
      throw error;
    }
  }

  async deleteTimeEntry(workspaceSlug: string, projectId: string, issueId: string, entryId: string): Promise<void> {
    try {
      await this.delete(
        `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/time-entries/${entryId}/`
      );
    } catch (error) {
      throw error;
    }
  }

  async fetchTimeSummary(workspaceSlug: string, projectId: string, issueIds: string[]): Promise<TIssueTimeSummary> {
    try {
      const { data } = await this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/time-summary/`, {
        params: { issue_ids: issueIds.join(",") },
      });
      return data;
    } catch (error) {
      throw error;
    }
  }

  async fetchWorkspaceTimeEntries(
    workspaceSlug: string,
    filters: TWorkspaceTimeEntriesFilters,
    cursor?: string,
    perPage?: number
  ): Promise<{
    results: TIssueTimeEntry[];
    total_results: number;
    next_cursor: string;
    prev_cursor: string;
    next_page_results: boolean;
    prev_page_results: boolean;
  }> {
    try {
      const { data } = await this.get(`/api/workspaces/${workspaceSlug}/time-entries/`, {
        params: {
          ...filters,
          ...(cursor ? { cursor } : {}),
          ...(perPage ? { per_page: perPage } : {}),
        },
      });
      return data;
    } catch (error) {
      throw error;
    }
  }
}

export const issueTimeService = new IssueTimeService();
