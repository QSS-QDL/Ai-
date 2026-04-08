import pyautogui
import cv2
import numpy as np
from typing import Optional, Tuple


class ScreenCapturer:
    """
    屏幕截屏工具类（复用pyautogui+OpenCV），支持全屏/局部截屏，输出OpenCV格式图像（BGR）。
    作为屏幕感知层的基础组件，为OCR/对象检测提供原始图像数据。
    """

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        初始化截屏器
        :param region: 局部截屏区域 (left, top, width, height)，None表示全屏
        """
        self.region = region  # 截屏区域（左、上、宽、高）

    def capture_fullscreen(self) -> np.ndarray:
        """截取全屏图像，返回OpenCV BGR格式数组"""
        screenshot = pyautogui.screenshot()  # PIL Image格式 (RGB)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)  # 转BGR

    def capture_region(self, region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        截取指定区域图像
        :param region: (left, top, width, height)，坐标基于屏幕左上角
        :return: OpenCV BGR格式数组
        """
        left, top, width, height = region
        screenshot = pyautogui.screenshot(region=(left, top, width, height))  # 局部截屏
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def capture(self) -> np.ndarray:
        """统一截屏入口：根据是否设置region决定全屏/局部截屏"""
        if self.region:
            return self.capture_region(self.region)
        return self.capture_fullscreen()


# 示例：测试截屏功能
if __name__ == "__main__":
    capturer = ScreenCapturer()  # 全屏截屏
    fullscreen_img = capturer.capture()
    cv2.imwrite("fullscreen_screenshot.png", fullscreen_img)  # 保存测试

    # 局部截屏示例（左上角(100,200)，宽300，高200）
    region_capturer = ScreenCapturer(region=(100, 200, 300, 200))
    region_img = region_capturer.capture()
    cv2.imwrite("region_screenshot.png", region_img)