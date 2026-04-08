import re
from typing import Dict, List, Tuple, Any, Optional


class RuleEngine:
    """
    规则引擎工具类（决策层核心组件），通过预定义规则将感知上下文（结构化元素+关键词）转换为决策建议，
    作为LLM推理的补充/替代方案，适用于明确场景的自动化决策（如“识别到提交按钮则建议点击”）。
    所属层：决策层（Decision Layer）
    """

    def __init__(self, rules: Optional[Dict[str, Dict]] = None):
        """
        初始化规则引擎
        :param rules: 自定义规则字典（键为规则名称，值为规则配置），默认使用内置规则
        """
        self.default_rules = self._load_default_rules()
        self.rules = rules if rules else self.default_rules

    def _load_default_rules(self) -> Dict[str, Dict]:
        """加载内置默认规则（覆盖常见场景）"""
        return {
            "submit_button_click": {
                "trigger": {
                    "element_label_contains": ["提交", "确认", "save", "confirm"],
                    "element_type": ["template_match", "yolo"],
                    "action_hint": "点击"
                },
                "suggestion": "点击{label}按钮完成操作",
                "tip": "步骤1：确认输入内容无误；步骤2：点击{label}按钮提交"
            },
            "input_field_fill": {
                "trigger": {
                    "element_label_contains": ["用户名", "密码", "邮箱", "搜索"],
                    "element_type": ["template_match", "yolo"],
                    "action_hint": "输入文本"
                },
                "suggestion": "在{label}输入框中输入内容",
                "tip": "步骤1：聚焦{label}输入框；步骤2：输入所需文本"
            },
            "link_click": {
                "trigger": {
                    "element_label_contains": ["详情", "更多", "help", "关于"],
                    "element_type": ["template_match", "yolo"],
                    "action_hint": "点击链接"
                },
                "suggestion": "点击{label}链接查看详情",
                "tip": "步骤1：移动光标至{label}链接；步骤2：单击打开"
            },
            "checkbox_toggle": {
                "trigger": {
                    "element_label_contains": ["同意", "记住我", "订阅"],
                    "element_type": ["template_match", "yolo"],
                    "action_hint": "勾选/取消勾选"
                },
                "suggestion": "{action} {label}选项",
                "tip": "步骤1：找到{label}复选框；步骤2：单击切换状态"
            }
        }

    def process(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        规则引擎推理入口：输入ContextProcessor输出的结构化上下文，输出决策建议+教学提示
        :param context: 结构化上下文（来自context_processor.process）
        :return: (决策建议, 教学提示) 双字符串元组
        """
        # 1. 提取规则引擎输入（适配format_for_rule_engine输出）
        rule_input = self._extract_rule_input(context)

        # 2. 遍历规则匹配场景
        for rule_name, rule_config in self.rules.items():
            if self._match_rule(rule_input, rule_config["trigger"]):
                # 3. 生成建议（填充模板变量）
                suggestion = rule_config["suggestion"].format(
                    label=rule_input["matched_element"]["label"],
                    action="勾选" if "同意" in rule_input["matched_element"]["label"] else "取消勾选"
                )
                tip = rule_config["tip"].format(label=rule_input["matched_element"]["label"])
                return suggestion, tip

        # 4. 无匹配规则时返回默认提示
        return "未识别到明确操作场景，请手动确认", "请检查屏幕元素或调整感知区域"

    def _extract_rule_input(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """从完整上下文提取规则引擎所需的精简输入"""
        # 优先使用format_for_rule_engine的输出（若存在）
        if "target_elements" in context.get("raw_data", {}):
            target_elements = context["raw_data"]["target_elements"]
        else:
            #  fallback：从elements中提取有效动作元素
            target_elements = [
                {"label": e["label"], "action": e["action_hint"], "coords": e["coordinates"]}
                for e in context["elements"]
                if e["action_hint"] != "未知动作"
            ]

        # 提取关键词（若有）
        keywords = context.get("text_summary", "").split()[:20] if "text_summary" in context else []

        # 匹配最相关的元素（按置信度排序）
        matched_element = None
        if target_elements:
            matched_element = sorted(target_elements, key=lambda x: x.get("confidence", 0), reverse=True)[0]

        return {
            "target_elements": target_elements,
            "keywords": keywords,
            "matched_element": matched_element
        }

    def _match_rule(self, rule_input: Dict[str, Any], trigger: Dict[str, Any]) -> bool:
        """判断当前场景是否匹配某条规则的触发条件"""
        if not rule_input["matched_element"]:
            return False

        element = rule_input["matched_element"]
        # 匹配元素标签包含关键词
        label_match = any(
            kw in element["label"].lower()
            for kw in trigger.get("element_label_contains", [])
        )
        # 匹配元素类型
        type_match = element.get("type", "") in trigger.get("element_type", [])
        # 匹配动作提示
        action_match = element.get("action", "") == trigger.get("action_hint", "")

        return label_match and type_match and action_match

    def add_custom_rule(self, rule_name: str, trigger: Dict, suggestion: str, tip: str):
        """添加自定义规则（扩展引擎能力）"""
        self.rules[rule_name] = {
            "trigger": trigger,
            "suggestion": suggestion,
            "tip": tip
        }

# 示例：与ContextProcessor联动（实际使用时需删除示例）
# if __name__ == "__main__":
#     from decision_layer.context_processor import ContextProcessor
#     from screen_capture_layer import OCREngine, ObjectDetector, ScreenCapturer
#
#     # 1. 初始化感知层与上下文处理器
#     capturer = ScreenCapturer()
#     ocr = OCREngine(engine="tesseract", lang="chi_sim+eng")
#     detector = ObjectDetector(detector_type="template", template_dir="templates")
#     context_processor = ContextProcessor(ocr, detector)
#
#     # 2. 模拟截屏与上下文生成
#     image = capturer.capture()
#     context = context_processor.process(image)
#
#     # 3. 初始化规则引擎并生成建议
#     rule_engine = RuleEngine()
#     suggestion, tip = rule_engine.process(context)
#     print(f"规则引擎建议：{suggestion}\n教学提示：{tip}")
#
#     # 4. 添加自定义规则（如“关闭按钮”规则）
#     rule_engine.add_custom_rule(
#         rule_name="close_button_click",
#         trigger={
#             "element_label_contains": ["关闭", "×", "cancel"],
#             "element_type": ["template_match", "yolo"],
#             "action_hint": "点击"
#         },
#         suggestion="点击{label}按钮关闭窗口",
#         tip="步骤1：定位{label}按钮；步骤2：单击关闭"
#     )