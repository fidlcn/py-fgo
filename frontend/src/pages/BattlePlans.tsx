import { useState } from "react";
import { useAsync, fetchBattlePlans } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";
import { usePersistentState } from "../hooks/usePersistentState";
import type { BattleAction, BattlePlan, BattleWave, CardPolicy } from "../types";

const ACTION_TYPES = [
  "servant_skill",
  "master_skill",
  "noble_phantasm",
  "select_enemy",
  "order_change",
  "face_cards",
  "wait_seconds",
  "wait_state",
];
const ACTION_LABELS: Record<string, string> = {
  servant_skill: "从者技能",
  master_skill: "御主技能",
  noble_phantasm: "宝具",
  select_enemy: "选择敌人",
  order_change: "换人",
  face_cards: "普通指令卡",
  wait_seconds: "等待秒数",
  wait_state: "等待状态",
};
const SLOTS = [1, 2, 3];
const COLORS = ["Arts", "Buster", "Quick"];

const DEFAULT_POLICY: CardPolicy = {
  np_order: [],
  face_card_count: 2,
  color_priority: ["Arts", "Buster", "Quick"],
  servant_priority: [],
  fallback_positions: [1, 2, 3],
};

export function BattlePlans() {
  const list = useAsync(fetchBattlePlans, []);
  const [editing, setEditing] = usePersistentState<BattlePlan | null>("py-fgo.battle-plans.editing", null);
  const [dirty, setDirty] = usePersistentState("py-fgo.battle-plans.dirty", false);
  const [saving, setSaving] = useState(false);

  async function createPlan() {
    const plan = await api.post<BattlePlan>("/api/battle-plans", {
      name: "新战斗方案",
      waves: [{ wave: 1, turns: [{ turn: 1, actions: [], card_policy: { ...DEFAULT_POLICY } }] }],
    });
    list.reload();
    setEditing(plan);
    setDirty(false);
  }

  function patch(mut: (p: BattlePlan) => void) {
    if (!editing) return;
    const clone: BattlePlan = JSON.parse(JSON.stringify(editing));
    mut(clone);
    setEditing(clone);
    setDirty(true);
  }

  async function save() {
    if (!editing) return;
    setSaving(true);
    try {
      const saved = await api.put<BattlePlan>(`/api/battle-plans/${editing.id}`, {
        name: editing.name,
        expected_party: editing.expected_party,
        waves: editing.waves,
        version: editing.version,
      });
      setEditing(saved);
      setDirty(false);
      list.reload();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function deletePlan(plan: BattlePlan) {
    const ok = window.confirm(`确认删除战斗方案「${plan.name}」？`);
    if (!ok) return;
    try {
      await api.del(`/api/battle-plans/${plan.id}`);
      if (editing?.id === plan.id) {
        setEditing(null);
        setDirty(false);
      }
      list.reload();
    } catch (e) {
      alert((e as Error).message);
    }
  }

  return (
    <div>
      <h1 className="page-title">战斗方案</h1>
      <p className="page-sub">
        使用“波次 / 回合 / 动作时间线 + 选卡策略”配置战斗流程。这里只填写从者位、
        技能编号等语义字段，不直接填写坐标。
      </p>

      <div className="grid" style={{ gridTemplateColumns: "300px 1fr" }}>
        <Card
          title="方案列表"
          actions={
            <button className="btn small" onClick={createPlan}>
              + 新建
            </button>
          }
        >
          {list.data && list.data.length === 0 ? (
            <Empty>还没有战斗方案。</Empty>
          ) : (
            <div className="grid">
              {list.data?.map((p) => (
                <div key={p.id} className="row spread">
                  <button
                    className="btn small secondary"
                    style={{ flex: 1, justifyContent: "flex-start" }}
                    onClick={() => {
                      setEditing(p);
                      setDirty(false);
                    }}
                  >
                    {p.name} {editing?.id === p.id && "•"}
                  </button>
                  <button className="btn small danger" onClick={() => deletePlan(p)}>
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>

        {editing ? (
          <Card
            title={
              <input
                value={editing.name}
                onChange={(e) => patch((p) => (p.name = e.target.value))}
                style={{ fontSize: 15, fontWeight: 600 }}
              />
            }
            actions={
              <>
                <button
                  className="btn small secondary"
                  disabled={!dirty}
                  onClick={() => {
                    setEditing(null);
                    setDirty(false);
                  }}
                >
                  放弃草稿
                </button>
                <button className="btn small" disabled={!dirty || saving} onClick={save}>
                  {saving ? "保存中…" : "保存"}
                </button>
              </>
            }
          >
            <PlanEditor plan={editing} patch={patch} />
          </Card>
        ) : (
          <Card>
            <Empty>请选择一个方案，或新建方案。</Empty>
          </Card>
        )}
      </div>
    </div>
  );
}

function PlanEditor({
  plan,
  patch,
}: {
  plan: BattlePlan;
  patch: (mut: (p: BattlePlan) => void) => void;
}) {
  function addWave() {
    patch((p) => p.waves.push({ wave: p.waves.length + 1, turns: [] }));
  }
  function deleteWave(index: number) {
    patch((p) => {
      p.waves.splice(index, 1);
      p.waves.forEach((wave, i) => (wave.wave = i + 1));
    });
  }
  return (
    <div className="grid">
      {plan.waves.map((w, wi) => (
        <WaveBlock
          key={wi}
          wave={w}
          patch={(mut) => patch((p) => mut(p.waves[wi]))}
          onDelete={() => deleteWave(wi)}
        />
      ))}
      <button className="btn small secondary" onClick={addWave}>
        + 添加波次
      </button>
    </div>
  );
}

function WaveBlock({
  wave,
  patch,
  onDelete,
}: {
  wave: BattleWave;
  patch: (mut: (w: BattleWave) => void) => void;
  onDelete: () => void;
}) {
  function deleteTurn(index: number) {
    patch((w) => {
      w.turns.splice(index, 1);
      w.turns.forEach((turn, i) => (turn.turn = i + 1));
    });
  }
  return (
    <Card
      title={`第 ${wave.wave} 波`}
      actions={
        <button className="btn small danger" onClick={onDelete}>
          删除波次
        </button>
      }
    >
      <div className="grid">
        {wave.turns.map((t, ti) => (
          <TurnBlock
            key={ti}
            turn={t}
            patch={(mut) => patch((w) => mut(w.turns[ti]))}
            onDelete={() => deleteTurn(ti)}
          />
        ))}
        <button
          className="btn small secondary"
          onClick={() =>
            patch((w) =>
              w.turns.push({ turn: w.turns.length + 1, actions: [], card_policy: { ...DEFAULT_POLICY } })
            )
          }
        >
          + 添加回合
        </button>
      </div>
    </Card>
  );
}

function TurnBlock({
  turn,
  patch,
  onDelete,
}: {
  turn: { turn: number; actions: BattleAction[]; card_policy?: CardPolicy };
  patch: (mut: (t: typeof turn) => void) => void;
  onDelete: () => void;
}) {
  function addAction(type: string) {
    patch((t) => {
      const a: BattleAction = { type };
      if (type === "servant_skill") Object.assign(a, { servant_slot: 1, skill: 1 });
      if (type === "master_skill") Object.assign(a, { skill: 1 });
      if (type === "noble_phantasm") Object.assign(a, { servant_slot: 1 });
      if (type === "select_enemy") Object.assign(a, { target_slot: 1 });
      if (type === "order_change") Object.assign(a, { reserve_slot: 1, active_slot: 1 });
      if (type === "wait_seconds") Object.assign(a, { seconds: 1 });
      if (type === "wait_state") Object.assign(a, { state: "BATTLE_COMMAND", timeout: 15 });
      t.actions.push(a);
    });
  }
  return (
    <div className="card" style={{ background: "var(--panel-2)" }}>
      <div className="spread" style={{ marginBottom: 10 }}>
        <strong>第 {turn.turn} 回合</strong>
        <div className="row">
          <span className="muted">{turn.actions.length} 个动作</span>
          <button className="btn small danger" onClick={onDelete}>
            删除回合
          </button>
        </div>
      </div>
      <div className="grid">
        {turn.actions.map((a, ai) => (
          <ActionRow
            key={ai}
            action={a}
            patch={(mut) => patch((t) => mut(t.actions[ai]))}
            onDelete={() => patch((t) => t.actions.splice(ai, 1))}
          />
        ))}
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        <select defaultValue="" onChange={(e) => e.target.value && (addAction(e.target.value), (e.target.value = ""))}>
          <option value="">+ 添加动作…</option>
          {ACTION_TYPES.map((t) => (
            <option key={t} value={t}>{ACTION_LABELS[t] ?? t}</option>
          ))}
        </select>
      </div>
      <CardPolicyEditor policy={turn.card_policy ?? {}} patch={(mut) => patch((t) => mut(t.card_policy ?? (t.card_policy = { ...DEFAULT_POLICY })))} />
    </div>
  );
}

function ActionRow({
  action,
  patch,
  onDelete,
}: {
  action: BattleAction;
  patch: (mut: (a: BattleAction) => void) => void;
  onDelete: () => void;
}) {
  const num = (key: keyof BattleAction) => (
    <input
      type="number"
      value={(action[key] as number) ?? 0}
      onChange={(e) => patch((a) => ((a[key] as number) = +e.target.value))}
      style={{ width: 80 }}
    />
  );
  return (
    <div className="row spread">
      <div className="row">
        <span className="badge">{ACTION_LABELS[action.type] ?? action.type}</span>
        {action.type === "servant_skill" && (
          <>
            <span className="muted">从者</span>
            {num("servant_slot")}
            <span className="muted">技能</span>
            {num("skill")}
            <span className="muted">目标</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "master_skill" && (
          <>
            <span className="muted">技能</span>
            {num("skill")}
            <span className="muted">目标</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "noble_phantasm" && (
          <>
            <span className="muted">从者</span>
            {num("servant_slot")}
          </>
        )}
        {action.type === "select_enemy" && (
          <>
            <span className="muted">敌人</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "order_change" && (
          <>
            <span className="muted">后排</span>
            {num("reserve_slot")}
            <span className="muted">前排</span>
            {num("active_slot")}
          </>
        )}
        {action.type === "wait_seconds" && (
          <>
            <span className="muted">秒数</span>
            {num("seconds")}
          </>
        )}
        {action.type === "wait_state" && (
          <input
            value={action.state ?? ""}
            onChange={(e) => patch((a) => (a.state = e.target.value))}
            style={{ width: 200 }}
          />
        )}
      </div>
      <button className="btn small danger" onClick={onDelete}>
        删除
      </button>
    </div>
  );
}

function CardPolicyEditor({
  policy,
  patch,
}: {
  policy: CardPolicy;
  patch: (mut: (p: CardPolicy) => void) => void;
}) {
  const toggle = (arr: number[], v: number) =>
    arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
  return (
    <div style={{ marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 10 }}>
      <div className="muted" style={{ marginBottom: 6 }}>
        选卡策略
      </div>
      <div className="row">
        <Field label="宝具顺序（从者位）">
          <div className="row">
            {SLOTS.map((s) => (
              <label key={s} className="row">
                <input
                  type="checkbox"
                  checked={(policy.np_order ?? []).includes(s)}
                  onChange={() => patch((p) => (p.np_order = toggle(p.np_order ?? [], s)))}
                />
                {s}
              </label>
            ))}
          </div>
        </Field>
        <Field label="补卡数量">
          <input
            type="number"
            value={policy.face_card_count ?? 0}
            onChange={(e) => patch((p) => (p.face_card_count = +e.target.value))}
            style={{ width: 80 }}
          />
        </Field>
        <Field label="兜底卡位">
          <div className="row">
            {[1, 2, 3, 4, 5].map((s) => (
              <label key={s} className="row">
                <input
                  type="checkbox"
                  checked={(policy.fallback_positions ?? []).includes(s)}
                  onChange={() => patch((p) => (p.fallback_positions = toggle(p.fallback_positions ?? [], s)))}
                />
                {s}
              </label>
            ))}
          </div>
        </Field>
      </div>
      <Field label="卡色优先级（逗号分隔）">
        <input
          value={(policy.color_priority ?? COLORS).join(", ")}
          onChange={(e) => patch((p) => (p.color_priority = e.target.value.split(",").map((s) => s.trim())))}
        />
      </Field>
    </div>
  );
}
