import { useState } from "react";
import { useAsync, fetchQuestProfiles } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";

const EMPTY = { name: "", category: "daily", entry_mode: "current_quest", server_region: "cn" };
const CATEGORY_LABELS: Record<string, string> = {
  daily: "日常本",
  event: "活动本",
  free: "自由本",
  custom: "自定义",
};
const REGION_LABELS: Record<string, string> = {
  cn: "国服",
  jp: "日服",
  na: "美服",
  other: "其他",
};
const ENTRY_LABELS: Record<string, string> = {
  current_quest: "当前关卡",
  auto_navigate: "自动导航（后续支持）",
};

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
      <h1 className="page-title">关卡配置</h1>
      <p className="page-sub">
        MVP 使用 <code>current_quest</code> 入口模式：先手动打开关卡详情页，
        软件从当前页面开始执行。
      </p>

      <Card title="新建配置" style={{ marginBottom: 18 }}>
        <Field label="名称">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <div className="row">
          <Field label="类型">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {["daily", "event", "free", "custom"].map((c) => (
                <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
              ))}
            </select>
          </Field>
          <Field label="入口模式">
            <select value={form.entry_mode} onChange={(e) => setForm({ ...form, entry_mode: e.target.value })}>
              <option value="current_quest">{ENTRY_LABELS.current_quest}</option>
              <option value="auto_navigate">{ENTRY_LABELS.auto_navigate}</option>
            </select>
          </Field>
          <Field label="服务器">
            <select value={form.server_region} onChange={(e) => setForm({ ...form, server_region: e.target.value })}>
              {["cn", "jp", "na", "other"].map((c) => (
                <option key={c} value={c}>{REGION_LABELS[c]}</option>
              ))}
            </select>
          </Field>
        </div>
        <button className="btn" disabled={!form.name} onClick={add}>
          创建
        </button>
      </Card>

      <Card title="配置列表">
        {list.data && list.data.length === 0 ? (
          <Empty>还没有关卡配置。</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>入口</th>
                <th>服务器</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.data?.map((q) => (
                <tr key={q.id}>
                  <td>{q.name}</td>
                  <td className="muted">{CATEGORY_LABELS[q.category] ?? q.category}</td>
                  <td className="muted">{ENTRY_LABELS[q.entry_mode] ?? q.entry_mode}</td>
                  <td className="muted">{REGION_LABELS[q.server_region] ?? q.server_region}</td>
                  <td>
                    <button
                      className="btn small danger"
                      onClick={async () => {
                        await api.del(`/api/quest-profiles/${q.id}`);
                        list.reload();
                      }}
                    >
                      删除
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
