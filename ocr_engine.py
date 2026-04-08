import cv2
import pytesseract
import easyocr
import numpy as np
from typing import List, Tuple, Optional


class OCREngine:
    """
    OCR文字识别工具类（复用Tesseract/EasyOCR），对预处理后的图像进行文字提取，
    输出结构化文本（如按钮标签、输入框内容），为决策层提供上下文。
    所属层：屏幕感知层（Screen Capture Layer）
    """

    def __init__(self, engine: str = "tesseract", lang: str = "chi_sim+eng"):
        """
        初始化OCR引擎
        :param engine: 选择引擎（"tesseract" 或 "easyocr"）
        :param lang: 识别语言（Tesseract用"chi_sim+eng"表示中英文，EasyOCR用["ch_sim", "en"]）
        """
        self.engine = engine.lower()
        self.lang = lang

        # 初始化EasyOCR读取器（仅需一次）
        if self.engine == "easyocr":
            self.reader = easyocr.Reader([lang.split("_")[0]], gpu=False)  # 禁用GPU（如需GPU可设为True）

        # 配置Tesseract路径（Windows需手动指定，Linux/macOS通常已加入PATH）
        if self.engine == "tesseract":
            pytesseract.pytesseract.tesseract_cmd = r"A:\AI_pro\cherry\ai\OCR\tesseract.exe"  # Windows示例路径

    def process(self, image: np.ndarray) -> str:
        """
        OCR识别入口：根据引擎类型调用对应工具
        :param image: 输入图像（预处理后的灰度/二值图，来自preprocess.py）
        :return: 识别出的完整文本（换行分隔段落）
        """
        if self.engine == "tesseract":
            return self._tesseract_recognize(image)
        elif self.engine == "easyocr":
            return self._easyocr_recognize(image)
        else:
            raise ValueError(f"不支持的OCR引擎：{self.engine}（可选tesseract/easyocr）")

    def _tesseract_recognize(self, image: np.ndarray) -> str:
        """Tesseract OCR识别（适合清晰印刷体）"""
        # 配置Tesseract参数（PSM 6：假设为统一文本块）
        config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"
        text = pytesseract.image_to_string(image, lang=self.lang, config=config)
        return text.strip()

    def _easyocr_recognize(self, image: np.ndarray) -> str:
        """EasyOCR识别（适合手写体/复杂背景，基于PyTorch）"""
        results: List[Tuple[List[List[int]], str, float]] = self.reader.readtext(image)
        # 按坐标排序（从上到下、从左到右），拼接文本
        sorted_results = sorted(results, key=lambda x: (x[0][0][1], x[0][0][0]))
        text = "\n".join([res[1] for res in sorted_results])
        return text.strip()

    def get_text_boxes(self, image: np.ndarray) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        获取文字区域的坐标与内容（用于对象检测联动）
        :param image: 输入图像
        :return: 列表，每个元素为（文本内容, (x, y, w, h) 边界框）
        """
        if self.engine == "tesseract":
            boxes = pytesseract.image_to_boxes(image, lang=self.lang)
            return self._parse_tesseract_boxes(boxes, image.shape)
        elif self.engine == "easyocr":
            results = self.reader.readtext(image)
            return [(res[1], (
            int(res[0][0][0]), int(res[0][0][1]), int(res[0][1][0] - res[0][0][0]), int(res[0][2][1] - res[0][0][1])))
                    for res in results]
        else:
            raise ValueError(f"不支持的OCR引擎：{self.engine}")

    def _parse_tesseract_boxes(self, boxes_str: str, img_shape: Tuple[int, int, int]) -> List[
        Tuple[str, Tuple[int, int, int, int]]]:
        """解析Tesseract返回的边界框字符串"""
        boxes = []
        h = img_shape[0]
        for line in boxes_str.splitlines():
            parts = line.split()
            if len(parts) < 6:
                continue
            char, x1, y1, x2, y2, _ = parts
            # Tesseract坐标是左下角为原点，转换为左上角（适配OpenCV）
            x = int(x1)
            y = h - int(y2)
            w = int(x2) - x
            h_box = int(y2) - (h - int(y1))  # 修正高度计算
            boxes.append((char, (x, y, w, h_box)))
        return boxes


# 示例：测试OCR功能
if __name__ == "__main__":
    # 1. 模拟输入（预处理后的灰度图，来自preprocess.py）
    test_image = cv2.imread("preprocessed_image.png", cv2.IMREAD_GRAYSCALE)  # 替换为实际预处理图像路径

    # 2. 初始化Tesseract引擎（中英文）
    tesseract_engine = OCREngine(engine="tesseract", lang="chi_sim+eng")
    tesseract_text = tesseract_engine.process(test_image)
    print("Tesseract识别结果：\n", tesseract_text)

    # 3. 初始化EasyOCR引擎（中英文）
    easyocr_engine = OCREngine(engine="easyocr", lang="ch_sim+en")
    easyocr_text = easyocr_engine.process(test_image)
    print("EasyOCR识别结果：\n", easyocr_text)

    # 4. 获取文字区域坐标（示例）
    text_boxes = tesseract_engine.get_text_boxes(test_image)
    print("文字区域坐标：", text_boxes[:3])  # 打印前3个区域