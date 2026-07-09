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
      <h1 className="page-title">Logs & Events</h1>
      <p className="page-sub">
        Application log tail + live event stream.{" "}
        {connected ? <span className="badge ok">● live</span> : <span className="badge muted">○ disconnected</span>}
      </p>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <Card title="Log file" actions={<button className="btn small secondary" onClick={reload}>Refresh</button>}>
          <pre className="log">{data?.log?.length ? data.log.join("\n") : "(empty)"}</pre>
        </Card>
        <Card title="Recent events (live)">
          <div className="event-log">
            {events.length === 0 ? (
              <Empty>No events yet.</Empty>
            ) : (
              events.map((e, idx) => (
                <div className="line" key={idx}>
                  <span className="ts">{new Date(e.timestamp).toLocaleTimeString()}</span>
                  <span className="type">{e.type}</span>
                  <span>{JSON.stringify(e.payload)}</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 18 }}>
        <Card title="Saved screenshots" actions={<button className="btn small secondary" onClick={shots.reload}>Refresh</button>}>
          {shots.data && shots.data.length === 0 ? (
            <Empty>No saved screenshots. Error screenshots are captured automatically on failure.</Empty>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Type</th>
                  <th>Size</th>
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
                    <td>{s.is_error ? <span className="badge err">error</span> : <span className="badge muted">normal</span>}</td>
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
