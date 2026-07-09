import { useState } from "react";
import { useAsync, fetchSupportProfiles } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";

const CLASSES = ["all", "saber", "archer", "lancer", "rider", "caster", "assassin", "berserker", "extra"];
const EMPTY = {
  name: "",
  class_filter: "all",
  fallback_mode: "first_recommended",
  max_scroll_pages: 5,
  max_refresh_count: 3,
};

export function SupportProfiles() {
  const list = useAsync(fetchSupportProfiles, []);
  const [form, setForm] = useState({ ...EMPTY });

  async function add() {
    await api.post("/api/support-profiles", { ...form, preferred: [] });
    setForm({ ...EMPTY });
    list.reload();
  }

  return (
    <div>
      <h1 className="page-title">Support Profiles</h1>
      <p className="page-sub">
        Class filter + fallback rules. Preferred-list OCR matching is a post-MVP enhancement;
        for now <code>first_recommended</code> picks the top support.
      </p>

      <Card title="New profile" style={{ marginBottom: 18 }}>
        <Field label="Name">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <div className="row">
          <Field label="Class filter">
            <select value={form.class_filter} onChange={(e) => setForm({ ...form, class_filter: e.target.value })}>
              {CLASSES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Fallback">
            <select value={form.fallback_mode} onChange={(e) => setForm({ ...form, fallback_mode: e.target.value })}>
              <option value="first_recommended">first_recommended</option>
              <option value="stop">stop</option>
            </select>
          </Field>
          <Field label="Max scroll pages">
            <input
              type="number"
              value={form.max_scroll_pages}
              onChange={(e) => setForm({ ...form, max_scroll_pages: +e.target.value })}
            />
          </Field>
          <Field label="Max refreshes">
            <input
              type="number"
              value={form.max_refresh_count}
              onChange={(e) => setForm({ ...form, max_refresh_count: +e.target.value })}
            />
          </Field>
        </div>
        <button className="btn" disabled={!form.name} onClick={add}>
          Create
        </button>
      </Card>

      <Card title="Profiles">
        {list.data && list.data.length === 0 ? (
          <Empty>No support profiles yet.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Class</th>
                <th>Fallback</th>
                <th>Scroll / Refresh</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.data?.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td className="muted">{s.class_filter}</td>
                  <td className="muted">{s.fallback_mode}</td>
                  <td className="muted">
                    {s.max_scroll_pages} / {s.max_refresh_count}
                  </td>
                  <td>
                    <button
                      className="btn small danger"
                      onClick={async () => {
                        await api.del(`/api/support-profiles/${s.id}`);
                        list.reload();
                      }}
                    >
                      Delete
                    </button>
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
