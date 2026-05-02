"""
Core financial analysis service.

Orchestrates market data collection, industry analysis, technology comparison,
SWOT generation and report assembly.
"""

from __future__ import annotations

import datetime
import uuid

from app.models_finance import (
    CapitalDynamics,
    Industry,
    IndustryAnalysis,
    IndustryReport,
    MarketOverview,
    PolicyEnvironment,
    ReportRequest,
    RiskFactors,
    TechComparisonRequest,
)
from app.services.data_sources import fetch_market_data, get_last_fetch_timestamp
from app.services.tech_analysis import DEFAULT_TECH_PAIRS, analyse_technologies


_POLICY_KB: dict[Industry, dict] = {
    Industry.TECH: {
        "recent_policies": [
            "《生成式人工智能服务管理暂行办法》（2023）",
            "数据安全法与个人信息保护法持续落地执行",
            "工信部《算力基础设施高质量发展行动计划》（2023）",
        ],
        "regulatory_trend": "监管框架逐步完善，鼓励创新与防范风险并重",
        "entry_barrier_change": "AI 大模型备案制度提高合规门槛",
    },
    Industry.CONSUMER: {
        "recent_policies": [
            "《电子商务法》修订讨论稿",
            "平台经济反垄断指南落地",
            "促进消费扩内需相关财政补贴政策",
        ],
        "regulatory_trend": "反垄断约束平台经济，消费补贴提振内需",
        "entry_barrier_change": "直播电商新规提高主播资质要求",
    },
    Industry.HEALTHCARE: {
        "recent_policies": [
            "国家医保药品目录谈判（2024 年版）",
            "医疗器械注册人制度推广",
            "NMPA《人工智能医疗器械注册审查指导原则》",
        ],
        "regulatory_trend": "集采控费持续，AI 医疗器械审批加速但门槛不降",
        "entry_barrier_change": "三类 AI 医疗器械注册周期仍在 24-36 个月",
    },
    Industry.ENERGY: {
        "recent_policies": [
            "《关于促进新型储能并网和调度运用的通知》",
            "新能源汽车购置补贴延续政策",
            "碳达峰碳中和 1+N 政策体系持续推进",
        ],
        "regulatory_trend": "绿色转型政策确定性强，储能调度政策细化",
        "entry_barrier_change": "光储一体化项目审批流程简化",
    },
    Industry.FINANCE: {
        "recent_policies": [
            "证监会《关于加强上市公司监管的意见》",
            "公募基金费率改革持续推进",
            "数字人民币试点城市扩展至全国",
        ],
        "regulatory_trend": "强监管常态化，资本市场质量提升优先于扩容",
        "entry_barrier_change": "量化私募持牌要求升级，外资券商牌照开放提速",
    },
    Industry.MANUFACTURING: {
        "recent_policies": [
            "《制造业数字化转型行动计划（2024-2026）》",
            "工业互联网标识解析体系建设",
            "专精特新企业认定标准更新",
        ],
        "regulatory_trend": "数字化转型补贴持续，碳排放管理要求提升",
        "entry_barrier_change": "高端制造自主可控要求提高国产替代壁垒",
    },
}

_CAPITAL_KB: dict[Industry, dict] = {
    Industry.TECH: {
        "recent_financing": ["国内 AI 大模型 A 轮密集", "Anthropic 系列融资带动关注度"],
        "ipo_ma_events": ["多家 AI 公司冲刺港股上市"],
        "institutional_changes": "险资加仓科技 ETF，外资净卖出后重新回流科创板",
    },
    Industry.CONSUMER: {
        "recent_financing": ["新零售品牌 Pre-A 轮密集", "社区团购赛道融资趋冷"],
        "ipo_ma_events": ["名创优品海外扩张并购"],
        "institutional_changes": "消费 ETF 规模扩张，外资持续增持白酒龙头",
    },
    Industry.HEALTHCARE: {
        "recent_financing": ["创新药 License-out 交易活跃", "医疗器械国产替代融资旺盛"],
        "ipo_ma_events": ["CXO 板块并购整合"],
        "institutional_changes": "医药 ETF 规模创新高，险资增持医药蓝筹",
    },
    Industry.ENERGY: {
        "recent_financing": ["固态电池赛道融资超 200 亿元", "储能系统集成商 B/C 轮活跃"],
        "ipo_ma_events": ["宁德时代海外工厂布局并购"],
        "institutional_changes": "新能源基金规模收缩但主动管理超额收益恢复",
    },
    Industry.FINANCE: {
        "recent_financing": ["金融科技 B2B SaaS 融资复苏", "数字人民币 ToB 服务商融资"],
        "ipo_ma_events": ["外资行加速申请独资基金公司"],
        "institutional_changes": "险资举牌银行股，公募基金仓位向红利风格切换",
    },
    Industry.MANUFACTURING: {
        "recent_financing": ["工业机器人赛道融资持续活跃", "专精特新企业上市通道加速"],
        "ipo_ma_events": ["三一重工海外并购加速"],
        "institutional_changes": "外资增持制造业 ETF，北向资金青睐高端装备",
    },
}

_RISK_KB: dict[Industry, dict] = {
    Industry.TECH: {
        "policy_risk": "AI 监管趋严可能导致产品下架或功能限制",
        "market_risk": "技术迭代加速，产品生命周期缩短",
        "technology_risk": "大模型幻觉、安全漏洞和竞争性开源替代",
        "other_risks": ["中美科技脱钩导致芯片断供风险", "人才抢夺成本持续上升"],
    },
    Industry.CONSUMER: {
        "policy_risk": "平台反垄断和数据隐私政策收紧",
        "market_risk": "消费降级压力下高毛利品类需求萎缩",
        "technology_risk": "AI 推荐算法监管（不得诱导成瘾）",
        "other_risks": ["供应链波动（国际物流成本）", "直播电商退货率居高不下"],
    },
    Industry.HEALTHCARE: {
        "policy_risk": "医保集采扩大范围持续压缩产品利润",
        "market_risk": "人口老龄化带来需求增长但支付能力不足",
        "technology_risk": "AI 医疗器械监管不确定性和责任归属",
        "other_risks": ["临床试验数据造假监管趋严", "CXO 订单向海外转移风险"],
    },
    Industry.ENERGY: {
        "policy_risk": "补贴退坡及绿证市场化波动",
        "market_risk": "锂价大幅波动压缩电池企业利润",
        "technology_risk": "固态电池技术路线不确定性影响当前液态电池投资回报",
        "other_risks": ["欧美碳关税（CBAM）影响出口", "产能过剩加剧行业竞争"],
    },
    Industry.FINANCE: {
        "policy_risk": "强监管下业务创新受限，牌照申请周期延长",
        "market_risk": "市场波动加剧导致基金赎回潮",
        "technology_risk": "网络安全与数据泄露风险",
        "other_risks": ["汇率波动影响跨境业务", "房地产风险向银行资产负债表传导"],
    },
    Industry.MANUFACTURING: {
        "policy_risk": "碳排放指标收紧增加高耗能企业成本",
        "market_risk": "房地产下行拖累工程机械需求",
        "technology_risk": "工业软件国产替代进度不及预期",
        "other_risks": ["海外需求下滑影响出口", "原材料价格波动（铜、铝、稀土）"],
    },
}

_SWOT_KB: dict[Industry, dict] = {
    Industry.TECH: {
        "strengths": ["工程师人才储量全球领先", "应用层创新速度快", "庞大本土用户基础"],
        "weaknesses": ["底层芯片受制于人", "原创性基础研究薄弱", "知识产权保护体系有待完善"],
        "opportunities": ["AI 工业化应用落地加速", "东南亚等新兴市场输出", "数字政府建设需求"],
        "threats": ["中美科技脱钩风险", "开源大模型颠覆商业模式", "监管合规成本上升"],
    },
    Industry.CONSUMER: {
        "strengths": ["14 亿人口基本盘", "数字化购物渗透率全球最高", "供应链完整性强"],
        "weaknesses": ["消费信心恢复缓慢", "高端品牌溢价能力不足", "退货成本居高"],
        "opportunities": ["AI 个性化驱动品类升级", "银发经济高增长", "下沉市场开拓"],
        "threats": ["消费降级压力持续", "平台反垄断政策", "国际品牌本地化竞争加剧"],
    },
    Industry.HEALTHCARE: {
        "strengths": ["仿制药工程能力世界级", "临床资源丰富", "创新药政策鼓励"],
        "weaknesses": ["原研创新积累薄弱", "医保支付能力有限", "医疗资源城乡不均"],
        "opportunities": ["AI 诊断降低基层医疗门槛", "出海 License-out 收益增长", "老龄化刚需"],
        "threats": ["集采持续压价", "CXO 地缘政治风险", "药物安全事件舆情风险"],
    },
    Industry.ENERGY: {
        "strengths": ["光伏/锂电全球产能第一", "成本曲线持续下降", "产业链垂直整合"],
        "weaknesses": ["核心材料（碳化硅、高纯石英）依赖进口", "储能调度体系不完善"],
        "opportunities": ["全球能源转型确定性需求", "固态电池技术突破", "虚拟电厂商业化"],
        "threats": ["欧美贸易壁垒（反倾销）", "产能过剩价格战", "碳关税增加出口成本"],
    },
    Industry.FINANCE: {
        "strengths": ["数字金融基础设施领先", "机构资产管理规模庞大", "政策工具箱丰富"],
        "weaknesses": ["直接融资比例偏低", "量化策略同质化", "个人投资者专业性不足"],
        "opportunities": ["数字人民币跨境结算", "养老金入市扩大机构资金来源", "公募基金出海"],
        "threats": ["楼市风险传导银行", "外资离场压力", "强监管限制金融创新"],
    },
    Industry.MANUFACTURING: {
        "strengths": ["完整工业体系", "规模化成本优势", "工程师人才充足"],
        "weaknesses": ["工业软件（EDA/PLC）短板", "高端精密仪器依赖进口", "品牌溢价弱"],
        "opportunities": ["工业大模型提升智能制造效率", "一带一路基建需求", "国防军工替代"],
        "threats": ["劳动力成本上升", "全球供应链重构（转移越南）", "碳排放成本上升"],
    },
}

_EXECUTIVE_SUMMARY_KB: dict[Industry, str] = {
    Industry.TECH: (
        "科技行业正处于 AI 大模型驱动的新一轮范式转换期。国内外大模型竞争格局加速分化，"
        "应用层落地节奏决定估值中枢。算力基础设施、AI 安全合规、垂直行业 SaaS 是核心投资主线。"
    ),
    Industry.CONSUMER: (
        "消费行业整体呈现分化复苏态势：高端可选消费承压，刚性消费与品牌升级赛道韧性较强。"
        "AI 个性化推荐提升转化率，下沉市场仍有增量空间。"
    ),
    Industry.HEALTHCARE: (
        "医药行业在集采压力下加速向创新转型，AI 辅助诊断落地加速，"
        "出海 License-out 成为创新药企新增长极。"
    ),
    Industry.ENERGY: (
        "新能源行业产能周期进入出清阶段，竞争格局趋于集中。"
        "储能与固态电池是中期最重要的技术突破方向。"
    ),
    Industry.FINANCE: (
        "金融行业监管趋严背景下业务创新空间收窄，但数字化转型持续深化。"
        "量化私募扩张、数字人民币推广、公募费率改革是近期核心变量。"
    ),
    Industry.MANUFACTURING: (
        "制造业数字化转型提速，工业大模型和机器人是最重要的效率提升工具。"
        "国产替代（工业软件、高端装备）和出海布局是主要增长驱动。"
    ),
}

_INVESTMENT_RECS: dict[Industry, tuple[str, str]] = {
    Industry.TECH: (
        "超配算力基础设施（服务器/光模块）、AI 应用 SaaS；标配互联网平台；低配芯片设计（短期兑现不确定）。",
        "警惕 AI 泡沫破裂风险，重点跟踪商业化落地进度和监管政策动向。",
    ),
    Industry.CONSUMER: (
        "超配高端白酒、刚需食品饮料和 AI 赋能零售平台；标配家电出海龙头；低配重资产线下零售。",
        "消费复苏节奏不确定，需密切观察居民可支配收入与消费信心指数变化。",
    ),
    Industry.HEALTHCARE: (
        "超配创新药出海（License-out 模式）、AI 医疗器械和 CXO 龙头；标配仿制药；低配集采强度大的板块。",
        "政策风险（集采扩围）和监管风险（数据安全）是最大不确定因素。",
    ),
    Industry.ENERGY: (
        "超配储能系统集成商和固态电池材料企业；标配光伏组件龙头；低配液态锂电中游（电解液）。",
        "产能过剩周期中底部布局逻辑成立，但需等待库存去化信号确认。",
    ),
    Industry.FINANCE: (
        "超配高股息银行股和量化私募相关标的；标配头部券商；低配非银金融小盘股。",
        "强监管和市场波动是核心风险，注意赎回潮对公募基金管理规模的冲击。",
    ),
    Industry.MANUFACTURING: (
        "超配工业机器人、工业大模型应用和高端精密制造；标配传统工程机械；低配高耗能制造业。",
        "全球供应链重构和碳排放政策是长期风险，建议关注出海布局能力强的企业。",
    ),
}


class FinanceService:
    """Orchestrates all financial analysis workflows."""

    @staticmethod
    def get_industry_analysis(industry: Industry) -> IndustryAnalysis:
        """Build a full industry analysis from knowledge base and market data."""
        market_data = fetch_market_data(industry)
        fetched_at = get_last_fetch_timestamp()

        return IndustryAnalysis(
            industry=industry,
            generated_at=fetched_at,
            data_freshness=f"数据更新于 {fetched_at.strftime('%Y-%m-%d %H:%M UTC')}",
            overview=MarketOverview(
                market_size_cny_billion=market_data.get("market_size_cny_billion"),
                yoy_growth_rate=market_data.get("yoy_growth_rate"),
                penetration_rate=market_data.get("penetration_rate"),
                top_players=market_data.get("top_players", []),
            ),
            policy=PolicyEnvironment(**_POLICY_KB[industry]),
            capital=CapitalDynamics(**_CAPITAL_KB[industry]),
            risks=RiskFactors(**_RISK_KB[industry]),
        )

    @staticmethod
    def generate_report(request: ReportRequest) -> IndustryReport:
        """Generate a full standardised industry report."""
        industry = request.industry
        analysis = FinanceService.get_industry_analysis(industry)

        tech_result = None
        if request.include_tech_comparison and industry in DEFAULT_TECH_PAIRS:
            new_tech, legacy_tech = DEFAULT_TECH_PAIRS[industry]
            tech_result = analyse_technologies(
                TechComparisonRequest(
                    industry=industry,
                    new_tech=new_tech,
                    legacy_tech=legacy_tech,
                )
            )

        swot = _SWOT_KB[industry]
        rec, warning = _INVESTMENT_RECS[industry]

        return IndustryReport(
            report_id=f"rpt_{uuid.uuid4().hex[:12]}",
            industry=industry,
            generated_at=analysis.generated_at,
            executive_summary=_EXECUTIVE_SUMMARY_KB[industry],
            analysis=analysis,
            tech_comparison=tech_result,
            swot_strengths=swot["strengths"],
            swot_weaknesses=swot["weaknesses"],
            swot_opportunities=swot["opportunities"],
            swot_threats=swot["threats"],
            investment_recommendation=rec,
            risk_warning=warning,
        )
