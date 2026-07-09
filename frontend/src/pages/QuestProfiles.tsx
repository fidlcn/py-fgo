import { useState } from "react";
import { useAsync, fetchQuestProfiles } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";

const EMPTY = { name: "", category: "daily", entry_mode: "current_quest", server_region: "cn" };

export function QuestProfiles() {
  const list = useAsync(fetchQuestProfiles, []);
  const [form, setForm] = useState({ ...EMPTY });

  async function add() {
    await api.post("/api/quest-profiles", form);
    setForm({ ...EMPTY });
    list.reload();
  }

  return (
    <div>
      <h1 className="page-title">Quest Profiles</h1>
      <p className="page-sub">
        MVP uses <code>current_quest</code> entry mode: you manually open the quest detail page,
        and the bot starts from there.
      </p>

      <Card title="New profile" style={{ marginBottom: 18 }}>
        <Field label="Name">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <div className="row">
          <Field label="Category">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {["daily", "event", "free", "custom"].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Entry mode">
            <select value={form.entry_mode} onChange={(e) => setForm({ ...form, entry_mode: e.target.value })}>
              <option value="current_quest">current_quest</option>
              <option value="auto_navigate">auto_navigate (later)</option>
            </select>
          </Field>
          <Field label="Server region">
            <select value={form.server_region} onChange={(e) => setForm({ ...form, server_region: e.target.value })}>
              {["cn", "jp", "na", "other"].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
        </div>
        <button className="btn" disabled={!form.name} onClick={add}>
          Create
        </button>
      </Card>

      <Card title="Profiles">
        {list.data && list.data.length === 0 ? (
          <Empty>No quest profiles yet.</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Entry</th>
                <th>Region</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.data?.map((q) => (
                <tr key={q.id}>
                  <td>{q.name}</td>
                  <td className="muted">{q.category}</td>
                  <td className="muted">{q.entry_mode}</td>
                  <td className="muted">{q.server_region}</td>
                  <td>
                    <button
                      className="btn small danger"
                      onClick={async () => {
                        await api.del(`/api/quest-profiles/${q.id}`);
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
