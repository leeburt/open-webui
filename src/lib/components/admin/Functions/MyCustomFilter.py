"""
title: 自定义消息过滤器
author: open-webui
version: 0.1
"""

from pydantic import BaseModel, Field
from typing import Optional

class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="过滤器优先级"
        )
        max_turns: int = Field(
            default=5, description="用户最大对话轮次"
        )
        sensitive_words: list = Field(
            default=["敏感词1", "敏感词2"], 
            description="需要过滤的敏感词列表"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.file_handler = True

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # 检查对话轮次
        if __user__.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])
            if len(messages) > self.valves.max_turns:
                raise Exception(
                    f"对话轮次超出限制。最大轮次: {self.valves.max_turns}"
                )

        # 检查敏感词
        messages = body.get("messages", [])
        for message in messages:
            content = message.get("content", "")
            for word in self.valves.sensitive_words:
                if word in content:
                    raise Exception(f"消息包含敏感词: {word}")

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # 在每条消息后添加标记
        messages = body.get("messages", [])
        modified_messages = []
        
        for message in messages:
            modified_message = {
                **message,
                "content": f"{message['content']} [已过滤]"
            }
            modified_messages.append(modified_message)

        return {"messages": modified_messages} 