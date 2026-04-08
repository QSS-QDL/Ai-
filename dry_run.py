from typing import List, Dict, Any
from security_audit_layer.PermissionManager import PermissionManager

class DryRunSimulator:
    def __init__(self, permission_manager: PermissionManager):
        self.permission_manager = permission_manager
        self.simulated_actions: List[Dict] = []

    def simulate_click(self, x: int, y: int, button: str = "left") -> bool:
        if not self.permission_manager.check_coordinates(x, y):
            self._log_simulated_action("click", {"x": x, "y": y, "button": button}, False, "权限不足")
            return False
        self._log_simulated_action("click", {"x": x, "y": y, "button": button}, True)
        print(f"[模拟] 点击：({x}, {y})，按键：{button}")
        return True

    def simulate_type(self, text: str, interval: float = 0.1) -> bool:
        self._log_simulated_action("type_text", {"text": text, "interval": interval}, True)
        print(f"[模拟] 输入文本：{text}")
        return True

    def simulate_open_file(self, file_path: str) -> bool:
        if not self.permission_manager.check_file_path(file_path):
            self._log_simulated_action("open_file", {"path": file_path}, False, "权限不足")
            return False
        self._log_simulated_action("open_file", {"path": file_path}, True)
        print(f"[模拟] 打开文件：{file_path}")
        return True

    def _log_simulated_action(self, action_type: str, params: Dict, success: bool, reason: str = ""):
        from datetime import datetime
        self.simulated_actions.append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "params": params,
            "success": success,
            "reason": reason
        })

    def get_simulated_log(self) -> List[Dict]:
        return self.simulated_actions.copy()

    def clear_log(self):
        self.simulated_actions.clear()