"""
안전 감지기 단위 테스트
Raspberry Pi 4 (64-bit) 환경 기준
"""

import pytest
import numpy as np
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '../src/greengrass/components/safety_detector')


class TestDetection:
    """Detection 데이터 클래스 테스트"""

    def test_detection_creation(self):
        """Detection 객체 생성 테스트"""
        from safety_detector import Detection

        detection = Detection(
            class_id=1,
            class_name="hardhat",
            confidence=0.95,
            bbox=(100, 100, 50, 50),
            timestamp="2024-01-15T10:00:00Z"
        )

        assert detection.class_id == 1
        assert detection.class_name == "hardhat"
        assert detection.confidence == 0.95
        assert detection.bbox == (100, 100, 50, 50)


class TestSafetyViolation:
    """SafetyViolation 데이터 클래스 테스트"""

    def test_violation_creation(self):
        """SafetyViolation 객체 생성 테스트"""
        from safety_detector import SafetyViolation

        violation = SafetyViolation(
            violation_type="NO_HARDHAT",
            person_id=1,
            missing_equipment=["hardhat"],
            location="site_1",
            timestamp="2024-01-15T10:00:00Z",
            frame_id=100,
            confidence=0.85
        )

        assert violation.violation_type == "NO_HARDHAT"
        assert violation.missing_equipment == ["hardhat"]
        assert violation.confidence == 0.85


class TestYOLOv8Detector:
    """YOLOv8 감지기 테스트"""

    @pytest.fixture
    def mock_model(self):
        """모델 모킹"""
        with patch('cv2.dnn.readNetFromONNX') as mock:
            mock.return_value = MagicMock()
            yield mock

    def test_preprocess_shape(self, mock_model):
        """전처리 출력 형태 테스트"""
        from safety_detector import YOLOv8Detector

        detector = YOLOv8Detector(
            model_path="test_model.onnx",
            confidence_threshold=0.5
        )

        # 테스트 이미지 생성
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        blob = detector.preprocess(test_image)

        # 출력 형태 확인: (1, 3, 640, 640)
        assert blob.shape == (1, 3, 640, 640)
        assert blob.dtype == np.float32

    def test_postprocess_empty(self, mock_model):
        """빈 출력 후처리 테스트"""
        from safety_detector import YOLOv8Detector

        detector = YOLOv8Detector(
            model_path="test_model.onnx",
            confidence_threshold=0.5
        )

        # 빈 출력
        outputs = np.zeros((1, 10, 0))  # 감지 없음
        detections = detector.postprocess(outputs, (480, 640))

        assert len(detections) == 0


class TestSafetyAnalyzer:
    """안전 분석기 테스트"""

    def test_no_violation(self):
        """위반 없음 테스트"""
        from safety_detector import SafetyAnalyzer, Detection

        analyzer = SafetyAnalyzer(
            violation_threshold=3,
            alert_cooldown=30
        )

        # 정상 감지 (안전장비 착용)
        detections = [
            Detection(0, "person", 0.9, (100, 100, 50, 100), "2024-01-15T10:00:00Z"),
            Detection(1, "hardhat", 0.85, (110, 90, 30, 30), "2024-01-15T10:00:00Z"),
            Detection(2, "safety_vest", 0.88, (105, 110, 40, 60), "2024-01-15T10:00:00Z"),
        ]

        violations = analyzer.analyze(detections, frame_id=1)

        assert len(violations) == 0

    def test_hardhat_violation(self):
        """안전모 미착용 위반 테스트"""
        from safety_detector import SafetyAnalyzer, Detection

        analyzer = SafetyAnalyzer(
            violation_threshold=3,
            alert_cooldown=0  # 쿨다운 비활성화
        )

        # 안전모 미착용 감지
        detections = [
            Detection(0, "person", 0.9, (100, 100, 50, 100), "2024-01-15T10:00:00Z"),
            Detection(4, "no_hardhat", 0.82, (110, 90, 30, 30), "2024-01-15T10:00:00Z"),
        ]

        violations = analyzer.analyze(detections, frame_id=1)

        assert len(violations) == 1
        assert violations[0].violation_type == "NO_HARDHAT"

    def test_alert_cooldown(self):
        """알림 쿨다운 테스트"""
        from safety_detector import SafetyAnalyzer, Detection
        import time

        analyzer = SafetyAnalyzer(
            violation_threshold=3,
            alert_cooldown=1  # 1초 쿨다운
        )

        detections = [
            Detection(4, "no_hardhat", 0.82, (110, 90, 30, 30), "2024-01-15T10:00:00Z"),
        ]

        # 첫 번째 분석 - 위반 감지
        violations1 = analyzer.analyze(detections, frame_id=1)
        assert len(violations1) == 1

        # 두 번째 분석 (쿨다운 내) - 위반 없음
        violations2 = analyzer.analyze(detections, frame_id=2)
        assert len(violations2) == 0

        # 쿨다운 후 - 위반 감지
        time.sleep(1.1)
        violations3 = analyzer.analyze(detections, frame_id=3)
        assert len(violations3) == 1


class TestCameraManager:
    """카메라 관리자 테스트"""

    @patch('cv2.VideoCapture')
    def test_camera_start(self, mock_capture):
        """카메라 시작 테스트"""
        from safety_detector import CameraManager

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_capture.return_value = mock_cap

        camera = CameraManager(
            camera_index=0,
            width=640,
            height=480,
            fps=15
        )

        result = camera.start()

        assert result == True
        mock_cap.set.assert_called()  # 설정 호출 확인

    @patch('cv2.VideoCapture')
    def test_camera_failure(self, mock_capture):
        """카메라 실패 테스트"""
        from safety_detector import CameraManager

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_capture.return_value = mock_cap

        camera = CameraManager(camera_index=0)
        result = camera.start()

        # CSI 카메라 시도 후 실패
        # (GStreamer도 실패한다고 가정)
        assert result == False


class TestKinesisPublisher:
    """Kinesis 발행자 테스트"""

    def test_local_mode_publish(self):
        """로컬 모드 발행 테스트"""
        from safety_detector import KinesisPublisher

        publisher = KinesisPublisher(
            stream_name="test-stream",
            region="ap-northeast-2"
        )

        # Stream Manager 없이 로컬 모드로 동작
        result = publisher.publish({"test": "data"})

        assert result == True


class TestIntegration:
    """통합 테스트"""

    @patch('cv2.VideoCapture')
    @patch('cv2.dnn.readNetFromONNX')
    def test_full_pipeline(self, mock_model, mock_capture):
        """전체 파이프라인 테스트"""
        from safety_detector import SafetyDetectorApp

        # 모킹 설정
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_capture.return_value = mock_cap

        mock_net = MagicMock()
        mock_net.forward.return_value = np.zeros((1, 10, 8400))
        mock_model.return_value = mock_net

        config = {
            "camera_index": 0,
            "frame_width": 640,
            "frame_height": 480,
            "fps": 15,
            "model_path": "test.onnx",
            "confidence_threshold": 0.5
        }

        app = SafetyDetectorApp(config)

        # 카메라 시작 확인
        assert app.camera is not None
        assert app.detector is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
