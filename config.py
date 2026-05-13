"""
品牌合规中枢配置
所有输出必须检索RAG知识库，严禁编造，严格遵循本文件品牌口径与合规规则。
"""

# === 品牌基础 ===
BRAND_NAME = "金山云"
BRAND_NAME_EN = "Kingsoft Cloud"
BRAND_SLOGAN = "成就你我，共享云端"

# === 品牌文风 ===
BRAND_TONE = {
    "style": "政企文风",
    "keywords": ["严谨", "专业", "可信赖", "务实", "前瞻"],
    "description": (
        "以严谨专业的政企文风呈现，语言精准、逻辑清晰、数据翔实。"
        "避免过度营销化表达，侧重技术实力与服务能力的客观呈现。"
        "面向政企客户群体，强调安全、稳定、合规的核心价值。"
    ),
    "do": [
        "使用客观数据与事实支撑",
        "体现技术专业性",
        "强调安全合规能力",
        "突出服务保障与SLA承诺",
        "引用官方口径与案例",
    ],
    "dont": [
        "使用绝对化用语（如'最'、'第一'、'唯一'等）",
        "使用夸张的营销化表述",
        "引用未经授权的竞品对比数据",
        "使用网络用语或口语化表达",
        "做出未经RAG知识库支撑的事实性宣称",
    ],
}

# === 禁用词 ===
FORBIDDEN_WORDS = [
    # 绝对化用语
    "最好", "最强", "最优", "最佳", "最先", "最新", "最先进",
    "第一", "唯一", "独家", "首选", "领先",
    "无敌", "绝对", "百分之百", "完美",
    "全球第一", "全国第一", "行业第一",
    # 夸张营销用语
    "革命性", "颠覆性", "划时代", "史无前例",
    "不可思议", "无与伦比", "前所未有",
    "秒杀", "碾压", "吊打", "完爆",
    # 不规范品牌名
    "金山云公司", "金山市", "KS云",
]

# 禁用词正则（用于模糊匹配）
FORBIDDEN_PATTERNS = [
    r"第一[名大强]",
    r"最[大强好优新先进]+的",
    r"全球?首[创选一]",
    r"行业?首[创选一]",
]

# === 免责声明 ===
REQUIRED_DISCLAIMERS = {
    "general": (
        f"【免责声明】以上内容由{BRAND_NAME}AI量产助手生成，"
        "仅作内部参考使用，正式发布前请经品牌合规审核。"
    ),
    "press_release": (
        f"【新闻稿声明】本稿件由{BRAND_NAME}官方发布，"
        "未经书面授权不得转载或引用。"
    ),
    "marketing": (
        f"【营销内容声明】以上内容仅供参考，"
        f"具体产品能力请以{BRAND_NAME}官网公布信息为准。"
    ),
}

# === 官方产品名 ===
PRODUCT_NAMES = {
    "cdn": "金山云CDN",
    "cloud_cdn": "金山云CDN",
    "ks3": "金山云对象存储KS3",
    "object_storage": "金山云对象存储KS3",
    "kcs": "金山云容器服务KCS",
    "container": "金山云容器服务KCS",
    "kec": "金山云云服务器KEC",
    "ecs": "金山云云服务器KEC",
    "slb": "金山云负载均衡SLB",
    "load_balancer": "金山云负载均衡SLB",
    "vpc": "金山云虚拟私有云VPC",
    "kingstor": "金山云分布式存储KingStor",
    "database": "金山云数据库",
    "krds": "金山云关系型数据库KRDS",
    "security": "金山云安全",
    "kns": "金山云安全KNS",
    "bigdata": "金山云大数据平台",
    "ai": "金山云AI平台",
    "video": "金山云视频云",
    "live": "金山云直播",
    "vod": "金山云点播",
    "hicdn": "金山云高清CDN",
}

# === 允许的品牌宣称（仅采信RAG知识库） ===
APPROVED_CLAIMS = [
    "金山云持续为政企客户提供稳定可靠的云服务",
    "金山云CDN节点覆盖全国",
    "金山云拥有多年政企服务经验",
    "金山云通过等保三级认证",
    "金山云提供7×24小时运维保障",
    "金山云支持混合云部署",
]

# === LLM配置 ===
LLM_CONFIG = {
    "api_base": "https://api.openai.com/v1",  # 可替换为金山云内部大模型
    "model": "glm-5",
    "temperature": 0.3,  # 低温度确保输出稳定
    "max_tokens": 8192,
    "timeout": 180,
}

# === RAG配置 ===
RAG_CONFIG = {
    "knowledge_base_dir": "knowledge_base",
    "chunk_size": 500,
    "chunk_overlap": 100,
    "top_k": 5,
    "embedding_model": "text-embedding-3-small",
    "chroma_persist_dir": ".chroma_db",
}

# === 导出配置 ===
EXPORT_CONFIG = {
    "output_dir": "output",
    "formats": ["markdown", "html", "docx"],
    "include_metadata": True,
    "include_rag_sources": True,
}
