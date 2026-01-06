"""
Lambda 핸들러 단위 테스트
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os

import sys
sys.path.insert(0, '../src/lambda/safety_processor')
sys.path.insert(0, '../src/lambda/api_handler')


class TestSafetyProcessorLambda:
    """안전 처리 Lambda 테스트"""

    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'SNS_TOPIC_ARN': 'arn:aws:sns:ap-northeast-2:123456789:test-topic'
    })
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_lambda_handler_success(self, mock_client, mock_resource):
        """성공적인 처리 테스트"""
        from handler import lambda_handler

        # DynamoDB 모킹
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table

        # 테스트 이벤트
        test_data = {
            'device_id': 'rpi4-001',
            'timestamp': '2024-01-15T10:00:00Z',
            'detections': [
                {'class_name': 'person', 'confidence': 0.9}
            ]
        }

        event = {
            'Records': [
                {
                    'kinesis': {
                        'data': base64.b64encode(
                            json.dumps(test_data).encode()
                        ).decode()
                    }
                }
            ]
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['processed'] == 1

    @patch.dict(os.environ, {
        'DYNAMODB_TABLE': 'test-table',
        'SNS_TOPIC_ARN': ''
    })
    @patch('boto3.resource')
    @patch('boto3.client')
    def test_process_violation(self, mock_client, mock_resource):
        """위반 처리 테스트"""
        from handler import process_detection_data, calculate_severity

        data = {
            'device_id': 'rpi4-001',
            'timestamp': '2024-01-15T10:00:00Z',
            'detections': [
                {'class_name': 'person', 'confidence': 0.9},
                {'class_name': 'no_hardhat', 'confidence': 0.82}
            ]
        }

        result = process_detection_data(data)

        assert result['has_violations'] == True
        assert result['violation_count'] == 1
        assert result['severity'] == 'MEDIUM'

    def test_calculate_severity(self):
        """심각도 계산 테스트"""
        from handler import calculate_severity

        # 위반 없음
        assert calculate_severity([]) == 'NONE'

        # 단일 위반
        assert calculate_severity([{'class_name': 'no_hardhat'}]) == 'MEDIUM'

        # 다중 위반
        assert calculate_severity([
            {'class_name': 'no_hardhat'},
            {'class_name': 'no_safety_vest'}
        ]) == 'HIGH'


class TestAPIHandlerLambda:
    """API 핸들러 Lambda 테스트"""

    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'})
    @patch('boto3.resource')
    def test_get_devices(self, mock_resource):
        """디바이스 조회 테스트"""
        from handler import lambda_handler

        # DynamoDB 모킹
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {'pk': 'rpi4-001'},
                {'pk': 'rpi4-002'},
                {'pk': 'rpi4-001'}  # 중복
            ]
        }
        mock_resource.return_value.Table.return_value = mock_table

        event = {
            'httpMethod': 'GET',
            'path': '/devices'
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['count'] == 2  # 중복 제거

    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'})
    @patch('boto3.resource')
    def test_get_events(self, mock_resource):
        """이벤트 조회 테스트"""
        from handler import lambda_handler

        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {'pk': 'rpi4-001', 'sk': '2024-01-15T10:00:00Z'}
            ]
        }
        mock_resource.return_value.Table.return_value = mock_table

        event = {
            'httpMethod': 'GET',
            'path': '/events',
            'queryStringParameters': None
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert 'events' in body

    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'})
    @patch('boto3.resource')
    def test_get_statistics(self, mock_resource):
        """통계 조회 테스트"""
        from handler import lambda_handler

        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {'pk': 'rpi4-001', 'has_violations': True, 'severity': 'HIGH'},
                {'pk': 'rpi4-002', 'has_violations': False, 'severity': 'NONE'},
                {'pk': 'rpi4-001', 'has_violations': True, 'severity': 'MEDIUM'}
            ]
        }
        mock_resource.return_value.Table.return_value = mock_table

        event = {
            'httpMethod': 'GET',
            'path': '/stats'
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['total_events'] == 3
        assert body['violation_count'] == 2

    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'})
    def test_not_found(self):
        """404 테스트"""
        from handler import lambda_handler

        event = {
            'httpMethod': 'GET',
            'path': '/unknown'
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 404

    @patch.dict(os.environ, {'DYNAMODB_TABLE': 'test-table'})
    def test_cors_options(self):
        """CORS OPTIONS 테스트"""
        from handler import lambda_handler

        event = {
            'httpMethod': 'OPTIONS',
            'path': '/devices'
        }

        result = lambda_handler(event, None)

        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
