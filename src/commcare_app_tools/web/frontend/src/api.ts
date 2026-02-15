// API client for the backend

import type {
  DomainInfo,
  AppInfo,
  UserInfo,
  CaseInfo,
  TestConfig,
  TestConfigCreate,
  WorkspaceStats,
  TerminalStatus,
} from './types';

// Use relative URL so it works regardless of host/port
const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} - ${error}`);
  }
  return response.json();
}

// Domain endpoints
export async function listDomains(): Promise<DomainInfo[]> {
  return fetchJson(`${API_BASE}/domains`);
}

// App endpoints
export async function listApps(domain: string): Promise<AppInfo[]> {
  return fetchJson(`${API_BASE}/domains/${domain}/apps`);
}

// User endpoints
export async function listUsers(domain: string): Promise<UserInfo[]> {
  return fetchJson(`${API_BASE}/domains/${domain}/users`);
}

// Case endpoints
export async function listCases(
  domain: string,
  caseType?: string,
  limit = 50
): Promise<CaseInfo[]> {
  const params = new URLSearchParams();
  if (caseType) params.set('case_type', caseType);
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/domains/${domain}/cases?${params}`);
}

export async function listCaseTypes(domain: string): Promise<string[]> {
  return fetchJson(`${API_BASE}/domains/${domain}/case-types`);
}

// Test config endpoints
export async function listTestConfigs(): Promise<TestConfig[]> {
  return fetchJson(`${API_BASE}/test-configs`);
}

export async function getTestConfig(id: string): Promise<TestConfig> {
  return fetchJson(`${API_BASE}/test-configs/${id}`);
}

export async function createTestConfig(config: TestConfigCreate): Promise<TestConfig> {
  return fetchJson(`${API_BASE}/test-configs`, {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function deleteTestConfig(id: string): Promise<void> {
  await fetchJson(`${API_BASE}/test-configs/${id}`, { method: 'DELETE' });
}

// Workspace endpoints
export async function getWorkspaceStats(): Promise<WorkspaceStats> {
  return fetchJson(`${API_BASE}/workspace/stats`);
}

export async function cleanWorkspace(): Promise<void> {
  await fetchJson(`${API_BASE}/workspace`, { method: 'DELETE' });
}

// Download endpoints
export interface DownloadResult {
  success: boolean;
  path: string;
  size_bytes: number;
}

export interface AppDownloadResult extends DownloadResult {
  app_id: string;
  app_name: string;
  version?: number;
}

export interface RestoreDownloadResult extends DownloadResult {
  user_id: string;
  username: string;
}

export interface DownloadStatus {
  downloaded: boolean;
  ccz_path?: string;
  restore_path?: string;
  app_info?: {
    app_id: string;
    name: string;
    version?: number;
    downloaded_at?: string;
  };
  user_info?: {
    user_id: string;
    username: string;
    downloaded_at?: string;
  };
}

export async function downloadApp(domain: string, appId: string): Promise<AppDownloadResult> {
  return fetchJson(`${API_BASE}/domains/${domain}/apps/${appId}/download`, {
    method: 'POST',
  });
}

export async function downloadRestore(
  domain: string,
  appId: string,
  userId: string
): Promise<RestoreDownloadResult> {
  return fetchJson(`${API_BASE}/domains/${domain}/apps/${appId}/users/${userId}/download-restore`, {
    method: 'POST',
  });
}

export async function getAppDownloadStatus(domain: string, appId: string): Promise<DownloadStatus> {
  return fetchJson(`${API_BASE}/domains/${domain}/apps/${appId}/status`);
}

export async function getRestoreStatus(
  domain: string,
  appId: string,
  userId: string
): Promise<DownloadStatus> {
  return fetchJson(`${API_BASE}/domains/${domain}/apps/${appId}/users/${userId}/status`);
}

// Terminal/CLI endpoints
export async function getTerminalStatus(): Promise<TerminalStatus> {
  return fetchJson(`${API_BASE}/terminal/status`);
}

export interface RunCommandResult {
  command: string;
  java_path: string;
  jar_path: string;
  ccz_path: string;
  restore_path?: string;
}

export async function getRunCommand(
  domain: string,
  appId: string,
  userId?: string
): Promise<RunCommandResult> {
  const params = new URLSearchParams();
  params.set('domain', domain);
  params.set('app_id', appId);
  if (userId) params.set('user_id', userId);
  return fetchJson(`${API_BASE}/run-command?${params}`);
}
