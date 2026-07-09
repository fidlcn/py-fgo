import { useEffect, useRef, useState } from "react";
import { useAsync, fetchInstances } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Stat, StatusBadge } from "../components/ui";

const FLOW_NODES = [
  { id: "quest_entry", title: "关卡入口" },
  { id: "support_select", title: "助战选择" },
  { id: "party_confirm", title: "队伍确认" },
  { id: "battle", title: "战斗执行" },
  { id: "result", title: "结算处理" },
  { id: "ap_recovery", title: "AP 恢复" },
  { id: "loop_complete", title: "回到入口" },
];

export function RunMonitor() {
  const inst = useAsync(fetchInstances, []);
  const [selected, setSelected] = useState<string>("");
  const [shot, setShot] = useState<string | null>(null);
  const [auto, setAuto] = useState(true);
  const [shotError, setShotError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);
  const failures = useRef(0);

  useEffect(() => {
    if (!selected) return;
    const grab = async () => {
      if (failures.current >= 3) {
        setAuto(false);
        return;
      }
      try {
        const blob = await api.raw(`/api/instances/${selected}/screenshot`);
        setShot(URL.createObjectURL(blob));
        failures.current = 0;
        setShotError(null);
      } catch (e) {
        failures.current += 1;
        setShotError(e instanceof Error ? e.message : String(e));
      }
    };
    failures.current = 0;
    setShotError(null);
    grab();
    if (auto) {
      timer.current = window.setInterval(grab, 4000);
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [selected, auto]);

  const current = inst.data?.find((i) => i.id === selected);
  const flow = current ? buildFlow(current.live_phase, current.live_phase_error) : null;

  return (
    <div>
      <h1 className="page-title">运行监控</h1>
      <p className="page-sub">查看实时截图、识别状态、任务进度和执行动作。</p>

      <Card title="模拟器实例" style={{ marginBottom: 18 }}>
        <div className="row">
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ maxWidth: 360 }}>
            <option value="">— 请选择 —</option>
            {inst.data?.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} ({i.adb_device_id})
              </option>
            ))}
          </select>
          <label className="row">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
            自动刷新（4 秒）
          </label>
          <button
            className="btn small secondary"
            onClick={async () => {
              if (!selected) return;
              try {
                failures.current = 0;
                const blob = await api.raw(`/api/instances/${selected}/screenshot`);
                setShot(URL.createObjectURL(blob));
                setShotError(null);
              } catch (e) {
                setShotError(e instanceof Error ? e.message : String(e));
              }
            }}
          >
            立即截图
          </button>
        </div>
        {shotError && (
          <div className="badge err" style={{ marginTop: 10 }}>
            截图失败：{shotError}。连续失败后已暂停自动刷新，请确认后端服务仍在运行。
          </div>
        )}
      </Card>

      {!current ? (
        <Card>
          <Empty>请选择要监控的模拟器实例。</Empty>
        </Card>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "2fr 1fr" }}>
          <Card title="截图">
            {shot ? <img className="screenshot" src={shot} alt="实时截图" /> : <Empty>暂无截图。</Empty>}
          </Card>
          <Card title="状态">
            <div className="row" style={{ marginBottom: 16 }}>
              <Stat value={<StatusBadge status={current.status} />} label="实例" />
              <Stat value={current.live_state ?? "—"} label="FGO 状态" />
              <Stat value={current.live_phase_label ?? "—"} label="流程阶段" />
            </div>
            <div className="row" style={{ marginBottom: 16 }}>
              <Stat value={current.live_completed ?? 0} label="已完成" />
              <Stat value={current.live_failure ?? 0} label="失败次数" />
            </div>
            <div className="muted">最近动作</div>
            <div>{current.live_action ?? "—"}</div>
            <div style={{ marginTop: 16 }}>
              <div className="muted" style={{ marginBottom: 8 }}>
                流程节点
              </div>
              {flow && <FlowView flow={flow} />}
              {current.live_phase_error && (
                <div className="badge err" style={{ marginTop: 12 }}>
                  阶段错误：{current.live_phase_error}
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function buildFlow(phase: string | undefined, phaseError: string | null | undefined) {
  const currentIndex = Math.max(0, FLOW_NODES.findIndex((node) => node.id === phase));
  return FLOW_NODES.map((node, index) => {
    let status: "done" | "current" | "wait" | "error" = "wait";
    if (phaseError && index === currentIndex) status = "error";
    else if (index < currentIndex) status = "done";
    else if (index === currentIndex) status = "current";
    return { ...node, status };
  });
}

function FlowView({
  flow,
}: {
  flow: Array<(typeof FLOW_NODES)[number] & { status: "done" | "current" | "wait" | "error" }>;
}) {
  return (
    <div className="flow-list">
      {flow.map((node, index) => (
        <div key={node.id} className={`flow-node ${node.status}`}>
          <div className="flow-dot">{index + 1}</div>
          <div className="flow-text">
            <div>{node.title}</div>
            <span>{flowStatusLabel(node.status)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function flowStatusLabel(status: "done" | "current" | "wait" | "error") {
  const labels = {
    done: "已通过",
    current: "当前节点",
    wait: "等待",
    error: "报错位置",
  };
  return labels[status];
}
