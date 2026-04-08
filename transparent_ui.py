import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QStatusBar)
from PyQt5.QtCore import Qt, QPoint, QObject, pyqtSignal
from PyQt5.QtGui import QFont


# 1. 信号类：与感知层联动（传递感知结果、决策建议、教学提示）
class PerceptionSignal(QObject):
    update_ui = pyqtSignal(str, str, str)  # 三个字符串参数：感知结果、决策建议、教学提示


class TransparentUI(QWidget):
    def __init__(self):
        super().__init__()
        # 缓存当前显示数据（增量感知：仅变化时刷新）
        self.current_data = None  # 格式：(感知结果, 决策建议, 教学提示)

        # 2. 窗口基础设置（严格匹配需求）
        self.setWindowTitle("Screen Perception Overlay")
        self.setGeometry(100, 100, 400, 300)  # 初始位置(100,100)、大小(400,300)
        # 窗口属性：始终在前、无边框、透明背景、半透明
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.85)  # 半透明度0.85

        # 3. UI元素设计（完整样式与布局）
        # 3.1 内容区：显示感知结果、决策建议、教学提示（分行）
        self.info_label = QLabel("", self)
        self.info_label.setFont(QFont("SimHei", 10))  # 黑体10号字
        self.info_label.setStyleSheet("""
            color: white; 
            background-color: rgba(0,0,0,0.5);  /* 半透黑背景 */
            padding: 10px; 
            border-radius: 5px;  /* 圆角5px */
        """)
        self.info_label.setWordWrap(True)  # 自动换行

        # 3.2 操作按钮区：接受/拒绝/演示（完整样式+事件绑定）
        self.accept_btn = QPushButton("接受", self)
        self.reject_btn = QPushButton("拒绝", self)
        self.demo_btn = QPushButton("演示", self)
        # 按钮统一样式（含hover效果）
        btn_style = """
            QPushButton {
                background-color: rgba(76, 175, 80, 0.7);  /* 绿色半透 */
                color: white; 
                border: none; 
                padding: 8px 16px;  /* 内边距 */
                border-radius: 4px;  /* 圆角4px */
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: rgba(76, 175, 80, 0.9);  /* hover加深 */
            }
        """
        for btn in [self.accept_btn, self.reject_btn, self.demo_btn]:
            btn.setStyleSheet(btn_style)

        # 3.3 状态栏：显示模式与权限
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("""
            background-color: rgba(0,0,0,0.3);  /* 深灰半透 */
            color: white; 
            font-size: 11px;
        """)
        self.status_bar.showMessage("模式：执行模式（需确认） | 权限：允许操作当前应用")

        # 3.4 布局管理（垂直+水平嵌套）
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.info_label)  # 内容区

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.accept_btn)
        h_layout.addWidget(self.reject_btn)
        h_layout.addWidget(self.demo_btn)
        v_layout.addLayout(h_layout)  # 按钮区

        v_layout.addWidget(self.status_bar)  # 状态栏
        self.setLayout(v_layout)

        # 4. 交互逻辑：按钮事件（含预留接口）
        self.accept_btn.clicked.connect(self.on_accept)
        self.reject_btn.clicked.connect(self.on_reject)
        self.demo_btn.clicked.connect(self.on_demo)

        # 5. 信号槽联动：与感知层对接（完整信号定义+绑定）
        self.perception_signal = PerceptionSignal()
        self.perception_signal.update_ui.connect(self.update_info_label)  # 绑定增量更新槽

    def update_info_label(self, perception_result, decision_suggestion, teaching_tip):
        """增量感知更新UI：仅数据变化时刷新"""
        new_data = (perception_result, decision_suggestion, teaching_tip)
        if new_data != self.current_data:  # 对比新旧数据
            # 分行显示内容（用换行符分隔）
            display_text = f"感知结果：{perception_result}\n决策建议：{decision_suggestion}\n教学提示：{teaching_tip}"
            self.info_label.setText(display_text)
            self.current_data = new_data  # 更新缓存

    def on_accept(self):
        """接受按钮：执行动作（预留PyAutoGUI接口）"""
        print(f"[日志] 用户接受建议 | 当前数据：{self.current_data}")
        # 预留执行层接口（需安装pyautogui）
        # import pyautogui
        # if self.current_data:
        #     # 示例：解析感知结果中的坐标（实际需结构化数据）
        #     # 假设感知结果为"识别到‘提交’按钮（坐标100,200）"
        #     coords = self.current_data[0].split("坐标")[1].strip("（）").split(",")
        #     x, y = int(coords[0]), int(coords[1])
        #     pyautogui.click(x=x, y=y)  # 模拟点击目标位置

    def on_reject(self):
        """拒绝按钮：忽略建议（记录日志）"""
        print(f"[日志] 用户拒绝建议 | 忽略内容：{self.current_data}")

    def on_demo(self):
        """演示按钮：高亮目标区域（预留OpenCV接口）"""
        print(f"[日志] 用户请求演示 | 高亮区域：{self.current_data}")
        # 预留教学层接口（需安装opencv-python、numpy、pyautogui）
        # import cv2
        # import numpy as np
        # if self.current_data:
        #     # 示例：解析感知结果中的坐标（实际需结构化数据）
        #     coords = self.current_data[0].split("坐标")[1].strip("（）").split(",")
        #     x, y = int(coords[0]), int(coords[1])
        #     w, h = 50, 30  # 示例区域大小（实际需感知层返回）
        #     # 截取当前屏幕并高亮区域
        #     screenshot = pyautogui.screenshot()
        #     img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        #     cv2.rectangle(img, (x,y), (x+w, y+h), (0,255,0), 2)  # 画绿框
        #     cv2.imshow("Demo Highlight", img)
        #     cv2.waitKey(2000)  # 显示2秒
        #     cv2.destroyAllWindows()

    # 6. 窗口拖动逻辑（无边框时支持鼠标拖动）
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 记录鼠标全局位置与窗口左上角的偏移量
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            # 移动窗口至新位置
            self.move(event.globalPos() - self.drag_pos)
            event.accept()


# 示例：模拟感知层发送数据（测试用）
def simulate_perception(ui_instance):
    ui_instance.perception_signal.update_ui.emit(
        "识别到‘提交’按钮（坐标100,200）",
        "建议点击提交按钮完成表单",
        "步骤1：输入用户名；步骤2：点击提交"
    )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = TransparentUI()
    ui.show()

    # 模拟感知层2秒后推送数据（测试用）
    from threading import Timer

    Timer(2, lambda: simulate_perception(ui)).start()

    sys.exit(app.exec_())