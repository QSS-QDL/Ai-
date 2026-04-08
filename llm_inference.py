import torch
import os
from typing import Tuple, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from llama_cpp import Llama  # 可选：llama.cpp Python绑定（轻量高效）
from decision_layer.context_processor import ContextProcessor  # 导入上下文处理器

class LLMInference:
    """
    本地LLM推理工具类（决策层核心组件），将ContextProcessor生成的文本提示输入本地模型（如Llama/Mistral），
    输出结构化决策建议（含教学提示），为展示层提供“可解释的行动指导”。
    所属层：决策层（Decision Layer）
    """

    def __init__(self, model_path: str, model_type: str = "hf", device: str = "auto", **kwargs):
        """
        初始化LLM推理器
        :param model_path: 模型路径（本地目录或Hugging Face Hub名称，如"meta-llama/Llama-2-7b-chat-hf"）
        :param model_type: 模型类型（"hf"=Hugging Face Transformers，"llama.cpp"=llama.cpp）
        :param device: 运行设备（"auto"/"cpu"/"cuda"，仅HF有效）
        :param kwargs: 模型参数（如HF的load_in_4bit=True，llama.cpp的n_ctx=2048）
        """
        self.model_path = model_path
        self.model_type = model_type.lower()
        self.device = device
        self.kwargs = kwargs
        self.model = None
        self.tokenizer = None
        self.llm = None  # llama.cpp实例
        self._load_model()

    def _load_model(self):
        """加载本地模型（支持HF Transformers和llama.cpp两种后端）"""
        if self.model_type == "hf":
            # Hugging Face Transformers加载（支持量化/GPU加速）
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map=self.device,
                load_in_4bit=self.kwargs.get("load_in_4bit", False),  # 4位量化（节省显存）
                torch_dtype=torch.float16 if "cuda" in self.device else torch.float32,
                trust_remote_code=True,
                **{k: v for k, v in self.kwargs.items() if k != "load_in_4bit"}
            )
        elif self.model_type == "llama.cpp":
            # llama.cpp加载（轻量高效，适合CPU环境）
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.kwargs.get("n_ctx", 2048),  # 上下文长度
                n_threads=self.kwargs.get("n_threads", 4),  # CPU线程数
                n_gpu_layers=self.kwargs.get("n_gpu_layers", 0)  # GPU加速层数（0=纯CPU）
            )
        else:
            raise ValueError(f"不支持的模型类型：{self.model_type}（可选hf/llama.cpp）")

    def generate_suggestion(self, prompt: str) -> Tuple[str, str]:
        """
        LLM推理入口：输入ContextProcessor生成的提示文本，输出决策建议+教学提示
        :param prompt: 文本提示（来自ContextProcessor.format_for_llm）
        :return: (决策建议, 教学提示) 双字符串元组
        """
        if self.model_type == "hf":
            return self._hf_generate(prompt)
        elif self.model_type == "llama.cpp":
            return self._llama_cpp_generate(prompt)
        else:
            raise RuntimeError("模型未正确加载")

    def _hf_generate(self, prompt: str) -> Tuple[str, str]:
        """Hugging Face Transformers推理（适合高精度生成）"""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.kwargs.get("max_new_tokens", 512),  # 最大生成长度
            temperature=self.kwargs.get("temperature", 0.7),  # 随机性（0-1，越低越确定）
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # 解析输出：提取“决策建议”和“教学提示”（按约定格式）
        return self._parse_response(response)

    def _llama_cpp_generate(self, prompt: str) -> Tuple[str, str]:
        """llama.cpp推理（适合低资源环境）"""
        response = self.llm(
            prompt,
            max_tokens=self.kwargs.get("max_tokens", 512),
            temperature=self.kwargs.get("temperature", 0.7),
            stop=["</s>", "###"]  # 停止符（根据模型调整）
        )["choices"][0]["text"]
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: str) -> Tuple[str, str]:
        """
        解析LLM输出（按约定格式：“决策建议：XXX\n教学提示：XXX”）
        若格式不符，自动分割为两部分（前50%为建议，后50%为提示）
        """
        # 尝试按关键词分割
        if "决策建议：" in response and "教学提示：" in response:
            suggestion_part = response.split("决策建议：")[1].split("教学提示：")[0].strip()
            tip_part = response.split("教学提示：")[1].strip()
        else:
            #  fallback：按行分割取首句和剩余部分
            lines = response.strip().split("\n")
            suggestion_part = lines[0][:200]  # 首行前200字符为建议
            tip_part = "\n".join(lines[1:])[:500]  # 剩余为提示（限长500）
        return suggestion_part, tip_part

    def unload_model(self):
        """释放模型资源（避免内存泄漏）"""
        if self.model_type == "hf":
            del self.model
            del self.tokenizer
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
        elif self.model_type == "llama.cpp":
            del self.llm
        self.model = None
        self.tokenizer = None
        self.llm = None


# 示例：与ContextProcessor联动（实际使用时需删除示例，仅保留类定义）
# if __name__ == "__main__":
#     from decision_layer.context_processor import ContextProcessor
#     from screen_capture_layer import OCREngine, ObjectDetector, ScreenCapturer
#
#     # 1. 初始化感知层组件
#     capturer = ScreenCapturer()
#     ocr = OCREngine(engine="tesseract", lang="chi_sim+eng")
#     detector = ObjectDetector(detector_type="template", template_dir="templates")
#     context_processor = ContextProcessor(ocr, detector)
#
#     # 2. 模拟截屏与上下文生成
#     image = capturer.capture()
#     context = context_processor.process(image)
#     llm_prompt = context_processor.format_for_llm(context)
#
#     # 3. 初始化LLM推理器（以llama.cpp为例，需提前下载gguf模型）
#     llm = LLMInference(
#         model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
#         model_type="llama.cpp",
#         n_ctx=2048,
#         n_threads=4
#     )
#
#     # 4. 生成决策建议与教学提示
#     suggestion, tip = llm.generate_suggestion(llm_prompt)
#     print(f"决策建议：{suggestion}\n教学提示：{tip}")
#
#     # 5. 释放资源
#     llm.unload_model()