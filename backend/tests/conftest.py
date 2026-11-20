import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from core import _load_database_module  # noqa: E402

# 固定"现在"：2026-11-19 10:20。种子数据据此生成：
#   班次3/4 今天 09:00–13:00 进行中；班次5 明天 09–13；班次6 明天 13–17；班次7 明天 11–15；
#   班次8/9 后天 09–17（9 已满员）；班次10 第三天 18–22；班次1/2 一周前已结束
FIXED_NOW = datetime(2026, 11, 19, 10, 20, 0)


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("tpl") / "template.db"
    _load_database_module("init_db").init_db(path)
    conn = sqlite3.connect(path)
    _load_database_module("seed").seed(conn, now=FIXED_NOW)
    conn.close()
    return path


class Clock:
    def __init__(self):
        self.value = FIXED_NOW

    def __call__(self):
        return self.value


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def app(template_db, tmp_path, clock):
    db = tmp_path / "test.db"
    shutil.copy(template_db, db)
    return create_app({"DATABASE": str(db), "SECRET_KEY": "test-secret", "TESTING": True, "NOW_FUNC": clock})


class Api:
    def __init__(self, client):
        self.client = client
        self.token = None

    def login(self, username, password):
        r = self.client.post("/api/login", json={"username": username, "password": password})
        if r.status_code == 200:
            self.token = r.get_json()["data"]["token"]
        return r

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, url, **kw):
        return self.client.get(url, headers=self._headers(), **kw)

    def post(self, url, json=None):
        return self.client.post(url, json=json if json is not None else {}, headers=self._headers())

    def put(self, url, json):
        return self.client.put(url, json=json, headers=self._headers())

    def delete(self, url):
        return self.client.delete(url, headers=self._headers())


@pytest.fixture
def anon(app):
    return Api(app.test_client())


@pytest.fixture
def admin(app):
    api = Api(app.test_client())
    assert api.login("admin_zhongwang", "admin123").status_code == 200
    return api


@pytest.fixture
def as_volunteer(app):
    def make(student_no, password=None):
        api = Api(app.test_client())
        r = api.login(student_no, password or student_no[-6:])
        assert r.status_code == 200, r.get_json()
        return api

    return make


def data(resp):
    body = resp.get_json()
    assert body["success"] is True, body
    return body["data"]


def message(resp):
    body = resp.get_json()
    assert body["success"] is False, body
    return body["message"]
