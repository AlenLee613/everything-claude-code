"""
Data source registry for the financial analysis module.

Defines all authoritative data sources (securities, funds, macro, media)
and provides a lightweight fetch layer.  Real integrations with akshare /
tushare are imported lazily so the service degrades gracefully when those
optional libraries are not installed.
"""

from __future__ import annotations

import datetime
from typing import Any

from loguru import logger

from app.models_finance import DataSource, DataSourceCategory, Industry


# ---------------------------------------------------------------------------
# Static source catalogue
# ---------------------------------------------------------------------------

ALL_SOURCES: list[DataSource] = [
    # Securities
    DataSource(
        name="沪深交易所",
        category=DataSourceCategory.SECURITIES,
        url="http://www.sse.com.cn",
        description="上交所 / 深交所官方数据",
        industries=list(Industry),
    ),
    DataSource(
        name="东方财富",
        category=DataSourceCategory.SECURITIES,
        url="https://www.eastmoney.com",
        description="东方财富网行情与资讯",
        industries=list(Industry),
    ),
    DataSource(
        name="同花顺",
        category=DataSourceCategory.SECURITIES,
        url="https://www.10jqka.com.cn",
        description="同花顺行情数据",
        industries=list(Industry),
    ),
    DataSource(
        name="Wind",
        category=DataSourceCategory.SECURITIES,
        url="https://www.wind.com.cn",
        description="Wind 金融终端（机构）",
        industries=list(Industry),
    ),
    DataSource(
        name="Choice（东财）",
        category=DataSourceCategory.SECURITIES,
        url="https://choice.eastmoney.com",
        description="东方财富 Choice 数据终端",
        industries=list(Industry),
    ),
    # Funds
    DataSource(
        name="天天基金网",
        category=DataSourceCategory.FUNDS,
        url="https://fund.eastmoney.com",
        description="公募基金净值与排行",
        industries=list(Industry),
    ),
    DataSource(
        name="晨星中国",
        category=DataSourceCategory.FUNDS,
        url="https://cn.morningstar.com",
        description="晨星基金评级与数据",
        industries=list(Industry),
    ),
    DataSource(
        name="基金业协会",
        category=DataSourceCategory.FUNDS,
        url="https://www.amac.org.cn",
        description="中国证券投资基金业协会信息披露",
        industries=list(Industry),
    ),
    # Macro
    DataSource(
        name="国家统计局",
        category=DataSourceCategory.MACRO,
        url="https://www.stats.gov.cn",
        description="GDP、CPI、工业增加值等宏观数据",
        industries=list(Industry),
    ),
    DataSource(
        name="中国人民银行",
        category=DataSourceCategory.MACRO,
        url="https://www.pbc.gov.cn",
        description="货币政策、利率、M2 等数据",
        industries=list(Industry),
    ),
    DataSource(
        name="发改委",
        category=DataSourceCategory.MACRO,
        url="https://www.ndrc.gov.cn",
        description="产业政策与发展规划",
        industries=list(Industry),
    ),
    # Media – general
    DataSource(
        name="证券时报",
        category=DataSourceCategory.MEDIA,
        url="https://www.stcn.com",
        description="证券时报权威金融资讯",
        industries=list(Industry),
    ),
    DataSource(
        name="上海证券报",
        category=DataSourceCategory.MEDIA,
        url="https://www.cnstock.com",
        description="上证报权威金融资讯",
        industries=list(Industry),
    ),
    DataSource(
        name="中国证券报",
        category=DataSourceCategory.MEDIA,
        url="https://www.cs.com.cn",
        description="中证报权威金融资讯",
        industries=list(Industry),
    ),
    DataSource(
        name="财新",
        category=DataSourceCategory.MEDIA,
        url="https://www.caixin.com",
        description="财新传媒深度财经报道",
        industries=list(Industry),
    ),
    # Media – tech
    DataSource(
        name="36氪",
        category=DataSourceCategory.MEDIA,
        url="https://36kr.com",
        description="36氪科技与创投资讯",
        industries=[Industry.TECH],
    ),
    DataSource(
        name="虎嗅",
        category=DataSourceCategory.MEDIA,
        url="https://www.huxiu.com",
        description="虎嗅科技深度报道",
        industries=[Industry.TECH],
    ),
    DataSource(
        name="极客公园",
        category=DataSourceCategory.MEDIA,
        url="https://www.geekpark.net",
        description="极客公园科技创新报道",
        industries=[Industry.TECH],
    ),
    # Media – consumer/retail
    DataSource(
        name="联商网",
        category=DataSourceCategory.MEDIA,
        url="https://www.linkshop.com.cn",
        description="联商网零售行业资讯",
        industries=[Industry.CONSUMER],
    ),
    DataSource(
        name="赢商网",
        category=DataSourceCategory.MEDIA,
        url="https://www.winshang.com",
        description="赢商网商业地产与零售资讯",
        industries=[Industry.CONSUMER],
    ),
    # Media – healthcare
    DataSource(
        name="药智网",
        category=DataSourceCategory.MEDIA,
        url="https://www.yaozh.com",
        description="药智网医药行业数据库",
        industries=[Industry.HEALTHCARE],
    ),
    DataSource(
        name="米内网",
        category=DataSourceCategory.MEDIA,
        url="https://www.menet.com.cn",
        description="米内网医药市场研究数据",
        industries=[Industry.HEALTHCARE],
    ),
    # Media – energy/manufacturing
    DataSource(
        name="高工产业研究",
        category=DataSourceCategory.MEDIA,
        url="https://www.gg-robot.com",
        description="高工产业研究院新能源报告",
        industries=[Industry.ENERGY, Industry.MANUFACTURING],
    ),
    DataSource(
        name="鑫椤资讯",
        category=DataSourceCategory.MEDIA,
        url="https://www.xinluozixun.com",
        description="鑫椤资讯锂电行业数据",
        industries=[Industry.ENERGY, Industry.MANUFACTURING],
    ),
]


def get_sources_for_industry(industry: Industry) -> list[DataSource]:
    """Return all data sources relevant to the given industry."""
    return [s for s in ALL_SOURCES if not s.industries or industry in s.industries]


# ---------------------------------------------------------------------------
# Fetch helpers (akshare with fallback to stub data)
# ---------------------------------------------------------------------------

def _try_akshare_market_data(industry: Industry) -> dict[str, Any] | None:
    """Attempt to pull real-time market data via akshare. Returns None on failure."""
    try:
        import akshare as ak  # type: ignore
        df = ak.stock_sector_spot(indicator="涨跌幅")
        logger.info("akshare sector data fetched ({} rows)", len(df))
        return {"source": "akshare", "rows": len(df)}
    except (ImportError, ConnectionError, KeyError) as exc:
        logger.warning("akshare fetch failed: {}", exc)
        return None


_STUB_DATA: dict[Industry, dict[str, Any]] = {
    Industry.TECH: {
        "market_size_cny_billion": 12500.0,
        "yoy_growth_rate": 18.5,
        "penetration_rate": 42.0,
        "top_players": ["华为", "腾讯", "阿里巴巴", "百度", "字节跳动"],
    },
    Industry.CONSUMER: {
        "market_size_cny_billion": 44000.0,
        "yoy_growth_rate": 6.2,
        "penetration_rate": 35.0,
        "top_players": ["拼多多", "阿里零售", "京东", "美团", "名创优品"],
    },
    Industry.HEALTHCARE: {
        "market_size_cny_billion": 8700.0,
        "yoy_growth_rate": 12.3,
        "penetration_rate": 28.0,
        "top_players": ["恒瑞医药", "迈瑞医疗", "药明康德", "复星医药", "华润三九"],
    },
    Industry.ENERGY: {
        "market_size_cny_billion": 9800.0,
        "yoy_growth_rate": 22.1,
        "penetration_rate": 15.0,
        "top_players": ["宁德时代", "比亚迪", "隆基绿能", "通威股份", "天合光能"],
    },
    Industry.FINANCE: {
        "market_size_cny_billion": 35000.0,
        "yoy_growth_rate": 4.8,
        "penetration_rate": 88.0,
        "top_players": ["工商银行", "招商银行", "平安保险", "东方证券", "蚂蚁集团"],
    },
    Industry.MANUFACTURING: {
        "market_size_cny_billion": 31000.0,
        "yoy_growth_rate": 5.5,
        "penetration_rate": 60.0,
        "top_players": ["三一重工", "中联重科", "格力电器", "美的集团", "海尔智家"],
    },
}


def fetch_market_data(industry: Industry) -> dict[str, Any]:
    """Fetch market data; tries akshare first, falls back to curated stub data."""
    real = _try_akshare_market_data(industry)
    if real:
        return real
    logger.info("Using stub market data for industry={}", industry.value)
    return _STUB_DATA.get(industry, {})


def get_last_fetch_timestamp() -> datetime.datetime:
    """Return current UTC time as the 'data freshness' timestamp."""
    return datetime.datetime.now(datetime.timezone.utc)
