"""
Testes de extra_sources.py usando respostas de exemplo (fixtures) no formato
documentado das APIs da Remotive e Arbeitnow — não faz chamadas de rede reais
(a sandbox de desenvolvimento bloqueia remotive.com/arbeitnow.com; rede real
só é possível localmente). Rodar: python test_extra_sources.py
"""
import extra_sources as es

_REMOTIVE_PAYLOAD = {
    "jobs": [
        {
            "id": 111,
            "title": "Full Stack Developer (React/Node)",
            "company_name": "Acme Remote Co",
            "candidate_required_location": "Worldwide",
            "salary": "$60k - $80k",
            "tags": ["full-stack", "react", "node"],
            "description": "<p>We need a <b>fullstack</b> dev.</p><ul><li>React</li></ul>",
            "url": "https://remotive.com/remote-jobs/software-dev/full-stack-dev-111",
            "publication_date": "2026-07-20T00:00:00",
        },
        {
            "id": 222,
            "title": "Backend Engineer (Go)",
            "company_name": "Other Co",
            "candidate_required_location": "USA Only",
            "tags": ["backend", "go"],
            "description": "<p>Backend only.</p>",
            "url": "https://remotive.com/remote-jobs/software-dev/backend-222",
            "publication_date": "2026-07-19T00:00:00",
        },
    ]
}

_ARBEITNOW_PAGE_1 = {
    "data": [
        {
            "slug": "fullstack-dev-berlin-99",
            "title": "Fullstack Developer",
            "company_name": "Berlin Startup",
            "remote": True,
            "location": "Berlin, Germany",
            "tags": ["fullstack", "vue"],
            "description": "<p>Fullstack role, <strong>remote</strong> ok.</p>",
            "url": "https://www.arbeitnow.com/jobs/fullstack-dev-berlin-99",
            "created_at": 1753100000,
        },
        {
            "slug": "onsite-frontend-only",
            "title": "Frontend Developer",
            "company_name": "OnSite Co",
            "remote": False,
            "location": "Munich, Germany",
            "tags": ["frontend"],
            "description": "<p>Onsite only.</p>",
            "url": "https://www.arbeitnow.com/jobs/onsite-frontend-only",
            "created_at": 1753100001,
        },
        {
            "slug": "remote-backend-only",
            "title": "Backend Developer",
            "company_name": "Remote Backend Co",
            "remote": True,
            "location": "Remote",
            "tags": ["backend"],
            "description": "<p>Backend only, not fullstack.</p>",
            "url": "https://www.arbeitnow.com/jobs/remote-backend-only",
            "created_at": 1753100002,
        },
    ]
}
_ARBEITNOW_EMPTY_PAGE = {"data": []}

_REMOTEOK_PAYLOAD = [
    {"legal": "By using this API you agree to remoteok.com/legal",
     "https://remoteok.com/legal": "description"},
    {
        "id": "999888",
        "position": "Fullstack Engineer (Ruby/React)",
        "company": "RemoteCo",
        "tags": ["fullstack", "ruby", "react"],
        "description": "<p>Build <b>fullstack</b> features.</p>",
        "location": "Worldwide",
        "salary_min": 70000,
        "salary_max": 100000,
        "url": "https://remoteok.com/remote-jobs/999888-fullstack-engineer-remoteco",
        "date": "2026-07-18T00:00:00+00:00",
    },
    {
        "id": "999777",
        "position": "DevOps Engineer",
        "company": "OpsCo",
        "tags": ["devops", "aws"],
        "description": "<p>Ops only.</p>",
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/999777",
        "date": "2026-07-17T00:00:00+00:00",
    },
]


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _install_fake_get(monkeypatch_state):
    def fake_get(url, params=None, timeout=None, headers=None):
        if "remotive" in url:
            return _FakeResp(_REMOTIVE_PAYLOAD)
        if "arbeitnow" in url:
            monkeypatch_state["n"] += 1
            if monkeypatch_state["n"] == 1:
                return _FakeResp(_ARBEITNOW_PAGE_1)
            return _FakeResp(_ARBEITNOW_EMPTY_PAGE)
        if "remoteok" in url:
            return _FakeResp(_REMOTEOK_PAYLOAD)
        raise AssertionError(f"unexpected url {url}")

    es.requests.get = fake_get


def test_is_fullstack_relevant():
    assert es._is_fullstack_relevant("Full Stack Developer")
    assert es._is_fullstack_relevant("Fullstack Engineer")
    assert es._is_fullstack_relevant("Full-Stack Dev")
    assert es._is_fullstack_relevant("Backend Dev", tags=["full-stack", "python"])
    assert not es._is_fullstack_relevant("Backend Engineer", tags=["backend"])


def test_strip_html():
    assert es._strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert es._strip_html("A &amp; B") == "A & B"
    assert es._strip_html(None) == ""


def test_fetch_remotive_filters_by_fullstack_relevance():
    _install_fake_get({"n": 0})
    jobs = es.fetch_remotive()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["id"] == "remotive-111"
    assert job["title"] == "Full Stack Developer (React/Node)"
    assert job["location"] == "Remoto (Worldwide)"
    assert "<" not in job["description"]
    assert "fullstack" in job["description"].lower()


def test_fetch_arbeitnow_filters_remote_and_fullstack():
    _install_fake_get({"n": 0})
    jobs = es.fetch_arbeitnow(max_pages=3)
    assert len(jobs) == 1
    job = jobs[0]
    assert job["id"] == "arbeitnow-fullstack-dev-berlin-99"
    assert job["location"] == "Remoto (Berlin, Germany)"


def test_fetch_remoteok_skips_legal_notice_and_filters_fullstack():
    _install_fake_get({"n": 0})
    jobs = es.fetch_remoteok()
    assert len(jobs) == 1
    job = jobs[0]
    assert job["id"] == "remoteok-999888"
    assert job["title"] == "Fullstack Engineer (Ruby/React)"
    assert job["company"] == "RemoteCo"
    assert "<" not in job["description"]


def test_fetch_remotive_disabled_returns_empty(monkeypatch=None):
    import config
    original = config.ENABLE_REMOTIVE
    config.ENABLE_REMOTIVE = False
    try:
        assert es.fetch_remotive() == []
    finally:
        config.ENABLE_REMOTIVE = original


def test_fetch_handles_network_error_gracefully():
    def broken_get(url, params=None, timeout=None, headers=None):
        raise es.requests.exceptions.ConnectionError("no network")

    es.requests.get = broken_get
    assert es.fetch_remotive() == []
    assert es.fetch_arbeitnow(max_pages=2) == []
    assert es.fetch_remoteok() == []


def test_fetch_all_extra_sources_combines_all_three():
    _install_fake_get({"n": 0})
    jobs = es.fetch_all_extra_sources()
    ids = {j["id"] for j in jobs}
    assert ids == {
        "remotive-111",
        "arbeitnow-fullstack-dev-berlin-99",
        "remoteok-999888",
    }


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passaram")
    return failed


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
