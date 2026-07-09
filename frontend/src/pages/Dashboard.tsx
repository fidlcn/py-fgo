import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAsync, useEvents, fetchInstances, fetchTasks } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Stat, StatusBadge } from "../components/ui";
import type { Instance, QuickStartResult, RunTask } from "../types";

export function Dashboard() {
  const inst = useAsync(fetchInstances, []);
  const tasks = useAsync(fetchTasks, []);
  const { events, connected } = useEvents();
  const [quickBusy, setQuickBusy] = useState(false);
  const [quickError, setQuickError] = useState<string | null>(null);
  const [quickResult, setQuickResult] = useState<QuickStartResult | null>(null);

  // Index latest task per instance.
  const taskByInstance = useMemo(() => {
    const map: Record<string, RunTask> = {};
    for (const t of tasks.data ?? []) {
      const cur = map[t.instance_id];
      if (!cur || (t.created_at > cur.created_at)) map[t.instance_id] = t;
    }
    return map;
  }, [tasks.data]);

  // Latest instance_status event per instance, for live overlay.
  const live = useMemo(() => {
    const map: Record<string, Record<string, unknown>> = {};
    for (const e of events) {
      if (e.type !== "instance_status") continue;
      const iid = e.payload.instance_id as string;
      if (iid && !map[iid]) map[iid] = e.payload;
    }
    return map;
  }, [events]);

  async function control(taskId: string | undefined, action: "start" | "pause" | "resume" | "stop") {
    if (!taskId) return;
    await api.post(`/api/tasks/${taskId}/${action}`);
    tasks.reload();
    inst.reload();
  }

  async function quickStart() {
    setQuickBusy(true);
    setQuickError(null);
    setQuickResult(null);
    try {
      const result = await api.post<QuickStartResult>("/api/quick-start");
      setQuickResult(result);
      tasks.reload();
      inst.reload();
    } catch (e) {
      setQuickError(e instanceof Error ? e.message : String(e));
    } finally {
      setQuickBusy(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">
        Live overview of emulator instances and running tasks.{" "}
        {connected ? (
          <span className="badge ok">● live</span>
        ) : (
          <span className="badge muted">○ disconnected</span>
        )}
      </p>

      <Card
        title="One-click start"
        actions={
          <button className="btn primary large" disabled={quickBusy} onClick={quickStart}>
            {quickBusy ? "Checking…" : "Start"}
          </button>
        }
      >
        <div className="quick-start-body">
          <div>
            Open MuMu, launch FGO, enter the quest detail screen, then press Start.
            The app will detect the running emulator, verify FGO is in front, create
            default profiles if needed, and start the task.
          </div>
          {quickError && <div className="badge err">{quickError}</div>}
          {quickResult && (
            <div className="badge ok">
              Started {quickResult.task.id} on {quickResult.preflight.instance.name}
              {" · "}
              {quickResult.preflight.state}
            </div>
          )}
        </div>
      </Card>

      {inst.loading && <p className="muted">Loading…</p>}
      {inst.error && <p className="badge err">{inst.error}</p>}

      <div className="grid">
        {(inst.data ?? []).map((i: Instance) => {
          const task = taskByInstance[i.id];
          const l = live[i.id] ?? {};
          const state = (l.state as string) ?? i.live_state ?? "—";
          const completed = (l.completed_count as number) ?? i.live_completed ?? 0;
          const action = (l.last_action as string) ?? i.live_action ?? "";
          return (
            <Card
              key={i.id}
              title={
                <div className="row">
                  <StatusBadge status={i.status} />
                  <strong>{i.name}</strong>
                  <span className="muted">{i.adb_device_id}</span>
                </div>
              }
              actions={
                <div className="row">
                  <button
                    className="btn small"
                    disabled={!task || task.status === "running"}
                    onClick={() => control(task?.id, "start")}
                  >
                    Start
                  </button>
                  <button
                    className="btn small secondary"
                    disabled={task?.status !== "running"}
                    onClick={() => control(task?.id, "pause")}
                  >
                    Pause
                  </button>
                  <button
                    className="btn small secondary"
                    disabled={!["running", "paused"].includes(task?.status ?? "")}
                    onClick={() => control(task?.id, "resume")}
                  >
                    Resume
                  </button>
                  <button
                    className="btn small danger"
                    disabled={!["running", "paused"].includes(task?.status ?? "")}
                    onClick={() => control(task?.id, "stop")}
                  >
                    Stop
                  </button>
                </div>
              }
            >
              <div className="row" style={{ marginBottom: 12 }}>
                <Stat value={state} label="FGO state" />
                <Stat value={completed} label="Completed" />
                <Stat value={task?.failure_count ?? 0} label="Failures" />
                <Stat
                  value={<StatusBadge status={task?.status ?? "no task"} />}
                  label="Task"
                />
              </div>
              <div className="muted" style={{ marginBottom: 8 }}>
                Last action: {action || "—"}
              </div>
              {task ? (
                <Link to="/monitor">Open monitor →</Link>
              ) : (
                <Link to="/tasks">Create a task →</Link>
              )}
            </Card>
          );
        })}
        {inst.data && inst.data.length === 0 && (
          <Card>
            <Empty>
              No instances yet. <Link to="/instances">Add a MuMu instance →</Link>
            </Empty>
          </Card>
        )}
      </div>
    </div>
  );
}
