import { useState } from "react";
import { useAsync, fetchSupportProfiles } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";

const CLASSES = ["all", "saber", "archer", "lancer", "rider", "caster", "assassin", "berserker", "extra"];
const CLASS_LABELS: Record<string, string> = {
  all: "全部",
  saber: "剑阶",
  archer: "弓阶",
  lancer: "枪阶",
  rider: "骑阶",
  caster: "术阶",
  assassin: "杀阶",
  berserker: "狂阶",
  extra: "特殊职阶",
};
const FALLBACK_LABELS: Record<string, string> = {
  first_recommended: "推荐第一个",
  stop: "停止任务",
};
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
      <h1 className="page-title">助战配置</h1>
      <p className="page-sub">
        配置助战职介筛选和兜底规则。指定好友/OCR 匹配属于后续增强；
        当前 <code>first_recommended</code> 会选择推荐列表第一个助战。
      </p>

      <Card title="新建配置" style={{ marginBottom: 18 }}>
        <Field label="名称">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <div className="row">
          <Field label="职介筛选">
            <select value={form.class_filter} onChange={(e) => setForm({ ...form, class_filter: e.target.value })}>
              {CLASSES.map((c) => (
                <option key={c} value={c}>{CLASS_LABELS[c]}</option>
              ))}
            </select>
          </Field>
          <Field label="兜底策略">
            <select value={form.fallback_mode} onChange={(e) => setForm({ ...form, fallback_mode: e.target.value })}>
              <option value="first_recommended">{FALLBACK_LABELS.first_recommended}</option>
              <option value="stop">{FALLBACK_LABELS.stop}</option>
            </select>
          </Field>
          <Field label="最大滚动页数">
            <input
              type="number"
              value={form.max_scroll_pages}
              onChange={(e) => setForm({ ...form, max_scroll_pages: +e.target.value })}
            />
          </Field>
          <Field label="最大刷新次数">
            <input
              type="number"
              value={form.max_refresh_count}
              onChange={(e) => setForm({ ...form, max_refresh_count: +e.target.value })}
            />
          </Field>
        </div>
        <button className="btn" disabled={!form.name} onClick={add}>
          创建
        </button>
      </Card>

      <Card title="配置列表">
        {list.data && list.data.length === 0 ? (
          <Empty>还没有助战配置。</Empty>
        ) : (
          <table>
            <thead>
              <tr>
                <th>名称</th>
                <th>职介</th>
                <th>兜底</th>
                <th>滚动 / 刷新</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.data?.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td className="muted">{CLASS_LABELS[s.class_filter] ?? s.class_filter}</td>
                  <td className="muted">{FALLBACK_LABELS[s.fallback_mode] ?? s.fallback_mode}</td>
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
