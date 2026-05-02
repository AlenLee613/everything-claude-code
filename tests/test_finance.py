"""
Tests for the financial analysis module.

Covers:
  - Data source listing endpoints
  - Industry analysis endpoint
  - Technology comparison (prd-competitor SKILL)
  - Report generation
  - Scheduler status endpoint
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models_finance import GartnerPhase, Industry


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

class TestDataSources:
    def test_list_all_data_sources(self, client: TestClient):
        response = client.get("/api/finance/data-sources")
        assert response.status_code == 200
        body = response.json()
        assert "sources" in body
        assert "total" in body
        assert body["total"] > 0
        assert body["total"] == len(body["sources"])

    def test_data_sources_have_required_fields(self, client: TestClient):
        response = client.get("/api/finance/data-sources")
        sources = response.json()["sources"]
        for source in sources:
            assert "name" in source
            assert "category" in source
            assert "description" in source

    def test_list_data_sources_by_industry_tech(self, client: TestClient):
        response = client.get("/api/finance/data-sources/tech")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] > 0
        names = [s["name"] for s in body["sources"]]
        # Tech-specific media sources should be present
        assert any("36" in n or "虎嗅" in n or "极客" in n for n in names)

    def test_list_data_sources_by_industry_healthcare(self, client: TestClient):
        response = client.get("/api/finance/data-sources/healthcare")
        assert response.status_code == 200
        body = response.json()
        names = [s["name"] for s in body["sources"]]
        assert any("药智" in n or "米内" in n for n in names)

    def test_invalid_industry_returns_422(self, client: TestClient):
        response = client.get("/api/finance/data-sources/unknown_industry")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Industry analysis
# ---------------------------------------------------------------------------

class TestIndustryAnalysis:
    @pytest.mark.parametrize("industry", [i.value for i in Industry])
    def test_get_analysis_all_industries(self, client: TestClient, industry: str):
        response = client.get(f"/api/finance/industries/{industry}")
        assert response.status_code == 200
        body = response.json()
        assert body["industry"] == industry
        assert "overview" in body
        assert "policy" in body
        assert "capital" in body
        assert "risks" in body
        assert "generated_at" in body

    def test_analysis_overview_has_top_players(self, client: TestClient):
        response = client.get("/api/finance/industries/tech")
        body = response.json()
        assert isinstance(body["overview"]["top_players"], list)
        assert len(body["overview"]["top_players"]) > 0

    def test_analysis_policy_has_recent_policies(self, client: TestClient):
        response = client.get("/api/finance/industries/finance")
        body = response.json()
        assert len(body["policy"]["recent_policies"]) > 0

    def test_analysis_risks_has_policy_risk(self, client: TestClient):
        response = client.get("/api/finance/industries/energy")
        body = response.json()
        assert body["risks"]["policy_risk"] != ""

    def test_invalid_industry_returns_422(self, client: TestClient):
        response = client.get("/api/finance/industries/bogus")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Technology comparison (prd-competitor SKILL)
# ---------------------------------------------------------------------------

class TestTechAnalysis:
    def _payload(self, industry: str, new_name: str, legacy_name: str) -> dict:
        return {
            "industry": industry,
            "new_tech": {"name": new_name, "is_emerging": True},
            "legacy_tech": {"name": legacy_name, "is_emerging": False},
        }

    def test_ai_vs_bi_finance(self, client: TestClient):
        response = client.post("/api/finance/tech-analysis", json=self._payload("finance", "AI大模型", "传统BI"))
        assert response.status_code == 200
        body = response.json()
        assert body["industry"] == "finance"
        assert len(body["new_tech_advantages"]) > 0
        assert len(body["new_tech_disadvantages"]) > 0
        assert len(body["legacy_tech_advantages"]) > 0
        assert 0.0 <= body["disruption_score"] <= 10.0
        assert body["gartner_phase"] in [p.value for p in GartnerPhase]

    def test_solid_state_battery_vs_liquid(self, client: TestClient):
        response = client.post("/api/finance/tech-analysis", json=self._payload("energy", "固态电池", "液态锂电池"))
        assert response.status_code == 200
        body = response.json()
        assert body["disruption_score"] >= 5.0
        assert body["gartner_phase_description"] != ""

    def test_quant_vs_active_management(self, client: TestClient):
        response = client.post("/api/finance/tech-analysis", json=self._payload("finance", "量化交易", "主动管理"))
        assert response.status_code == 200
        body = response.json()
        assert body["investment_implication"] != ""

    def test_unknown_tech_returns_default_profile(self, client: TestClient):
        response = client.post("/api/finance/tech-analysis", json=self._payload("tech", "完全未知的黑科技XYZ", "古老技术ABC"))
        assert response.status_code == 200
        body = response.json()
        assert body["gartner_phase"] == GartnerPhase.INNOVATION_TRIGGER.value

    def test_missing_required_fields_returns_422(self, client: TestClient):
        response = client.post("/api/finance/tech-analysis", json={"industry": "tech"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

class TestReportGeneration:
    @pytest.mark.parametrize("industry", [i.value for i in Industry])
    def test_generate_report_all_industries(self, client: TestClient, industry: str):
        response = client.post("/api/finance/reports", json={"industry": industry, "include_tech_comparison": True})
        assert response.status_code == 200
        body = response.json()
        assert body["industry"] == industry
        assert body["report_id"].startswith("rpt_")
        assert body["executive_summary"] != ""

    def test_report_includes_swot(self, client: TestClient):
        response = client.post("/api/finance/reports", json={"industry": "healthcare", "include_tech_comparison": False})
        body = response.json()
        assert len(body["swot_strengths"]) > 0
        assert len(body["swot_weaknesses"]) > 0
        assert len(body["swot_opportunities"]) > 0
        assert len(body["swot_threats"]) > 0

    def test_report_includes_tech_comparison_when_requested(self, client: TestClient):
        response = client.post("/api/finance/reports", json={"industry": "finance", "include_tech_comparison": True})
        body = response.json()
        assert body["tech_comparison"] is not None
        assert body["tech_comparison"]["industry"] == "finance"

    def test_report_excludes_tech_comparison_when_not_requested(self, client: TestClient):
        response = client.post("/api/finance/reports", json={"industry": "tech", "include_tech_comparison": False})
        body = response.json()
        assert body["tech_comparison"] is None

    def test_report_has_investment_recommendation(self, client: TestClient):
        response = client.post("/api/finance/reports", json={"industry": "energy", "include_tech_comparison": False})
        body = response.json()
        assert body["investment_recommendation"] != ""
        assert body["risk_warning"] != ""

    def test_report_missing_industry_returns_422(self, client: TestClient):
        response = client.post("/api/finance/reports", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class TestScheduler:
    def test_scheduler_status_endpoint(self, client: TestClient):
        response = client.get("/api/finance/scheduler/status")
        assert response.status_code == 200
        body = response.json()
        assert "running" in body
        assert "jobs" in body
        assert "next_run_times" in body

    def test_trigger_refresh_all(self, client: TestClient):
        response = client.post("/api/finance/scheduler/trigger")
        assert response.status_code == 202
        assert "已触发全行业数据刷新" in response.json()["message"]

    def test_trigger_refresh_single_industry(self, client: TestClient):
        response = client.post("/api/finance/scheduler/trigger?industry=tech")
        assert response.status_code == 202
        assert "tech" in response.json()["message"]
