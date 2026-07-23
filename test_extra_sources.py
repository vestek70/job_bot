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


_JOBICY_PAYLOAD = {
    "jobs": [
        {
            "id": 55501,
            "jobTitle": "Senior Backend Developer (Python)",
            "companyName": "JobicyCo",
            "jobGeo": "Anywhere",
            "jobIndustry": ["Dev"],
            "jobExcerpt": "Backend role",
            "jobDescription": "<p>Backend <b>Python</b> work.</p>",
            "url": "https://jobicy.com/jobs/55501-backend-dev",
            "pubDate": "2026-07-18",
            "annualSalaryMin": 60000,
            "annualSalaryMax": 90000,
        },
        {
            "id": 55502,
            "jobTitle": "Product Manager",
            "companyName": "OtherCo",
            "jobGeo": "Anywhere",
            "jobIndustry": ["Business"],
            "jobDescription": "<p>PM role.</p>",
            "url": "https://jobicy.com/jobs/55502-pm",
            "pubDate": "2026-07-17",
        },
    ]
}

_THEMUSE_PAGE_0 = {
    "results": [
        {
            "id": 77701,
            "name": "Full Stack Developer",
            "company": {"name": "MuseCo"},
            "locations": [{"name": "São Paulo, Brazil"}],
            "refs": {"landing_page": "https://www.themuse.com/jobs/museco/fullstack"},
            "contents": "<p>Fullstack at MuseCo.</p>",
            "publication_date": "2026-07-16T00:00:00Z",
        },
        {
            "id": 77702,
            "name": "Recruiter",
            "company": {"name": "MuseCo"},
            "locations": [{"name": "Rio de Janeiro, Brazil"}],
            "refs": {"landing_page": "https://www.themuse.com/jobs/museco/recruiter"},
            "contents": "<p>HR role.</p>",
            "publication_date": "2026-07-15T00:00:00Z",
        },
    ]
}
_THEMUSE_EMPTY = {"results": []}


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
        if "jobicy" in url:
            return _FakeResp(_JOBICY_PAYLOAD)
        if "themuse" in url:
            monkeypatch_state["muse"] = monkeypatch_state.get("muse", 0) + 1
            if monkeypatch_state["muse"] == 1:
                return _FakeResp(_THEMUSE_PAGE_0)
            return _FakeResp(_THEMUSE_EMPTY)
        raise AssertionError(f"unexpected url {url}")

    es.requests.get = fake_get


def test_is_dev_relevant_broad():
    # Amplo: casa dev em geral, não só fullstack
    assert es._is_dev_relevant("Full Stack Developer")
    assert es._is_dev_relevant("Backend Engineer")
    assert es._is_dev_relevant("Frontend Developer")
    assert es._is_dev_relevant("React Developer")
    assert es._is_dev_relevant("Desenvolvedor Python")
    assert es._is_dev_relevant("Programador PHP")
    assert es._is_dev_relevant("QA Analyst", tags=["node", "javascript"])
    # Não casa fora de dev
    assert not es._is_dev_relevant("Sales Manager")
    assert not es._is_dev_relevant("Recruiter", tags=["hr"])


def test_strip_html():
    assert es._strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert es._strip_html("A &amp; B") == "A & B"
    assert es._strip_html(None) == ""


def test_fetch_remotive_filters_by_dev_relevance():
    _install_fake_get({"n": 0})
    jobs = es.fetch_remotive()
    # agora backend também passa (relevância ampla): fullstack + backend = 2
    ids = {j["id"] for j in jobs}
    assert "remotive-111" in ids
    fs = next(j for j in jobs if j["id"] == "remotive-111")
    assert fs["location"] == "Remoto (Worldwide)"
    assert "<" not in fs["description"]


def test_fetch_arbeitnow_filters_remote_and_dev():
    _install_fake_get({"n": 0})
    jobs = es.fetch_arbeitnow(max_pages=3)
    # fullstack (remote) + backend (remote) passam; frontend onsite é descartado
    ids = {j["id"] for j in jobs}
    assert "arbeitnow-fullstack-dev-berlin-99" in ids
    assert "arbeitnow-onsite-frontend-only" not in ids  # remote=False


def test_fetch_remoteok_skips_legal_notice_and_filters_dev():
    _install_fake_get({"n": 0})
    jobs = es.fetch_remoteok()
    ids = {j["id"] for j in jobs}
    assert "remoteok-999888" in ids
    job = next(j for j in jobs if j["id"] == "remoteok-999888")
    assert job["company"] == "RemoteCo"
    assert "<" not in job["description"]


def test_fetch_jobicy_filters_dev_and_strips_html():
    _install_fake_get({"n": 0})
    jobs = es.fetch_jobicy()
    ids = {j["id"] for j in jobs}
    assert ids == {"jobicy-55501"}  # backend passa, product manager não
    job = jobs[0]
    assert job["company"] == "JobicyCo"
    assert job["location"] == "Remoto (Anywhere)"
    assert "<" not in job["description"]


def test_fetch_themuse_filters_dev_paginates():
    _install_fake_get({"n": 0, "muse": 0})
    jobs = es.fetch_themuse(max_pages=2)
    ids = {j["id"] for j in jobs}
    assert ids == {"themuse-77701"}  # fullstack passa, recruiter não
    job = jobs[0]
    assert job["company"] == "MuseCo"
    assert "São Paulo, Brazil" in job["location"]
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
    assert es.fetch_jobicy() == []
    assert es.fetch_themuse(max_pages=2) == []


def test_fetch_all_extra_sources_combines_all_sources():
    _install_fake_get({"n": 0, "muse": 0})
    jobs = es.fetch_all_extra_sources()
    ids = {j["id"] for j in jobs}
    # pelo menos uma vaga esperada de cada fonte deve aparecer
    assert "remotive-111" in ids
    assert "arbeitnow-fullstack-dev-berlin-99" in ids
    assert "remoteok-999888" in ids
    assert "jobicy-55501" in ids
    assert "themuse-77701" in ids


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
