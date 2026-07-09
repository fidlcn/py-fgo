import { useState } from "react";
import { useAsync, fetchBattlePlans } from "../api/hooks";
import { api } from "../api/client";
import { Card, Empty, Field } from "../components/ui";
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
  const [editing, setEditing] = useState<BattlePlan | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  async function createPlan() {
    const plan = await api.post<BattlePlan>("/api/battle-plans", {
      name: "New plan",
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

  return (
    <div>
      <h1 className="page-title">Battle Plans</h1>
      <p className="page-sub">
        Wave / turn / action timeline with a card policy. Use semantic fields (servant slot,
        skill number) — never raw coordinates.
      </p>

      <div className="grid" style={{ gridTemplateColumns: "300px 1fr" }}>
        <Card
          title="Plans"
          actions={
            <button className="btn small" onClick={createPlan}>
              + New
            </button>
          }
        >
          {list.data && list.data.length === 0 ? (
            <Empty>No plans yet.</Empty>
          ) : (
            <div className="grid">
              {list.data?.map((p) => (
                <button
                  key={p.id}
                  className="btn small secondary"
                  style={{ justifyContent: "flex-start" }}
                  onClick={() => {
                    setEditing(p);
                    setDirty(false);
                  }}
                >
                  {p.name} {editing?.id === p.id && "•"}
                </button>
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
              <button className="btn small" disabled={!dirty || saving} onClick={save}>
                {saving ? "Saving…" : "Save"}
              </button>
            }
          >
            <PlanEditor plan={editing} patch={patch} />
          </Card>
        ) : (
          <Card>
            <Empty>Select a plan or create a new one.</Empty>
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
  return (
    <div className="grid">
      {plan.waves.map((w, wi) => (
        <WaveBlock key={wi} wave={w} patch={(mut) => patch((p) => mut(p.waves[wi]))} />
      ))}
      <button className="btn small secondary" onClick={addWave}>
        + Add wave
      </button>
    </div>
  );
}

function WaveBlock({
  wave,
  patch,
}: {
  wave: BattleWave;
  patch: (mut: (w: BattleWave) => void) => void;
}) {
  return (
    <Card title={`Wave ${wave.wave}`}>
      <div className="grid">
        {wave.turns.map((t, ti) => (
          <TurnBlock key={ti} turn={t} patch={(mut) => patch((w) => mut(w.turns[ti]))} />
        ))}
        <button
          className="btn small secondary"
          onClick={() =>
            patch((w) =>
              w.turns.push({ turn: w.turns.length + 1, actions: [], card_policy: { ...DEFAULT_POLICY } })
            )
          }
        >
          + Add turn
        </button>
      </div>
    </Card>
  );
}

function TurnBlock({
  turn,
  patch,
}: {
  turn: { turn: number; actions: BattleAction[]; card_policy?: CardPolicy };
  patch: (mut: (t: typeof turn) => void) => void;
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
        <strong>Turn {turn.turn}</strong>
        <span className="muted">{turn.actions.length} action(s)</span>
      </div>
      <div className="grid">
        {turn.actions.map((a, ai) => (
          <ActionRow key={ai} action={a} patch={(mut) => patch((t) => mut(t.actions[ai]))} />
        ))}
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        <select defaultValue="" onChange={(e) => e.target.value && (addAction(e.target.value), (e.target.value = ""))}>
          <option value="">+ Add action…</option>
          {ACTION_TYPES.map((t) => (
            <option key={t}>{t}</option>
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
}: {
  action: BattleAction;
  patch: (mut: (a: BattleAction) => void) => void;
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
        <span className="badge">{action.type}</span>
        {action.type === "servant_skill" && (
          <>
            <span className="muted">servant</span>
            {num("servant_slot")}
            <span className="muted">skill</span>
            {num("skill")}
            <span className="muted">target</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "master_skill" && (
          <>
            <span className="muted">skill</span>
            {num("skill")}
            <span className="muted">target</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "noble_phantasm" && (
          <>
            <span className="muted">servant</span>
            {num("servant_slot")}
          </>
        )}
        {action.type === "select_enemy" && (
          <>
            <span className="muted">enemy</span>
            {num("target_slot")}
          </>
        )}
        {action.type === "order_change" && (
          <>
            <span className="muted">reserve</span>
            {num("reserve_slot")}
            <span className="muted">active</span>
            {num("active_slot")}
          </>
        )}
        {action.type === "wait_seconds" && (
          <>
            <span className="muted">seconds</span>
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
        Card policy
      </div>
      <div className="row">
        <Field label="NP order (servant slots)">
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
        <Field label="Face card count">
          <input
            type="number"
            value={policy.face_card_count ?? 0}
            onChange={(e) => patch((p) => (p.face_card_count = +e.target.value))}
            style={{ width: 80 }}
          />
        </Field>
        <Field label="Fallback positions">
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
      <Field label="Color priority (comma separated)">
        <input
          value={(policy.color_priority ?? COLORS).join(", ")}
          onChange={(e) => patch((p) => (p.color_priority = e.target.value.split(",").map((s) => s.trim())))}
        />
      </Field>
    </div>
  );
}
