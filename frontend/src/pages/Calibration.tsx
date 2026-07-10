import { MouseEvent, useMemo, useRef, useState } from "react";
import { useAsync, fetchInstances } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";
import type { CalibrationData, CalibrationExport } from "../types";

const BASE_W = 1280;
const BASE_H = 720;

export function Calibration() {
  const inst = useAsync(fetchInstances, []);
  const cal = useAsync<CalibrationData>(() => api.get("/api/calibration"), []);
  const [selected, setSelected] = useState("");
  const [pointKey, setPointKey] = useState("QUEST_START_BUTTON");
  const [shot, setShot] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const selectedPoint = cal.data?.available.find((p) => p.key === pointKey);
  const groupedPoints = useMemo(() => {
    const groups = new Map<string, NonNullable<CalibrationData["available"]>>();
    for (const point of cal.data?.available ?? []) {
      const list = groups.get(point.category) ?? [];
      list.push(point);
      groups.set(point.category, list);
    }
    return Array.from(groups.entries());
  }, [cal.data]);

  async function capture() {
    if (!selected) return;
    const blob = await api.raw(`/api/instances/${selected}/screenshot`);
    setShot(URL.createObjectURL(blob));
    setMessage("截图已更新。请选择点位后，在截图上点击目标位置。");
  }

  async function mark(e: MouseEvent<HTMLImageElement>) {
    const img = imgRef.current;
    if (!img || !pointKey) return;
    const rect = img.getBoundingClientRect();
    const actualX = Math.round(((e.clientX - rect.left) / rect.width) * img.naturalWidth);
    const actualY = Math.round(((e.clientY - rect.top) / rect.height) * img.naturalHeight);
    const baseX = Math.round((actualX * BASE_W) / img.naturalWidth);
    const baseY = Math.round((actualY * BASE_H) / img.naturalHeight);
    await api.post("/api/calibration", { key: pointKey, x: baseX, y: baseY });
    cal.reload();
    setMessage(`已保存 ${labelFor(pointKey, cal.data)} = (${baseX}, ${baseY})`);
  }

  async function clearPoint(key: string) {
    await api.del(`/api/calibration/${key}`);
    cal.reload();
  }

  async function exportPoints() {
    const data = await api.get<CalibrationExport>("/api/calibration/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fgo-coordinates-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setMessage("已导出当前点位坐标 JSON。");
  }

  return (
    <div>
      <h1 className="page-title">坐标校准</h1>
      <p className="page-sub">
        用 ADB 截图直接标记关键按钮位置。点击会保存为 1280×720 基准坐标，后续执行任务时优先使用校准坐标。
      </p>

      <div className="grid" style={{ gridTemplateColumns: "360px 1fr" }}>
        <Card title="校准控制">
          <Field label="模拟器实例">
            <select value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">— 请选择 —</option>
              {inst.data?.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.adb_device_id})
                </option>
              ))}
            </select>
          </Field>
          <Field label="要校准的点位">
            <select value={pointKey} onChange={(e) => setPointKey(e.target.value)}>
              {groupedPoints.map(([category, points]) => (
                <optgroup key={category} label={category}>
                  {points.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </Field>
          {selectedPoint && (
            <div className="calibration-point-meta">
              <div>
                <span className="muted">Key</span>
                <strong>{selectedPoint.key}</strong>
              </div>
              <div>
                <span className="muted">默认</span>
                <strong>{selectedPoint.default[0]}, {selectedPoint.default[1]}</strong>
              </div>
              <div>
                <span className="muted">当前</span>
                <strong>{selectedPoint.current[0]}, {selectedPoint.current[1]}</strong>
              </div>
              <span className={`badge ${selectedPoint.overridden ? "ok" : "muted"}`}>
                {selectedPoint.overridden ? "已校准" : "默认值"}
              </span>
            </div>
          )}
          <div className="row">
            <button className="btn" disabled={!selected} onClick={capture}>
              获取截图
            </button>
            <button className="btn secondary" disabled={!cal.data} onClick={exportPoints}>
              导出点位坐标
            </button>
          </div>
          {message && <p className="muted">{message}</p>}
        </Card>

        <Card title="截图标记">
          {shot ? (
            <img
              ref={imgRef}
              className="screenshot calibration-shot"
              src={shot}
              alt="校准截图"
              onClick={mark}
            />
          ) : (
            <Empty>先选择模拟器并获取截图。</Empty>
          )}
        </Card>
      </div>

      <div style={{ marginTop: 18 }}>
        <Card title="已保存坐标">
          {!cal.data || Object.keys(cal.data.overrides).length === 0 ? (
            <Empty>还没有校准坐标。</Empty>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>点位</th>
                  <th>坐标</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cal.data.available.filter((p) => p.overridden).map((point) => (
                  <tr key={point.key}>
                    <td>{point.label}</td>
                    <td className="muted">
                      {point.current[0]}, {point.current[1]}
                    </td>
                    <td>
                      <button className="btn small danger" onClick={() => clearPoint(point.key)}>
                        清除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}

function labelFor(key: string, data: CalibrationData | null): string {
  return data?.available.find((p) => p.key === key)?.label ?? key;
}
