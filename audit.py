"""
安全审计模块
记录所有操作日志，支持权限检查
日志存储于本地 logs/ 目录
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from functools import wraps


class AuditLogger:
    """
    审计日志记录器
    记录操作时间、类型、目标、结果，存储于本地 logs/ 目录
    """

    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        """
        初始化审计日志器
        :param log_dir: 日志存储目录
        :param log_level: 日志级别
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建专用 logger
        self.logger = logging.getLogger("AuditLogger")
        self.logger.setLevel(log_level)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件处理器 - 按日期分割日志文件
            log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 控制台处理器（可选）
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        self.logger.info("审计日志系统初始化完成")

    def log_action(
        self,
        action_type: str,
        target: str,
        success: bool,
        params: Optional[Dict[str, Any]] = None,
        reason: str = "",
        user_confirmed: bool = False
    ):
        """
        记录操作审计日志
        :param action_type: 操作类型（click/type/hotkey 等）
        :param target: 操作目标（坐标/文本/键名）
        :param success: 是否成功
        :param params: 额外参数
        :param reason: 失败原因或备注
        :param user_confirmed: 是否经过用户确认
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "target": target,
            "success": success,
            "params": params or {},
            "reason": reason,
            "user_confirmed": user_confirmed
        }
        
        status = "✓" if success else "✗"
        confirmed_mark = "[已确认]" if user_confirmed else "[未确认]"
        
        log_message = (
            f"{status} {confirmed_mark} | "
            f"类型：{action_type} | "
            f"目标：{target}"
        )
        
        if reason:
            log_message += f" | 原因：{reason}"
        
        if success:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)
        
        return log_entry

    def log_permission_check(
        self,
        app_name: str,
        action_type: str,
        allowed: bool
    ):
        """
        记录权限检查日志
        :param app_name: 应用名称
        :param action_type: 请求的操作类型
        :param allowed: 是否允许
        """
        status = "允许" if allowed else "拒绝"
        self.logger.info(f"权限检查 | 应用：{app_name} | 操作：{action_type} | 结果：{status}")

    def log_security_event(self, event_type: str, details: str):
        """
        记录安全事件
        :param event_type: 事件类型
        :param details: 事件详情
        """
        self.logger.warning(f"[安全事件] 类型：{event_type} | 详情：{details}")

    def get_today_log_path(self) -> Path:
        """获取今日日志文件路径"""
        return self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"

    def clear_old_logs(self, days: int = 7):
        """
        清理旧日志
        :param days: 保留天数
        """
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("audit_*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                self.logger.info(f"已删除旧日志：{log_file.name}")


# 权限白名单管理器
class PermissionWhitelist:
    """
    权限白名单管理器
    检查目标应用是否在允许列表中
    """

    def __init__(self, allowed_apps: Optional[List[str]] = None):
        """
        初始化白名单
        :param allowed_apps: 允许的应用列表（进程名或窗口标题关键词）
        """
        self.allowed_apps = set(allowed_apps or [])
        self.audit_logger = AuditLogger()

    def add_app(self, app_name: str):
        """添加应用到白名单"""
        self.allowed_apps.add(app_name.lower())
        self.audit_logger.log_security_event(
            "白名单更新",
            f"添加应用：{app_name}"
        )

    def remove_app(self, app_name: str):
        """从白名单移除应用"""
        self.allowed_apps.discard(app_name.lower())
        self.audit_logger.log_security_event(
            "白名单更新",
            f"移除应用：{app_name}"
        )

    def is_allowed(self, app_name: str) -> bool:
        """
        检查应用是否在白名单中
        :param app_name: 应用名称
        :return: True 如果允许
        """
        if not self.allowed_apps:
            return True  # 空名单表示允许所有
        
        app_lower = app_name.lower()
        for allowed in self.allowed_apps:
            if allowed in app_lower:
                return True
        return False

    def check_and_log(self, app_name: str, action_type: str) -> bool:
        """
        检查权限并记录日志
        :param app_name: 应用名称
        :param action_type: 操作类型
        :return: True 如果允许
        """
        allowed = self.is_allowed(app_name)
        self.audit_logger.log_permission_check(app_name, action_type, allowed)
        return allowed


# 权限检查装饰器
def require_user_confirmation(func: Callable) -> Callable:
    """
    要求用户确认的装饰器
    在执行操作前检查用户确认标志位
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 检查是否有 user_confirmed 属性且为 True
        if hasattr(self, 'user_confirmed') and not self.user_confirmed:
            self.audit_logger.log_security_event(
                "未授权操作拦截",
                f"操作：{func.__name__} 未经用户确认"
            )
            raise PermissionError(f"操作 '{func.__name__}' 需要用户确认")
        
        return func(self, *args, **kwargs)
    
    return wrapper


def check_app_permission(func: Callable) -> Callable:
    """
    检查应用权限的装饰器
    在执行操作前检查目标应用是否在白名单中
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'permission_whitelist'):
            # 尝试获取当前活动窗口名称（需要平台相关实现）
            app_name = kwargs.get('app_name', 'unknown')
            
            if not self.permission_whitelist.is_allowed(app_name):
                self.audit_logger.log_permission_check(app_name, func.__name__, False)
                raise PermissionError(f"应用 '{app_name}' 不在白名单中")
            
            self.permission_whitelist.check_and_log(app_name, func.__name__)
        
        return func(self, *args, **kwargs)
    
    return wrapper


# 示例使用
if __name__ == "__main__":
    # 初始化审计日志
    audit = AuditLogger()
    
    print("=== 测试审计日志系统 ===\n")
    
    # 测试操作日志
    audit.log_action(
        action_type="click",
        target="(100, 200)",
        success=True,
        params={"button": "left"},
        user_confirmed=True
    )
    
    audit.log_action(
        action_type="type_text",
        target="Hello World",
        success=False,
        reason="目标窗口不存在",
        user_confirmed=True
    )
    
    # 测试权限白名单
    whitelist = PermissionWhitelist(allowed_apps=["chrome", "notepad", "excel"])
    
    print(f"\nChrome 是否允许：{whitelist.is_allowed('chrome')}")
    print(f"Firefox 是否允许：{whitelist.is_allowed('firefox')}")
    print(f"Notepad 是否允许：{whitelist.is_allowed('Notepad++')}")
    
    # 记录权限检查
    whitelist.check_and_log("chrome", "click")
    whitelist.check_and_log("firefox", "click")
    
    # 查看日志文件
    log_path = audit.get_today_log_path()
    print(f"\n日志文件位置：{log_path.absolute()}")
    
    if log_path.exists():
        print(f"\n=== 今日日志内容 ===")
        with open(log_path, 'r', encoding='utf-8') as f:
            print(f.read())
