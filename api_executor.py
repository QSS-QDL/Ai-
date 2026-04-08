import os
import subprocess
import sys
from typing import List, Dict, Any, Optional
from security_audit_layer.PermissionManager import  PermissionManager


class APIExecutor:
    def __init__(self, permission_manager: PermissionManager, dry_run: bool = True):
        self.permission_manager = permission_manager
        self.dry_run = dry_run
        self.action_log: List[Dict] = []

    def open_file(self, file_path: str) -> bool:
        if not self.permission_manager.check_file_path(file_path):
            self._log_action("open_file", {"path": file_path}, False, "权限不足")
            return False

        if self.dry_run:
            print(f"[Dry-Run] 模拟打开文件：{file_path}")
            self._log_action("open_file", {"path": file_path}, True, dry_run=True)
            return True
        else:
            try:
                if os.name == "nt":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path])
                else:
                    subprocess.run(["xdg-open", file_path])
                print(f"[执行] 打开文件：{file_path}")
                self._log_action("open_file", {"path": file_path}, True)
                return True
            except Exception as e:
                print(f"[错误] 打开文件失败：{e}")
                self._log_action("open_file", {"path": file_path}, False, str(e))
                return False

    def run_program(self, program_path: str, args: Optional[List] = None) -> bool:
        if not self.permission_manager.check_program_path(program_path):
            self._log_action("run_program", {"path": program_path, "args": args}, False, "权限不足")
            return False

        if self.dry_run:
            print(f"[Dry-Run] 模拟运行程序：{program_path} 参数：{args}")
            self._log_action("run_program", {"path": program_path, "args": args}, True, dry_run=True)
            return True
        else:
            try:
                subprocess.run([program_path] + (args or []), check=True)
                print(f"[执行] 运行程序：{program_path} 参数：{args}")
                self._log_action("run_program", {"path": program_path, "args": args}, True)
                return True
            except Exception as e:
                print(f"[错误] 运行程序失败：{e}")
                self._log_action("run_program", {"path": program_path, "args": args}, False, str(e))
                return False

    def fill_form(self, form_type: str, data: Dict[str, Any]) -> bool:
        if not self.permission_manager.check_form_type(form_type):
            self._log_action("fill_form", {"type": form_type, "data": data}, False, "权限不足")
            return False

        if self.dry_run:
            print(f"[Dry-Run] 模拟填表：类型={form_type}，数据={data}")
            self._log_action("fill_form", {"type": form_type, "data": data}, True, dry_run=True)
            return True
        else:
            try:
                if form_type == "excel":
                    print(f"[执行] 填Excel表单：{data}")
                elif form_type == "web":
                    print(f"[执行] 填网页表单：{data}")
                else:
                    raise ValueError(f"不支持的表单类型：{form_type}")
                self._log_action("fill_form", {"type": form_type, "data": data}, True)
                return True
            except Exception as e:
                print(f"[错误] 填表失败：{e}")
                self._log_action("fill_form", {"type": form_type, "data": data}, False, str(e))
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