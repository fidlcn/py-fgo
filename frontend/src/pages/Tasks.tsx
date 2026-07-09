import { useState } from "react";
import { useAsync, fetchInstances, fetchQuestProfiles, fetchSupportProfiles, fetchBattlePlans, fetchTasks } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field, StatusBadge } from "../components/ui";

export function Tasks() {
  const inst = useAsync(fetchInstances, []);
  const qp = useAsync(fetchQuestProfiles, []);
  const sp = useAsync(fetchSupportProfiles, []);
  const bp = useAsync(fetchBattlePlans, []);
  const tasks = useAsync(fetchTasks, []);

  const [instanceId, setInstanceId] = useState("");
  const [questId, setQuestId] = useState("");
  const [supportId, setSupportId] = useState("");
  const [planId, setPlanId] = useState("");
  const [count, setCount] = useState(10);
  const [stopOnFail, setStopOnFail] = useState(true);
  const [maxFail, setMaxFail] = useState(3);
  const [apEnabled, setApEnabled] = useState(false);

  const ready = instanceId && questId && supportId && planId;

  async function create() {
    await api.post("/api/tasks", {
      instance_id: instanceId,
      quest_profile_id: questId,
      support_profile_id: supportId,
      battle_plan_id: planId,
      loop_config: { mode: "count", count, stop_on_failure: stopOnFail, max_failures: maxFail },
      ap_recovery: { enabled: apEnabled, priority: ["bronze", "silver", "gold"], max_items: 3 },
    });
    tasks.reload();
  }

  async function control(id: string, action: "start" | "pause" | "resume" | "stop") {
    await api.post(`/api/tasks/${id}/${action}`);
    tasks.reload();
  }

  return (
    <div>
      <h1 className="page-title">任务</h1>
      <p className="page-sub">将模拟器实例、关卡配置、助战配置和战斗方案绑定为一次运行任务。</p>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 18 }}>
        <Card title="创建任务">
          <Field label="模拟器实例">
            <select value={instanceId} onChange={(e) => setInstanceId(e.target.value)}>
              <option value="">— 请选择 —</option>
              {inst.data?.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.adb_device_id})
                </option>
              ))}
            </select>
          </Field>
          <Field label="关卡配置">
            <select value={questId} onChange={(e) => setQuestId(e.target.value)}>
              <option value="">— 请选择 —</option>
              {qp.data?.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="助战配置">
            <select value={supportId} onChange={(e) => setSupportId(e.target.value)}>
              <option value="">— 请选择 —</option>
              {sp.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="战斗方案">
            <select value={planId} onChange={(e) => setPlanId(e.target.value)}>
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
              <input type="number" value={count} onChange={(e) => setCount(+e.target.value)} style={{ width: 100 }} />
            </Field>
            <Field label="最大失败次数">
              <input type="number" value={maxFail} onChange={(e) => setMaxFail(+e.target.value)} style={{ width: 100 }} />
            </Field>
          </div>
          <div className="row">
            <label className="row">
              <input type="checkbox" checked={stopOnFail} onChange={(e) => setStopOnFail(e.target.checked)} />
              失败后停止
            </label>
            <label className="row">
              <input type="checkbox" checked={apEnabled} onChange={(e) => setApEnabled(e.target.checked)} />
              自动恢复 AP
            </label>
          </div>
          <button className="btn" disabled={!ready} onClick={create}>
            创建任务
          </button>
        </Card>
      </div>

      <Card title="任务列表">
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
                <tr key={t.id}>
                  <td className="muted">{t.id}</td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>{t.completed_count}</td>
                  <td>{t.failure_count}</td>
                  <td className="muted" style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {t.last_error ?? "—"}
                  </td>
                  <td>
                    <div className="row">
                      <button className="btn small" disabled={t.status === "running"} onClick={() => control(t.id, "start")}>
                        启动
                      </button>
                      <button className="btn small secondary" disabled={t.status !== "running"} onClick={() => control(t.id, "pause")}>
                        暂停
                      </button>
                      <button className="btn small secondary" disabled={!["running", "paused"].includes(t.status)} onClick={() => control(t.id, "resume")}>
                        继续
                      </button>
                      <button className="btn small danger" disabled={!["running", "paused"].includes(t.status)} onClick={() => control(t.id, "stop")}>
                        停止
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
