"""
Lambda 함수: REST API 핸들러
API Gateway 통합
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'safety-events')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handler(event: Dict, context: Any) -> Dict:
    """API Gateway Lambda 핸들러"""

    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    try:
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}

        if path == '/devices':
            result = get_devices()
        elif path == '/events':
            params = event.get('queryStringParameters') or {}
            result = get_events(params)
        elif path == '/stats':
            result = get_statistics()
        elif path == '/violations':
            params = event.get('queryStringParameters') or {}
            result = get_violations(params)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not Found'})
            }

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, cls=DecimalEncoder, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"오류: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }


def get_devices() -> Dict:
    """등록된 디바이스 목록 조회"""
    table = dynamodb.Table(TABLE_NAME)

    response = table.scan(
        ProjectionExpression='pk',
        Select='SPECIFIC_ATTRIBUTES'
    )

    devices = list(set(item['pk'] for item in response.get('Items', [])))

    return {
        'devices': devices,
        'count': len(devices)
    }


def get_events(params: Dict) -> Dict:
    """이벤트 조회"""
    table = dynamodb.Table(TABLE_NAME)
    device_id = params.get('device_id')
    limit = int(params.get('limit', 100))

    if device_id:
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': device_id},
            ScanIndexForward=False,
            Limit=limit
        )
    else:
        response = table.scan(Limit=limit)

    return {
        'events': response.get('Items', []),
        'count': len(response.get('Items', []))
    }


def get_violations(params: Dict) -> Dict:
    """위반 이벤트만 조회"""
    table = dynamodb.Table(TABLE_NAME)

    response = table.scan(
        FilterExpression='has_violations = :v',
        ExpressionAttributeValues={':v': True},
        Limit=int(params.get('limit', 100))
    )

    return {
        'violations': response.get('Items', []),
        'count': len(response.get('Items', []))
    }


def get_statistics() -> Dict:
    """통계 조회"""
    table = dynamodb.Table(TABLE_NAME)

    response = table.scan()
    items = response.get('Items', [])

    total_events = len(items)
    violations = [i for i in items if i.get('has_violations')]

    severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'NONE': 0}
    for item in items:
        severity = item.get('severity', 'NONE')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    return {
        'total_events': total_events,
        'violation_count': len(violations),
        'violation_rate': round(len(violations) / total_events * 100, 2) if total_events > 0 else 0,
        'severity_distribution': severity_counts
    }
