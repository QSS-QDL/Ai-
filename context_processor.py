import json
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import numpy as np
import cv2

# 导入感知层组件（根据实际项目结构调整导入路径）
from screen_capture_layer import OCREngine, ObjectDetector


class ContextProcessor:
    """
    感知数据整合工具类（决策层核心组件），将屏幕感知层（OCR/对象检测）的输出整合为结构化上下文，
    为LLM/规则引擎提供“屏幕状态+元素信息+文本内容”的统一描述，支撑决策建议生成。
    所属层：决策层（Decision Layer）
    """

    def __init__(self, ocr_engine: OCREngine, object_detector: ObjectDetector):
        """
        初始化上下文处理器
        :param ocr_engine: 感知层OCR引擎实例（已配置语言/参数）
        :param object_detector: 感知层对象检测器实例（已配置检测类型/模板）
        """
        self.ocr_engine = ocr_engine
        self.object_detector = object_detector
        self.cached_context: Optional[Dict] = None  # 缓存上一次整合的上下文（增量处理）

    def process(self, image: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        整合感知数据：OCR文本 + 对象检测结果 → 结构化上下文
        :param image: 输入图像（BGR格式，来自screen_capture_layer/screenshot.py）
        :param region: 局部感知区域 (left, top, width, height)，None表示全屏
        :return: 结构化上下文字典（含屏幕状态、元素列表、文本摘要）
        """
        # 1. OCR文字识别（获取屏幕文本）
        full_text = self.ocr_engine.process(image)
        text_boxes = self.ocr_engine.get_text_boxes(image)  # 文字区域坐标 [(文本, (x,y,w,h)), ...]

        # 2. 对象检测（获取按钮/窗口/图标等元素）
        detected_objects = self.object_detector.detect(
            image)  # [{"type":..., "label":..., "box":(x,y,w,h), "confidence":...}, ...]

        # 3. 整合数据（关联文本与元素，如按钮标签与按钮坐标）
        elements = self._merge_elements_and_text(detected_objects, text_boxes)

        # 4. 格式化上下文（适配LLM/规则引擎输入）
        context = {
            "screen_state": {
                "region": region if region else "fullscreen",
                "timestamp": self._get_timestamp()  # ISO格式时间戳
            },
            "elements": elements,  # 结构化元素列表（含类型、标签、坐标、关联文本、动作提示）
            "text_summary": full_text[:500] + "..." if len(full_text) > 500 else full_text,  # 文本摘要（限制长度）
            "raw_data": {
                "ocr_boxes": text_boxes[:10],  # 仅保留前10个文字区域（避免冗余）
                "detections": detected_objects[:10]  # 仅保留前10个检测结果
            }
        }

        # 5. 增量处理（仅变化时更新缓存）
        if context != self.cached_context:
            self.cached_context = context.copy()  # 深拷贝缓存
            return context
        return self.cached_context  # 无变化时返回缓存

    def _merge_elements_and_text(self, objects: List[Dict], text_boxes: List[Tuple[str, Tuple[int, int, int, int]]]) -> \
    List[Dict]:
        """
        关联元素检测结果与OCR文字区域（如按钮标签绑定按钮坐标）
        :param objects: 对象检测结果（来自ObjectDetector.detect）
        :param text_boxes: OCR文字区域（来自OCREngine.get_text_boxes）
        :return: 整合后的元素列表（含关联文本）
        """
        merged_elements = []
        for obj in objects:
            obj_box = obj["box"]  # (x, y, w, h)
            # 查找与元素框重叠的文字区域（IoU > 0.3视为关联文本）
            related_text = []
            for text, txt_box in text_boxes:
                iou = self._calculate_iou(obj_box, txt_box)
                if iou > 0.3:
                    related_text.append(text)

            merged_elements.append({
                "type": obj["type"],  # 元素类型（template_match/yolo）
                "label": obj["label"],  # 元素标签（如"submit_button"）
                "coordinates": obj_box,  # 坐标 (x, y, w, h)
                "confidence": round(obj["confidence"], 4),  # 检测置信度（保留4位小数）
                "related_text": " ".join(related_text),  # 关联文本（如按钮上的“提交”字样）
                "action_hint": self._infer_action_hint(obj["label"])  # 推测动作（如点击/输入）
            })
        return merged_elements

    @staticmethod
    def _calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """计算元素框与文字框的交并比（IoU），判断关联性"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        # 计算交集区域坐标
        inter_x1 = max(x1, x2)
        inter_y1 = max(y1, y2)
        inter_x2 = min(x1 + w1, x2 + w2)
        inter_y2 = min(y1 + h1, y2 + h2)

        # 交集面积（无交集则为0）
        inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)

        # 并集面积 = 两框面积和 - 交集面积
        union_area = w1 * h1 + w2 * h2 - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    @staticmethod
    def _infer_action_hint(label: str) -> str:
        """根据元素标签推测动作提示（如按钮→点击，输入框→输入）"""
        label_lower = label.lower()
        if "button" in label_lower or "btn" in label_lower:
            return "点击"
        elif "input" in label_lower or "field" in label_lower or "文本框" in label_lower:
            return "输入文本"
        elif "window" in label_lower or "窗口" in label_lower:
            return "切换窗口"
        elif "checkbox" in label_lower or "复选框" in label_lower:
            return "勾选/取消勾选"
        elif "link" in label_lower or "链接" in label_lower:
            return "点击链接"
        return "未知动作"

    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳（ISO 8601格式）"""
        return datetime.now().isoformat()

    def format_for_llm(self, context: Dict[str, Any]) -> str:
        """将结构化上下文转换为LLM可读的文本提示（含指令）"""
        prompt = f"""【屏幕状态】区域：{context['screen_state']['region']}，时间：{context['screen_state']['timestamp']}
【元素列表】
"""
        for idx, elem in enumerate(context["elements"], 1):
            prompt += (
                f"{idx}. 类型：{elem['type']}，标签：{elem['label']}，"
                f"坐标：{elem['coordinates']}，置信度：{elem['confidence']}，"
                f"关联文本：'{elem['related_text']}'，动作提示：{elem['action_hint']}\n"
            )

        prompt += f"\n【文本摘要】\n{context['text_summary']}\n\n"
        prompt += "请根据以上信息，生成简洁的决策建议（如'点击XX按钮'），并附带教学提示（分步骤说明）。"
        return prompt

    def format_for_rule_engine(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """将结构化上下文转换为规则引擎输入格式（精简版）"""
        return {
            "target_elements": [
                {"label": e["label"], "action": e["action_hint"], "coords": e["coordinates"]}
                for e in context["elements"]
                if e["action_hint"] != "未知动作"  # 过滤无效动作
            ],
            "keywords": context["text_summary"].split()[:20]  # 提取前20个关键词
        }