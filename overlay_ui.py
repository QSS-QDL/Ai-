"""
PyQt6 透明悬浮交互界面模块
无边框、半透明背景、始终置顶、支持鼠标穿透（除非点击按钮）
显示 AI 建议文本、教学提示文本、三个操作按钮（接受/拒绝/演示）
"""
import sys
import logging
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStatusBar, QShortcut
)
from PyQt6.QtCore import Qt, QPoint, QObject, pyqtSignal, QKeySequence
from PyQt6.QtGui import QFont, QKeyEvent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UISignals(QObject):
    """
    UI 信号类：用于与主控制器通信
    所有信号必须在主线程中触发
    """
    # 用户操作信号
    accept_clicked = pyqtSignal()
    reject_clicked = pyqtSignal()
    demo_clicked = pyqtSignal()
    
    # 数据更新信号（从主控制器到 UI）
    update_display = pyqtSignal(str, str, str)  # (感知结果，决策建议，教学提示)
    
    # 唤醒信号
    wake_up = pyqtSignal()


class OverlayUI(QWidget):
    """
    透明悬浮交互界面
    特性：无边框、半透明背景、始终置顶、鼠标穿透（除非点击按钮）
    """

    def __init__(
        self,
        opacity: float = 0.85,
        dark_mode: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        # 缓存当前显示数据（增量更新：仅变化时刷新）
        self.current_data: Optional[Tuple[str, str, str]] = None
        
        # 初始化信号
        self.ui_signals = UISignals()
        
        # 窗口基础设置
        self._setup_window(opacity)
        
        # 创建 UI 组件
        self._create_widgets(dark_mode)
        
        # 设置布局
        self._setup_layout()
        
        # 连接信号槽
        self._connect_signals()
        
        # 设置快捷键
        self._setup_shortcuts()
        
        logger.info("OverlayUI 初始化完成")

    def _setup_window(self, opacity: float):
        """配置窗口基本属性"""
        self.setWindowTitle("Voice Assistant Overlay")
        self.setGeometry(100, 100, 450, 350)
        
        # 窗口属性：始终在前、无边框、透明背景
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(opacity)
        
        # 允许鼠标穿透（点击空白区域不拦截）
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # 但按钮需要接收鼠标事件（在按钮上单独设置）
        # 这将在创建按钮时处理

    def _create_widgets(self, dark_mode: bool):
        """创建 UI 组件"""
        # 内容标签：显示感知结果、决策建议、教学提示
        self.info_label = QLabel("", self)
        self.info_label.setFont(QFont("SimHei", 11))
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # 样式表
        if dark_mode:
            self.info_label.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: rgba(0, 0, 0, 0.7);
                    padding: 12px;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
        else:
            self.info_label.setStyleSheet("""
                QLabel {
                    color: black;
                    background-color: rgba(255, 255, 255, 0.9);
                    padding: 12px;
                    border-radius: 8px;
                    border: 1px solid rgba(0, 0, 0, 0.2);
                }
            """)
        
        # 操作按钮：接受/拒绝/演示
        self.accept_btn = QPushButton("接受 (Enter)", self)
        self.reject_btn = QPushButton("拒绝 (Esc)", self)
        self.demo_btn = QPushButton("演示 (Space)", self)
        
        # 按钮样式
        btn_base_style = """
            QPushButton {
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
        """
        
        # 各按钮特定颜色
        self.accept_btn.setStyleSheet(btn_base_style + """
            QPushButton {
                background-color: rgba(76, 175, 80, 0.85);
            }
            QPushButton:hover {
                background-color: rgba(76, 175, 80, 0.95);
            }
        """)
        
        self.reject_btn.setStyleSheet(btn_base_style + """
            QPushButton {
                background-color: rgba(244, 67, 54, 0.85);
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.95);
            }
        """)
        
        self.demo_btn.setStyleSheet(btn_base_style + """
            QPushButton {
                background-color: rgba(33, 150, 243, 0.85);
            }
            QPushButton:hover {
                background-color: rgba(33, 150, 243, 0.95);
            }
        """)
        
        # 按钮需要接收鼠标事件（覆盖窗口的鼠标穿透）
        for btn in [self.accept_btn, self.reject_btn, self.demo_btn]:
            btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 状态栏：显示模式与权限状态
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 11px;
                border-radius: 4px;
            }
        """)
        self.status_bar.showMessage("模式：安全模式 (Dry-Run) | 按 Ctrl+Space 唤醒")

    def _setup_layout(self):
        """设置布局管理"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 内容区
        main_layout.addWidget(self.info_label, stretch=2)
        
        # 按钮区（水平布局）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addWidget(self.accept_btn, stretch=1)
        btn_layout.addWidget(self.reject_btn, stretch=1)
        btn_layout.addWidget(self.demo_btn, stretch=1)
        main_layout.addLayout(btn_layout, stretch=1)
        
        # 状态栏
        main_layout.addWidget(self.status_bar, stretch=0)
        
        self.setLayout(main_layout)

    def _connect_signals(self):
        """连接按钮信号到主控制器"""
        self.accept_btn.clicked.connect(self._on_accept)
        self.reject_btn.clicked.connect(self._on_reject)
        self.demo_btn.clicked.connect(self._on_demo)
        
        # 连接数据更新信号
        self.ui_signals.update_display.connect(self.update_info_label)

    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        # Ctrl+Space: 唤醒/隐藏
        self.wake_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.wake_shortcut.activated.connect(self.ui_signals.wake_up.emit)
        
        # Enter: 接受
        self.accept_shortcut = QShortcut(QKeySequence("Return"), self)
        self.accept_shortcut.activated.connect(self._on_accept)
        
        # Esc: 拒绝
        self.reject_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.reject_shortcut.activated.connect(self._on_reject)
        
        # Space: 演示
        self.demo_shortcut = QShortcut(QKeySequence("Space"), self)
        self.demo_shortcut.activated.connect(self._on_demo)

    def update_info_label(
        self,
        perception_result: str,
        decision_suggestion: str,
        teaching_tip: str
    ):
        """
        增量更新 UI 显示
        仅当数据变化时才刷新，避免闪烁
        :param perception_result: 感知层结果
        :param decision_suggestion: 决策层建议
        :param teaching_tip: 教学提示
        """
        new_data = (perception_result, decision_suggestion, teaching_tip)
        
        if new_data != self.current_data:
            # 格式化显示文本
            display_text = f"""
<b style="font-size: 12px; color: #4FC3F7;">📊 感知结果：</b><br/>
{perception_result}<br/><br/>
<b style="font-size: 12px; color: #81C784;">💡 决策建议：</b><br/>
{decision_suggestion}<br/><br/>
<b style="font-size: 12px; color: #FFB74D;">📚 教学提示：</b><br/>
{teaching_tip}
"""
            self.info_label.setText(display_text.strip())
            self.current_data = new_data
            logger.debug(f"UI 更新：{perception_result[:50]}...")

    def _on_accept(self):
        """接受按钮回调"""
        logger.info("[UI] 用户点击：接受")
        self.ui_signals.accept_clicked.emit()
        self.status_bar.showMessage("✓ 已接受建议，正在执行...")

    def _on_reject(self):
        """拒绝按钮回调"""
        logger.info("[UI] 用户点击：拒绝")
        self.ui_signals.reject_clicked.emit()
        self.status_bar.showMessage("✗ 已拒绝建议")

    def _on_demo(self):
        """演示按钮回调"""
        logger.info("[UI] 用户点击：演示")
        self.ui_signals.demo_clicked.emit()
        self.status_bar.showMessage("▶ 演示模式中...")

    def toggle_visibility(self):
        """切换窗口可见性"""
        if self.isVisible():
            self.hide()
            logger.info("UI 已隐藏")
        else:
            self.show()
            self.activateWindow()
            logger.info("UI 已显示")

    def set_status_message(self, message: str):
        """
        设置状态栏消息
        必须在主线程调用
        :param message: 状态消息
        """
        self.status_bar.showMessage(message)

    def set_mode(self, dry_run: bool):
        """
        设置运行模式
        :param dry_run: True=安全模式，False=执行模式
        """
        mode_str = "安全模式 (Dry-Run)" if dry_run else "执行模式"
        self.status_bar.showMessage(f"模式：{mode_str} | 按 Ctrl+Space 唤醒")


# 示例：独立测试 UI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建 UI 实例
    ui = OverlayUI(opacity=0.9, dark_mode=True)
    ui.show()
    
    # 模拟数据更新（2 秒后）
    from PyQt6.QtCore import QTimer
    
    def simulate_data():
        ui.ui_signals.update_display.emit(
            "识别到 '提交' 按钮（坐标：100, 200）",
            "建议点击提交按钮完成表单",
            "步骤 1：确认信息无误\n步骤 2：点击提交按钮"
        )
    
    QTimer.singleShot(2000, simulate_data)
    
    sys.exit(app.exec())
