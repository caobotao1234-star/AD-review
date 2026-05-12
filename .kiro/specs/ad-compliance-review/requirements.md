# Requirements Document

## Introduction

抖音广告虚假宣传审查 Agent Demo：基于 ReAct 架构（LangGraph）实现的智能广告合规审查系统。系统接收广告图片与商品结构化数据，通过多模态视觉模型、关键词检测、RAG 法条检索、图文一致性校验等工具自主推理，输出违规判定、法规依据及处理建议。

## Glossary

- **Agent**: 基于 LangGraph 实现的 ReAct 架构智能体，自主决定工具调用顺序
- **Vision_Model**: 字节火山方舟 Doubao-1.5-vision-pro-32k 多模态视觉模型
- **Reasoning_Model**: 字节火山方舟 Doubao-1.5-pro-32k 纯文本推理模型，作为 Agent 主控
- **Embedding_Model**: 字节火山方舟 Doubao-embedding 向量化模型
- **Ad_Image**: 待审查的广告图片文件
- **Product_JSON**: 与广告图片同名的 JSON 文件，包含商品页结构化数据（标题、价格、功效声明等）
- **Case_Pair**: 一对 Ad_Image 和 Product_JSON 的组合，构成一个审查案例
- **Keyword_Library**: 包含数十条违规关键词的本地词库
- **RAG_Store**: 基于 ChromaDB 的本地向量数据库，存储广告法、反不正当竞争法条款
- **Category_Rules**: 按商品类目（医疗器械、保健食品、金融、教育培训等）定义的加严审查规则
- **Violation_Type**: 违规类型枚举，包括绝对化用语、虚构承诺、虚假对比、医疗暗示、价格欺诈、资质伪造
- **Severity_Level**: 处理分级，包括下架、限流、标注三个等级
- **Confidence_Score**: 通过两次独立判断加一致性校验得出的置信度分数
- **Review_Queue**: review_queue/ 目录，存放待人工复核的不确定案例 JSON 文件
- **Audit_Log**: 记录 Agent 每一步推理、工具调用及结果的审计日志

## Requirements

### Requirement 1: 批量输入处理

**User Story:** As a 审核运营人员, I want to 批量提交广告图片和商品数据进行审查, so that 可以高效处理多个广告案例。

#### Acceptance Criteria

1. THE Agent SHALL accept a batch of Case_Pairs where each pair consists of one Ad_Image file and one Product_JSON file with the same filename stem
2. WHEN a batch is submitted, THE Agent SHALL validate that each Ad_Image has a corresponding Product_JSON file
3. IF a Case_Pair is missing either the Ad_Image or the Product_JSON, THEN THE Agent SHALL report the missing file and skip that pair
4. THE Agent SHALL process batches containing no more than 10 Case_Pairs per run
5. IF a batch contains more than 10 Case_Pairs, THEN THE Agent SHALL reject the batch and report the size limit

### Requirement 2: 多模态视觉分析

**User Story:** As a 审核运营人员, I want to 通过视觉模型同时完成文字识别和视觉违规判断, so that 无需依赖独立 OCR 服务即可获取图片中的文案和视觉线索。

#### Acceptance Criteria

1. WHEN a Case_Pair is processed, THE Vision_Model SHALL analyze the Ad_Image to extract all visible text content
2. WHEN a Case_Pair is processed, THE Vision_Model SHALL identify visual violation indicators including exaggerated before-after comparisons, fake certification stamps, and misleading charts
3. THE Vision_Model SHALL return structured output containing extracted text and a list of visual violation indicators with descriptions
4. IF the Vision_Model fails to process an Ad_Image, THEN THE Agent SHALL log the error and mark the case as requiring manual review

### Requirement 3: 关键词检测

**User Story:** As a 审核运营人员, I want to 通过关键词匹配快速发现高风险文案, so that 明显违规的内容能被优先标记。

#### Acceptance Criteria

1. WHEN text is extracted from an Ad_Image, THE Agent SHALL match the text against the Keyword_Library
2. WHEN one or more keywords are matched, THE Agent SHALL treat the matches as strong signals and trigger further analysis by the Reasoning_Model
3. THE Agent SHALL NOT produce a final violation judgment based solely on keyword matches without further reasoning
4. THE Keyword_Library SHALL contain categorized entries mapping each keyword to its associated Violation_Type

### Requirement 4: RAG 法条检索

**User Story:** As a 审核运营人员, I want to 在违规判定中引用具体法律条款, so that 审查结论有明确法律依据。

#### Acceptance Criteria

1. THE RAG_Store SHALL store law articles split by article number using regex pattern "第X条", with metadata including law name, chapter, and article number
2. WHEN the Agent identifies a potential violation, THE Agent SHALL query the RAG_Store to retrieve relevant law articles
3. THE Agent SHALL cite specific law articles in the output using the format "《法规名》第X条第Y项" (e.g., "《广告法》第九条第三项")
4. THE RAG_Store SHALL contain representative articles from 《中华人民共和国广告法》 and 《反不正当竞争法》
5. THE Embedding_Model SHALL vectorize law article text for storage in and retrieval from the RAG_Store

### Requirement 5: 图文一致性校验

**User Story:** As a 审核运营人员, I want to 对比广告图片文案与商品页数据, so that 能发现图文矛盾的虚假宣传。

#### Acceptance Criteria

1. WHEN a Case_Pair is processed, THE Agent SHALL compare the text extracted from the Ad_Image with the claims in the Product_JSON
2. WHEN the Ad_Image text contradicts the Product_JSON data on price, efficacy, specifications, or origin, THE Agent SHALL flag the contradiction as a potential violation
3. THE Agent SHALL specify which fields in the Product_JSON contradict which text segments in the Ad_Image

### Requirement 6: 类目敏感度分级

**User Story:** As a 审核运营人员, I want to 根据商品类目自动加载对应的加严规则, so that 高风险类目（如医疗、金融）受到更严格的审查。

#### Acceptance Criteria

1. WHEN a Case_Pair is processed, THE Agent SHALL identify the product category from the Product_JSON
2. THE Category_Rules SHALL define heightened scrutiny rules for at least the following categories: 医疗器械, 保健食品, 金融, 教育培训
3. WHEN a product belongs to a sensitive category, THE Agent SHALL apply the corresponding Category_Rules in addition to general rules
4. IF the product category cannot be determined, THEN THE Agent SHALL apply general rules and log the ambiguity

### Requirement 7: 违规判定与分级

**User Story:** As a 审核运营人员, I want to 获得细分的违规类型和处理建议, so that 可以按严重程度采取不同措施。

#### Acceptance Criteria

1. THE Agent SHALL classify detected violations into one or more of the following Violation_Types: 绝对化用语, 虚构承诺, 虚假对比, 医疗暗示, 价格欺诈, 资质伪造
2. THE Agent SHALL assign a Severity_Level to each violation: 下架 for severe violations, 限流 for moderate violations, 标注 for minor violations
3. THE Agent SHALL output a structured result for each Case_Pair containing: user ID, Violation_Type, reasoning, legal basis, Confidence_Score, and recommended Severity_Level

### Requirement 8: 置信度评估

**User Story:** As a 审核运营人员, I want to 获得可靠的置信度分数, so that 可以区分确定违规和需要人工复核的擦边案例。

#### Acceptance Criteria

1. WHEN the Agent makes a violation judgment, THE Agent SHALL perform two independent reasoning passes on the same evidence
2. THE Agent SHALL compare the two independent judgments for consistency
3. WHEN both judgments agree, THE Agent SHALL assign a high Confidence_Score
4. WHEN the two judgments disagree, THE Agent SHALL assign a low Confidence_Score and flag the case for human review
5. THE Confidence_Score SHALL be a numeric value between 0.0 and 1.0

### Requirement 9: 人工复核队列

**User Story:** As a 审核运营人员, I want to 将不确定的案例导出到复核队列, so that 复核员可以人工审查并做出最终决定。

#### Acceptance Criteria

1. WHEN a case has a Confidence_Score below a configurable threshold, THE Agent SHALL write the case result to a JSON file in the Review_Queue directory
2. THE Review_Queue JSON file SHALL contain all case details plus a human_decision field initialized to null
3. WHEN a reviewer fills in the human_decision field, THE system SHALL support a script that reads back the decision for record-keeping
4. THE Review_Queue directory SHALL be review_queue/ relative to the project root

### Requirement 10: 审计日志

**User Story:** As a 系统管理员, I want to 记录 Agent 每一步的推理和工具调用, so that 审查过程可追溯、可审计。

#### Acceptance Criteria

1. THE Agent SHALL log every reasoning step including the thought, selected tool, tool input, and tool output
2. THE Audit_Log SHALL record timestamps for each step
3. THE Audit_Log SHALL be persisted to a file that can be reviewed after execution
4. WHEN a case is completed, THE Audit_Log SHALL contain the complete chain of reasoning from input to final judgment

### Requirement 11: ReAct 架构实现

**User Story:** As a 开发者, I want to 使用 ReAct 架构让 Agent 自主决定工具调用顺序, so that 系统具备灵活的推理能力而非固定流水线。

#### Acceptance Criteria

1. THE Agent SHALL be implemented using LangGraph with a ReAct (Reasoning + Acting) loop
2. THE Agent SHALL have access to the following tools: vision analysis, keyword matching, RAG retrieval, consistency check, category rule lookup
3. THE Reasoning_Model SHALL decide which tool to invoke at each step based on the current reasoning state
4. THE Agent SHALL terminate the reasoning loop when sufficient evidence is gathered to produce a final judgment or when all relevant tools have been consulted

### Requirement 12: 结果输出格式

**User Story:** As a 审核运营人员, I want to 获得结构化的审查结果, so that 结果可以被下游系统消费或展示。

#### Acceptance Criteria

1. THE Agent SHALL output results as JSON objects
2. EACH result JSON SHALL contain the following fields: case_id, user_id, violation_types (list), reasoning, legal_references (list), confidence_score, recommended_action, image_path, json_path
3. WHEN no violation is detected, THE Agent SHALL output a result with an empty violation_types list and recommended_action set to "通过"
4. THE Agent SHALL write batch results to an output JSON file upon completion
