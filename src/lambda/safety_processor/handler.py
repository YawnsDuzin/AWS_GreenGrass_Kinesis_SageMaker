"""
Lambda 함수: 안전 위반 처리기
Kinesis Data Streams 이벤트 처리
"""

import json
import base64
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
sagemaker_runtime = boto3.client('sagemaker-runtime')

# 환경 변수
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'safety-events')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT', 'safety-detection-endpoint')


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Lambda 핸들러 - Kinesis 이벤트 처리
    """
    logger.info(f"수신된 레코드 수: {len(event.get('Records', []))}")

    processed_count = 0
    violation_count = 0

    for record in event.get('Records', []):
        try:
            # Kinesis 데이터 디코딩
            payload = base64.b64decode(record['kinesis']['data'])
            data = json.loads(payload.decode('utf-8'))

            # 데이터 처리
            result = process_detection_data(data)

            if result.get('has_violations'):
                violation_count += 1

                # 알림 발송
                send_violation_alert(result)

            # DynamoDB 저장
            save_to_dynamodb(result)

            processed_count += 1

        except Exception as e:
            logger.error(f"레코드 처리 오류: {e}")

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'violations': violation_count
        })
    }

    logger.info(f"처리 완료: {processed_count}개, 위반: {violation_count}개")
    return response


def process_detection_data(data: Dict) -> Dict:
    """감지 데이터 처리 및 분석"""
    detections = data.get('detections', [])

    # 위반 감지
    violations = [d for d in detections if 'no_' in d.get('class_name', '')]

    result = {
        'device_id': data.get('device_id', 'unknown'),
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
        'frame_id': data.get('frame_id', 0),
        'detection_count': len(detections),
        'has_violations': len(violations) > 0,
        'violation_count': len(violations),
        'violation_types': list(set(v.get('class_name') for v in violations)),
        'severity': calculate_severity(violations),
        'detections': detections
    }

    return result


def calculate_severity(violations: List[Dict]) -> str:
    """위반 심각도 계산"""
    if not violations:
        return 'NONE'
    elif len(violations) == 1:
        return 'MEDIUM'
    elif len(violations) >= 2:
        return 'HIGH'
    return 'LOW'


def send_violation_alert(result: Dict):
    """SNS로 위반 알림 발송"""
    if not SNS_TOPIC_ARN:
        logger.warning("SNS Topic ARN 미설정")
        return

    message = {
        'alert_type': 'SAFETY_VIOLATION',
        'device_id': result['device_id'],
        'severity': result['severity'],
        'violation_types': result['violation_types'],
        'timestamp': result['timestamp']
    }

    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message, ensure_ascii=False),
            Subject=f"[{result['severity']}] 안전 위반 감지 - {result['device_id']}"
        )
        logger.info(f"알림 발송 완료: {result['device_id']}")
    except Exception as e:
        logger.error(f"알림 발송 실패: {e}")


def save_to_dynamodb(result: Dict):
    """DynamoDB에 결과 저장"""
    table = dynamodb.Table(TABLE_NAME)

    item = {
        'pk': result['device_id'],
        'sk': result['timestamp'],
        'frame_id': result['frame_id'],
        'detection_count': result['detection_count'],
        'has_violations': result['has_violations'],
        'violation_count': result['violation_count'],
        'severity': result['severity'],
        'ttl': int(datetime.now().timestamp()) + (7 * 24 * 60 * 60)  # 7일 후 만료
    }

    try:
        table.put_item(Item=item)
        logger.debug(f"DynamoDB 저장: {result['device_id']}")
    except Exception as e:
        logger.error(f"DynamoDB 저장 실패: {e}")
