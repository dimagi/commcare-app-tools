// API response types

export interface DomainInfo {
  domain: string;
  name: string;
}

export interface AppInfo {
  id: string;
  name: string;
  version?: number;
}

export interface UserInfo {
  id: string;
  username: string;
  first_name?: string;
  last_name?: string;
}

export interface CaseInfo {
  case_id: string;
  case_type: string;
  name?: string;
  owner_id?: string;
}

export interface TestConfig {
  id: string;
  name: string;
  domain: string;
  app_id: string;
  app_name: string;
  user_id: string;
  username: string;
  case_type?: string;
  case_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TestConfigCreate {
  name: string;
  domain: string;
  app_id: string;
  app_name: string;
  user_id: string;
  username: string;
  case_type?: string;
  case_id?: string;
}

export interface WorkspaceStats {
  domains: number;
  apps: number;
  users: number;
  size_bytes: number;
  size_human: string;
  path: string;
}

export interface TerminalStatus {
  ready: boolean;
  java: {
    found: boolean;
    path?: string;
    error?: string;
  };
  cli_jar: {
    built: boolean;
    path?: string;
  };
}
