import json

from app.backend.kiosk_lock import KioskLockStore


def test_kiosk_lock_stores_admin_visible_password_and_hash(tmp_path):
    path = tmp_path / "kiosk_lock.json"
    store = KioskLockStore(path)

    snapshot = store.configure(
        password="MijnGeheim123",
        reminder_question="Welke vraag?",
        reminder_hint="Denk hieraan",
        notes="Eigen notitie",
    )

    assert snapshot["configured"] is True
    assert snapshot["password"] == "MijnGeheim123"
    assert snapshot["reminder_question"] == "Welke vraag?"
    assert store.verify_password("MijnGeheim123") is True
    assert store.verify_password("verkeerd") is False

    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["password"] == "MijnGeheim123"
    assert payload["password_hash"]
    assert payload["password_salt"]


def test_kiosk_lock_override_is_explicit_separate_check(tmp_path):
    store = KioskLockStore(tmp_path / "kiosk_lock.json")
    store.configure(password="LokaalPw", reminder_question="", reminder_hint="", notes="")

    assert store.verify_password("Aitje123!") is False
    assert store.verify_override_password("Aitje123!", "Aitje123!") is True
    assert store.verify_override_password("verkeerd", "Aitje123!") is False
    assert store.verify_override_password("Aitje123!", "") is False


def test_kiosk_lock_backfills_visible_password_after_legacy_verify(tmp_path):
    path = tmp_path / "kiosk_lock.json"
    store = KioskLockStore(path)
    store.configure(password="OudWachtwoord", reminder_question="", reminder_hint="", notes="")

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("password")
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert store.snapshot()["password"] == ""
    assert store.verify_password("OudWachtwoord") is True
    assert store.snapshot()["password"] == "OudWachtwoord"
