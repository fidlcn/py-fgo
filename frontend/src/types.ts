// Domain types mirroring the backend response shapes (to_dict outputs).

export interface ApiResponse<T> {
  ok: boolean;
  data: T;
  error: { code: string; message: string } | null;
}

export interface Instance {
  id: string;
  name: string;
  emulator_type: string;
  adb_device_id: string;
  resolution_width: number;
  resolution_height: number;
  screenshot_interval_ms: number;
  status: string;
  current_task_id: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
  updated_at: string;
  // Live overlay (only when a worker is running).
  live_state?: string;
  live_completed?: number;
  live_failure?: number;
  live_action?: string;
}

export interface QuestProfile {
  id: string;
  name: string;
  category: string;
  entry_mode: string;
  server_region: string;
  navigation_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PreferredSupport {
  friend_name?: string;
  servant?: string;
  ce?: string;
  priority?: number;
}

export interface SupportProfile {
  id: string;
  name: string;
  class_filter: string;
  preferred: PreferredSupport[];
  fallback_mode: string;
  max_scroll_pages: number;
  max_refresh_count: number;
  created_at: string;
  updated_at: string;
}

export interface BattleAction {
  type: string;
  servant_slot?: number;
  skill?: number;
  target_slot?: number;
  reserve_slot?: number;
  active_slot?: number;
  seconds?: number;
  state?: string;
}

export interface CardPolicy {
  np_order?: number[];
  face_card_count?: number;
  color_priority?: string[];
  servant_priority?: number[];
  fallback_positions?: number[];
}

export interface BattleTurn {
  turn: number;
  actions: BattleAction[];
  card_policy?: CardPolicy;
}

export interface BattleWave {
  wave: number;
  turns: BattleTurn[];
}

export interface BattlePlan {
  id: string;
  name: string;
  expected_party: Record<string, unknown>;
  waves: BattleWave[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LoopConfig {
  mode?: string;
  count?: number;
  stop_on_failure?: boolean;
  max_failures?: number;
}

export interface ApRecovery {
  enabled?: boolean;
  priority?: string[];
  max_items?: number;
  used_items?: number;
}

export interface RunTask {
  id: string;
  instance_id: string;
  quest_profile_id: string;
  support_profile_id: string;
  battle_plan_id: string;
  status: string;
  loop_config: LoopConfig;
  ap_recovery: ApRecovery;
  completed_count: number;
  failure_count: number;
  last_error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ScanDevice {
  device_id: string;
  state: string;
}

export interface BotEvent {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface QuickStartResult {
  preflight: {
    instance: Instance;
    package_name: string;
    state: string;
    confidence: number;
    matched_template: string | null;
  };
  task: RunTask;
  defaults: {
    quest_profile_id: string;
    support_profile_id: string;
    battle_plan_id: string;
  };
}

export interface CalibrationPoint {
  key: string;
  label: string;
}

export interface CalibrationData {
  available: CalibrationPoint[];
  overrides: Record<string, [number, number]>;
}
