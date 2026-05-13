# 金山云品牌内容模板库-官方量产工具

金山云品牌官方AI量产助手，服务于品牌营销内容批量生产。

核心原则：所有输出必须检索RAG知识库，严禁编造，严格遵循config.py品牌口径与合规规则。

## 安装

```bash
cd ~/coding/ksbrand-toolkit
pip install -r requirements.txt
```

## 配置

1. 设置OpenAI兼容API环境变量：
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可替换为金山云内部大模型
```

2. 将品牌规范文档放入 `knowledge_base/` 对应子目录

## 使用

### RAG知识库

```bash
# 构建向量索引
python main.py rag build

# 检索知识库
python main.py rag search "金山云CDN"
```

### 模板管理

```bash
# 列出所有模板
python main.py template list

# 查看模板详情
python main.py template show product_announce/product_launch
```

### 内容量产

```bash
# 单条生成
python main.py generate single product_announce/product_launch \
  --params product=CDN --params version=3.0

# 批量量产
python main.py batch product_announce/product_launch --csv data.csv
```

### 合规检查

```bash
# 检查已有内容
python main.py check output/result.md
```

### 导出

```bash
# 导出生成结果
python main.py export output/ --format markdown
python main.py export output/ --format html
python main.py export output/ --format docx
```

## 项目结构

```
ksbrand-toolkit/
├── config.py                  # 品牌口径、禁用词、合规规则
├── main.py                    # CLI入口
├── knowledge_base/            # RAG知识库目录
│   ├── brand_guidelines/      # 品牌规范
│   ├── product_capabilities/  # 产品能力
│   ├── cases/                 # 案例库
│   ├── data/                  # 官方数据与口径
│   └── compliance/            # 合规规范
├── templates/                 # 内容模板（Jinja2）
├── output/                    # 量产输出
└── src/                       # 核心源码
    ├── rag/                   # RAG检索
    ├── compliance/            # 合规审核
    ├── generator/             # 内容生成
    ├── templates/             # 模板引擎
    └── exporter/              # 导出
```

## 测试

```bash
pytest tests/ -v
```
