from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_frontend_uses_same_origin_api_proxy_and_loading_state():
    api_source = (ROOT / "web" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    next_config = (ROOT / "web" / "next.config.ts").read_text(encoding="utf-8")
    fleet_page = (ROOT / "web" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert '"/backend-api"' in api_source
    assert 'source: "/backend-api/:path*"' in next_config
    assert "setLoading(false)" in fleet_page
    assert "All Fleet Generation Assets (loading…)" in fleet_page


def test_evidence_accordion_renders_evidence_states_and_provenance():
    accordion_source = (ROOT / "web" / "src" / "components" / "EvidenceAccordion.tsx").read_text(encoding="utf-8")
    assert "OBSERVED" in accordion_source
    assert "RETRIEVED" in accordion_source
    assert "INFERRED" in accordion_source
    assert "INTERNAL_SYNTHETIC" in accordion_source
    assert "Historical context only; it does not confirm the current diagnosis." in accordion_source
