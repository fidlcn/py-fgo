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
      <h1 className="page-title">首页</h1>
      <p className="page-sub">
        查看模拟器实例和正在运行的任务。{" "}
        {connected ? (
          <span className="badge ok">● 实时连接</span>
        ) : (
          <span className="badge muted">○ 未连接</span>
        )}
      </p>

      <Card
        title="一键启动"
        actions={
          <button className="btn primary large" disabled={quickBusy} onClick={quickStart}>
            {quickBusy ? "检测中…" : "启动"}
          </button>
        }
      >
        <div className="quick-start-body">
          <div>
            先打开 MuMu 和 FGO，并停在关卡详情页。点击启动后，软件会自动检测模拟器、
            确认 FGO 位于前台，必要时创建默认配置，然后开始执行任务。
          </div>
          {quickError && <div className="badge err">{quickError}</div>}
          {quickResult && (
            <div className="badge ok">
              已启动任务 {quickResult.task.id}，实例：{quickResult.preflight.instance.name}
              {" · "}
              {quickResult.preflight.state}
            </div>
          )}
        </div>
      </Card>

      {inst.loading && <p className="muted">加载中…</p>}
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
                    启动
                  </button>
                  <button
                    className="btn small secondary"
                    disabled={task?.status !== "running"}
                    onClick={() => control(task?.id, "pause")}
                  >
                    暂停
                  </button>
                  <button
                    className="btn small secondary"
                    disabled={!["running", "paused"].includes(task?.status ?? "")}
                    onClick={() => control(task?.id, "resume")}
                  >
                    继续
                  </button>
                  <button
                    className="btn small danger"
                    disabled={!["running", "paused"].includes(task?.status ?? "")}
                    onClick={() => control(task?.id, "stop")}
                  >
                    停止
                  </button>
                </div>
              }
            >
              <div className="row" style={{ marginBottom: 12 }}>
                <Stat value={state} label="FGO 状态" />
                <Stat value={completed} label="已完成" />
                <Stat value={task?.failure_count ?? 0} label="失败次数" />
                <Stat
                  value={<StatusBadge status={task?.status ?? "no task"} />}
                  label="任务"
                />
              </div>
              <div className="muted" style={{ marginBottom: 8 }}>
                最近动作：{action || "—"}
              </div>
              {task ? (
                <Link to="/monitor">打开监控 →</Link>
              ) : (
                <Link to="/tasks">创建任务 →</Link>
              )}
            </Card>
          );
        })}
        {inst.data && inst.data.length === 0 && (
          <Card>
            <Empty>
              还没有模拟器实例。<Link to="/instances">添加 MuMu 实例 →</Link>
            </Empty>
          </Card>
        )}
      </div>
    </div>
  );
}
