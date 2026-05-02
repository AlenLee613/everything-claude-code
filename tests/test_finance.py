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


# ---------------------------------------------------------------------------
# Competitor Analysis (prd-competitor SKILL)
# ---------------------------------------------------------------------------

class TestCompetitorAnalysis:
    def _payload(self, category: str, target_name: str | None = None) -> dict:
        body: dict = {"product_category": category}
        if target_name is not None:
            body["target_product_name"] = target_name
        return body

    @pytest.mark.parametrize("category", [
        "project_management", "note_taking", "antivirus", "crm", "bi_analytics"
    ])
    def test_all_categories_return_200(self, client: TestClient, category: str):
        response = client.post("/api/finance/competitor-analysis", json=self._payload(category))
        assert response.status_code == 200
        body = response.json()
        assert body["product_category"] == category

    def test_response_has_competitors(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("project_management"))
        body = response.json()
        assert len(body["competitors"]) >= 5
        for c in body["competitors"]:
            assert "name" in c
            assert "strengths" in c
            assert "weaknesses" in c
            assert isinstance(c["pricing_tiers"], list)

    def test_response_has_feature_comparison(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("note_taking"))
        body = response.json()
        assert len(body["feature_comparison"]) > 0
        row = body["feature_comparison"][0]
        assert "feature" in row
        assert "category" in row
        assert "competitor_support" in row
        assert isinstance(row["competitor_support"], dict)

    def test_response_has_market_gaps(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("antivirus"))
        body = response.json()
        assert len(body["market_gaps"]) > 0
        gap = body["market_gaps"][0]
        assert "need" in gap
        assert "demand_level" in gap
        assert "opportunity_size" in gap

    def test_response_has_swot_analyses(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("crm"))
        body = response.json()
        assert len(body["swot_analyses"]) >= 3
        swot = body["swot_analyses"][0]
        assert "competitor_name" in swot
        assert len(swot["strengths"]) > 0
        assert len(swot["weaknesses"]) > 0

    def test_response_has_strategic_insights(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("bi_analytics"))
        body = response.json()
        insights = body["strategic_insights"]
        assert insights["positioning_statement"] != ""
        assert len(insights["p0_features"]) > 0
        assert insights["pricing_recommendation"] != ""
        assert insights["gtm_recommendation"] != ""

    def test_market_metadata_present(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("project_management"))
        body = response.json()
        assert body["market_size_usd_billion"] is not None
        assert body["market_growth_rate_pct"] is not None
        assert len(body["market_leaders"]) > 0

    def test_optional_target_product_name(self, client: TestClient):
        response = client.post(
            "/api/finance/competitor-analysis",
            json=self._payload("note_taking", "MyApp"),
        )
        assert response.status_code == 200
        assert response.json()["target_product_name"] == "MyApp"

    def test_optional_target_product_name_defaults_to_none(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("crm"))
        assert response.status_code == 200
        assert response.json()["target_product_name"] is None

    def test_research_sources_provided(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("antivirus"))
        body = response.json()
        assert len(body["research_sources"]) >= 3

    def test_invalid_category_returns_422(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json={"product_category": "unknown_xyz"})
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json={})
        assert response.status_code == 422

    def test_competitor_g2_rating_in_valid_range(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("project_management"))
        body = response.json()
        for c in body["competitors"]:
            if c["g2_rating"] is not None:
                assert 0.0 <= c["g2_rating"] <= 5.0

    def test_generated_at_present(self, client: TestClient):
        response = client.post("/api/finance/competitor-analysis", json=self._payload("antivirus"))
        body = response.json()
        assert "generated_at" in body
        assert body["generated_at"] is not None

