"""
智能决策层 - Ollama 客户端模块
对接本地 Ollama 服务，支持多模态（视觉 + 文本）推理
仅使用 requests 标准库，不依赖 transformers 或 llama-cpp-python
"""
import base64
import json
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

import requests


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMInference:
    """
    Ollama API 客户端，用于与 qwen3-vl 等多模态模型交互
    支持将屏幕截图转为 Base64 并通过 Ollama /api/chat 接口发送
    """

    # System Prompt：要求模型输出严格格式
    SYSTEM_PROMPT = """你是一个桌面自动化助手。请分析用户提供的屏幕截图，并给出操作建议。
请严格按照以下格式输出：
决策建议：<具体的操作建议，如"点击提交按钮">
教学提示：<分步骤的教学提示，如"步骤 1：找到提交按钮；步骤 2：点击它">

注意：只输出上述两个字段，不要添加其他内容。"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3-vl:latest",
        timeout: int = 60
    ):
        """
        初始化 Ollama 客户端
        :param base_url: Ollama API 基础 URL
        :param model: 模型名称
        :param timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.api_endpoint = f"{self.base_url}/api/chat"
        
        logger.info(f"LLMInference 初始化完成：base_url={self.base_url}, model={self.model}")

    def _image_to_base64(self, image_bytes: bytes) -> str:
        """
        将图像 bytes 转换为 Base64 字符串
        :param image_bytes: PNG 或其他格式的图像 bytes
        :return: Base64 编码字符串
        """
        return base64.b64encode(image_bytes).decode('utf-8')

    def _parse_response(self, response_text: str) -> Tuple[str, str]:
        """
        解析 LLM 响应，提取决策建议和教学提示
        处理模型输出格式偏差，提供健壮的解析逻辑
        :param response_text: 模型原始响应文本
        :return: (决策建议，教学提示) 元组
        """
        suggestion = ""
        tip = ""

        # 处理空响应
        if not response_text or not response_text.strip():
            return "无法解析建议", "无教学提示"

        # 尝试按关键词分割
        if "决策建议：" in response_text and "教学提示：" in response_text:
            try:
                suggestion_part = response_text.split("决策建议：")[1].split("教学提示：")[0].strip()
                tip_part = response_text.split("教学提示：")[1].strip()
                suggestion = suggestion_part
                tip = tip_part
            except (IndexError, AttributeError) as e:
                logger.warning(f"解析失败，使用 fallback 策略：{e}")
                lines = response_text.strip().split("\n")
                suggestion = lines[0][:200] if lines else "无法解析建议"
                tip = "\n".join(lines[1:])[:500] if len(lines) > 1 else "无教学提示"
        elif "决策建议:" in response_text and "教学提示:" in response_text:
            # 兼容英文冒号
            try:
                suggestion_part = response_text.split("决策建议:")[1].split("教学提示:")[0].strip()
                tip_part = response_text.split("教学提示:")[1].strip()
                suggestion = suggestion_part
                tip = tip_part
            except (IndexError, AttributeError) as e:
                logger.warning(f"解析失败，使用 fallback 策略：{e}")
                lines = response_text.strip().split("\n")
                suggestion = lines[0][:200] if lines else "无法解析建议"
                tip = "\n".join(lines[1:])[:500] if len(lines) > 1 else "无教学提示"
        else:
            # Fallback：按行分割取首句和剩余部分
            lines = response_text.strip().split("\n")
            suggestion = lines[0][:200] if lines else "无法解析建议"
            tip = "\n".join(lines[1:])[:500] if len(lines) > 1 else "无教学提示"

        return suggestion, tip

    def infer(
        self,
        image_bytes: Optional[bytes] = None,
        user_prompt: str = "请分析当前屏幕并给出操作建议",
        stream: bool = False
    ) -> Tuple[str, str]:
        """
        执行多模态推理
        :param image_bytes: 屏幕截图的 PNG bytes（可选）
        :param user_prompt: 用户自定义提示词
        :param stream: 是否使用流式响应
        :return: (决策建议，教学提示) 元组
        :raises ConnectionError: Ollama 服务不可达
        :raises TimeoutError: 请求超时
        :raises ValueError: 模型响应格式错误
        """
        # 构建消息内容
        content = []
        
        # 如果有图像，添加图像内容
        if image_bytes:
            base64_image = self._image_to_base64(image_bytes)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            })
        
        # 添加文本提示
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n用户问题：{user_prompt}"
        content.append({"type": "text", "text": full_prompt})
        
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        
        logger.info(f"发送请求到 Ollama API: {self.api_endpoint}")
        
        try:
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=self.timeout,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                # 流式响应处理
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        json_response = json.loads(line)
                        if "message" in json_response and "content" in json_response["message"]:
                            full_response += json_response["message"]["content"]
                response_text = full_response
            else:
                # 非流式响应
                result = response.json()
                response_text = result.get("message", {}).get("content", "")
            
            logger.info(f"收到模型响应，长度：{len(response_text)}")
            return self._parse_response(response_text)
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ollama 连接失败：{e}")
            raise ConnectionError(f"无法连接到 Ollama 服务 ({self.base_url})") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时：{e}")
            raise TimeoutError(f"Ollama 请求超时 ({self.timeout}秒)") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP 错误：{e}")
            raise ValueError(f"Ollama API 返回错误：{e.response.status_code}") from e
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败：{e}")
            raise ValueError(f"无法解析 Ollama 响应") from e

    def infer_text_only(
        self,
        user_prompt: str,
        stream: bool = False
    ) -> Tuple[str, str]:
        """
        纯文本推理（不使用图像）
        :param user_prompt: 用户提示词
        :param stream: 是否使用流式响应
        :return: (决策建议，教学提示) 元组
        """
        return self.infer(image_bytes=None, user_prompt=user_prompt, stream=stream)

    def health_check(self) -> bool:
        """
        检查 Ollama 服务是否可用
        :return: True 如果服务可用，False 否则
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"健康检查失败：{e}")
            return False


# 单元测试用例（模拟 API 响应）
def test_llm_inference():
    """测试 LLMInference 类的解析逻辑"""
    llm = LLMInference(base_url="http://mock-url", model="test-model")
    
    # 测试正常格式解析
    normal_response = "决策建议：点击提交按钮\n教学提示：步骤 1：找到按钮；步骤 2：点击"
    suggestion, tip = llm._parse_response(normal_response)
    assert "点击提交按钮" in suggestion
    assert "步骤 1" in tip
    print("✓ 正常格式解析测试通过")
    
    # 测试英文冒号格式
    colon_response = "决策建议：打开文件\n教学提示：先选择文件"
    suggestion, tip = llm._parse_response(colon_response)
    assert "打开文件" in suggestion
    assert "先选择文件" in tip
    print("✓ 英文冒号格式解析测试通过")
    
    # 测试 fallback 格式
    fallback_response = "第一行是建议\n第二行是提示\n第三行也是提示"
    suggestion, tip = llm._parse_response(fallback_response)
    assert "第一行是建议" in suggestion
    assert "第二行是提示" in tip
    print("✓ Fallback 格式解析测试通过")
    
    # 测试空响应
    empty_response = ""
    suggestion, tip = llm._parse_response(empty_response)
    assert suggestion == "无法解析建议"
    assert tip == "无教学提示"
    print("✓ 空响应解析测试通过")
    
    print("\n所有单元测试通过！")


if __name__ == "__main__":
    test_llm_inference()
