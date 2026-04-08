"""
Voice 桌面自动化助手 - 主控制器模块
采用事件驱动架构，协调屏幕捕获、Ollama 推理、UI 展示、自动化执行四大模块
确保 UI 线程（PyQt6）不阻塞，耗时操作在子线程运行
"""
import sys
import logging
import configparser
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

# 导入项目模块
from screenshot import ScreenCapturer
from llm_inference import LLMInference
from overlay_ui import OverlayUI, UISignals
from executor import ActionExecutor
from audit import AuditLogger, PermissionWhitelist

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("voice_assistant.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """
    工作线程：执行耗时任务（截图 + AI 推理）
    通过信号与主线程通信
    """
    # 信号定义
    task_started = pyqtSignal()
    task_completed = pyqtSignal(str, str, str)  # (感知结果，决策建议，教学提示)
    task_error = pyqtSignal(str)  # 错误消息
    
    def __init__(self, capturer: ScreenCapturer, llm: LLMInference, user_prompt: str = ""):
        super().__init__()
        self.capturer = capturer
        self.llm = llm
        self.user_prompt = user_prompt or "请分析当前屏幕并给出操作建议"
    
    def run(self):
        """线程入口：执行截图和 AI 推理"""
        try:
            self.task_started.emit()
            
            # 1. 截取屏幕
            logger.info("开始截取屏幕...")
            image_bytes = self.capturer.capture()
            perception_result = f"已捕获屏幕图像 ({len(image_bytes)} bytes)"
            
            # 2. 调用 Ollama 推理
            logger.info("正在调用 Ollama 进行 AI 推理...")
            suggestion, tip = self.llm.infer(
                image_bytes=image_bytes,
                user_prompt=self.user_prompt
            )
            
            # 3. 发送结果到主线程
            self.task_completed.emit(perception_result, suggestion, tip)
            
        except ConnectionError as e:
            error_msg = f"Ollama 连接失败：{e}"
            logger.error(error_msg)
            self.task_error.emit(error_msg)
        except TimeoutError as e:
            error_msg = f"请求超时：{e}"
            logger.error(error_msg)
            self.task_error.emit(error_msg)
        except Exception as e:
            error_msg = f"任务执行失败：{e}"
            logger.error(error_msg)
            self.task_error.emit(error_msg)


class MainController(QObject):
    """
    主控制器：事件驱动核心
    协调屏幕捕获、Ollama 推理、UI 展示、自动化执行四大模块
    """
    
    # 全局信号
    shutdown_signal = pyqtSignal()
    
    def __init__(self, config_path: str = "config.ini"):
        super().__init__()
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化各模块组件
        self._init_components()
        
        # 状态管理
        self.is_running = False
        self.current_task_thread: Optional[WorkerThread] = None
        self.user_confirmed = False  # 用户确认标志
        
        # 连接 UI 信号
        self._connect_ui_signals()
        
        logger.info("MainController 初始化完成")
    
    def _load_config(self) -> configparser.ConfigParser:
        """加载配置文件"""
        config = configparser.ConfigParser()
        
        if self.config_path.exists():
            config.read(self.config_path, encoding='utf-8')
            logger.info(f"配置文件已加载：{self.config_path}")
        else:
            logger.warning(f"配置文件不存在：{self.config_path}，使用默认配置")
            # 设置默认配置
            config['ollama'] = {
                'base_url': 'http://localhost:11434',
                'model': 'qwen3-vl:latest',
                'timeout': '60'
            }
            config['security'] = {
                'dry_run': 'True',
                'allowed_apps': ''
            }
        
        return config
    
    def _init_components(self):
        """初始化各模块组件"""
        # 1. 屏幕捕获模块
        ollama_cfg = self.config.get('ollama', {})
        self.capturer = ScreenCapturer()
        
        # 2. Ollama 推理模块
        self.llm = LLMInference(
            base_url=ollama_cfg.get('base_url', 'http://localhost:11434'),
            model=ollama_cfg.get('model', 'qwen3-vl:latest'),
            timeout=ollama_cfg.getint('timeout', 60)
        )
        
        # 3. UI 模块
        ui_cfg = self.config.get('ui', {})
        opacity = ui_cfg.getfloat('window_opacity', 0.85)
        dark_mode = ui_cfg.getboolean('dark_mode', True)
        self.ui = OverlayUI(opacity=opacity, dark_mode=dark_mode)
        
        # 4. 执行器模块
        security_cfg = self.config.get('security', {})
        dry_run = security_cfg.getboolean('dry_run', True)
        self.executor = ActionExecutor(dry_run=dry_run)
        
        # 5. 审计日志模块
        self.audit_logger = AuditLogger()
        
        # 6. 权限白名单
        allowed_apps_str = security_cfg.get('allowed_apps', '')
        allowed_apps = [app.strip() for app in allowed_apps_str.split(',') if app.strip()]
        self.permission_whitelist = PermissionWhitelist(allowed_apps=allowed_apps)
        
        # 将白名单注入执行器（用于装饰器检查）
        self.executor.permission_whitelist = self.permission_whitelist
        self.executor.audit_logger = self.audit_logger
    
    def _connect_ui_signals(self):
        """连接 UI 信号到控制器槽函数"""
        # 用户操作信号
        self.ui.ui_signals.accept_clicked.connect(self._on_user_accept)
        self.ui.ui_signals.reject_clicked.connect(self._on_user_reject)
        self.ui.ui_signals.demo_clicked.connect(self._on_user_demo)
        self.ui.ui_signals.wake_up.connect(self._on_wake_up)
    
    def start(self):
        """启动助手"""
        if self.is_running:
            logger.warning("助手已在运行中")
            return
        
        self.is_running = True
        self.ui.show()
        
        # 更新 UI 状态
        dry_run = self.executor.dry_run
        self.ui.set_mode(dry_run)
        
        logger.info("Voice Assistant 已启动")
        self.ui.set_status_message("就绪 | 按 Ctrl+Space 触发智能分析")
    
    def stop(self):
        """停止助手"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止当前任务
        if self.current_task_thread and self.current_task_thread.isRunning():
            self.current_task_thread.terminate()
            self.current_task_thread.wait()
        
        self.ui.hide()
        logger.info("Voice Assistant 已停止")
    
    def trigger_analysis(self, user_prompt: str = ""):
        """
        触发智能分析（在主线程外执行）
        :param user_prompt: 可选的用户自定义提示
        """
        if not self.is_running:
            logger.warning("助手未启动，无法触发分析")
            return
        
        # 如果已有任务在运行，先终止
        if self.current_task_thread and self.current_task_thread.isRunning():
            logger.info("终止之前的任务...")
            self.current_task_thread.terminate()
            self.current_task_thread.wait()
        
        # 创建新工作线程
        self.current_task_thread = WorkerThread(
            capturer=self.capturer,
            llm=self.llm,
            user_prompt=user_prompt
        )
        
        # 连接线程信号
        self.current_task_thread.task_started.connect(
            lambda: self.ui.set_status_message("正在分析屏幕...")
        )
        self.current_task_thread.task_completed.connect(self._on_analysis_complete)
        self.current_task_thread.task_error.connect(self._on_analysis_error)
        
        # 启动线程
        self.current_task_thread.start()
        logger.info("智能分析任务已启动")
    
    def _on_analysis_complete(
        self,
        perception_result: str,
        decision_suggestion: str,
        teaching_tip: str
    ):
        """
        分析完成回调（在主线程执行）
        :param perception_result: 感知结果
        :param decision_suggestion: 决策建议
        :param teaching_tip: 教学提示
        """
        logger.info("分析完成，更新 UI 显示")
        
        # 通过信号更新 UI（确保线程安全）
        self.ui.ui_signals.update_display.emit(
            perception_result,
            decision_suggestion,
            teaching_tip
        )
        
        self.ui.set_status_message("分析完成 | 请按接受/拒绝/演示")
        
        # 记录审计日志
        self.audit_logger.log_action(
            action_type="ai_analysis",
            target="screen",
            success=True,
            params={
                "suggestion": decision_suggestion[:100],
                "tip": teaching_tip[:100]
            },
            user_confirmed=False
        )
    
    def _on_analysis_error(self, error_msg: str):
        """
        分析错误回调
        :param error_msg: 错误消息
        """
        logger.error(f"分析失败：{error_msg}")
        
        self.ui.set_status_message(f"错误：{error_msg}")
        
        # 记录审计日志
        self.audit_logger.log_action(
            action_type="ai_analysis",
            target="screen",
            success=False,
            reason=error_msg,
            user_confirmed=False
        )
    
    def _on_user_accept(self):
        """用户点击接受按钮"""
        logger.info("用户确认：接受建议")
        self.user_confirmed = True
        
        # 获取当前显示的数据
        if self.ui.current_data:
            perception_result, suggestion, tip = self.ui.current_data
            
            # 记录审计日志
            self.audit_logger.log_action(
                action_type="user_accept",
                target=suggestion[:100],
                success=True,
                user_confirmed=True
            )
            
            # TODO: 根据建议执行具体操作
            # 这里需要解析 suggestion 并调用 executor 执行相应动作
            self.ui.set_status_message("✓ 已接受，准备执行操作...")
    
    def _on_user_reject(self):
        """用户点击拒绝按钮"""
        logger.info("用户确认：拒绝建议")
        self.user_confirmed = False
        
        # 记录审计日志
        self.audit_logger.log_action(
            action_type="user_reject",
            target="ai_suggestion",
            success=True,
            user_confirmed=True
        )
        
        self.ui.set_status_message("✗ 已拒绝建议")
    
    def _on_user_demo(self):
        """用户点击演示按钮"""
        logger.info("用户请求：演示模式")
        
        # 记录审计日志
        self.audit_logger.log_action(
            action_type="user_demo",
            target="screen_highlight",
            success=True,
            user_confirmed=True
        )
        
        # TODO: 实现演示逻辑（高亮目标区域等）
        self.ui.set_status_message("▶ 演示模式中...")
    
    def _on_wake_up(self):
        """唤醒/隐藏 UI"""
        self.ui.toggle_visibility()
    
    def toggle_dry_run(self):
        """切换安全模式/执行模式"""
        self.executor.set_dry_run(not self.executor.dry_run)
        self.ui.set_mode(self.executor.dry_run)
    
    def cleanup(self):
        """清理资源"""
        logger.info("正在清理资源...")
        self.stop()
        
        # 保存审计日志
        log_path = self.audit_logger.get_today_log_path()
        logger.info(f"今日审计日志：{log_path}")


def main():
    """主入口函数"""
    # 创建 QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Assistant")
    
    # 创建主控制器
    controller = MainController(config_path="config.ini")
    
    # 设置全局快捷键 Ctrl+Space
    wake_shortcut = QShortcut(QKeySequence("Ctrl+Space"), controller.ui)
    wake_shortcut.activated.connect(controller.trigger_analysis)
    
    # 启动助手
    controller.start()
    
    # 注册退出处理
    def on_exit():
        controller.cleanup()
    
    import atexit
    atexit.register(on_exit)
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
