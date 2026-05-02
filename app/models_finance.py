"""
Pydantic models for the financial analysis module.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Industry(str, Enum):
    TECH = "tech"
    CONSUMER = "consumer"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    FINANCE = "finance"
    MANUFACTURING = "manufacturing"


class GartnerPhase(str, Enum):
    INNOVATION_TRIGGER = "innovation_trigger"
    PEAK_OF_INFLATED_EXPECTATIONS = "peak_of_inflated_expectations"
    TROUGH_OF_DISILLUSIONMENT = "trough_of_disillusionment"
    SLOPE_OF_ENLIGHTENMENT = "slope_of_enlightenment"
    PLATEAU_OF_PRODUCTIVITY = "plateau_of_productivity"


class DataSourceCategory(str, Enum):
    SECURITIES = "securities"
    FUNDS = "funds"
    MACRO = "macro"
    MEDIA = "media"


# ---------------------------------------------------------------------------
# Data source models
# ---------------------------------------------------------------------------

class DataSource(BaseModel):
    name: str
    category: DataSourceCategory
    url: Optional[str] = None
    description: str
    industries: list[Industry] = Field(default_factory=list)


class DataSourcesResponse(BaseModel):
    sources: list[DataSource]
    total: int


# ---------------------------------------------------------------------------
# Industry analysis models
# ---------------------------------------------------------------------------

class MarketOverview(BaseModel):
    market_size_cny_billion: Optional[float] = Field(None, description="市场规模（亿元人民币）")
    yoy_growth_rate: Optional[float] = Field(None, description="同比增长率（%）")
    penetration_rate: Optional[float] = Field(None, description="渗透率（%）")
    top_players: list[str] = Field(default_factory=list, description="主要市场参与者")


class PolicyEnvironment(BaseModel):
    recent_policies: list[str] = Field(default_factory=list, description="近期监管政策")
    regulatory_trend: str = Field("", description="监管趋势概述")
    entry_barrier_change: str = Field("", description="行业准入变化")


class CapitalDynamics(BaseModel):
    recent_financing: list[str] = Field(default_factory=list, description="近期融资事件")
    ipo_ma_events: list[str] = Field(default_factory=list, description="IPO/并购事件")
    institutional_changes: str = Field("", description="机构持仓变化摘要")


class RiskFactors(BaseModel):
    policy_risk: str = Field("", description="政策风险")
    market_risk: str = Field("", description="市场风险")
    technology_risk: str = Field("", description="技术风险")
    other_risks: list[str] = Field(default_factory=list, description="其他风险")


class IndustryAnalysis(BaseModel):
    industry: Industry
    generated_at: datetime
    data_freshness: str = Field("", description="数据更新时间说明")
    overview: MarketOverview
    policy: PolicyEnvironment
    capital: CapitalDynamics
    risks: RiskFactors


# ---------------------------------------------------------------------------
# Technology comparison (prd-competitor SKILL)
# ---------------------------------------------------------------------------

class TechEntry(BaseModel):
    name: str = Field(..., description="技术名称")
    description: str = Field("", description="技术简述")
    launch_year: Optional[int] = Field(None, description="技术出现/商用年份")
    is_emerging: bool = Field(False, description="是否为新兴技术")


class TechComparisonRequest(BaseModel):
    industry: Industry
    new_tech: TechEntry
    legacy_tech: TechEntry


class TechComparisonResult(BaseModel):
    industry: Industry
    new_tech: TechEntry
    legacy_tech: TechEntry
    gartner_phase: GartnerPhase
    gartner_phase_description: str
    new_tech_advantages: list[str]
    new_tech_disadvantages: list[str]
    legacy_tech_advantages: list[str]
    legacy_tech_disadvantages: list[str]
    disruption_score: float = Field(..., ge=0.0, le=10.0, description="颠覆程度（0-10）")
    disruption_explanation: str
    investment_implication: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# Standardised report
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    industry: Industry
    include_tech_comparison: bool = Field(True, description="是否包含新技术 vs 历史技术分析")


class IndustryReport(BaseModel):
    report_id: str
    industry: Industry
    generated_at: datetime
    executive_summary: str
    analysis: IndustryAnalysis
    tech_comparison: Optional[TechComparisonResult] = None
    swot_strengths: list[str]
    swot_weaknesses: list[str]
    swot_opportunities: list[str]
    swot_threats: list[str]
    investment_recommendation: str
    risk_warning: str


# ---------------------------------------------------------------------------
# Scheduler status
# ---------------------------------------------------------------------------

class SchedulerStatus(BaseModel):
    running: bool
    jobs: list[dict]
    next_run_times: dict[str, Optional[str]]
