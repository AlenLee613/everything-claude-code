"""
Financial analysis API endpoints.

Routes:
  GET  /api/finance/data-sources                  – List all authoritative data sources
  GET  /api/finance/data-sources/{industry}        – Sources filtered by industry
  GET  /api/finance/industries/{industry}          – Full industry analysis
  POST /api/finance/tech-analysis                  – New-vs-legacy technology comparison
  POST /api/finance/reports                        – Generate standardised industry report
  GET  /api/finance/scheduler/status               – APScheduler status
  POST /api/finance/scheduler/trigger              – Manually trigger a data refresh
"""

from __future__ import annotations

from fastapi import APIRouter, status
from app.models_finance import (
    CompetitorAnalysisRequest,
    CompetitorAnalysisResult,
    DataSourcesResponse,
    Industry,
    IndustryAnalysis,
    IndustryReport,
    ReportRequest,
    SchedulerStatus,
    TechComparisonRequest,
    TechComparisonResult,
)
from app.services.competitor_analysis import analyse_competitors
from app.services.data_sources import ALL_SOURCES, get_sources_for_industry
from app.services.finance_service import FinanceService
from app.services.scheduler import (
    _daily_refresh_all,
    _refresh_industry,
    get_scheduler_status,
)
from app.services.tech_analysis import analyse_technologies

router = APIRouter(prefix="/api/finance", tags=["Financial Analysis"])


@router.get(
    "/data-sources",
    response_model=DataSourcesResponse,
    summary="列出所有权威数据源",
)
def list_data_sources() -> DataSourcesResponse:
    """返回系统内注册的全部权威数据源，涵盖证券、基金、宏观数据及行业媒体。"""
    return DataSourcesResponse(sources=ALL_SOURCES, total=len(ALL_SOURCES))


@router.get(
    "/data-sources/{industry}",
    response_model=DataSourcesResponse,
    summary="按行业筛选数据源",
)
def list_data_sources_by_industry(industry: Industry) -> DataSourcesResponse:
    """返回与指定行业相关的权威数据源列表。"""
    sources = get_sources_for_industry(industry)
    return DataSourcesResponse(sources=sources, total=len(sources))


@router.get(
    "/industries/{industry}",
    response_model=IndustryAnalysis,
    summary="行业市场分析",
)
def get_industry_analysis(industry: Industry) -> IndustryAnalysis:
    """
    返回指定行业的完整市场分析，包括：
    - **行业概览**：市场规模、增长率、渗透率、主要玩家
    - **政策环境**：近期监管政策与准入变化
    - **资本动态**：融资事件、IPO/并购、机构持仓变化
    - **风险提示**：政策、市场、技术和其他风险
    """
    return FinanceService.get_industry_analysis(industry)


@router.post(
    "/tech-analysis",
    response_model=TechComparisonResult,
    status_code=status.HTTP_200_OK,
    summary="新技术 vs 历史技术对比分析（prd-competitor SKILL）",
)
def technology_comparison(request: TechComparisonRequest) -> TechComparisonResult:
    """
    对新兴技术与历史技术进行专业对比分析，输出：
    - **Gartner 曲线定位**、**新/历史技术优劣势**、**颠覆度评分（0-10）**、**投资建议**

    典型对比示例：`AI大模型` vs `传统BI`（finance）、`固态电池` vs `液态锂电池`（energy）
    """
    return analyse_technologies(request)


@router.post(
    "/competitor-analysis",
    response_model=CompetitorAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="竞品分析（prd-competitor SKILL）",
)
def competitor_analysis(request: CompetitorAnalysisRequest) -> CompetitorAnalysisResult:
    """
    对指定产品类别进行深度竞品分析，输出：
    - **竞品详细档案**（目标客户、核心功能、优劣势、定价、GTM 策略、用户评价）
    - **功能对比矩阵**（各竞品功能支持情况）
    - **市场缺口分析**（未被满足的用户需求）
    - **SWOT 分析**（头部竞品）
    - **战略建议**（定位、定价、MVP 功能优先级、GTM 策略）

    支持产品类别：`project_management` | `note_taking` | `antivirus` | `crm` | `bi_analytics`
    """
    return analyse_competitors(request)


@router.post(
    "/reports",
    response_model=IndustryReport,
    status_code=status.HTTP_200_OK,
    summary="生成标准化行业分析报告",
)
def generate_report(request: ReportRequest) -> IndustryReport:
    """
    生成完整的标准化行业报告（执行摘要、数据看板、技术对比、SWOT、投资建议）。
    """
    return FinanceService.generate_report(request)


@router.get(
    "/scheduler/status",
    response_model=SchedulerStatus,
    summary="查看数据刷新调度器状态",
)
def scheduler_status() -> SchedulerStatus:
    """返回 APScheduler 的运行状态及所有已注册任务的下次执行时间。"""
    return get_scheduler_status()


@router.post(
    "/scheduler/trigger",
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发数据刷新",
)
def trigger_refresh(industry: Industry | None = None) -> dict:
    """
    立即触发一次数据刷新。不传 `industry` 时刷新所有行业；传入特定行业时仅刷新该行业。
    """
    if industry:
        _refresh_industry(industry)
        return {"message": f"已触发行业数据刷新: {industry.value}"}
    _daily_refresh_all()
    return {"message": "已触发全行业数据刷新"}
