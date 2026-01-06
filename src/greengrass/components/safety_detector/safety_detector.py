#!/usr/bin/env python3
"""
건설현장 안전장비 감지 컴포넌트
Raspberry Pi 4 (64-bit Bullseye) 최적화 버전

이 컴포넌트는 AWS IoT GreenGrass V2에서 실행되며,
카메라로부터 영상을 받아 안전장비 착용 여부를 감지합니다.
"""

import json
import time
import logging
import argparse
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from queue import Queue
import sys
import os

import cv2
import numpy as np

# GreenGrass IPC 클라이언트
try:
    import awsiot.greengrasscoreipc
    from awsiot.greengrasscoreipc.model import (
        PublishToIoTCoreRequest,
        QOS
    )
    GREENGRASS_AVAILABLE = True
except ImportError:
    GREENGRASS_AVAILABLE = False
    print("GreenGrass IPC 라이브러리 없음 - 로컬 모드로 실행")

# Stream Manager 클라이언트
try:
    from stream_manager import (
        StreamManagerClient,
        MessageStreamDefinition,
        StrategyOnFull,
        ExportDefinition,
        KinesisConfig,
        Persistence
    )
    STREAM_MANAGER_AVAILABLE = True
except ImportError:
    STREAM_MANAGER_AVAILABLE = False
    print("Stream Manager 라이브러리 없음")


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SafetyDetector")


@dataclass
class Detection:
    """감지 결과 데이터 클래스"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    timestamp: str


@dataclass
class SafetyViolation:
    """안전 위반 이벤트"""
    violation_type: str
    person_id: Optional[int]
    missing_equipment: List[str]
    location: str
    timestamp: str
    frame_id: int
    confidence: float


class YOLOv8Detector:
    """
    YOLOv8 기반 안전장비 감지기
    Raspberry Pi 4 NEON 최적화
    """

    # 안전장비 클래스 정의
    SAFETY_CLASSES = {
        0: "person",
        1: "hardhat",
        2: "safety_vest",
        3: "safety_shoes",
        4: "no_hardhat",
        5: "no_safety_vest"
    }

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.4,
        num_threads: int = 4,
        use_neon: bool = True
    ):
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.num_threads = num_threads
        self.use_neon = use_neon

        logger.info(f"모델 로딩: {model_path}")
        logger.info(f"스레드 수: {num_threads}, NEON 사용: {use_neon}")

        # OpenCV DNN 백엔드 설정 (Raspberry Pi 4 최적화)
        self._setup_opencv_backend()

        # ONNX 모델 로드
        self.net = cv2.dnn.readNetFromONNX(model_path)

        # 추론 백엔드 및 타겟 설정
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        logger.info("모델 로딩 완료")

    def _setup_opencv_backend(self):
        """OpenCV 백엔드 최적화 설정"""
        # 스레드 수 설정
        cv2.setNumThreads(self.num_threads)

        # NEON 최적화 활성화 (ARM 프로세서)
        if self.use_neon:
            os.environ["OPENCV_OPENCL_RUNTIME"] = ""
            os.environ["OPENCV_OPENCL_DEVICE"] = ""

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        이미지 전처리

        Args:
            frame: BGR 이미지 (OpenCV 형식)

        Returns:
            전처리된 blob
        """
        # 입력 크기 (YOLOv8n 기본값)
        input_size = (640, 640)

        # Blob 생성 (정규화 및 리사이즈)
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1/255.0,
            size=input_size,
            mean=(0, 0, 0),
            swapRB=True,
            crop=False
        )

        return blob

    def postprocess(
        self,
        outputs: np.ndarray,
        original_shape: Tuple[int, int]
    ) -> List[Detection]:
        """
        모델 출력 후처리

        Args:
            outputs: 모델 출력
            original_shape: 원본 이미지 크기 (height, width)

        Returns:
            감지 결과 리스트
        """
        detections = []

        # YOLOv8 출력 형식: [1, num_classes + 4, num_detections]
        outputs = outputs[0].T  # Transpose

        height, width = original_shape
        x_scale = width / 640
        y_scale = height / 640

        boxes = []
        confidences = []
        class_ids = []

        for detection in outputs:
            # 첫 4개: x_center, y_center, w, h
            # 나머지: 클래스별 confidence
            x_center, y_center, w, h = detection[:4]
            class_scores = detection[4:]

            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]

            if confidence >= self.confidence_threshold:
                # 좌표 변환
                x = int((x_center - w/2) * x_scale)
                y = int((y_center - h/2) * y_scale)
                w = int(w * x_scale)
                h = int(h * y_scale)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(int(class_id))

        # Non-Maximum Suppression
        if boxes:
            indices = cv2.dnn.NMSBoxes(
                boxes,
                confidences,
                self.confidence_threshold,
                self.nms_threshold
            )

            timestamp = datetime.now().isoformat()

            for i in indices.flatten():
                detections.append(Detection(
                    class_id=class_ids[i],
                    class_name=self.SAFETY_CLASSES.get(class_ids[i], "unknown"),
                    confidence=confidences[i],
                    bbox=tuple(boxes[i]),
                    timestamp=timestamp
                ))

        return detections

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        프레임에서 객체 감지 수행

        Args:
            frame: BGR 이미지

        Returns:
            감지 결과 리스트
        """
        # 전처리
        blob = self.preprocess(frame)

        # 추론
        self.net.setInput(blob)
        outputs = self.net.forward()

        # 후처리
        detections = self.postprocess(outputs, frame.shape[:2])

        return detections


class CameraManager:
    """
    Raspberry Pi 카메라 관리
    CSI 카메라 및 USB 카메라 지원
    """

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 15
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.is_running = False
        self.frame_queue = Queue(maxsize=2)
        self.capture_thread = None

    def start(self) -> bool:
        """카메라 시작"""
        try:
            # V4L2 백엔드 사용 (Raspberry Pi 최적화)
            self.cap = cv2.VideoCapture(
                self.camera_index,
                cv2.CAP_V4L2
            )

            if not self.cap.isOpened():
                # CSI 카메라 시도 (libcamera 파이프라인)
                gst_pipeline = (
                    f"libcamerasrc ! "
                    f"video/x-raw,width={self.width},height={self.height},"
                    f"framerate={self.fps}/1 ! "
                    f"videoconvert ! appsink"
                )
                self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

            if not self.cap.isOpened():
                logger.error("카메라를 열 수 없습니다")
                return False

            # 카메라 설정
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # MJPEG 포맷 설정 (더 낮은 CPU 사용)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            logger.info(f"카메라 시작: {self.width}x{self.height}@{self.fps}fps")
            return True

        except Exception as e:
            logger.error(f"카메라 초기화 실패: {e}")
            return False

    def _capture_loop(self):
        """백그라운드 캡처 루프"""
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # 큐가 가득 차면 오래된 프레임 삭제
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                self.frame_queue.put(frame)
            else:
                time.sleep(0.01)

    def read(self) -> Optional[np.ndarray]:
        """프레임 읽기"""
        try:
            return self.frame_queue.get(timeout=1.0)
        except:
            return None

    def stop(self):
        """카메라 중지"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info("카메라 중지됨")


class KinesisPublisher:
    """
    Kinesis Data Streams로 데이터 전송
    Stream Manager 활용
    """

    def __init__(
        self,
        stream_name: str,
        region: str = "ap-northeast-2"
    ):
        self.stream_name = stream_name
        self.region = region
        self.client = None
        self.local_stream_name = f"local-{stream_name}"

    def connect(self) -> bool:
        """Stream Manager 연결"""
        if not STREAM_MANAGER_AVAILABLE:
            logger.warning("Stream Manager 사용 불가 - 로컬 모드")
            return False

        try:
            self.client = StreamManagerClient()

            # 로컬 스트림 생성 또는 기존 스트림 사용
            try:
                self.client.create_message_stream(
                    MessageStreamDefinition(
                        name=self.local_stream_name,
                        max_size=268435456,  # 256 MB
                        stream_segment_size=16777216,  # 16 MB
                        strategy_on_full=StrategyOnFull.OverwriteOldestData,
                        persistence=Persistence.File,
                        flush_on_write=False,
                        export_definition=ExportDefinition(
                            kinesis=[
                                KinesisConfig(
                                    identifier=f"kinesis-{self.stream_name}",
                                    kinesis_stream_name=self.stream_name,
                                    batch_size=1,
                                    batch_interval_millis=100
                                )
                            ]
                        )
                    )
                )
                logger.info(f"스트림 생성됨: {self.local_stream_name}")
            except Exception as e:
                if "exist" in str(e).lower():
                    logger.info(f"기존 스트림 사용: {self.local_stream_name}")
                else:
                    raise

            return True

        except Exception as e:
            logger.error(f"Stream Manager 연결 실패: {e}")
            return False

    def publish(self, data: Dict) -> bool:
        """데이터 발행"""
        try:
            if self.client:
                message = json.dumps(data).encode('utf-8')
                self.client.append_message(self.local_stream_name, message)
                return True
            else:
                # 로컬 모드: 로그로 출력
                logger.info(f"[LOCAL] 발행: {json.dumps(data, ensure_ascii=False)}")
                return True
        except Exception as e:
            logger.error(f"발행 실패: {e}")
            return False

    def close(self):
        """연결 종료"""
        if self.client:
            self.client.close()


class IoTCorePublisher:
    """
    AWS IoT Core로 MQTT 메시지 발행
    GreenGrass IPC 활용
    """

    def __init__(self, topic_prefix: str = "construction/safety"):
        self.topic_prefix = topic_prefix
        self.ipc_client = None

    def connect(self) -> bool:
        """IPC 클라이언트 연결"""
        if not GREENGRASS_AVAILABLE:
            logger.warning("GreenGrass IPC 사용 불가 - 로컬 모드")
            return False

        try:
            self.ipc_client = awsiot.greengrasscoreipc.connect()
            logger.info("IoT Core IPC 연결됨")
            return True
        except Exception as e:
            logger.error(f"IPC 연결 실패: {e}")
            return False

    def publish_detection(self, detections: List[Detection], device_id: str):
        """감지 결과 발행"""
        topic = f"{self.topic_prefix}/{device_id}/detections"

        payload = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "detection_count": len(detections),
            "detections": [asdict(d) for d in detections]
        }

        self._publish(topic, payload)

    def publish_violation(self, violation: SafetyViolation, device_id: str):
        """안전 위반 발행"""
        topic = f"{self.topic_prefix}/{device_id}/violations"
        payload = asdict(violation)
        payload["device_id"] = device_id

        self._publish(topic, payload, qos=QOS.AT_LEAST_ONCE if GREENGRASS_AVAILABLE else None)

    def _publish(self, topic: str, payload: Dict, qos=None):
        """메시지 발행"""
        try:
            message = json.dumps(payload).encode('utf-8')

            if self.ipc_client:
                request = PublishToIoTCoreRequest(
                    topic_name=topic,
                    qos=qos or QOS.AT_MOST_ONCE,
                    payload=message
                )
                self.ipc_client.publish_to_iot_core(request)
                logger.debug(f"IoT Core 발행: {topic}")
            else:
                logger.info(f"[LOCAL] {topic}: {payload}")

        except Exception as e:
            logger.error(f"IoT Core 발행 실패: {e}")


class SafetyAnalyzer:
    """
    안전 위반 분석기
    감지 결과를 분석하여 안전 위반 판단
    """

    def __init__(
        self,
        violation_threshold: int = 3,
        alert_cooldown: int = 30
    ):
        self.violation_threshold = violation_threshold
        self.alert_cooldown = alert_cooldown
        self.violation_history = {}
        self.last_alert_time = {}

    def analyze(
        self,
        detections: List[Detection],
        frame_id: int,
        location: str = "construction_site"
    ) -> List[SafetyViolation]:
        """
        감지 결과 분석

        Args:
            detections: 감지 결과
            frame_id: 프레임 ID
            location: 현장 위치

        Returns:
            안전 위반 리스트
        """
        violations = []
        current_time = time.time()

        # 사람과 장비 분리
        persons = [d for d in detections if d.class_name == "person"]
        hardhats = [d for d in detections if d.class_name == "hardhat"]
        vests = [d for d in detections if d.class_name == "safety_vest"]
        no_hardhats = [d for d in detections if d.class_name == "no_hardhat"]
        no_vests = [d for d in detections if d.class_name == "no_safety_vest"]

        # 안전모 미착용 위반
        for i, no_hat in enumerate(no_hardhats):
            violation_key = f"no_hardhat_{i}"

            if self._should_alert(violation_key, current_time):
                violations.append(SafetyViolation(
                    violation_type="NO_HARDHAT",
                    person_id=i,
                    missing_equipment=["hardhat"],
                    location=location,
                    timestamp=datetime.now().isoformat(),
                    frame_id=frame_id,
                    confidence=no_hat.confidence
                ))
                self.last_alert_time[violation_key] = current_time

        # 안전조끼 미착용 위반
        for i, no_vest in enumerate(no_vests):
            violation_key = f"no_vest_{i}"

            if self._should_alert(violation_key, current_time):
                violations.append(SafetyViolation(
                    violation_type="NO_SAFETY_VEST",
                    person_id=i,
                    missing_equipment=["safety_vest"],
                    location=location,
                    timestamp=datetime.now().isoformat(),
                    frame_id=frame_id,
                    confidence=no_vest.confidence
                ))
                self.last_alert_time[violation_key] = current_time

        return violations

    def _should_alert(self, violation_key: str, current_time: float) -> bool:
        """알림 발송 여부 확인 (쿨다운 적용)"""
        last_time = self.last_alert_time.get(violation_key, 0)
        return (current_time - last_time) >= self.alert_cooldown


class SafetyDetectorApp:
    """
    메인 애플리케이션 클래스
    """

    def __init__(self, config: Dict):
        self.config = config
        self.device_id = os.environ.get("AWS_IOT_THING_NAME", "rpi4-safety-001")
        self.is_running = False
        self.frame_count = 0

        # 컴포넌트 초기화
        self.camera = CameraManager(
            camera_index=config.get("camera_index", 0),
            width=config.get("frame_width", 640),
            height=config.get("frame_height", 480),
            fps=config.get("fps", 15)
        )

        self.detector = YOLOv8Detector(
            model_path=config.get("model_path", "models/yolov8n_safety.onnx"),
            confidence_threshold=config.get("confidence_threshold", 0.5),
            nms_threshold=config.get("nms_threshold", 0.4),
            num_threads=config.get("inference_threads", 4),
            use_neon=config.get("use_neon", True)
        )

        self.kinesis_publisher = KinesisPublisher(
            stream_name=config.get("kinesis_stream_name", "safety-detection-stream"),
            region=config.get("region", "ap-northeast-2")
        )

        self.iot_publisher = IoTCorePublisher(
            topic_prefix="construction/safety"
        )

        self.analyzer = SafetyAnalyzer(
            violation_threshold=config.get("violation_threshold", 3),
            alert_cooldown=config.get("alert_cooldown_seconds", 30)
        )

    def start(self):
        """애플리케이션 시작"""
        logger.info("=== 건설현장 안전 감지 시스템 시작 ===")
        logger.info(f"디바이스 ID: {self.device_id}")

        # 카메라 시작
        if not self.camera.start():
            logger.error("카메라 시작 실패")
            return

        # Kinesis 연결
        self.kinesis_publisher.connect()

        # IoT Core 연결
        self.iot_publisher.connect()

        self.is_running = True
        self._run_detection_loop()

    def _run_detection_loop(self):
        """메인 감지 루프"""
        logger.info("감지 루프 시작")

        fps_start_time = time.time()
        fps_frame_count = 0

        while self.is_running:
            try:
                # 프레임 읽기
                frame = self.camera.read()
                if frame is None:
                    continue

                self.frame_count += 1
                fps_frame_count += 1

                # 객체 감지
                start_time = time.time()
                detections = self.detector.detect(frame)
                inference_time = (time.time() - start_time) * 1000

                # 안전 위반 분석
                violations = self.analyzer.analyze(
                    detections,
                    frame_id=self.frame_count,
                    location=self.config.get("location", "site_1")
                )

                # 결과 발행
                if detections:
                    self.iot_publisher.publish_detection(detections, self.device_id)

                    # Kinesis로 상세 데이터 전송
                    self.kinesis_publisher.publish({
                        "device_id": self.device_id,
                        "frame_id": self.frame_count,
                        "timestamp": datetime.now().isoformat(),
                        "inference_time_ms": inference_time,
                        "detections": [asdict(d) for d in detections]
                    })

                # 위반 발생 시 알림
                for violation in violations:
                    logger.warning(f"안전 위반 감지: {violation.violation_type}")
                    self.iot_publisher.publish_violation(violation, self.device_id)

                # FPS 계산 (5초마다)
                elapsed = time.time() - fps_start_time
                if elapsed >= 5.0:
                    fps = fps_frame_count / elapsed
                    logger.info(f"FPS: {fps:.1f}, 추론 시간: {inference_time:.1f}ms")
                    fps_start_time = time.time()
                    fps_frame_count = 0

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"감지 루프 오류: {e}")
                time.sleep(1)

        self.stop()

    def stop(self):
        """애플리케이션 중지"""
        logger.info("시스템 종료 중...")
        self.is_running = False
        self.camera.stop()
        self.kinesis_publisher.close()
        logger.info("시스템 종료 완료")


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(description="건설현장 안전 감지 시스템")
    parser.add_argument(
        "--config",
        type=str,
        help="JSON 형식의 설정"
    )
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()

    # 설정 로드
    if args.config:
        try:
            config = json.loads(args.config)
        except json.JSONDecodeError:
            logger.error("설정 파싱 실패")
            config = {}
    else:
        config = {}

    # 기본 설정
    default_config = {
        "camera_index": 0,
        "frame_width": 640,
        "frame_height": 480,
        "fps": 15,
        "model_path": "models/yolov8n_safety.onnx",
        "confidence_threshold": 0.5,
        "nms_threshold": 0.4,
        "inference_threads": 4,
        "use_neon": True,
        "kinesis_stream_name": "safety-detection-stream",
        "region": "ap-northeast-2",
        "violation_threshold": 3,
        "alert_cooldown_seconds": 30,
        "location": "construction_site_1"
    }

    # 설정 병합
    final_config = {**default_config, **config}

    # 애플리케이션 시작
    app = SafetyDetectorApp(final_config)

    try:
        app.start()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    finally:
        app.stop()


if __name__ == "__main__":
    main()
