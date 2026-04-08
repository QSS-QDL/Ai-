import cv2
import numpy as np
from typing import Tuple, Optional


class ImagePreprocessor:
    """
    图像预处理工具类（复用OpenCV），对截屏输出的BGR图像进行灰度化、降噪、二值化等操作，
    为OCR（文字识别）和对象检测（元素定位）提供更清晰的输入。
    所属层：屏幕感知层（Screen Capture Layer）
    """

    def __init__(self, grayscale: bool = True, denoise: bool = True, binarize: bool = False):
        """
        初始化预处理器
        :param grayscale: 是否转为灰度图（默认True，OCR/检测常用）
        :param denoise: 是否降噪（默认True，去除椒盐噪声/高斯噪声）
        :param binarize: 是否二值化（默认False，需根据场景开启）
        """
        self.grayscale = grayscale
        self.denoise = denoise
        self.binarize = binarize

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        统一预处理入口：按顺序执行灰度化→降噪→二值化
        :param image: 输入图像（OpenCV BGR格式，来自screenshot.py）
        :return: 预处理后的图像（单通道灰度图或二值图）
        """
        processed = image.copy()

        # 1. 灰度化（BGR→GRAY）
        if self.grayscale:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)

        # 2. 降噪（高斯模糊/中值滤波，根据图像类型选择）
        if self.denoise:
            if len(processed.shape) == 3:  # 若为彩色图（未灰度化）
                processed = cv2.GaussianBlur(processed, (5, 5), 0)
            else:  # 若为灰度图
                processed = cv2.medianBlur(processed, 5)  # 中值滤波去椒盐噪声

        # 3. 二值化（Otsu自适应阈值，适用于文字/元素轮廓）
        if self.binarize:
            _, processed = cv2.threshold(
                processed, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )

        return processed

    def crop_region(self, image: np.ndarray, region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        裁剪图像至指定区域（辅助局部感知）
        :param image: 输入图像（BGR或灰度图）
        :param region: 裁剪区域 (x, y, width, height)，基于图像左上角
        :return: 裁剪后的子图像
        """
        x, y, w, h = region
        return image[y:y + h, x:x + w]

    def resize_to_scale(self, image: np.ndarray, scale_factor: float) -> np.ndarray:
        """
        按比例缩放图像（适配OCR模型输入尺寸）
        :param image: 输入图像
        :param scale_factor: 缩放因子（>1放大，<1缩小）
        :return: 缩放后的图像
        """
        return cv2.resize(
            image, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA
        )


# 示例：测试预处理流程
if __name__ == "__main__":
    # 1. 模拟截屏输入（BGR格式，来自screenshot.py）
    mock_image = cv2.imread("test_screenshot.png")  # 替换为实际截屏路径

    # 2. 初始化预处理器（灰度+降噪+二值化）
    preprocessor = ImagePreprocessor(grayscale=True, denoise=True, binarize=True)

    # 3. 执行预处理
    processed_img = preprocessor.process(mock_image)

    # 4. 保存结果（供OCR/检测使用）
    cv2.imwrite("preprocessed_image.png", processed_img)

    # 5. 测试局部裁剪
    cropped_img = preprocessor.crop_region(mock_image, region=(100, 200, 300, 200))
    cv2.imwrite("cropped_image.png", cropped_img)