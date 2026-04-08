from typing import List, Dict, Any, Optional, Tuple


class PermissionManager:
    def __init__(
            self,
            allowed_dirs: Optional[List[str]] = None,
            allowed_apps: Optional[List[str]] = None,
            allowed_coords: Optional[List[Tuple[int, int, int, int]]] = None
    ):
        """
        初始化权限管理器
        :param allowed_dirs: 允许访问的目录列表 (前缀匹配)
        :param allowed_apps: 允许运行的程序路径列表
        :param allowed_coords: 允许点击的坐标区域列表 [(x1, y1, x2, y2), ...]
        """
        self.allowed_dirs = allowed_dirs or []
        self.allowed_apps = allowed_apps or []
        self.allowed_coords = allowed_coords or []

    def check_coordinates(self, x: int, y: int) -> bool:
        """
        校验坐标是否在允许范围内
        :param x: 横坐标
        :param y: 纵坐标
        :return: True 如果允许，False 如果拒绝
        """
        # 如果没有设置限制，默认允许所有 (或者你可以改为默认拒绝 return False)
        if not self.allowed_coords:
            return True

        for (x1, y1, x2, y2) in self.allowed_coords:
            # 确保坐标顺序正确 (min, max)
            min_x, max_x = sorted([x1, x2])
            min_y, max_y = sorted([y1, y2])

            if min_x <= x <= max_x and min_y <= y <= max_y:
                return True
        return False

    def check_file_path(self, file_path: str) -> bool:
        """
        校验文件路径是否在允许目录内
        :param file_path: 文件绝对路径
        :return: True 如果允许，False 如果拒绝
        """
        if not self.allowed_dirs:
            return True

        import os
        abs_path = os.path.abspath(file_path)

        for dir_path in self.allowed_dirs:
            abs_dir = os.path.abspath(dir_path)
            # 检查路径是否以允许的目录开头
            if abs_path.startswith(abs_dir + os.sep) or abs_path == abs_dir:
                return True
        return False

    def check_program_path(self, program_path: str) -> bool:
        """
        校验程序路径是否在允许列表内
        :param program_path: 程序路径
        :return: True 如果允许，False 如果拒绝
        """
        if not self.allowed_apps:
            return True

        import os
        abs_path = os.path.abspath(program_path)

        # 精确匹配或文件名匹配
        for app in self.allowed_apps:
            abs_app = os.path.abspath(app)
            if abs_path == abs_app or os.path.basename(abs_path) == os.path.basename(abs_app):
                return True
        return False

    def check_form_type(self, form_type: str) -> bool:
        """
        校验表单类型是否允许
        :param form_type: 表单类型 (如 "excel", "web")
        :return: True 如果允许，False 如果拒绝
        """
        # 修复：去除了字符串中多余的空格
        allowed_form_types = ["excel", "web", "csv"]
        return form_type.lower() in [t.lower() for t in allowed_form_types]