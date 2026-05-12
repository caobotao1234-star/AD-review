"""配置模块：加载环境变量和系统常量"""

import os
from dotenv import load_dotenv

load_dotenv()

# 火山方舟 API 配置
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

# 模型 Endpoint ID
ARK_REASONING_MODEL = os.getenv("ARK_REASONING_MODEL", "")
ARK_VISION_MODEL = os.getenv("ARK_VISION_MODEL", "")
ARK_EMBEDDING_MODEL = os.getenv("ARK_EMBEDDING_MODEL", "")

# 置信度阈值
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# 批量处理上限
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10"))

# 重试配置
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
RETRY_EXPONENTIAL_BASE = 2
RETRYABLE_STATUS_CODES = [429, 500, 502, 503, 504]

# 路径配置
DATA_DIR = "data"
CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
KEYWORDS_PATH = os.path.join(DATA_DIR, "keywords.json")
CATEGORY_RULES_PATH = os.path.join(DATA_DIR, "category_rules.json")
INPUT_DIR = "input"
OUTPUT_DIR = "output"
REVIEW_QUEUE_DIR = "review_queue"
LOGS_DIR = "logs"
