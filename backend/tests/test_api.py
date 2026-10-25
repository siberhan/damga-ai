from fastapi.testclient import TestClient
import pytest
from damga.api import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "damga-ai-backend"
    assert "chain_mode" in data


def test_api_cases():
    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]


def test_api_files_crud():
    # Register file
    reg_payload = {
        "plant_id": "TR-ALIAGA-DEMO-001",
        "year": 2026,
        "cn_code": "72142000",
    }
    create_resp = client.post("/api/files", json=reg_payload)
    assert create_resp.status_code == 200
    file_data = create_resp.json()
    assert "file_key" in file_data
    file_key = file_data["file_key"]

    # List files
    list_resp = client.get("/api/files")
    assert list_resp.status_code == 200
    files_list = list_resp.json()
    assert any(f["file_key"] == file_key for f in files_list)

    # Get file detail
    detail_resp = client.get(f"/api/files/{file_key}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["file_key"] == file_key
    assert "attempts" in detail


def test_full_offline_flow(tmp_path, monkeypatch):
    # Offline (no registry) and a temp state folder: no chain calls, demo state untouched.
    monkeypatch.setenv("DAMGA_REGISTRY_ADDRESS", "")
    monkeypatch.setenv("DAMGA_STATE_DIR", str(tmp_path))

    file_key = client.post("/api/files", json={"plant_id": "TR-ALIAGA-DEMO-001", "year": 2026, "cn_code": "72142000"}).json()["file_key"]
    attempt = client.post(f"/api/files/{file_key}/attempts", json={"case_id": "honest-01"})
    assert attempt.status_code == 200, attempt.text
    assert attempt.json()["attempt_index"] == 0

    issued = client.post(f"/api/files/{file_key}/attempts/0/verify", json={"demo_signer": True})
    assert issued.status_code == 200, issued.text
    pid, salt = issued.json()["passport_id"], issued.json()["importer_salt"]
    assert client.get(f"/api/files/{file_key}/importer-salt").json() == {"passport_id": pid, "importer_salt": salt}

    public = client.get(f"/api/passports/{pid}").json()
    assert public["claims"][0]["verified_on_chain"] is False
    assert "scrap_share_permille" not in str(public) and "input_mix" not in str(public)

    disc = client.get(f"/api/passports/{pid}/disclose?salts={salt}")
    assert disc.status_code == 200
    assert set(disc.json()) == {"passport_id", "direct_kg_per_t", "commitment_match", "cost_gap_note"}
    assert client.get(f"/api/passports/{pid}/disclose?salts=123456").status_code == 403
    assert client.get(f"/api/passports/{pid}/disclose").status_code == 403

    redirect = client.get("/01/00200000000014/10/2026-72142000", follow_redirects=False)
    assert redirect.headers["location"] == f"/passport/{pid}"


def test_unknown_passport_is_404(tmp_path, monkeypatch):
    monkeypatch.setenv("DAMGA_STATE_DIR", str(tmp_path))
    assert client.get("/api/passports/999").status_code == 404
    assert client.get("/01/00200000000014/10/2026-72142000", follow_redirects=False).status_code == 404


def test_importer_salt_needs_a_passport(tmp_path, monkeypatch):
    monkeypatch.setenv("DAMGA_STATE_DIR", str(tmp_path))
    assert client.get("/api/files/0xabc/importer-salt").status_code == 404
