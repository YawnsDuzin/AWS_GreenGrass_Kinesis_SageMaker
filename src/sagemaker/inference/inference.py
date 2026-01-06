#!/usr/bin/env python3
"""
SageMaker 추론 스크립트
안전장비 감지 모델 배포용
"""

import os
import json
import logging
import io
import base64
from typing import Dict, List, Any

import numpy as np
from PIL import Image
import cv2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SafetyInference")

# 전역 모델 객체
model = None


def model_fn(model_dir: str):
    """
    모델 로드 함수 (SageMaker 호출)

    Args:
        model_dir: 모델 디렉토리 경로

    Returns:
        로드된 모델
    """
    global model
    logger.info(f"모델 로딩: {model_dir}")

    # ONNX 모델 사용 (최적화됨)
    onnx_path = os.path.join(model_dir, 'model.onnx')

    if os.path.exists(onnx_path):
        import onnxruntime as ort

        # ONNX Runtime 세션 생성
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        model = ort.InferenceSession(
            onnx_path,
            sess_options=session_options,
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        logger.info("ONNX 모델 로드됨")
    else:
        # PyTorch 모델 사용
        from ultralytics import YOLO
        pt_path = os.path.join(model_dir, 'best.pt')
        model = YOLO(pt_path)
        logger.info("PyTorch 모델 로드됨")

    # 메타데이터 로드
    metadata_path = os.path.join(model_dir, 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)
        logger.info(f"메타데이터: {metadata}")

    return model


def input_fn(request_body: bytes, content_type: str) -> np.ndarray:
    """
    입력 전처리 함수

    Args:
        request_body: 요청 본문
        content_type: 콘텐츠 유형

    Returns:
        전처리된 이미지 배열
    """
    if content_type == 'application/json':
        data = json.loads(request_body)

        # Base64 인코딩된 이미지
        if 'image' in data:
            image_data = base64.b64decode(data['image'])
            image = Image.open(io.BytesIO(image_data))
            image = np.array(image)

            # BGR로 변환 (OpenCV 형식)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            return image

        # URL에서 이미지 로드
        elif 'url' in data:
            import urllib.request
            with urllib.request.urlopen(data['url']) as response:
                image_data = response.read()
            image = Image.open(io.BytesIO(image_data))
            return np.array(image)

    elif content_type in ['image/jpeg', 'image/png']:
        image = Image.open(io.BytesIO(request_body))
        image = np.array(image)

        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        return image

    raise ValueError(f"지원하지 않는 콘텐츠 유형: {content_type}")


def predict_fn(input_data: np.ndarray, model) -> Dict:
    """
    추론 함수

    Args:
        input_data: 입력 이미지
        model: 로드된 모델

    Returns:
        추론 결과
    """
    import onnxruntime as ort

    if isinstance(model, ort.InferenceSession):
        # ONNX 모델 추론
        return _predict_onnx(input_data, model)
    else:
        # YOLOv8 모델 추론
        return _predict_yolo(input_data, model)


def _predict_onnx(image: np.ndarray, session) -> Dict:
    """ONNX 모델 추론"""
    # 전처리
    input_size = (640, 640)
    original_shape = image.shape[:2]

    # 리사이즈 및 정규화
    resized = cv2.resize(image, input_size)
    blob = resized.astype(np.float32) / 255.0
    blob = blob.transpose(2, 0, 1)  # HWC -> CHW
    blob = np.expand_dims(blob, 0)  # 배치 차원 추가

    # 추론
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: blob})

    # 후처리
    detections = _postprocess_yolov8(outputs[0], original_shape, input_size)

    return {'detections': detections}


def _predict_yolo(image: np.ndarray, model) -> Dict:
    """YOLOv8 모델 추론"""
    results = model(image, verbose=False)

    detections = []
    for result in results:
        boxes = result.boxes

        for i in range(len(boxes)):
            box = boxes.xyxy[i].cpu().numpy()
            confidence = float(boxes.conf[i])
            class_id = int(boxes.cls[i])
            class_name = result.names[class_id]

            detections.append({
                'class_id': class_id,
                'class_name': class_name,
                'confidence': round(confidence, 4),
                'bbox': {
                    'x1': int(box[0]),
                    'y1': int(box[1]),
                    'x2': int(box[2]),
                    'y2': int(box[3])
                }
            })

    return {'detections': detections}


def _postprocess_yolov8(
    outputs: np.ndarray,
    original_shape: tuple,
    input_size: tuple,
    conf_threshold: float = 0.5,
    nms_threshold: float = 0.4
) -> List[Dict]:
    """YOLOv8 출력 후처리"""

    CLASS_NAMES = {
        0: 'person',
        1: 'hardhat',
        2: 'safety_vest',
        3: 'safety_shoes',
        4: 'no_hardhat',
        5: 'no_safety_vest'
    }

    outputs = outputs[0].T

    height, width = original_shape
    x_scale = width / input_size[0]
    y_scale = height / input_size[1]

    boxes = []
    confidences = []
    class_ids = []

    for detection in outputs:
        x_center, y_center, w, h = detection[:4]
        class_scores = detection[4:]

        class_id = np.argmax(class_scores)
        confidence = class_scores[class_id]

        if confidence >= conf_threshold:
            x1 = int((x_center - w/2) * x_scale)
            y1 = int((y_center - h/2) * y_scale)
            x2 = int((x_center + w/2) * x_scale)
            y2 = int((y_center + h/2) * y_scale)

            boxes.append([x1, y1, x2 - x1, y2 - y1])
            confidences.append(float(confidence))
            class_ids.append(int(class_id))

    # NMS
    detections = []
    if boxes:
        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

        for i in indices.flatten():
            x, y, w, h = boxes[i]
            detections.append({
                'class_id': class_ids[i],
                'class_name': CLASS_NAMES.get(class_ids[i], 'unknown'),
                'confidence': round(confidences[i], 4),
                'bbox': {
                    'x1': x,
                    'y1': y,
                    'x2': x + w,
                    'y2': y + h
                }
            })

    return detections


def output_fn(prediction: Dict, accept: str) -> bytes:
    """
    출력 포맷팅 함수

    Args:
        prediction: 추론 결과
        accept: Accept 헤더

    Returns:
        포맷팅된 응답
    """
    if accept == 'application/json':
        return json.dumps(prediction, ensure_ascii=False)

    raise ValueError(f"지원하지 않는 Accept 유형: {accept}")
