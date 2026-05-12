# Implementation Plan: 广告合规审查 Agent

## Overview

基于 LangGraph ReAct 架构实现广告合规审查智能体，分 7 个阶段递增式开发。每阶段完成后 git commit。技术栈：Python + LangGraph + ChromaDB + 火山方舟（Doubao 系列模型，兼容 OpenAI SDK）。

## Tasks

- [x] 1. 阶段一：项目骨架 + 配置 + 数据模型
  - [x] 1.1 初始化项目结构和依赖配置
    - 创建项目目录结构：`src/`, `src/tools/`, `scripts/`, `data/`, `tests/`, `input/`, `output/`, `review_queue/`, `logs/`, `ref/`
    - 创建 `pyproject.toml`，声明依赖：langgraph, langchain-openai, chromadb, python-docx, hypothesis, pytest
    - 创建 `.env.example` 文件，包含 `ARK_API_KEY`, `ARK_BASE_URL`, `ARK_VISION_MODEL`, `ARK_REASONING_MODEL`, `ARK_EMBEDDING_MODEL` 等配置项
    - 创建 `src/config.py` 加载环境变量和配置常量（置信度阈值、重试配置、批量上限等）
    - _Requirements: 11.1, 4.5_

  - [x] 1.2 实现数据模型定义
    - 在 `src/models.py` 中定义所有 dataclass：CasePair, VisionResult, VisualIndicator, KeywordHit, LawArticle, Contradiction, CategoryRuleSet, ReviewResult, ReviewQueueItem, AuditLogEntry
    - 实现 ReviewResult 和 ReviewQueueItem 的 JSON 序列化/反序列化方法
    - _Requirements: 2.3, 3.4, 4.3, 5.2, 7.3, 9.2, 10.1, 12.2_

  - [x] 1.3 实现输入验证和 Case_Pair 配对逻辑
    - 在 `src/pairing.py` 中实现 `find_case_pairs(input_dir)` 函数
    - 扫描目录，按文件名 stem 配对图片（.png/.jpg/.jpeg）和 JSON 文件
    - 报告未配对文件，验证批量大小 <= 10
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.4 编写 Property Test：Case_Pair 配对正确性
    - **Property 1: Case_Pair 配对正确性**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]* 1.5 编写 Property Test：批量大小限制
    - **Property 2: 批量大小限制**
    - **Validates: Requirements 1.4, 1.5**

  - [x] 1.6 Git commit：`feat: 初始化项目骨架、配置和数据模型`

- [x] 2. 阶段二：RAG 构建脚本
  - [x] 2.1 实现 RAG 构建脚本 `scripts/build_rag.py`
    - 使用 python-docx 读取 `ref/中华人民共和国广告法_20210429.docx`
    - 按正则 `第.+?条` 切分法条，提取法规名、章节、条款号作为 metadata
    - 使用 Doubao-embedding 模型向量化每条法条
    - 存入 ChromaDB（持久化到 `data/chroma_db/`）
    - 脚本应支持命令行运行：`python scripts/build_rag.py`
    - 打印切分结果摘要（条数、示例）供用户确认
    - _Requirements: 4.1, 4.4, 4.5_

  - [ ]* 2.2 编写 Property Test：法条切分正确性
    - **Property 5: 法条切分正确性（RAG 构建 Round-Trip）**
    - **Validates: Requirements 4.1**

  - [x] 2.3 Git commit：`feat: 实现 RAG 法条构建脚本`

- [x] 3. 阶段三：工具集实现
  - [x] 3.1 实现视觉分析工具 `src/tools/vision.py`
    - 实现 `vision_analyze(image_path: str) -> VisionResult`
    - 调用 Doubao-1.5-vision-pro-32k，传入图片 base64 和结构化 prompt
    - 解析模型返回为 VisionResult（提取文字 + 视觉违规线索）
    - 处理 API 错误，失败时抛出异常供 Agent 捕获
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 3.2 编写 Property Test：视觉分析结果结构完整性
    - **Property 3: 视觉分析结果结构完整性**
    - **Validates: Requirements 2.3**

  - [x] 3.3 实现关键词检测工具 `src/tools/keywords.py`
    - 创建 `data/keywords.json` 关键词库（包含绝对化用语、医疗暗示等各类违规关键词）
    - 实现 `keyword_match(text: str) -> list[KeywordHit]`
    - 遍历关键词库，匹配文本中出现的关键词，返回命中列表（含上下文）
    - _Requirements: 3.1, 3.4_

  - [ ]* 3.4 编写 Property Test：关键词匹配完整性
    - **Property 4: 关键词匹配完整性**
    - **Validates: Requirements 3.1, 3.4**

  - [x] 3.5 实现 RAG 检索工具 `src/tools/rag.py`
    - 实现 `rag_search(query: str, top_k: int = 3) -> list[LawArticle]`
    - 连接 ChromaDB，使用 Doubao-embedding 向量化 query，检索最相关法条
    - 返回 LawArticle 列表（含法规名、条款号、原文、相关度分数）
    - _Requirements: 4.2, 4.3, 4.5_

  - [x] 3.6 实现图文一致性校验工具 `src/tools/consistency.py`
    - 实现 `check_consistency(extracted_text: str, product_json: dict) -> list[Contradiction]`
    - 对比图片文字与 JSON 中的 price, efficacy_claims, specifications, origin 字段
    - 返回矛盾点列表，每项指明图片文案段、JSON 字段和矛盾描述
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 3.7 编写 Property Test：图文矛盾检测结构完整性
    - **Property 7: 图文矛盾检测结构完整性**
    - **Validates: Requirements 5.2, 5.3**

  - [x] 3.8 实现类目规则查询工具 `src/tools/category.py`
    - 创建 `data/category_rules.json`（医疗器械、保健食品、金融、教育培训的加严规则）
    - 实现 `get_category_rules(category: str) -> CategoryRuleSet`
    - 未知类目返回通用规则并记录日志
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 3.9 编写 Property Test：类目规则返回正确性
    - **Property 8: 类目规则返回正确性**
    - **Validates: Requirements 6.1, 6.3**

  - [x] 3.10 Git commit：`feat: 实现全部工具集（vision, keywords, rag, consistency, category）`

- [x] 4. 阶段四：Agent 主控（LangGraph ReAct）
  - [x] 4.1 实现 Agent 主控 `src/agent.py`
    - 使用 LangGraph 构建 ReAct Agent
    - 注册所有工具（vision_analyze, keyword_match, rag_search, check_consistency, get_category_rules）
    - 配置 Doubao-1.5-pro-32k 作为推理模型
    - 实现 `review_case(case: CasePair) -> ReviewResult` 方法
    - Agent 自主决定工具调用顺序，收集足够证据后终止循环
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 4.2 实现违规判定和分级逻辑
    - 在 Agent 最终推理中分类违规类型（绝对化用语、虚构承诺、虚假对比、医疗暗示、价格欺诈、资质伪造）
    - 根据违规严重度分配处理建议（下架/限流/标注）
    - 确保法条引用格式为 `《法规名》第X条第Y项`
    - _Requirements: 7.1, 7.2, 4.3_

  - [ ]* 4.3 编写 Property Test：违规类型和处理建议枚举约束
    - **Property 9: 违规类型和处理建议枚举约束**
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 4.4 编写 Property Test：法条引用格式合规
    - **Property 6: 法条引用格式合规**
    - **Validates: Requirements 4.3**

  - [x] 4.5 Git commit：`feat: 实现 LangGraph ReAct Agent 主控`

- [x] 5. 阶段五：批量运行入口 + 置信度 + 复核队列
  - [x] 5.1 实现置信度评估逻辑
    - 在 `src/confidence.py` 中实现双重推理置信度计算
    - 对同一证据做两次独立推理（不同 prompt 变体）
    - 比较两次判断一致性，一致则高置信度，不一致则低置信度
    - 置信度为 0.0-1.0 的数值
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 5.2 编写 Property Test：置信度计算一致性
    - **Property 10: 置信度计算一致性**
    - **Validates: Requirements 8.3, 8.4, 8.5**

  - [x] 5.3 实现人工复核队列写入
    - 在 `src/review_queue.py` 中实现低置信度案例写入 `review_queue/` 目录
    - 写入 JSON 包含所有案例详情 + `human_decision: null` + `review_notes: null`
    - _Requirements: 9.1, 9.2, 9.4_

  - [ ]* 5.4 编写 Property Test：低置信度案例路由到复核队列
    - **Property 11: 低置信度案例路由到复核队列**
    - **Validates: Requirements 9.1, 9.2**

  - [x] 5.5 实现批量运行入口 `main.py`
    - 验证 input/ 目录中的 Case_Pairs
    - 检查批量大小限制
    - 逐个调用 Agent 审查（含置信度评估）
    - 输出结果到 `output/results.json`
    - 低置信度案例写入 `review_queue/`
    - _Requirements: 1.1, 1.4, 1.5, 12.4_

  - [x] 5.6 Git commit：`feat: 实现批量入口、置信度评估和复核队列`

- [x] 6. 阶段六：审计日志 + 输出格式化 + 复核回读
  - [x] 6.1 实现审计日志记录
    - 在 `src/audit_log.py` 中实现 AuditLogger 类
    - 记录每步推理：timestamp, case_id, step_number, step_type, tool_name, tool_input, tool_output, content
    - 持久化到 `logs/{case_id}_{timestamp}.json`
    - 集成到 Agent 主控中，在 ReAct 循环每步记录
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 6.2 编写 Property Test：审计日志完整性
    - **Property 13: 审计日志完整性**
    - **Validates: Requirements 10.1, 10.2, 10.4**

  - [x] 6.3 实现结果输出格式化
    - 确保 ReviewResult 序列化为完整 JSON（含所有必需字段）
    - 无违规时 violation_types 为空列表，recommended_action 为 "通过"
    - 批量结果写入 `output/results.json`
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 6.4 编写 Property Test：结果 JSON 结构完整性
    - **Property 14: 结果 JSON 结构完整性**
    - **Validates: Requirements 7.3, 12.1, 12.2**

  - [ ]* 6.5 编写 Property Test：无违规结果格式
    - **Property 15: 无违规结果格式**
    - **Validates: Requirements 12.3**

  - [x] 6.6 实现复核决定回读脚本 `scripts/review_reader.py`
    - 读取 `review_queue/` 中已填写 human_decision 的 JSON 文件
    - 汇总复核结果并打印
    - _Requirements: 9.3_

  - [ ]* 6.7 编写 Property Test：复核决定回读 Round-Trip
    - **Property 12: 复核决定回读 Round-Trip**
    - **Validates: Requirements 9.3**

  - [x] 6.8 Git commit：`feat: 实现审计日志、输出格式化和复核回读`

- [-] 7. 阶段七：测试数据生成提示词 + 使用说明
  - [x] 7.1 创建测试数据生成提示词文档
    - 在 `docs/test_data_prompt.md` 中编写 GPT 提示词
    - 提示词应指导生成：Product_JSON 样例（覆盖各类目和违规类型）、对应的广告图片描述
    - 包含正常案例和各种违规案例的生成指引
    - _Requirements: 1.1_

  - [x] 7.2 创建项目使用说明 README.md
    - 环境配置说明（.env 配置、依赖安装）
    - RAG 构建步骤（`python scripts/build_rag.py`）
    - 运行方式（`python main.py`）
    - 输入输出目录说明
    - 复核队列使用方式
    - _Requirements: 全部_

  - [-] 7.3 Git commit：`docs: 添加测试数据生成提示词和使用说明`

- [ ] 8. 最终检查点
  - 确保所有测试通过，ask the user if questions arise.

## Notes

- 标记 `*` 的子任务为可选测试任务，可跳过以加速 MVP 开发
- 每个阶段末尾包含 git commit 任务，commit message 使用中文
- RAG 构建脚本（阶段二）需用户手动运行 `python scripts/build_rag.py` 体验流程
- 法条来源：`ref/中华人民共和国广告法_20210429.docx`（用户已下载）
- 火山方舟 API base_url: `https://ark.cn-beijing.volces.com/api/v3`，兼容 OpenAI SDK
- 阶段七提供 GPT 提示词，用户用其生成测试用的 Product_JSON 和广告图片描述
