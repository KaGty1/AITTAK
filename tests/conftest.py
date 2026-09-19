import pytest

import app.database as database
import app.inject as inject
import app.sensitive as sensitive


@pytest.fixture(autouse=True)
def clean_caches():
    def reset():
        inject._rules_cache = None
        inject._inject_id_map.clear()
        sensitive._rules_cache = None
        sensitive._compiled_cache = None

    reset()
    yield
    reset()


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    await database.init_db()
    yield database.get_db()
    await database.close_db()
