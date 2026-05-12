# 抖音广告虚假宣传审查 Agent Demo

基于 ReAct 架构（LangGraph）实现的智能广告合规审查系统。

## 架构

```
输入(图片+JSON) → Agent主控(Doubao-1.5-pro-32k) → ReAct循环
                                                      ├── 视觉分析(Doubao-vision)
                                                      ├── 关键词检测(本地)
                                                      ├── RAG法条检索(ChromaDB)
                                                      ├── 图文一致性校验
                                                      └── 类目规则查询
                                                   → 双重推理置信度
                                                   → 输出结果 / 人工复核
```

## 快速开始

### 1. 安装依赖

```bash
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入火山方舟 API Key 和模型 Endpoint ID
```

需要在[火山方舟控制台](https://console.volcengine.com/ark)创建以下推理接入点：
- Doubao-1.5-pro-32k（主控推理）
- Doubao-1.5-vision-pro-32k（视觉分析）
- Doubao-embedding（向量化）

### 3. 构建 RAG 法条数据库

```bash
python scripts/build_rag.py
```

脚本会读取 `ref/` 目录下的法条 docx 文件，按条款切分并向量化存入 ChromaDB。

### 4. 准备测试数据

参考 `docs/test_data_prompt.md` 中的提示词，用 GPT 生成测试用的商品 JSON 和广告图片，放入 `input/` 目录。

### 5. 运行审查

```bash
python main.py
```

### 6. 查看结果

- 审查结果：`output/results_*.json`
- 审计日志：`logs/` 目录
- 待复核案例：`review_queue/` 目录

### 7. 人工复核（可选）

编辑 `review_queue/` 中的 JSON 文件，填写 `human_decision` 字段，然后运行：

```bash
python scripts/review_reader.py
```

## 目录结构

```
├── main.py                 # 批量运行入口
├── src/
│   ├── agent.py            # LangGraph ReAct Agent 主控
│   ├── config.py           # 配置
│   ├── models.py           # 数据模型
│   ├── pairing.py          # 输入配对逻辑
│   ├── confidence.py       # 置信度评估
│   ├── review_queue.py     # 复核队列管理
│   ├── audit_log.py        # 审计日志
│   └── tools/
│       ├── vision.py       # 多模态视觉分析
│       ├── keywords.py     # 关键词检测
│       ├── rag.py          # RAG 法条检索
│       ├── consistency.py  # 图文一致性校验
│       └── category.py     # 类目规则查询
├── scripts/
│   ├── build_rag.py        # RAG 构建脚本
│   └── review_reader.py    # 复核结果回读
├── data/
│   ├── keywords.json       # 关键词库
│   ├── category_rules.json # 类目加严规则
│   └── chroma_db/          # ChromaDB 数据（构建后生成）
├── ref/                    # 法条原文 docx
├── input/                  # 输入（广告图片 + JSON）
├── output/                 # 输出结果
├── review_queue/           # 人工复核队列
├── logs/                   # 审计日志
└── docs/
    └── test_data_prompt.md # 测试数据生成提示词
```

## 技术栈

- Python 3.10+
- LangGraph（ReAct Agent 框架）
- 火山方舟 Doubao 系列模型（兼容 OpenAI SDK）
- ChromaDB（本地向量数据库）
- python-docx（法条文档解析）
