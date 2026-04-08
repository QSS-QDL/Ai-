"""
自动化执行模块
封装 PyAutoGUI，支持点击、输入、快捷键操作
增加"安全模式"（Dry-run，仅日志记录不操作）
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

import pyautogui

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    自动化执行器
    封装 PyAutoGUI 操作，支持安全模式（Dry-run）
    """

    def __init__(self, dry_run: bool = True):
        """
        初始化执行器
        :param dry_run: True=安全模式（仅日志），False=实际执行
        """
        self.dry_run = dry_run
        self.action_log: List[Dict[str, Any]] = []
        
        # PyAutoGUI 安全设置
        pyautogui.FAILSAFE = True  # 鼠标移到屏幕角落可中断
        pyautogui.PAUSE = 0.1  # 操作间隔
        
        logger.info(f"ActionExecutor 初始化完成，模式：{'安全模式 (Dry-Run)' if dry_run else '执行模式'}")

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1
    ) -> bool:
        """
        模拟鼠标点击
        :param x: X 坐标
        :param y: Y 坐标
        :param button: 按钮类型 (left/middle/right)
        :param clicks: 点击次数
        :param interval: 多次点击间隔
        :return: True 如果成功或处于安全模式，False 如果失败
        """
        action_info = {
            "type": "click",
            "params": {"x": x, "y": y, "button": button, "clicks": clicks},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            logger.info(f"[Dry-Run] 模拟点击：({x}, {y}), 按钮：{button}, 次数：{clicks}")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)
            logger.info(f"[执行] 点击：({x}, {y}), 按钮：{button}")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 点击失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def double_click(self, x: int, y: int) -> bool:
        """双击指定位置"""
        return self.click(x, y, clicks=2)

    def right_click(self, x: int, y: int) -> bool:
        """右键点击指定位置"""
        return self.click(x, y, button="right")

    def move_to(self, x: int, y: int, duration: float = 0.5) -> bool:
        """
        移动鼠标到指定位置
        :param x: X 坐标
        :param y: Y 坐标
        :param duration: 移动耗时（秒）
        """
        action_info = {
            "type": "move_to",
            "params": {"x": x, "y": y, "duration": duration},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            logger.info(f"[Dry-Run] 模拟移动鼠标到：({x}, {y})")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            pyautogui.moveTo(x, y, duration=duration)
            logger.info(f"[执行] 移动鼠标到：({x}, {y})")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 移动失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """
        模拟键盘输入文本
        :param text: 要输入的文本
        :param interval: 字符间隔（秒）
        """
        action_info = {
            "type": "type_text",
            "params": {"text": text, "interval": interval},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            logger.info(f"[Dry-Run] 模拟输入文本：{text[:50]}...")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            pyautogui.write(text, interval=interval)
            logger.info(f"[执行] 输入文本：{text[:50]}...")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 输入失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def press_key(self, key: str, presses: int = 1, interval: float = 0.1) -> bool:
        """
        模拟按键
        :param key: 键名（如 'enter', 'ctrl', 'a'）
        :param presses: 按压次数
        :param interval: 多次按压间隔
        """
        action_info = {
            "type": "press_key",
            "params": {"key": key, "presses": presses},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            logger.info(f"[Dry-Run] 模拟按键：{key} x{presses}")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            pyautogui.press(key, presses=presses, interval=interval)
            logger.info(f"[执行] 按键：{key} x{presses}")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 按键失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def hotkey(self, *keys: str) -> bool:
        """
        模拟组合键
        :param keys: 组合键列表（如 'ctrl', 'c'）
        """
        action_info = {
            "type": "hotkey",
            "params": {"keys": list(keys)},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            logger.info(f"[Dry-Run] 模拟组合键：{'+'.join(keys)}")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"[执行] 组合键：{'+'.join(keys)}")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 组合键失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        模拟滚轮滚动
        :param clicks: 滚动量（正数向上，负数向下）
        :param x: 可选的 X 坐标
        :param y: 可选的 Y 坐标
        """
        action_info = {
            "type": "scroll",
            "params": {"clicks": clicks, "x": x, "y": y},
            "timestamp": datetime.now().isoformat()
        }
        
        if self.dry_run:
            direction = "上" if clicks > 0 else "下"
            logger.info(f"[Dry-Run] 模拟滚动：{abs(clicks)}次（向{direction}）")
            self._log_action(action_info, success=True, dry_run=True)
            return True
        
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            logger.info(f"[执行] 滚动：{clicks}次")
            self._log_action(action_info, success=True)
            return True
        except Exception as e:
            logger.error(f"[错误] 滚动失败：{e}")
            self._log_action(action_info, success=False, reason=str(e))
            return False

    def _log_action(self, action_info: Dict[str, Any], success: bool, reason: str = "", dry_run: bool = False):
        """记录操作日志"""
        log_entry = {
            **action_info,
            "success": success,
            "dry_run": dry_run or self.dry_run,
            "reason": reason
        }
        self.action_log.append(log_entry)

    def get_action_log(self) -> List[Dict[str, Any]]:
        """获取操作日志副本"""
        return self.action_log.copy()

    def clear_log(self):
        """清空操作日志"""
        self.action_log.clear()
        logger.info("操作日志已清空")

    def set_dry_run(self, dry_run: bool):
        """
        切换运行模式
        :param dry_run: True=安全模式，False=执行模式
        """
        self.dry_run = dry_run
        mode_str = "安全模式 (Dry-Run)" if dry_run else "执行模式"
        logger.info(f"切换至：{mode_str}")

    def get_current_position(self) -> tuple:
        """获取当前鼠标位置"""
        return pyautogui.position()


# 权限检查装饰器
def require_permission(permission_type: str = "general"):
    """
    权限检查装饰器
    :param permission_type: 权限类型
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'permission_manager') and self.permission_manager:
                # 这里可以添加具体的权限检查逻辑
                pass
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试执行器
    executor = ActionExecutor(dry_run=True)
    
    print("=== 测试 ActionExecutor ===\n")
    
    # 测试点击
    executor.click(100, 200)
    
    # 测试移动
    executor.move_to(300, 400, duration=0.3)
    
    # 测试输入
    executor.type_text("Hello, World!")
    
    # 测试按键
    executor.press_key("enter")
    
    # 测试组合键
    executor.hotkey("ctrl", "c")
    
    # 测试滚动
    executor.scroll(-3)
    
    # 查看日志
    print("\n=== 操作日志 ===")
    for entry in executor.get_action_log():
        print(f"{entry['timestamp']} - {entry['type']}: {entry['params']} - {'✓' if entry['success'] else '✗'}")
