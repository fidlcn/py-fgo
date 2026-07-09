"""Integration: FastAPI health, CRUD, task create (no worker), WS events (spec 14.2)."""

from __future__ import annotations


def test_health(app_client):
    r = app_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["status"] == "ok"


def _seed(app_client):
    inst = app_client.post("/api/instances", json={"name": "M1", "adb_device_id": "127.0.0.1:7555"}).json()["data"]
    qp = app_client.post("/api/quest-profiles", json={"name": "q"}).json()["data"]
    sp = app_client.post("/api/support-profiles", json={"name": "s", "class_filter": "caster"}).json()["data"]
    bp = app_client.post(
        "/api/battle-plans",
        json={"name": "b", "waves": [{"wave": 1, "turns": [{"turn": 1, "actions": [{"type": "servant_skill", "servant_slot": 1, "skill": 1}]}]}]},
    ).json()["data"]
    return inst, qp, sp, bp


def test_instance_crud(app_client):
    inst = app_client.post("/api/instances", json={"name": "X", "adb_device_id": "127.0.0.1:7000"}).json()["data"]
    assert app_client.get("/api/instances").json()["data"][0]["id"] == inst["id"]
    patched = app_client.patch(f"/api/instances/{inst['id']}", json={"name": "Y"}).json()["data"]
    assert patched["name"] == "Y"
    app_client.delete(f"/api/instances/{inst['id']}")
    assert app_client.get("/api/instances").json()["data"] == []


def test_duplicate_device_id_conflict(app_client):
    app_client.post("/api/instances", json={"name": "A", "adb_device_id": "127.0.0.1:7555"})
    r = app_client.post("/api/instances", json={"name": "B", "adb_device_id": "127.0.0.1:7555"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"


def test_profile_crud(app_client):
    for kind, path in [
        ("quest", "/api/quest-profiles"),
        ("support", "/api/support-profiles"),
        ("battle", "/api/battle-plans"),
    ]:
        if kind == "battle":
            payload = {"name": "b", "waves": [{"wave": 1, "turns": [{"turn": 1, "actions": []}]}]}
        else:
            payload = {"name": "b"}
        created = app_client.post(path, json=payload).json()["data"]
        assert app_client.get(path).json()["data"][0]["id"] == created["id"]
        got = app_client.get(f"{path}/{created['id']}").json()["data"]
        assert got["id"] == created["id"]
        app_client.delete(f"{path}/{created['id']}")
        assert app_client.get(path).json()["data"] == []


def test_invalid_battle_plan_rejected(app_client):
    r = app_client.post(
        "/api/battle-plans",
        json={"name": "bad", "waves": [{"turns": [{"actions": [{"type": "nope"}]}]}]},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BATTLE_PLAN_ERROR"


def test_create_task_without_starting_worker(app_client):
    inst, qp, sp, bp = _seed(app_client)
    task = app_client.post(
        "/api/tasks",
        json={
            "instance_id": inst["id"],
            "quest_profile_id": qp["id"],
            "support_profile_id": sp["id"],
            "battle_plan_id": bp["id"],
            "loop_config": {"mode": "count", "count": 5},
        },
    ).json()["data"]
    assert task["status"] == "pending"
    assert task["loop_config"]["count"] == 5
    assert app_client.get("/api/tasks").json()["data"][0]["id"] == task["id"]


def test_websocket_event_format(app_client):
    # Publish an event before connecting so it's in recent history.
    app_client.app.state.bus.publish("task_status", task_id="t1", status="running")
    with app_client.websocket_connect("/ws/events") as ws:
        evt = ws.receive_json()
    assert evt["type"] == "task_status"
    assert evt["payload"]["task_id"] == "t1"
    assert evt["payload"]["status"] == "running"
    assert "timestamp" in evt


def test_quick_start_preflight_reports_no_adb_device(app_client):
    r = app_client.post("/api/quick-start/preflight")
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "NO_ADB_DEVICE"
