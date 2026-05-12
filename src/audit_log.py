"""审计日志：记录 Agent 每一步推理和工具调用"""

import json
import os
from datetime import datetime
from pathlib import Path

from src.config import LOGS_DIR
from src.models import AuditLogEntry


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.entries: list[AuditLogEntry] = []
        self._step_counter = 0

    def log_step(
        self,
        step_type: str,
        content: str = "",
        tool_name: str = None,
        tool_input: dict = None,
        tool_output: str = None,
    ):
        """记录一步推理"""
        self._step_counter += 1
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            case_id=self.case_id,
            step_number=self._step_counter,
            step_type=step_type,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            content=content,
        )
        self.entries.append(entry)

    def save(self) -> str:
        """持久化日志到文件"""
        Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.case_id}_{timestamp}.json"
        filepath = os.path.join(LOGS_DIR, filename)

        data = [e.to_dict() for e in self.entries]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath
