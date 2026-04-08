from PyQt5.QtCore import QObject, pyqtSignal

# 信号类：独立定义，用于与感知层联动（传递感知结果、决策建议、教学提示）
class PerceptionSignal(QObject):
    """
    感知层与展示交互层的信号桥梁，通过pyqtSignal传递三字符串参数：
    - perception_result: 屏幕感知层的结构化结果（如“识别到‘提交’按钮（坐标100,200）”）
    - decision_suggestion: 决策层的行动建议（如“建议点击提交按钮”）
    - teaching_tip: 可视化/教学层的分步提示（如“步骤1：输入用户名”）
    """
    update_ui = pyqtSignal(str, str, str)  # 信号定义：三字符串参数