// Data-fetching + live-event hooks.

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./client";
import type {
  BattlePlan,
  BotEvent,
  Instance,
  QuestProfile,
  RunTask,
  ScanDevice,
  SupportProfile,
} from "../types";

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    setLoading(true);
    fn()
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e?.message ?? String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => {
    reload();
  }, [reload]);
  return { data, error, loading, reload, setData };
}

/** Subscribe to the backend WebSocket event stream. Returns recent events. */
export function useEvents(max = 50) {
  const [events, setEvents] = useState<BotEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/events`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (msg) => {
      try {
        const evt: BotEvent = JSON.parse(msg.data);
        setEvents((prev) => [evt, ...prev].slice(0, max));
      } catch {
        /* ignore non-JSON ping frames */
      }
    };
    return () => ws.close();
  }, [max]);

  return { events, connected };
}

// Typed resource fetchers.
export const fetchInstances = () => api.get<Instance[]>("/api/instances");
export const fetchQuestProfiles = () => api.get<QuestProfile[]>("/api/quest-profiles");
export const fetchSupportProfiles = () => api.get<SupportProfile[]>("/api/support-profiles");
export const fetchBattlePlans = () => api.get<BattlePlan[]>("/api/battle-plans");
export const fetchTasks = () => api.get<RunTask[]>("/api/tasks");
export const fetchScan = () => api.post<ScanDevice[]>("/api/instances/scan-adb");
