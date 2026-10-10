import os

import pytest

from app import create_app


@pytest.fixture
def app_client(tmp_path):
    db_path = tmp_path / "smart_fridge_test.db"
    app = create_app({"TESTING": True, "DATABASE_PATH": str(db_path), "API_KEY": "smart-fridge-demo-key"})
    with app.test_client() as client:
        yield client
