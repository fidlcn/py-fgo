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
      <h1 className="page-title">Run Monitor</h1>
      <p className="page-sub">Live screenshot, detected state, progress, and worker actions.</p>

      <Card title="Instance" style={{ marginBottom: 18 }}>
        <div className="row">
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ maxWidth: 360 }}>
            <option value="">— select —</option>
            {inst.data?.map((i) => (
              <option key={i.id} value={i.id}>
                {i.name} ({i.adb_device_id})
              </option>
            ))}
          </select>
          <label className="row">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
            Auto-refresh (4s)
          </label>
          <button
            className="btn small secondary"
            onClick={async () => selected && setShot(URL.createObjectURL(await api.raw(`/api/instances/${selected}/screenshot`)))}
          >
            Capture now
          </button>
        </div>
      </Card>

      {!current ? (
        <Card>
          <Empty>Select an instance to monitor.</Empty>
        </Card>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "2fr 1fr" }}>
          <Card title="Screenshot">
            {shot ? <img className="screenshot" src={shot} alt="live" /> : <Empty>No screenshot.</Empty>}
          </Card>
          <Card title="Status">
            <div className="row" style={{ marginBottom: 16 }}>
              <Stat value={<StatusBadge status={current.status} />} label="Instance" />
              <Stat value={current.live_state ?? "—"} label="FGO state" />
            </div>
            <div className="row" style={{ marginBottom: 16 }}>
              <Stat value={current.live_completed ?? 0} label="Completed" />
              <Stat value={current.live_failure ?? 0} label="Failures" />
            </div>
            <div className="muted">Last action</div>
            <div>{current.live_action ?? "—"}</div>
          </Card>
        </div>
      )}
    </div>
  );
}
