import { useEffect, useRef, useState } from "react";
import { useAsync, fetchInstances } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Stat, StatusBadge } from "../components/ui";

export function RunMonitor() {
  const inst = useAsync(fetchInstances, []);
  const [selected, setSelected] = useState<string>("");
  const [shot, setShot] = useState<string | null>(null);
  const [auto, setAuto] = useState(true);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!selected) return;
    const grab = async () => {
      try {
        const blob = await api.raw(`/api/instances/${selected}/screenshot`);
        setShot(URL.createObjectURL(blob));
      } catch {
        /* offline / error */
      }
    };
    grab();
    if (auto) {
      timer.current = window.setInterval(grab, 4000);
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [selected, auto]);

  const current = inst.data?.find((i) => i.id === selected);

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
            onClick={async () => selected && setShot(URL.createObjectURL(await api.raw(`/api/instances/${selected}/screenshot`)))}
          >
            立即截图
          </button>
        </div>
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
            </div>
            <div className="row" style={{ marginBottom: 16 }}>
              <Stat value={current.live_completed ?? 0} label="已完成" />
              <Stat value={current.live_failure ?? 0} label="失败次数" />
            </div>
            <div className="muted">最近动作</div>
            <div>{current.live_action ?? "—"}</div>
          </Card>
        </div>
      )}
    </div>
  );
}
