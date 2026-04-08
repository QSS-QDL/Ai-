import pyautogui
import os
import sys
from typing import List, Dict, Any, Optional
from security_audit_layer.PermissionManager import PermissionManager


class AutomationTool:
    def __init__(self, permission_manager: PermissionManager, dry_run: bool = True):
        self.permission_manager = permission_manager
        self.dry_run = dry_run
        self.action_log: List[Dict] = []

    def click(self, x: int, y: int, button: str = "left") -> bool:
        if not self.permission_manager.check_coordinates(x, y):
            self._log_action("click", {"x": x, "y": y, "button": button}, False, "权限不足")
            return False

        if self.dry_run:
            print(f"[Dry-Run] 模拟点击：({x}, {y})，按键：{button}")
            self._log_action("click", {"x": x, "y": y, "button": button}, True, dry_run=True)
            return True
        else:
            try:
                pyautogui.click(x=x, y=y, button=button)
                print(f"[执行] 点击：({x}, {y})，按键：{button}")
                self._log_action("click", {"x": x, "y": y, "button": button}, True)
                return True
            except Exception as e:
                print(f"[错误] 点击失败：{e}")
                self._log_action("click", {"x": x, "y": y, "button": button}, False, str(e))
                return False

    def type_text(self, text: str, interval: float = 0.1) -> bool:
        if self.dry_run:
            print(f"[Dry-Run] 模拟输入文本：{text}")
            self._log_action("type_text", {"text": text, "interval": interval}, True, dry_run=True)
            return True
        else:
            try:
                pyautogui.typewrite(text, interval=interval)
                print(f"[执行] 输入文本：{text}")
                self._log_action("type_text", {"text": text, "interval": interval}, True)
                return True
            except Exception as e:
                print(f"[错误] 输入失败：{e}")
                self._log_action("type_text", {"text": text, "interval": interval}, False, str(e))
                return False

    def scroll(self, clicks: int, direction: str = "down") -> bool:
        if self.dry_run:
            print(f"[Dry-Run] 模拟滚动：{clicks}次（{direction}）")
            self._log_action("scroll", {"clicks": clicks, "direction": direction}, True, dry_run=True)
            return True
        else:
            try:
                pyautogui.scroll(clicks)
                print(f"[执行] 滚动：{clicks}次（{direction}）")
                self._log_action("scroll", {"clicks": clicks, "direction": direction}, True)
                return True
            except Exception as e:
                print(f"[错误] 滚动失败：{e}")
                self._log_action("scroll", {"clicks": clicks, "direction": direction}, False, str(e))
                return False

    def _log_action(self, action_type: str, params: Dict, success: bool, reason: str = "", dry_run: bool = False):
        from datetime import datetime
        self.action_log.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "params": params,
            "success": success,
            "dry_run": dry_run,
            "reason": reason
        })

    def get_action_log(self) -> List[Dict]:
        return self.action_log.copy()

    def set_dry_run(self, dry_run: bool):
        self.dry_run = dry_run
        print(f"切换至{'安全模式（Dry-Run）' if dry_run else '执行模式'}")