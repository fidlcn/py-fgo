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
      alert(r.online ? "设备在线 ✓" : "设备离线 ✗");
    } catch (e) {
      alert((e as Error).message);
    }
  }

  async function screenshot(id: string) {
    const blob = await api.raw(`/api/instances/${id}/screenshot`);
    setShot(URL.createObjectURL(blob));
  }

  async function remove(id: string) {
    if (!confirm("确定删除这个模拟器实例吗？")) return;
    await api.del(`/api/instances/${id}`);
    list.reload();
  }

  return (
    <div>
      <h1 className="page-title">模拟器</h1>
      <p className="page-sub">通过 ADB 连接和管理 MuMu 模拟器实例。</p>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Card title="添加实例">
          <Field label="名称">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="ADB 设备 ID（例如 127.0.0.1:7555）">
            <input
              value={form.adb_device_id}
              onChange={(e) => setForm({ ...form, adb_device_id: e.target.value })}
            />
          </Field>
          <div className="row">
            <Field label="宽度">
              <input
                type="number"
                value={form.resolution_width}
                onChange={(e) => setForm({ ...form, resolution_width: +e.target.value })}
              />
            </Field>
            <Field label="高度">
              <input
                type="number"
                value={form.resolution_height}
                onChange={(e) => setForm({ ...form, resolution_height: +e.target.value })}
              />
            </Field>
          </div>
          <button className="btn" disabled={busy || !form.name || !form.adb_device_id} onClick={add}>
            添加
          </button>
        </Card>

        <Card
          title="ADB 扫描"
          actions={
            <button
              className="btn small secondary"
              onClick={async () => setScan(await fetchScan())}
            >
              扫描设备
            </button>
          }
        >
          {scan === null ? (
            <Empty>点击“扫描设备”执行 `adb devices`。</Empty>
          ) : scan.length === 0 ? (
            <Empty>未发现设备，请确认 ADB 在 PATH 中且模拟器已启动。</Empty>
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
                        使用
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
        <Card title="实例列表">
          {list.data && list.data.length === 0 ? (
            <Empty>还没有模拟器实例。</Empty>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>设备</th>
                  <th>分辨率</th>
                  <th>状态</th>
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
                          测试
                        </button>
                        <button className="btn small secondary" onClick={() => screenshot(i.id)}>
                          截图
                        </button>
                        <button className="btn small danger" onClick={() => remove(i.id)}>
                          删除
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
          <Card title="截图" actions={<button className="btn small secondary" onClick={() => setShot(null)}>关闭</button>}>
            <img className="screenshot" src={shot} alt="截图" />
          </Card>
        </div>
      )}
    </div>
  );
}
