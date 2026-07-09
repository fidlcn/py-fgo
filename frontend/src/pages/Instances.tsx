import { useState } from "react";
import { useAsync, fetchInstances, fetchScan } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field, StatusBadge } from "../components/ui";
import type { ScanDevice } from "../types";

const EMPTY = { name: "", adb_device_id: "", resolution_width: 1280, resolution_height: 720 };

export function Instances() {
  const list = useAsync(fetchInstances, []);
  const [form, setForm] = useState({ ...EMPTY });
  const [scan, setScan] = useState<ScanDevice[] | null>(null);
  const [shot, setShot] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function add() {
    setBusy(true);
    try {
      await api.post("/api/instances", form);
      setForm({ ...EMPTY });
      list.reload();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function test(id: string) {
    try {
      const r = await api.post<{ online: boolean }>(`/api/instances/${id}/test`);
      alert(r.online ? "Device is online ✓" : "Device offline ✗");
    } catch (e) {
      alert((e as Error).message);
    }
  }

  async function screenshot(id: string) {
    const blob = await api.raw(`/api/instances/${id}/screenshot`);
    setShot(URL.createObjectURL(blob));
  }

  async function remove(id: string) {
    if (!confirm("Delete this instance?")) return;
    await api.del(`/api/instances/${id}`);
    list.reload();
  }

  return (
    <div>
      <h1 className="page-title">Instances</h1>
      <p className="page-sub">MuMu emulator instances controlled over ADB.</p>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Card title="Add instance">
          <Field label="Name">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="ADB device id (e.g. 127.0.0.1:7555)">
            <input
              value={form.adb_device_id}
              onChange={(e) => setForm({ ...form, adb_device_id: e.target.value })}
            />
          </Field>
          <div className="row">
            <Field label="Width">
              <input
                type="number"
                value={form.resolution_width}
                onChange={(e) => setForm({ ...form, resolution_width: +e.target.value })}
              />
            </Field>
            <Field label="Height">
              <input
                type="number"
                value={form.resolution_height}
                onChange={(e) => setForm({ ...form, resolution_height: +e.target.value })}
              />
            </Field>
          </div>
          <button className="btn" disabled={busy || !form.name || !form.adb_device_id} onClick={add}>
            Add
          </button>
        </Card>

        <Card
          title="ADB scan"
          actions={
            <button
              className="btn small secondary"
              onClick={async () => setScan(await fetchScan())}
            >
              Scan devices
            </button>
          }
        >
          {scan === null ? (
            <Empty>Click “Scan devices” to run `adb devices`.</Empty>
          ) : scan.length === 0 ? (
            <Empty>No devices found (is adb on PATH / emulator running?).</Empty>
          ) : (
            <table>
              <tbody>
                {scan.map((d) => (
                  <tr key={d.device_id}>
                    <td>{d.device_id}</td>
                    <td>
                      <StatusBadge status={d.state} />
                    </td>
                    <td>
                      <button
                        className="btn small secondary"
                        onClick={() => setForm({ ...form, adb_device_id: d.device_id })}
                      >
                        Use
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <div style={{ marginTop: 18 }}>
        <Card title="Instances">
          {list.data && list.data.length === 0 ? (
            <Empty>No instances yet.</Empty>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Device</th>
                  <th>Resolution</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {list.data?.map((i) => (
                  <tr key={i.id}>
                    <td>{i.name}</td>
                    <td className="muted">{i.adb_device_id}</td>
                    <td>
                      {i.resolution_width}×{i.resolution_height}
                    </td>
                    <td>
                      <StatusBadge status={i.status} />
                    </td>
                    <td>
                      <div className="row">
                        <button className="btn small secondary" onClick={() => test(i.id)}>
                          Test
                        </button>
                        <button className="btn small secondary" onClick={() => screenshot(i.id)}>
                          Screenshot
                        </button>
                        <button className="btn small danger" onClick={() => remove(i.id)}>
                          Delete
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

      {shot && (
        <div style={{ marginTop: 18 }}>
          <Card title="Screenshot" actions={<button className="btn small secondary" onClick={() => setShot(null)}>Close</button>}>
            <img className="screenshot" src={shot} alt="screenshot" />
          </Card>
        </div>
      )}
    </div>
  );
}
