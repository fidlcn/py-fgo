import { useState } from "react";
import { useAsync, fetchInstances, fetchQuestProfiles, fetchSupportProfiles, fetchBattlePlans, fetchTasks } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field, StatusBadge } from "../components/ui";
import { usePersistentState } from "../hooks/usePersistentState";
import type { RunTask } from "../types";

const EMPTY_DRAFT = {
  instanceId: "",
  questId: "",
  supportId: "",
  planId: "",
  count: 10,
  stopOnFail: true,
  maxFail: 3,
  apEnabled: false,
};

export function Tasks() {
  const inst = useAsync(fetchInstances, []);
  const qp = useAsync(fetchQuestProfiles, []);
  const sp = useAsync(fetchSupportProfiles, []);
  const bp = useAsync(fetchBattlePlans, []);
  const tasks = useAsync(fetchTasks, []);

  const [draft, setDraft] = usePersistentState("py-fgo.tasks.create-draft", EMPTY_DRAFT);
  const [controlError, setControlError] = useState<string | null>(null);

  const ready = draft.instanceId && draft.questId && draft.supportId && draft.planId;

  async function create() {
    await api.post("/api/tasks", {
      instance_id: draft.instanceId,
      quest_profile_id: draft.questId,
      support_profile_id: draft.supportId,
      battle_plan_id: draft.planId,
      loop_config: {
        mode: "count",
        count: draft.count,
        stop_on_failure: draft.stopOnFail,
        max_failures: draft.maxFail,
      },
      ap_recovery: { enabled: draft.apEnabled, priority: ["bronze", "silver", "gold"], max_items: 3 },
    });
    tasks.reload();
  }

  async function control(id: string, action: TaskAction) {
    setControlError(null);
    try {
      await api.post(`/api/tasks/${id}/${action}`);
      tasks.reload();
    } catch (e) {
      setControlError(e instanceof Error ? e.message : String(e));
      tasks.reload();
    }
  }

  async function remove(id: string) {
    if (!window.confirm("确定删除这个任务吗？")) return;
    setControlError(null);
    try {
      await api.del(`/api/tasks/${id}`);
      tasks.reload();
    } catch (e) {
      setControlError(e instanceof Error ? e.message : String(e));
      tasks.reload();
    }
  }

  return (
    <div>
      <h1 className="page-title">任务</h1>
      <p className="page-sub">将模拟器实例、关卡配置、助战配置和战斗方案绑定为一次运行任务。</p>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 18 }}>
        <Card title="创建任务">
          <Field label="模拟器实例">
            <select value={draft.instanceId} onChange={(e) => setDraft({ ...draft, instanceId: e.target.value })}>
              <option value="">— 请选择 —</option>
              {inst.data?.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.adb_device_id})
                </option>
              ))}
            </select>
          </Field>
          <Field label="关卡配置">
            <select value={draft.questId} onChange={(e) => setDraft({ ...draft, questId: e.target.value })}>
              <option value="">— 请选择 —</option>
              {qp.data?.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="助战配置">
            <select value={draft.supportId} onChange={(e) => setDraft({ ...draft, supportId: e.target.value })}>
              <option value="">— 请选择 —</option>
              {sp.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="战斗方案">
            <select value={draft.planId} onChange={(e) => setDraft({ ...draft, planId: e.target.value })}>
              <option value="">— 请选择 —</option>
              {bp.data?.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </Field>
          <div className="row">
            <Field label="循环次数">
              <input
                type="number"
                value={draft.count}
                onChange={(e) => setDraft({ ...draft, count: +e.target.value })}
                style={{ width: 100 }}
              />
            </Field>
            <Field label="最大失败次数">
              <input
                type="number"
                value={draft.maxFail}
                onChange={(e) => setDraft({ ...draft, maxFail: +e.target.value })}
                style={{ width: 100 }}
              />
            </Field>
          </div>
          <div className="row">
            <label className="row">
              <input
                type="checkbox"
                checked={draft.stopOnFail}
                onChange={(e) => setDraft({ ...draft, stopOnFail: e.target.checked })}
              />
              失败后停止
            </label>
            <label className="row">
              <input
                type="checkbox"
                checked={draft.apEnabled}
                onChange={(e) => setDraft({ ...draft, apEnabled: e.target.checked })}
              />
              自动恢复 AP
            </label>
          </div>
          <div className="row">
            <button className="btn" disabled={!ready} onClick={create}>
              创建任务
            </button>
            <button className="btn secondary" onClick={() => setDraft({ ...EMPTY_DRAFT })}>
              清空表单
            </button>
          </div>
        </Card>
      </div>

      <Card title="任务列表">
        {controlError && (
          <div className="badge err" style={{ marginBottom: 12 }}>
            操作失败：{controlError}
          </div>
        )}
        {tasks.data && tasks.data.length === 0 ? (
          <Empty>还没有任务。</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>状态</th>
                <th>已完成</th>
                <th>失败次数</th>
                <th>最近错误</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tasks.data?.map((t) => (
                <TaskRow key={t.id} task={t} control={control} remove={remove} />
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

function TaskRow({
  task,
  control,
  remove,
}: {
  task: RunTask;
  control: (id: string, action: TaskAction) => void;
  remove: (id: string) => void;
}) {
  const canStart = ["pending", "paused", "stopped", "failed", "completed"].includes(task.status);
  const canPause = task.status === "running";
  const canResume = task.status === "paused";
  const canStop = ["running", "paused"].includes(task.status);
  const canReset = task.status === "stopping";
  const canDelete = !["running", "paused", "stopping"].includes(task.status);

  return (
    <tr>
      <td className="muted">{task.id}</td>
      <td>
        <StatusBadge status={task.status} />
      </td>
      <td>{task.completed_count}</td>
      <td>{task.failure_count}</td>
      <td className="muted" style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
        {task.last_error ?? "—"}
      </td>
      <td>
        <div className="row">
          <button className="btn small" disabled={!canStart} onClick={() => control(task.id, "start")}>
            启动
          </button>
          <button className="btn small secondary" disabled={!canPause} onClick={() => control(task.id, "pause")}>
            暂停
          </button>
          <button className="btn small secondary" disabled={!canResume} onClick={() => control(task.id, "resume")}>
            继续
          </button>
          <button className="btn small danger" disabled={!canStop} onClick={() => control(task.id, "stop")}>
            停止
          </button>
          <button className="btn small secondary" disabled={!canReset} onClick={() => control(task.id, "reset")}>
            重置
          </button>
          <button className="btn small danger" disabled={!canDelete} onClick={() => remove(task.id)}>
            删除
          </button>
        </div>
      </td>
    </tr>
  );
}

type TaskAction = "start" | "pause" | "resume" | "stop" | "reset";
