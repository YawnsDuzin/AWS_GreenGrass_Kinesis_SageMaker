"""
Kinesis 처리기 단위 테스트
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '../src/kinesis')


class TestKinesisDataProcessor:
    """Kinesis 데이터 처리기 테스트"""

    @patch('boto3.client')
    @patch('boto3.resource')
    def test_process_records_no_violations(self, mock_resource, mock_client):
        """위반 없는 레코드 처리 테스트"""
        from data_processor import KinesisDataProcessor

        processor = KinesisDataProcessor(
            stream_name="test-stream",
            region="ap-northeast-2"
        )

        records = [{
            'Data': json.dumps({
                'device_id': 'rpi4-001',
                'timestamp': '2024-01-15T10:00:00Z',
                'detections': [
                    {'class_name': 'person', 'confidence': 0.9},
                    {'class_name': 'hardhat', 'confidence': 0.85}
                ]
            }).encode('utf-8')
        }]

        events = processor.process_records(records)

        assert len(events) == 1
        assert events[0].severity == "LOW"
        assert events[0].event_type == "NORMAL"

    @patch('boto3.client')
    @patch('boto3.resource')
    def test_process_records_with_violations(self, mock_resource, mock_client):
        """위반 있는 레코드 처리 테스트"""
        from data_processor import KinesisDataProcessor

        processor = KinesisDataProcessor(
            stream_name="test-stream",
            region="ap-northeast-2"
        )

        records = [{
            'Data': json.dumps({
                'device_id': 'rpi4-001',
                'timestamp': '2024-01-15T10:00:00Z',
                'detections': [
                    {'class_name': 'person', 'confidence': 0.9},
                    {'class_name': 'no_hardhat', 'confidence': 0.82},
                    {'class_name': 'no_safety_vest', 'confidence': 0.78}
                ]
            }).encode('utf-8')
        }]

        events = processor.process_records(records)

        assert len(events) == 1
        assert events[0].severity == "HIGH"
        assert events[0].event_type == "MULTIPLE_VIOLATIONS"


class TestFirehoseTransformer:
    """Firehose 변환기 테스트"""

    def test_transform_record(self):
        """레코드 변환 테스트"""
        from firehose_transformer import transform_record

        # 테스트 데이터
        test_data = {
            "device_id": "rpi4-001",
            "timestamp": "2024-01-15T10:00:00Z",
            "detections": [
                {"class_name": "person", "confidence": 0.9},
                {"class_name": "no_hardhat", "confidence": 0.82}
            ]
        }

        record = {
            'recordId': 'test-1',
            'data': base64.b64encode(json.dumps(test_data).encode()).decode()
        }

        result = transform_record(record)

        assert result['recordId'] == 'test-1'
        assert result['result'] == 'Ok'

        # 디코딩 및 확인
        decoded = base64.b64decode(result['data']).decode()
        enriched = json.loads(decoded.strip())

        assert enriched['device_id'] == 'rpi4-001'
        assert 'detection_summary' in enriched
        assert enriched['violation_count'] == 1
        assert enriched['severity'] == 'MEDIUM'

    def test_enrich_data_no_violations(self):
        """위반 없는 데이터 강화 테스트"""
        from firehose_transformer import enrich_data

        data = {
            "device_id": "rpi4-001",
            "detections": [
                {"class_name": "person", "confidence": 0.9},
                {"class_name": "hardhat", "confidence": 0.85}
            ]
        }

        enriched = enrich_data(data)

        assert enriched['violation_count'] == 0
        assert enriched['severity'] == 'LOW'
        assert not enriched['detection_summary']['has_violations']

    def test_lambda_handler(self):
        """Lambda 핸들러 테스트"""
        from firehose_transformer import lambda_handler

        test_data = {
            "device_id": "rpi4-001",
            "detections": [{"class_name": "person", "confidence": 0.9}]
        }

        event = {
            "records": [
                {
                    "recordId": "rec-1",
                    "data": base64.b64encode(json.dumps(test_data).encode()).decode()
                }
            ]
        }

        result = lambda_handler(event, None)

        assert len(result['records']) == 1
        assert result['records'][0]['result'] == 'Ok'


class TestVideoProcessor:
    """비디오 처리기 테스트"""

    @patch('boto3.client')
    def test_get_gstreamer_pipeline(self, mock_client):
        """GStreamer 파이프라인 생성 테스트"""
        from video_processor import VideoUploader

        pipeline = VideoUploader.get_gstreamer_pipeline(
            stream_name="test-stream",
            region="ap-northeast-2",
            width=640,
            height=480,
            fps=15
        )

        assert "test-stream" in pipeline
        assert "ap-northeast-2" in pipeline
        assert "640" in pipeline
        assert "480" in pipeline

    @patch('boto3.client')
    def test_get_usb_camera_pipeline(self, mock_client):
        """USB 카메라 파이프라인 테스트"""
        from video_processor import VideoUploader

        pipeline = VideoUploader.get_usb_camera_pipeline(
            stream_name="test-stream",
            device="/dev/video0"
        )

        assert "/dev/video0" in pipeline
        assert "test-stream" in pipeline


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
