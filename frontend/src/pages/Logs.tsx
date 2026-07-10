import { useAsync, useEvents } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty } from "../components/ui";
import type { BotEvent } from "../types";

interface LogData {
  log: string[];
  events: BotEvent[];
}

export function LogsPage() {
  const { data, reload } = useAsync<LogData>(() => api.get("/api/logs"), []);
  const shots = useAsync(() => api.get<{ name: string; size: number; is_error: boolean; url: string }[]>("/api/logs/screenshots"), []);
  const { events, connected } = useEvents(100);

  return (
    <div>
      <h1 className="page-title">日志与事件</h1>
      <p className="page-sub">
        应用日志尾部和实时事件流。{" "}
        {connected ? <span className="badge ok">● 实时连接</span> : <span className="badge muted">○ 未连接</span>}
      </p>

      <div className="grid logs-grid">
        <Card title="日志文件" actions={<button className="btn small secondary" onClick={reload}>刷新</button>}>
          <pre className="log">{data?.log?.length ? data.log.join("\n") : "（空）"}</pre>
        </Card>
        <Card title="最近事件（实时）">
          <div className="event-log">
            {events.length === 0 ? (
              <Empty>暂无事件。</Empty>
            ) : (
              events.map((e, idx) => (
                <div className="line" key={idx}>
                  <span className="ts">{new Date(e.timestamp).toLocaleTimeString()}</span>
                  <span className="type">{e.type}</span>
                  <span className="payload">{JSON.stringify(e.payload)}</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 18 }}>
        <Card title="已保存截图" actions={<button className="btn small secondary" onClick={shots.reload}>刷新</button>}>
          {shots.data && shots.data.length === 0 ? (
            <Empty>暂无保存截图。任务失败时会自动保存异常截图。</Empty>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>文件</th>
                  <th>类型</th>
                  <th>大小</th>
                </tr>
              </thead>
              <tbody>
                {shots.data?.map((s) => (
                  <tr key={s.name}>
                    <td>
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.name}
                      </a>
                    </td>
                    <td>{s.is_error ? <span className="badge err">异常</span> : <span className="badge muted">普通</span>}</td>
                    <td className="muted">{(s.size / 1024).toFixed(1)} KB</td>
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
