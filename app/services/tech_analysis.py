"""
Technology insight analysis service – prd-competitor SKILL.

Evaluates new vs historical technologies across an industry:
  • Gartner hype cycle positioning
  • Pros / cons assessment
  • Disruption scoring (0-10)
  • Investment implications
"""

from __future__ import annotations

import datetime
from typing import Any

from app.models_finance import (
    GartnerPhase,
    Industry,
    TechComparisonRequest,
    TechComparisonResult,
    TechEntry,
)

# ---------------------------------------------------------------------------
# Curated technology knowledge base
# ---------------------------------------------------------------------------

_TECH_PROFILES: dict[str, dict[str, Any]] = {
    "ai大模型": {
        "gartner_phase": GartnerPhase.PEAK_OF_INFLATED_EXPECTATIONS,
        "gartner_description": (
            "AI 大模型正处于期望膨胀的高峰期，业界对其颠覆性抱有极高期待，"
            "但大规模落地仍面临成本、合规和数据安全挑战。"
        ),
        "advantages": [
            "自然语言处理能力大幅超越传统 BI，支持非结构化数据洞察",
            "研报摘要、情绪分析、异常检测可实现端到端自动化",
            "边际推理成本持续下降，规模化后 ROI 显著提升",
            "多模态能力（文本+图表+语音）融合分析",
        ],
        "disadvantages": [
            "幻觉（Hallucination）风险导致金融决策误导",
            "模型可解释性不足，难以满足监管要求",
            "私有金融数据微调成本高，数据隐私合规复杂",
            "高推理算力成本，实时低延迟场景压力较大",
        ],
        "disruption_score": 8.5,
        "disruption_explanation": (
            "AI 大模型将重塑金融数据分析、研报撰写、智能投顾等环节，"
            "对传统 BI 工具形成结构性替代威胁，但短期内仍以辅助增强为主。"
        ),
        "investment_implication": (
            "关注算力基础设施（GPU/国产芯片）、金融大模型应用层（智能投顾、合规审核）"
            "以及数据安全合规赛道。"
        ),
    },
    "量化交易": {
        "gartner_phase": GartnerPhase.SLOPE_OF_ENLIGHTENMENT,
        "gartner_description": (
            "量化交易已走过过度期望阶段，机构量化占比持续提升，"
            "策略同质化加剧但 AI 增强型量化正开辟新的 alpha 来源。"
        ),
        "advantages": [
            "情绪偏差消除，严格执行纪律性交易",
            "高频数据挖掘能力远超人工，多因子模型成熟",
            "风险实时监控与自动止损，回撤控制优于主动管理",
            "规模化复制成本低",
        ],
        "disadvantages": [
            "策略同质化导致市场拥挤，超额收益（alpha）衰减",
            "黑天鹅事件下模型失效风险",
            "高频策略受交易所政策监管约束增强",
            "人才成本高，策略迭代需持续投入",
        ],
        "disruption_score": 7.0,
        "disruption_explanation": (
            "量化已深度改变基金行业格局，主动管理规模承压，"
            "但主观量化融合策略正成为新趋势。"
        ),
        "investment_implication": (
            "关注量化私募头部机构上市机会，以及为量化提供数据服务和算力的基础设施企业。"
        ),
    },
    "数字人民币": {
        "gartner_phase": GartnerPhase.SLOPE_OF_ENLIGHTENMENT,
        "gartner_description": (
            "数字人民币试点城市持续扩大，技术路线基本成熟，"
            "正从试点走向规模化推广阶段。"
        ),
        "advantages": [
            "央行直接发行，信用背书最高，清算效率显著提升",
            "可编程性支持条件付款、智能合约等金融创新",
            "跨境支付潜力，推动人民币国际化",
            "交易可追溯，有助于反洗钱、反逃税",
        ],
        "disadvantages": [
            "替代现有第三方支付生态阻力大",
            "隐私保护与监管透明度之间的政策张力",
            "国际推广面临地缘政治障碍",
            "商户端改造与培训成本",
        ],
        "disruption_score": 7.5,
        "disruption_explanation": (
            "对现有第三方支付格局构成中期竞争压力，"
            "长期将重塑跨境结算和货币政策传导机制。"
        ),
        "investment_implication": (
            "关注数字人民币技术服务商（银联、京东数科）、跨境支付基础设施及合规科技企业。"
        ),
    },
    "大语言模型": {
        "gartner_phase": GartnerPhase.PEAK_OF_INFLATED_EXPECTATIONS,
        "gartner_description": (
            "大语言模型（LLM）正处于期望峰值，各行各业加速落地，但 ROI 证明仍是主要挑战。"
        ),
        "advantages": [
            "通用性强，单模型覆盖多场景",
            "少量样本（few-shot）即可完成复杂任务",
            "代码生成、文档处理等效率提升显著",
            "开源生态（Llama、Qwen）降低采用门槛",
        ],
        "disadvantages": [
            "训练成本高昂，碳排放压力",
            "知识截止日期问题，需 RAG 补充实时信息",
            "版权与数据来源争议",
            "安全越狱（Jailbreak）与对抗攻击风险",
        ],
        "disruption_score": 9.0,
        "disruption_explanation": (
            "LLM 对软件开发、内容生产、知识服务等行业形成颠覆性冲击，"
            "未来三到五年将重塑大部分脑力工作流程。"
        ),
        "investment_implication": (
            "关注算力（英伟达、华为昇腾）、基础模型公司、垂直应用 SaaS 以及 AI 安全合规赛道。"
        ),
    },
    "固态电池": {
        "gartner_phase": GartnerPhase.TROUGH_OF_DISILLUSIONMENT,
        "gartner_description": (
            "固态电池期望已从高峰回落，量产良率和成本问题仍未突破，"
            "但头部企业研发投入持续加大，有望在 2027-2030 年进入商业化起步阶段。"
        ),
        "advantages": [
            "能量密度大幅提升（理论值>500Wh/kg）",
            "无液态电解质，本质安全性更高",
            "充放电循环寿命显著更长",
            "工作温度范围更宽",
        ],
        "disadvantages": [
            "界面电阻问题导致离子传导效率低",
            "量产制造工艺尚不成熟，良率低",
            "当前成本是液态锂电池的 5-10 倍",
            "产业链配套不完善",
        ],
        "disruption_score": 8.0,
        "disruption_explanation": (
            "固态电池一旦量产突破，将对现有液态锂电产业链形成颠覆，"
            "重塑动力电池、储能和消费电子格局。"
        ),
        "investment_implication": (
            "关注固态电解质材料（氧化物、硫化物路线）、布局固态电池的整车厂及设备企业。"
        ),
    },
    "ai辅助诊断": {
        "gartner_phase": GartnerPhase.SLOPE_OF_ENLIGHTENMENT,
        "gartner_description": (
            "AI 辅助诊断（影像 AI）已通过 NMPA 认证落地，"
            "正从试点走向大规模医院部署阶段。"
        ),
        "advantages": [
            "影像识别准确率接近或超过初级医生",
            "缓解基层医疗资源不足问题",
            "24 小时不间断、无疲劳误诊率低",
            "数据积累形成飞轮效应，模型持续迭代",
        ],
        "disadvantages": [
            "罕见病与复杂病例泛化能力不足",
            "医疗数据标注成本高，跨医院数据孤岛",
            "监管审批周期长（NMPA 二三类医疗器械）",
            "医生接受度与法律责任归属问题",
        ],
        "disruption_score": 7.5,
        "disruption_explanation": (
            "AI 辅助诊断将重塑基层医疗诊断流程，长期压缩传统影像科医生的增量需求。"
        ),
        "investment_implication": (
            "关注通过 NMPA 三类证的 AI 医疗器械公司，以及医疗数据标注和医院信息化赛道。"
        ),
    },
}

_DEFAULT_PROFILE: dict[str, Any] = {
    "gartner_phase": GartnerPhase.INNOVATION_TRIGGER,
    "gartner_description": "该技术尚处于创新萌芽阶段，市场认知度低，商业化路径有待验证。",
    "advantages": ["技术创新性强，潜在颠覆空间大", "先发优势明显"],
    "disadvantages": ["技术成熟度低，不确定性高", "市场教育成本大"],
    "disruption_score": 5.0,
    "disruption_explanation": "技术影响尚难量化，建议持续跟踪。",
    "investment_implication": "建议以小仓位关注，等待技术成熟度验证信号。",
}

_LEGACY_TECH_PROS: dict[str, list[str]] = {
    "传统bi": ["成熟稳定，监管合规路径清晰", "可解释性强，审计友好", "集成现有 IT 体系成本低"],
    "主动管理": ["灵活应对市场异常，黑天鹅防范能力强", "品牌与投资者信任积累深"],
    "传统支付": ["用户使用习惯成熟，切换阻力大", "监管框架完善，合规成本可预测"],
    "液态锂电池": ["产业链配套完善，成本持续下降", "制造工艺成熟，良率高"],
    "传统影像诊断": ["临床经验丰富，复杂病例判断更全面", "法律责任归属清晰"],
}


def _lookup_profile(tech_name: str) -> dict[str, Any]:
    lower = tech_name.lower()
    for key, profile in _TECH_PROFILES.items():
        if key in lower or lower in key:
            return profile
    return _DEFAULT_PROFILE


def _lookup_legacy_pros(tech_name: str) -> list[str]:
    lower = tech_name.lower()
    for key, pros in _LEGACY_TECH_PROS.items():
        if key in lower or lower in key:
            return pros
    return ["技术验证充分，业界信任度高", "实施风险低，文档与支持生态完善"]


def analyse_technologies(request: TechComparisonRequest) -> TechComparisonResult:
    """
    Perform a structured technology comparison using the prd-competitor SKILL framework.
    """
    profile = _lookup_profile(request.new_tech.name)
    legacy_pros = _lookup_legacy_pros(request.legacy_tech.name)
    legacy_cons = [
        f"相对新技术：{adv[:30]}…方面存在差距"
        for adv in profile["advantages"][:3]
    ]

    return TechComparisonResult(
        industry=request.industry,
        new_tech=request.new_tech,
        legacy_tech=request.legacy_tech,
        gartner_phase=profile["gartner_phase"],
        gartner_phase_description=profile["gartner_description"],
        new_tech_advantages=profile["advantages"],
        new_tech_disadvantages=profile["disadvantages"],
        legacy_tech_advantages=legacy_pros,
        legacy_tech_disadvantages=legacy_cons,
        disruption_score=profile["disruption_score"],
        disruption_explanation=profile["disruption_explanation"],
        investment_implication=profile["investment_implication"],
        generated_at=datetime.datetime.now(datetime.timezone.utc),
    )


# Default technology pairs per industry (used by report generator)
DEFAULT_TECH_PAIRS: dict[Industry, tuple[TechEntry, TechEntry]] = {
    Industry.FINANCE: (
        TechEntry(name="AI大模型", description="基于大语言模型的金融数据分析与智能投顾", launch_year=2023, is_emerging=True),
        TechEntry(name="传统BI", description="基于报表与 OLAP 的商业智能工具", launch_year=2000, is_emerging=False),
    ),
    Industry.TECH: (
        TechEntry(name="大语言模型", description="通用大语言模型（GPT/Qwen/文心）", launch_year=2022, is_emerging=True),
        TechEntry(name="传统搜索引擎", description="基于关键词索引的搜索系统", launch_year=1998, is_emerging=False),
    ),
    Industry.ENERGY: (
        TechEntry(name="固态电池", description="全固态锂电池（氧化物/硫化物电解质）", launch_year=2026, is_emerging=True),
        TechEntry(name="液态锂电池", description="液态电解质锂离子电池", launch_year=1991, is_emerging=False),
    ),
    Industry.HEALTHCARE: (
        TechEntry(name="AI辅助诊断", description="基于深度学习的医学影像辅助诊断系统", launch_year=2018, is_emerging=True),
        TechEntry(name="传统影像诊断", description="放射科医生人工判读 CT/MRI", launch_year=1970, is_emerging=False),
    ),
    Industry.CONSUMER: (
        TechEntry(name="AI个性化推荐", description="基于大模型的实时个性化商品推荐", launch_year=2023, is_emerging=True),
        TechEntry(name="传统协同过滤", description="基于用户行为矩阵分解的推荐算法", launch_year=2005, is_emerging=False),
    ),
    Industry.MANUFACTURING: (
        TechEntry(name="工业大模型", description="工业场景专用大语言与视觉模型", launch_year=2024, is_emerging=True),
        TechEntry(name="传统MES系统", description="制造执行系统（规则驱动）", launch_year=1990, is_emerging=False),
    ),
}
