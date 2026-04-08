"""
屏幕感知与截图模块
支持全屏/区域截图，内存高效，直接转为 Base64 供 AI 使用
"""
import base64
import io
from typing import Optional, Tuple
from pathlib import Path

import mss
import mss.tools
from PIL import Image


class ScreenCapturer:
    """
    屏幕截屏工具类，支持全屏/局部截屏，输出 Base64 编码图像
    作为屏幕感知层的基础组件，为 OCR/对象检测/AI 推理提供原始图像数据
    """

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        初始化截屏器
        :param region: 局部截屏区域 (left, top, width, height)，None 表示全屏
        """
        self.region = region
        self.sct = mss.mss()

    def capture_fullscreen(self) -> bytes:
        """截取全屏图像，返回 PNG 格式的 bytes"""
        monitor = self.sct.monitors[0]  # 所有显示器
        screenshot = self.sct.grab(monitor)
        return mss.tools.to_png(screenshot.rgb, screenshot.size)

    def capture_region(self, region: Tuple[int, int, int, int]) -> bytes:
        """
        截取指定区域图像
        :param region: (left, top, width, height)，坐标基于屏幕左上角
        :return: PNG 格式的 bytes
        """
        left, top, width, height = region
        monitor = {"left": left, "top": top, "width": width, "height": height}
        screenshot = self.sct.grab(monitor)
        return mss.tools.to_png(screenshot.rgb, screenshot.size)

    def capture(self) -> bytes:
        """统一截屏入口：根据是否设置 region 决定全屏/局部截屏"""
        if self.region:
            return self.capture_region(self.region)
        return self.capture_fullscreen()

    def capture_to_base64(self) -> str:
        """
        截取屏幕并转换为 Base64 编码字符串
        :return: Base64 编码的 PNG 图像字符串（不含前缀）
        """
        image_bytes = self.capture()
        return base64.b64encode(image_bytes).decode('utf-8')

    def capture_to_base64_with_prefix(self) -> str:
        """
        截取屏幕并转换为带 Data URI 前缀的 Base64 编码字符串
        :return: Base64 编码的 PNG 图像字符串（含 data:image/png;base64,前缀）
        """
        base64_str = self.capture_to_base64()
        return f"data:image/png;base64,{base64_str}"

    def set_region(self, region: Optional[Tuple[int, int, int, int]]):
        """动态设置截图区域"""
        self.region = region

    @staticmethod
    def blur_image(image_bytes: bytes, regions: list) -> bytes:
        """
        对图像敏感区域进行模糊化处理
        :param image_bytes: PNG 图像 bytes
        :param regions: 需要模糊的区域列表 [(x, y, w, h), ...]
        :return: 模糊处理后的 PNG 图像 bytes
        """
        from PIL import ImageFilter
        
        img = Image.open(io.BytesIO(image_bytes))
        for (x, y, w, h) in regions:
            region = img.crop((x, y, x + w, y + h))
            blurred = region.filter(ImageFilter.GaussianBlur(radius=10))
            img.paste(blurred, (x, y))
        
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()

    def capture_with_blur(self, blur_regions: list) -> str:
        """
        截图并对敏感区域进行模糊处理后返回 Base64
        :param blur_regions: 需要模糊的区域列表 [(x, y, w, h), ...]
        :return: Base64 编码的 PNG 图像字符串
        """
        image_bytes = self.capture()
        if blur_regions:
            image_bytes = self.blur_image(image_bytes, blur_regions)
        return base64.b64encode(image_bytes).decode('utf-8')


# 示例：测试截屏功能
if __name__ == "__main__":
    capturer = ScreenCapturer()  # 全屏截屏
    base64_img = capturer.capture_to_base64()
    print(f"全屏截图 Base64 长度：{len(base64_img)}")

    # 局部截屏示例（左上角 (100,200)，宽 300，高 200）
    region_capturer = ScreenCapturer(region=(100, 200, 300, 200))
    region_base64 = region_capturer.capture_to_base64()
    print(f"区域截图 Base64 长度：{len(region_base64)}")
