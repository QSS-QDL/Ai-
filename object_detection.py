import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path


class ObjectDetector:
    """
    对象/元素检测工具类（复用OpenCV模板匹配/YOLO），识别屏幕中的按钮、窗口、图标等元素，
    输出结构化数据（类型、坐标、标签），为决策层提供“元素定位”上下文。
    所属层：屏幕感知层（Screen Capture Layer）
    """

    def __init__(self, detector_type: str = "template", template_dir: Optional[str] = None,
                 yolo_model: Optional[str] = None):
        """
        初始化检测器
        :param detector_type: 检测类型（"template"=模板匹配，"yolo"=YOLO目标检测）
        :param template_dir: 模板匹配用（存储按钮/图标模板的目录，如"templates/button/"）
        :param yolo_model: YOLO用（模型路径，如"yolov8n.pt"）
        """
        self.detector_type = detector_type.lower()
        self.template_dir = Path(template_dir) if template_dir else None
        self.yolo_model = yolo_model

        # 初始化YOLO模型（OpenCV DNN）
        if self.detector_type == "yolo":
            self.net = cv2.dnn.readNetFromONNX(yolo_model) if yolo_model else None
            if not self.net:
                raise ValueError("YOLO模式需提供模型路径（如yolov8n.pt）")

        # 加载模板（模板匹配用）
        self.templates = {}
        if self.detector_type == "template" and self.template_dir:
            self._load_templates()

    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        统一检测入口：根据类型调用模板匹配/YOLO
        :param image: 输入图像（BGR格式，来自screenshot.py）
        :return: 检测结果列表，每个元素含{"type": 类型, "label": 标签, "box": (x,y,w,h)}
        """
        if self.detector_type == "template":
            return self._template_match(image)
        elif self.detector_type == "yolo":
            return self._yolo_detect(image)
        else:
            raise ValueError(f"不支持的检测类型：{self.detector_type}（可选template/yolo）")

    def _load_templates(self):
        """加载模板目录下的所有图像（按子目录分类，如button/submit.png→标签"submit_button"）"""
        for category_dir in self.template_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                for template_file in category_dir.glob("*.png"):
                    template = cv2.imread(str(template_file), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self.templates[f"{category}_{template_file.stem}"] = template

    def _template_match(self, image: np.ndarray) -> List[Dict]:
        """模板匹配检测（适合已知元素模板，如固定按钮）"""
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        results = []

        for label, template in self.templates.items():
            # 多尺度模板匹配（适应不同分辨率）
            for scale in [0.8, 1.0, 1.2]:
                resized_template = cv2.resize(template, None, fx=scale, fy=scale)
                h, w = resized_template.shape
                # 匹配（归一化互相关）
                match_res = cv2.matchTemplate(gray_image, resized_template, cv2.TM_CCOEFF_NORMED)
                threshold = 0.8  # 匹配阈值
                loc = np.where(match_res >= threshold)

                # 过滤重叠结果（非极大值抑制）
                for pt in zip(*loc[::-1]):
                    results.append({
                        "type": "template_match",
                        "label": label,
                        "box": (pt[0], pt[1], w, h),
                        "confidence": match_res[pt[1], pt[0]]
                    })
        return self._nms(results)  # 非极大值抑制去重

    def _yolo_detect(self, image: np.ndarray) -> List[Dict]:
        """YOLO目标检测（适合未知元素，如通用按钮/窗口）"""
        blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.net.getUnconnectedOutLayersNames())

        # 解析YOLO输出（假设COCO类别，如"button"需自定义训练）
        h, w = image.shape[:2]
        results = []
        for output in outputs:
            for det in output:
                scores = det[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:  # 置信度阈值
                    cx, cy, bw, bh = det[0:4] * np.array([w, h, w, h])
                    x = int(cx - bw / 2)
                    y = int(cy - bh / 2)
                    results.append({
                        "type": "yolo",
                        "label": f"class_{class_id}",  # 需映射为实际标签（如"button"）
                        "box": (x, y, int(bw), int(bh)),
                        "confidence": float(confidence)
                    })
        return self._nms(results)

    def _nms(self, detections: List[Dict], iou_thresh: float = 0.4) -> List[Dict]:
        """非极大值抑制（NMS）：过滤重叠检测框"""
        if not detections:
            return []
        # 按置信度排序
        detections.sort(key=lambda x: x["confidence"], reverse=True)
        keep = []
        while detections:
            current = detections.pop(0)
            keep.append(current)
            # 移除与当前框重叠高的检测
            detections = [d for d in detections if self._iou(current["box"], d["box"]) < iou_thresh]
        return keep

    @staticmethod
    def _iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """计算两个框的交并比（IoU）"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        # 计算交集区域
        inter_x1 = max(x1, x2)
        inter_y1 = max(y1, y2)
        inter_x2 = min(x1 + w1, x2 + w2)
        inter_y2 = min(y1 + h1, y2 + h2)
        inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        # 计算并集区域
        union_area = w1 * h1 + w2 * h2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0


# 示例：测试对象检测功能
if __name__ == "__main__":
    # 1. 模拟输入（截屏图像，来自screenshot.py）
    test_image = cv2.imread("fullscreen_screenshot.png")  # 替换为实际截屏路径

    # 2. 模板匹配模式（需提前准备templates/button/submit.png）
    template_detector = ObjectDetector(detector_type="template", template_dir="templates")
    template_results = template_detector.detect(test_image)
    print("模板匹配结果：", template_results)

    # 3. YOLO模式（需提供yolov8n.pt模型）
    #yolo_detector = ObjectDetector(detector_type="yolo", yolo_model="yolov8n.pt")
    #yolo_results = yolo_detector.detect(test_image)
    #print("YOLO检测结果：", yolo_results)

    # 4. 保存带检测框的图像（测试用）
    for res in template_results:
        x, y, w, h = res["box"]
        cv2.rectangle(test_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(test_image, res["label"], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imwrite("detected_objects.png", test_image)