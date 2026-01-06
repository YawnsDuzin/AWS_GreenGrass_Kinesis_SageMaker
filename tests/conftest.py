"""
Pytest 설정 및 공통 픽스처
"""

import pytest
import numpy as np
import json
from unittest.mock import MagicMock


@pytest.fixture
def sample_detection_data():
    """샘플 감지 데이터"""
    return {
        'device_id': 'rpi4-001',
        'timestamp': '2024-01-15T10:00:00Z',
        'frame_id': 100,
        'detections': [
            {
                'class_id': 0,
                'class_name': 'person',
                'confidence': 0.95,
                'bbox': {'x1': 100, 'y1': 100, 'x2': 150, 'y2': 200}
            },
            {
                'class_id': 1,
                'class_name': 'hardhat',
                'confidence': 0.88,
                'bbox': {'x1': 110, 'y1': 90, 'x2': 140, 'y2': 110}
            }
        ]
    }


@pytest.fixture
def sample_violation_data():
    """샘플 위반 데이터"""
    return {
        'device_id': 'rpi4-001',
        'timestamp': '2024-01-15T10:00:00Z',
        'frame_id': 100,
        'detections': [
            {
                'class_id': 0,
                'class_name': 'person',
                'confidence': 0.95,
                'bbox': {'x1': 100, 'y1': 100, 'x2': 150, 'y2': 200}
            },
            {
                'class_id': 4,
                'class_name': 'no_hardhat',
                'confidence': 0.82,
                'bbox': {'x1': 110, 'y1': 90, 'x2': 140, 'y2': 110}
            }
        ]
    }


@pytest.fixture
def sample_image():
    """샘플 테스트 이미지"""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_kinesis_client():
    """Kinesis 클라이언트 모킹"""
    client = MagicMock()
    client.describe_stream.return_value = {
        'StreamDescription': {
            'Shards': [{'ShardId': 'shard-001'}]
        }
    }
    client.get_shard_iterator.return_value = {
        'ShardIterator': 'test-iterator'
    }
    return client


@pytest.fixture
def mock_dynamodb_table():
    """DynamoDB 테이블 모킹"""
    table = MagicMock()
    table.put_item.return_value = {}
    table.query.return_value = {'Items': []}
    table.scan.return_value = {'Items': []}
    return table


@pytest.fixture
def mock_sns_client():
    """SNS 클라이언트 모킹"""
    client = MagicMock()
    client.publish.return_value = {'MessageId': 'test-message-id'}
    return client


# 환경 변수 설정
@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """테스트용 환경 변수 설정"""
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'ap-northeast-2')
    monkeypatch.setenv('DYNAMODB_TABLE', 'test-safety-events')
    monkeypatch.setenv('SNS_TOPIC_ARN', 'arn:aws:sns:ap-northeast-2:123456789:test-topic')
