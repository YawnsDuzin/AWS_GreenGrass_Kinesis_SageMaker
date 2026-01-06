#!/usr/bin/env python3
"""
Kinesis Firehose 데이터 변환기
S3에 저장하기 전 데이터 변환 및 강화
"""

import json
import base64
from datetime import datetime
from typing import Dict, List, Any


def transform_record(record: Dict) -> Dict:
    """
    단일 레코드 변환

    Args:
        record: 원본 Kinesis 레코드

    Returns:
        변환된 레코드
    """
    # Base64 디코딩
    payload = base64.b64decode(record['data']).decode('utf-8')
    data = json.loads(payload)

    # 데이터 강화
    enriched_data = enrich_data(data)

    # 파티셔닝을 위한 타임스탬프 추가
    enriched_data['processing_timestamp'] = datetime.now().isoformat()
    enriched_data['year'] = datetime.now().strftime('%Y')
    enriched_data['month'] = datetime.now().strftime('%m')
    enriched_data['day'] = datetime.now().strftime('%d')
    enriched_data['hour'] = datetime.now().strftime('%H')

    # 결과 인코딩 (줄바꿈 추가 - S3에서 JSON Lines 형식)
    result = json.dumps(enriched_data) + '\n'

    return {
        'recordId': record['recordId'],
        'result': 'Ok',
        'data': base64.b64encode(result.encode('utf-8')).decode('utf-8')
    }


def enrich_data(data: Dict) -> Dict:
    """
    데이터 강화

    Args:
        data: 원본 데이터

    Returns:
        강화된 데이터
    """
    enriched = data.copy()

    # 감지 결과 요약
    detections = data.get('detections', [])

    # 클래스별 카운트
    class_counts = {}
    for detection in detections:
        class_name = detection.get('class_name', 'unknown')
        class_counts[class_name] = class_counts.get(class_name, 0) + 1

    enriched['detection_summary'] = {
        'total_detections': len(detections),
        'class_counts': class_counts,
        'has_violations': any('no_' in d.get('class_name', '') for d in detections)
    }

    # 평균 신뢰도
    if detections:
        avg_confidence = sum(d.get('confidence', 0) for d in detections) / len(detections)
        enriched['detection_summary']['avg_confidence'] = round(avg_confidence, 3)

    # 위반 유형 분류
    violations = [d for d in detections if 'no_' in d.get('class_name', '')]
    if violations:
        enriched['violation_types'] = list(set(d.get('class_name') for d in violations))
        enriched['violation_count'] = len(violations)
        enriched['severity'] = 'HIGH' if len(violations) > 1 else 'MEDIUM'
    else:
        enriched['violation_types'] = []
        enriched['violation_count'] = 0
        enriched['severity'] = 'LOW'

    return enriched


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Lambda 핸들러 (Kinesis Firehose 변환)

    Args:
        event: Firehose 이벤트
        context: Lambda 컨텍스트

    Returns:
        변환된 레코드 배치
    """
    output = []

    for record in event['records']:
        try:
            transformed = transform_record(record)
            output.append(transformed)
        except Exception as e:
            # 변환 실패 시 원본 유지
            output.append({
                'recordId': record['recordId'],
                'result': 'ProcessingFailed',
                'data': record['data']
            })

    return {'records': output}


# 로컬 테스트
if __name__ == "__main__":
    # 테스트 데이터
    test_data = {
        "device_id": "rpi4-001",
        "timestamp": "2024-01-15T10:30:00Z",
        "detections": [
            {"class_name": "person", "confidence": 0.95},
            {"class_name": "hardhat", "confidence": 0.88},
            {"class_name": "no_safety_vest", "confidence": 0.76}
        ]
    }

    # Base64 인코딩
    encoded = base64.b64encode(json.dumps(test_data).encode()).decode()

    # 테스트 이벤트
    test_event = {
        "records": [
            {"recordId": "test-1", "data": encoded}
        ]
    }

    result = lambda_handler(test_event, None)

    # 결과 확인
    for record in result['records']:
        decoded = base64.b64decode(record['data']).decode()
        print(json.dumps(json.loads(decoded), indent=2, ensure_ascii=False))
