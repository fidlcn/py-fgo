import { useState } from "react";
import { useAsync } from "../api/hooks";
import { api } from "../api/client";
import { Card, Field } from "../components/ui";

interface SettingsData {
  server: Record<string, unknown>;
  adb: Record<string, unknown>;
  runtime: { screenshot_interval_ms: number; action_delay_ms: number; base_resolution: number[] };
  vision: { template_threshold: number; state_threshold: number };
  logging: { level: string };
}

export function Settings() {
  const { data, reload } = useAsync<SettingsData>(() => api.get("/api/settings"), []);
  const [patch, setPatch] = useState({
    logging_level: "",
    screenshot_interval_ms: 0,
    action_delay_ms: 0,
    template_threshold: 0,
    state_threshold: 0,
  });
  const [saved, setSaved] = useState(false);

  function init() {
    if (!data) return;
    setPatch({
      logging_level: data.logging.level,
      screenshot_interval_ms: data.runtime.screenshot_interval_ms,
      action_delay_ms: data.runtime.action_delay_ms,
      template_threshold: data.vision.template_threshold,
      state_threshold: data.vision.state_threshold,
    });
  }

  async function save() {
    await api.patch("/api/settings", patch);
    setSaved(true);
    reload();
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div>
      <h1 className="page-title">Settings</h1>
      <p className="page-sub">Runtime-tunable configuration (in memory).</p>

      {data && (
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <Card title="Current config">
            <pre className="log">{JSON.stringify(data, null, 2)}</pre>
          </Card>

          <Card
            title="Adjust"
            actions={
              <>
                {saved && <span className="badge ok">saved</span>}
                {!patch.logging_level && <button className="btn small secondary" onClick={init}>Load current</button>}
                <button className="btn small" onClick={save}>Save</button>
              </>
            }
          >
            <Field label="Log level">
              <input value={patch.logging_level} onChange={(e) => setPatch({ ...patch, logging_level: e.target.value })} />
            </Field>
            <div className="row">
              <Field label="Screenshot interval (ms)">
                <input type="number" value={patch.screenshot_interval_ms} onChange={(e) => setPatch({ ...patch, screenshot_interval_ms: +e.target.value })} />
              </Field>
              <Field label="Action delay (ms)">
                <input type="number" value={patch.action_delay_ms} onChange={(e) => setPatch({ ...patch, action_delay_ms: +e.target.value })} />
              </Field>
            </div>
            <div className="row">
              <Field label="Template threshold">
                <input type="number" step="0.01" value={patch.template_threshold} onChange={(e) => setPatch({ ...patch, template_threshold: +e.target.value })} />
              </Field>
              <Field label="State threshold">
                <input type="number" step="0.01" value={patch.state_threshold} onChange={(e) => setPatch({ ...patch, state_threshold: +e.target.value })} />
              </Field>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
