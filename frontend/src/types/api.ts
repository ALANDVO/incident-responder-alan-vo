export enum SeverityLevel {
  SEV1 = 'SEV1',
  SEV2 = 'SEV2',
  SEV3 = 'SEV3',
  SEV4 = 'SEV4',
}

export enum IncidentStatus {
  OPEN = 'open',
  IN_PROGRESS = 'in_progress',
  RESOLVED = 'resolved',
  CLOSED = 'closed',
}

export enum CommsChannel {
  STATUS = 'status',
  SLACK = 'slack',
  EMAIL = 'email',
}

export enum CommsPhase {
  INITIAL = 'initial',
  UPDATE = 'update',
  EXEC = 'exec',
  RESOLVED = 'resolved',
  CUSTOMER = 'customer',
  LEADERSHIP = 'leadership',
  ENGINEERING = 'engineering',
}

export enum UserRole {
  VIEWER = 'viewer',
  OPERATOR = 'operator',
  ADMIN = 'admin',
}

export interface Incident {
  id: number;
  title: string;
  description: string;
  raw_data: string | null;
  status: IncidentStatus;
  severity: SeverityLevel | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface IncidentCreate {
  title: string;
  description: string;
  raw_data?: string;
}

export interface IncidentUpdate {
  title?: string;
  description?: string;
  status?: IncidentStatus;
  severity?: SeverityLevel;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  page: number;
  page_size: number;
}

export interface TriageRequest {
  incident_id: number;
  use_llm: boolean;
}

export interface TriageResult {
  id: number;
  incident_id: number;
  severity: SeverityLevel;
  confidence: number;
  reasoning: string;
  containment_plan: string;
  llm_provider: string;
  llm_model: string;
  created_at: string;
}

export interface BlastAnalysisRequest {
  incident_id: number;
  services?: string[];
  use_llm: boolean;
}

export interface BlastAnalysis {
  id: number;
  incident_id: number;
  affected_services: string[];
  data_impact: string;
  dependency_chain: string;
  user_impact: string;
  recovery_estimate: string;
  llm_provider: string;
  llm_model: string;
  created_at: string;
}

export interface CommsTemplateRequest {
  incident_id: number;
  channel: CommsChannel;
  phase: CommsPhase;
  use_llm: boolean;
}

export interface CommsTemplate {
  id: number;
  incident_id: number;
  channel: CommsChannel;
  phase: CommsPhase;
  content: string;
  llm_provider: string;
  llm_model: string;
  created_at: string;
}

export interface PostmortemRequest {
  incident_id: number;
  use_llm: boolean;
}

export interface Postmortem {
  id: number;
  incident_id: number;
  summary: string;
  timeline: string;
  root_cause: string;
  what_went_well: string;
  what_went_poorly: string;
  contributing_factors: string;
  action_items: ActionItem[];
  lessons_learned: string;
  llm_provider: string;
  llm_model: string;
  created_at: string;
}

export interface ActionItem {
  id: number;
  action: string;
  owner: string;
  due: string;
  priority: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string;
  role: UserRole;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export interface LLMProvidersResponse {
  providers: string[];
  current: string;
  model: string;
}