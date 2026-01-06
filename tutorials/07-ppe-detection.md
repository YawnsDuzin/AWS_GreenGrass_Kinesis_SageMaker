# Part 7: PPE 감지 구현 상세

이 파트에서는 PPE 감지 로직의 상세 구현과 최적화 방법을 설명합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] YOLOv8 추론 파이프라인 이해
- [x] Raspberry Pi 최적화 기법
- [x] 안전 위반 판단 로직
- [x] 프레임 처리 최적화
- [x] 실시간 시각화 (선택)

---

## 1. YOLOv8 추론 파이프라인

### 1.1 전체 흐름

```
카메라 입력 → 전처리 → ONNX 추론 → 후처리 → NMS → 결과 출력
     ↓            ↓          ↓           ↓        ↓
 [BGR 이미지]  [Blob 변환]  [모델 실행]  [좌표 변환]  [중복 제거]
```

### 1.2 상세 추론 코드

```python
#!/usr/bin/env python3
"""
YOLOv8 추론 상세 구현
Raspberry Pi 4 (64-bit) 최적화
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass
import time


@dataclass
class BoundingBox:
    """바운딩 박스"""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class Detection:
    """감지 결과"""
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox


class YOLOv8Inference:
    """YOLOv8 ONNX 추론 클래스"""

    # PPE 클래스 정의
    CLASSES = {
        0: 'person',
        1: 'hardhat',
        2: 'safety_vest',
        3: 'safety_shoes',
        4: 'no_hardhat',
        5: 'no_safety_vest'
    }

    # 클래스별 색상 (BGR)
    COLORS = {
        'person': (255, 128, 0),
        'hardhat': (0, 255, 0),
        'safety_vest': (0, 255, 255),
        'safety_shoes': (255, 255, 0),
        'no_hardhat': (0, 0, 255),      # 빨강 - 위험
        'no_safety_vest': (0, 0, 255)   # 빨강 - 위험
    }

    def __init__(
        self,
        model_path: str,
        input_size: int = 640,
        conf_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        num_threads: int = 4
    ):
        """
        Args:
            model_path: ONNX 모델 경로
            input_size: 입력 이미지 크기
            conf_threshold: 신뢰도 임계값
            nms_threshold: NMS 임계값
            num_threads: CPU 스레드 수
        """
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold

        # OpenCV 스레드 설정
        cv2.setNumThreads(num_threads)

        # 모델 로드
        print(f"모델 로딩: {model_path}")
        self.net = cv2.dnn.readNetFromONNX(model_path)

        # CPU 최적화 백엔드
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        print(f"모델 로딩 완료 (입력: {input_size}x{input_size})")

    def preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        이미지 전처리

        Args:
            frame: BGR 이미지

        Returns:
            blob: 전처리된 입력
            scale_x: X 스케일 팩터
            scale_y: Y 스케일 팩터
        """
        h, w = frame.shape[:2]

        # 스케일 팩터 계산
        scale_x = w / self.input_size
        scale_y = h / self.input_size

        # Blob 생성
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1/255.0,
            size=(self.input_size, self.input_size),
            mean=(0, 0, 0),
            swapRB=True,  # BGR → RGB
            crop=False
        )

        return blob, scale_x, scale_y

    def postprocess(
        self,
        outputs: np.ndarray,
        scale_x: float,
        scale_y: float
    ) -> List[Detection]:
        """
        모델 출력 후처리

        Args:
            outputs: 모델 원시 출력
            scale_x: X 스케일 팩터
            scale_y: Y 스케일 팩터

        Returns:
            감지 결과 리스트
        """
        # YOLOv8 출력 형식: [1, 4+num_classes, num_detections]
        # Transpose: [num_detections, 4+num_classes]
        outputs = outputs[0].T

        boxes = []
        confidences = []
        class_ids = []

        for detection in outputs:
            # 첫 4개: x_center, y_center, width, height
            x_center, y_center, w, h = detection[:4]

            # 나머지: 클래스별 점수
            class_scores = detection[4:]
            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]

            if confidence >= self.conf_threshold:
                # 좌표 변환 (center → corner) 및 스케일 적용
                x1 = int((x_center - w/2) * scale_x)
                y1 = int((y_center - h/2) * scale_y)
                x2 = int((x_center + w/2) * scale_x)
                y2 = int((y_center + h/2) * scale_y)

                boxes.append([x1, y1, x2-x1, y2-y1])
                confidences.append(float(confidence))
                class_ids.append(int(class_id))

        # NMS (Non-Maximum Suppression)
        detections = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                confidences,
                self.conf_threshold,
                self.nms_threshold
            )

            for i in indices.flatten():
                x, y, w, h = boxes[i]
                detections.append(Detection(
                    class_id=class_ids[i],
                    class_name=self.CLASSES.get(class_ids[i], 'unknown'),
                    confidence=confidences[i],
                    bbox=BoundingBox(x, y, x+w, y+h)
                ))

        return detections

    def detect(self, frame: np.ndarray) -> Tuple[List[Detection], float]:
        """
        프레임에서 객체 감지

        Args:
            frame: BGR 이미지

        Returns:
            detections: 감지 결과
            inference_time: 추론 시간 (ms)
        """
        # 전처리
        blob, scale_x, scale_y = self.preprocess(frame)

        # 추론
        start_time = time.time()
        self.net.setInput(blob)
        outputs = self.net.forward()
        inference_time = (time.time() - start_time) * 1000

        # 후처리
        detections = self.postprocess(outputs, scale_x, scale_y)

        return detections, inference_time

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        감지 결과 시각화

        Args:
            frame: 원본 이미지
            detections: 감지 결과
            show_confidence: 신뢰도 표시 여부

        Returns:
            시각화된 이미지
        """
        result = frame.copy()

        for det in detections:
            color = self.COLORS.get(det.class_name, (128, 128, 128))
            bbox = det.bbox

            # 바운딩 박스
            thickness = 3 if 'no_' in det.class_name else 2
            cv2.rectangle(result, (bbox.x1, bbox.y1), (bbox.x2, bbox.y2), color, thickness)

            # 라벨
            label = det.class_name
            if show_confidence:
                label += f" {det.confidence:.2f}"

            # 라벨 배경
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(result, (bbox.x1, bbox.y1-th-10), (bbox.x1+tw+10, bbox.y1), color, -1)

            # 라벨 텍스트
            cv2.putText(result, label, (bbox.x1+5, bbox.y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return result
```

---

## 2. 안전 위반 판단 로직

### 2.1 위반 분석기

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import time


@dataclass
class SafetyViolation:
    """안전 위반"""
    violation_type: str
    person_bbox: Optional[BoundingBox]
    missing_items: List[str]
    confidence: float
    timestamp: str
    severity: str  # LOW, MEDIUM, HIGH


class SafetyAnalyzer:
    """안전 위반 분석기"""

    # 위반 유형
    VIOLATION_TYPES = {
        'no_hardhat': ('NO_HARDHAT', '안전모 미착용'),
        'no_safety_vest': ('NO_SAFETY_VEST', '안전조끼 미착용')
    }

    def __init__(
        self,
        alert_cooldown: int = 30,  # 동일 위반 재알림 간격 (초)
        iou_threshold: float = 0.3  # 장비-사람 매칭 IoU
    ):
        self.alert_cooldown = alert_cooldown
        self.iou_threshold = iou_threshold
        self.last_alerts = {}  # {violation_key: timestamp}

    def analyze(
        self,
        detections: List[Detection],
        frame_id: int
    ) -> List[SafetyViolation]:
        """
        감지 결과 분석

        Args:
            detections: 감지 결과
            frame_id: 프레임 ID

        Returns:
            위반 리스트
        """
        violations = []
        current_time = time.time()

        # 클래스별 분류
        persons = [d for d in detections if d.class_name == 'person']
        hardhats = [d for d in detections if d.class_name == 'hardhat']
        vests = [d for d in detections if d.class_name == 'safety_vest']
        no_hardhats = [d for d in detections if d.class_name == 'no_hardhat']
        no_vests = [d for d in detections if d.class_name == 'no_safety_vest']

        # 안전모 미착용 위반
        for i, no_hat in enumerate(no_hardhats):
            violation_key = f"no_hardhat_{self._get_position_key(no_hat.bbox)}"

            if self._should_alert(violation_key, current_time):
                # 관련 사람 찾기
                person = self._find_related_person(no_hat.bbox, persons)

                violations.append(SafetyViolation(
                    violation_type='NO_HARDHAT',
                    person_bbox=person.bbox if person else None,
                    missing_items=['hardhat'],
                    confidence=no_hat.confidence,
                    timestamp=datetime.now().isoformat(),
                    severity='HIGH'
                ))

                self.last_alerts[violation_key] = current_time

        # 안전조끼 미착용 위반
        for i, no_vest in enumerate(no_vests):
            violation_key = f"no_vest_{self._get_position_key(no_vest.bbox)}"

            if self._should_alert(violation_key, current_time):
                person = self._find_related_person(no_vest.bbox, persons)

                violations.append(SafetyViolation(
                    violation_type='NO_SAFETY_VEST',
                    person_bbox=person.bbox if person else None,
                    missing_items=['safety_vest'],
                    confidence=no_vest.confidence,
                    timestamp=datetime.now().isoformat(),
                    severity='MEDIUM'
                ))

                self.last_alerts[violation_key] = current_time

        return violations

    def _should_alert(self, key: str, current_time: float) -> bool:
        """알림 발송 여부 (쿨다운 확인)"""
        last_time = self.last_alerts.get(key, 0)
        return (current_time - last_time) >= self.alert_cooldown

    def _get_position_key(self, bbox: BoundingBox) -> str:
        """위치 기반 키 생성 (그리드 분할)"""
        # 이미지를 4x4 그리드로 분할하여 위치 추적
        grid_x = bbox.center[0] // 160
        grid_y = bbox.center[1] // 120
        return f"{grid_x}_{grid_y}"

    def _find_related_person(
        self,
        item_bbox: BoundingBox,
        persons: List[Detection]
    ) -> Optional[Detection]:
        """장비와 관련된 사람 찾기 (IoU 기반)"""
        best_person = None
        best_iou = 0

        for person in persons:
            iou = self._calculate_iou(item_bbox, person.bbox)
            if iou > best_iou and iou >= self.iou_threshold:
                best_iou = iou
                best_person = person

        return best_person

    def _calculate_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        """IoU 계산"""
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = box1.area + box2.area - intersection

        return intersection / union if union > 0 else 0.0
```

---

## 3. Raspberry Pi 최적화

### 3.1 성능 최적화 설정

```python
import os

def setup_rpi_optimization():
    """Raspberry Pi 최적화 설정"""

    # OpenBLAS 스레드 제한 (메모리 사용 최적화)
    os.environ['OPENBLAS_NUM_THREADS'] = '4'
    os.environ['OMP_NUM_THREADS'] = '4'

    # OpenCV 스레드 설정
    cv2.setNumThreads(4)

    # 메모리 할당 최적화
    cv2.setUseOptimized(True)

    print("Raspberry Pi 최적화 적용 완료")


def get_optimal_settings() -> dict:
    """환경에 맞는 최적 설정 반환"""

    # Raspberry Pi 4 메모리 확인
    with open('/proc/meminfo') as f:
        meminfo = f.read()
        total_mem = int(meminfo.split('MemTotal:')[1].split()[0]) // 1024  # MB

    settings = {
        'input_size': 640,
        'batch_size': 1,
        'num_threads': 4
    }

    # 메모리 기반 설정 조정
    if total_mem < 2048:  # 2GB 미만
        settings['input_size'] = 416
        print("⚠️ 메모리 부족: 입력 크기 축소")
    elif total_mem < 4096:  # 4GB 미만
        settings['input_size'] = 512

    return settings
```

### 3.2 프레임 스킵 및 버퍼링

```python
import threading
from queue import Queue
from collections import deque


class OptimizedCapture:
    """최적화된 카메라 캡처"""

    def __init__(
        self,
        source: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 15,
        buffer_size: int = 2,
        skip_frames: int = 0  # 처리 못한 프레임 스킵
    ):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.buffer_size = buffer_size
        self.skip_frames = skip_frames

        self.cap = None
        self.running = False
        self.frame_buffer = deque(maxlen=buffer_size)
        self.lock = threading.Lock()
        self.frame_count = 0

    def start(self):
        """캡처 시작"""
        self.cap = cv2.VideoCapture(self.source, cv2.CAP_V4L2)

        # V4L2 설정
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # 버퍼 크기 최소화
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            raise RuntimeError("카메라 열기 실패")

        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()

        print(f"카메라 시작: {self.width}x{self.height}@{self.fps}fps")

    def _capture_loop(self):
        """백그라운드 캡처"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1

                # 프레임 스킵
                if self.skip_frames > 0 and self.frame_count % (self.skip_frames + 1) != 0:
                    continue

                with self.lock:
                    self.frame_buffer.append((self.frame_count, frame))

    def read(self) -> tuple:
        """최신 프레임 읽기"""
        with self.lock:
            if self.frame_buffer:
                return self.frame_buffer[-1]  # 최신 프레임
            return None, None

    def stop(self):
        """캡처 중지"""
        self.running = False
        if self.cap:
            self.cap.release()
```

### 3.3 추론 결과 캐싱

```python
from functools import lru_cache
import hashlib


class CachedDetector:
    """결과 캐싱 지원 감지기"""

    def __init__(self, detector: YOLOv8Inference, cache_size: int = 10):
        self.detector = detector
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def detect_with_cache(
        self,
        frame: np.ndarray,
        similarity_threshold: float = 0.95
    ) -> List[Detection]:
        """
        유사 프레임 캐싱으로 추론 최적화

        Args:
            frame: 입력 프레임
            similarity_threshold: 캐시 히트 유사도 임계값

        Returns:
            감지 결과
        """
        # 프레임 해시 (다운샘플링)
        small = cv2.resize(frame, (64, 64))
        frame_hash = hashlib.md5(small.tobytes()).hexdigest()

        # 캐시 확인
        if frame_hash in self.cache:
            self.cache_hits += 1
            return self.cache[frame_hash]

        # 새 추론
        self.cache_misses += 1
        detections, _ = self.detector.detect(frame)

        # 캐시 저장
        self.cache[frame_hash] = detections

        # 캐시 크기 제한
        if len(self.cache) > 100:
            # 가장 오래된 항목 삭제
            oldest = list(self.cache.keys())[0]
            del self.cache[oldest]

        return detections

    @property
    def cache_hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0
```

---

## 4. 실시간 시각화 (선택)

### 4.1 웹 스트리밍 서버

```python
from flask import Flask, Response
import threading

app = Flask(__name__)
output_frame = None
lock = threading.Lock()


def generate_frames():
    """MJPEG 스트림 생성"""
    global output_frame

    while True:
        with lock:
            if output_frame is None:
                continue
            _, buffer = cv2.imencode('.jpg', output_frame)
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/video')
def video_feed():
    """비디오 피드 엔드포인트"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def start_web_server(port: int = 8080):
    """웹 서버 시작"""
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, threaded=True),
        daemon=True
    ).start()
    print(f"웹 스트리밍 시작: http://localhost:{port}/video")


def update_frame(frame: np.ndarray):
    """출력 프레임 업데이트"""
    global output_frame
    with lock:
        output_frame = frame.copy()
```

### 4.2 통합 사용 예시

```python
def main_with_visualization():
    """시각화 포함 메인 루프"""

    # 웹 서버 시작
    start_web_server(8080)

    # 컴포넌트 초기화
    detector = YOLOv8Inference('model.onnx')
    analyzer = SafetyAnalyzer()
    capture = OptimizedCapture()

    capture.start()

    while True:
        frame_id, frame = capture.read()
        if frame is None:
            continue

        # 감지
        detections, inference_time = detector.detect(frame)

        # 분석
        violations = analyzer.analyze(detections, frame_id)

        # 시각화
        vis_frame = detector.draw_detections(frame, detections)

        # 위반 표시
        if violations:
            cv2.putText(
                vis_frame,
                f"⚠️ VIOLATIONS: {len(violations)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 0, 255), 2
            )

        # FPS 표시
        cv2.putText(
            vis_frame,
            f"Inference: {inference_time:.1f}ms",
            (10, vis_frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (0, 255, 0), 2
        )

        # 웹 스트림 업데이트
        update_frame(vis_frame)
```

---

## 5. 성능 벤치마크

### 5.1 벤치마크 스크립트

```python
def benchmark_inference(detector: YOLOv8Inference, num_frames: int = 100):
    """추론 성능 벤치마크"""

    # 더미 이미지
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    times = []

    # 웜업
    for _ in range(10):
        detector.detect(dummy_frame)

    # 벤치마크
    for i in range(num_frames):
        _, inference_time = detector.detect(dummy_frame)
        times.append(inference_time)

    # 결과
    avg_time = np.mean(times)
    std_time = np.std(times)
    fps = 1000 / avg_time

    print(f"=== 벤치마크 결과 ({num_frames} 프레임) ===")
    print(f"평균 추론 시간: {avg_time:.1f}ms")
    print(f"표준편차: {std_time:.1f}ms")
    print(f"추론 FPS: {fps:.1f}")
    print(f"최소: {min(times):.1f}ms, 최대: {max(times):.1f}ms")

    return avg_time, fps


if __name__ == "__main__":
    detector = YOLOv8Inference('model.onnx')
    benchmark_inference(detector)
```

예상 결과 (Raspberry Pi 4):
```
=== 벤치마크 결과 (100 프레임) ===
평균 추론 시간: 85.3ms
표준편차: 5.2ms
추론 FPS: 11.7
최소: 78.1ms, 최대: 102.3ms
```

---

## ✅ 체크리스트

- [ ] YOLOv8 추론 파이프라인 이해
- [ ] 안전 위반 분석기 구현
- [ ] Raspberry Pi 최적화 적용
- [ ] 프레임 스킵/버퍼링 구현
- [ ] 웹 시각화 (선택)
- [ ] 벤치마크 실행 (10+ FPS 달성)

---

## 📚 다음 단계

[Part 8: 알림 시스템 구축](./08-alert-system.md)으로 이동하여
SNS를 통한 실시간 알림 시스템을 구축합니다.
