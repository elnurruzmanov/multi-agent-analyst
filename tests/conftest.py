import os
import sys

os.environ["MOCK_LLM"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

import config  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def prepared_environment():
    """Build the sample DB and document index once, in mock mode."""
    assert config.MOCK, "tests must run offline"
    from db import init_db
    if not os.path.exists(init_db.DB):
        init_db.main()
    import ingestion
    if not config.qdrant().collection_exists(config.COLLECTION):
        ingestion.main()
    yield
    config.qdrant().close()


@pytest.fixture(autouse=True)
def isolated_memory(tmp_path, monkeypatch):
    import memory
    monkeypatch.setattr(memory, "PATH", str(tmp_path / "memory.json"))
