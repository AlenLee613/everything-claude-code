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


# ---------------------------------------------------------------------------
# Competitor analysis (prd-competitor SKILL)
# ---------------------------------------------------------------------------

class ProductCategory(str, Enum):
    PROJECT_MANAGEMENT = "project_management"
    NOTE_TAKING = "note_taking"
    ANTIVIRUS = "antivirus"
    CRM = "crm"
    BI_ANALYTICS = "bi_analytics"


class CompetitorPricingTier(BaseModel):
    name: str = Field(..., description="套餐名称，如 Free / Pro / Enterprise")
    price: str = Field(..., description="价格，如 $0 / $10/用户/月 / 自定义")
    key_features: list[str] = Field(default_factory=list, description="该套餐核心功能")


class CompetitorProfile(BaseModel):
    name: str
    founded_year: Optional[int] = None
    funding: Optional[str] = None
    employee_range: Optional[str] = None
    website: Optional[str] = None
    target_customers: str = Field("", description="目标客户描述")
    customer_segments: list[str] = Field(default_factory=list, description="客户细分，如 enterprise / SMB / consumer")
    core_features: list[str] = Field(default_factory=list)
    advanced_features: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    pricing_tiers: list[CompetitorPricingTier] = Field(default_factory=list)
    market_positioning: str = Field("", description="市场定位声明")
    value_proposition: str = Field("", description="核心价值主张")
    gtm_strategy: str = Field("", description="GTM 策略，如 product-led / sales-led / self-serve")
    g2_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="G2 评分")
    g2_review_count: Optional[int] = None
    common_praises: list[str] = Field(default_factory=list)
    common_complaints: list[str] = Field(default_factory=list)


class FeatureComparisonRow(BaseModel):
    feature: str
    category: str = Field(..., description="功能类别，如 核心功能 / 高级功能 / 用户体验 / 集成生态 / 定价")
    competitor_support: dict[str, str] = Field(
        default_factory=dict,
        description="各竞品支持情况：✅ 支持 | ❌ 不支持 | ⚠️ 部分支持",
    )


class MarketGap(BaseModel):
    need: str = Field(..., description="未满足的市场需求")
    demand_level: str = Field(..., description="需求强度：高 / 中 / 低")
    competitor_coverage: str = Field(..., description="竞品覆盖：❌ 无 / ⚠️ 部分 / ✅ 有")
    opportunity_size: str = Field(..., description="机会大小：大 / 中 / 小")


class CompetitorSwot(BaseModel):
    competitor_name: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)


class StrategicInsights(BaseModel):
    positioning_statement: str = Field("", description="建议产品定位声明")
    primary_target: str = Field("", description="首要目标客户")
    secondary_target: str = Field("", description="次要目标客户")
    core_value_prop: str = Field("", description="核心价值主张（一句话）")
    differentiation: str = Field("", description="与竞品的差异化")
    p0_features: list[str] = Field(default_factory=list, description="MVP 必备功能 (P0)")
    p1_features: list[str] = Field(default_factory=list, description="V1.0 重要功能 (P1)")
    p2_features: list[str] = Field(default_factory=list, description="未来规划功能 (P2)")
    pricing_recommendation: str = Field("", description="定价策略建议")
    gtm_recommendation: str = Field("", description="市场进入策略建议")


class CompetitorAnalysisRequest(BaseModel):
    product_category: ProductCategory
    target_product_name: Optional[str] = Field(None, description="目标产品名称（可选，用于定制化建议）")


class CompetitorAnalysisResult(BaseModel):
    product_category: ProductCategory
    target_product_name: Optional[str] = None
    generated_at: datetime
    market_size_usd_billion: Optional[float] = Field(None, description="市场规模（十亿美元）")
    market_growth_rate_pct: Optional[float] = Field(None, description="年增长率（%）")
    market_leaders: list[str] = Field(default_factory=list, description="市场领导者")
    competitors: list[CompetitorProfile] = Field(default_factory=list)
    feature_comparison: list[FeatureComparisonRow] = Field(default_factory=list)
    market_gaps: list[MarketGap] = Field(default_factory=list)
    swot_analyses: list[CompetitorSwot] = Field(default_factory=list)
    strategic_insights: StrategicInsights = Field(default_factory=StrategicInsights)
    research_sources: list[str] = Field(default_factory=list)
