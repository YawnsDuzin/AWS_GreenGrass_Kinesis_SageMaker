# 2.4 기타 연관 AWS 서비스

## 개요

공사현장 안전관리 시스템 구축에 활용할 수 있는 추가 AWS 서비스들을 소개합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    관련 AWS 서비스 맵                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    컴퓨팅 & 컨테이너                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Lambda    │  │     ECS     │  │  Fargate    │             │   │
│  │  │ (서버리스)  │  │ (컨테이너)  │  │ (서버리스)  │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AI/ML 서비스                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Rekognition │  │   Textract  │  │  Comprehend │             │   │
│  │  │ (이미지/영상)│  │ (문서 OCR) │  │ (자연어)    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    스토리지 & 데이터베이스                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │     S3      │  │  DynamoDB   │  │ Timestream  │             │   │
│  │  │ (객체저장)  │  │ (NoSQL)     │  │ (시계열)    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    분석 & 시각화                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │  QuickSight │  │    Athena   │  │    Glue     │             │   │
│  │  │ (대시보드)  │  │ (SQL 분석) │  │ (ETL)       │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    알림 & 통신                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │     SNS     │  │     SQS     │  │EventBridge  │             │   │
│  │  │ (푸시알림)  │  │ (메시지큐) │  │ (이벤트버스)│             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI/ML 서비스

### Amazon Rekognition

이미지 및 비디오 분석을 위한 완전관리형 서비스입니다.

```python
# rekognition_safety.py
import boto3

class SafetyAnalyzer:
    def __init__(self):
        self.client = boto3.client('rekognition')

    def detect_ppe(self, image_bytes):
        """개인 보호 장비(PPE) 감지"""
        response = self.client.detect_protective_equipment(
            Image={'Bytes': image_bytes},
            SummarizationAttributes={
                'MinConfidence': 80,
                'RequiredEquipmentTypes': [
                    'FACE_COVER',    # 마스크
                    'HAND_COVER',    # 장갑
                    'HEAD_COVER'     # 헬멧
                ]
            }
        )

        # 결과 분석
        summary = response['Summary']
        persons_without_equipment = summary['PersonsWithoutRequiredEquipment']
        persons_with_equipment = summary['PersonsWithRequiredEquipment']

        violations = []
        for person_idx in persons_without_equipment:
            person = response['Persons'][person_idx['PersonIndex']]
            violations.append({
                'person_index': person_idx['PersonIndex'],
                'bounding_box': person['BoundingBox'],
                'missing_equipment': self._get_missing_equipment(person)
            })

        return {
            'compliant_count': len(persons_with_equipment),
            'violation_count': len(persons_without_equipment),
            'violations': violations
        }

    def _get_missing_equipment(self, person):
        """누락된 장비 확인"""
        missing = []
        for body_part in person['BodyParts']:
            for equipment in body_part['EquipmentDetections']:
                if not equipment.get('CoversBodyPart', {}).get('Value', False):
                    missing.append(equipment['Type'])
        return missing

    def detect_faces(self, image_bytes):
        """얼굴 감지 (출입 관리용)"""
        response = self.client.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )

        faces = []
        for face in response['FaceDetails']:
            faces.append({
                'bounding_box': face['BoundingBox'],
                'confidence': face['Confidence'],
                'emotions': face['Emotions'],
                'age_range': face['AgeRange']
            })

        return faces

    def compare_faces(self, source_bytes, target_bytes):
        """얼굴 비교 (신원 확인)"""
        response = self.client.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=90
        )

        if response['FaceMatches']:
            return {
                'match': True,
                'similarity': response['FaceMatches'][0]['Similarity']
            }
        return {'match': False, 'similarity': 0}

    def start_video_analysis(self, bucket, video_key):
        """비디오 PPE 분석 시작"""
        response = self.client.start_protective_equipment_detection(
            Video={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': video_key
                }
            },
            NotificationChannel={
                'SNSTopicArn': 'arn:aws:sns:ap-northeast-2:123456789012:video-analysis',
                'RoleArn': 'arn:aws:iam::123456789012:role/RekognitionRole'
            },
            EquipmentTypes=['HEAD_COVER', 'HAND_COVER', 'FACE_COVER']
        )

        return response['JobId']
```

#### Rekognition 요금

| 기능 | 요금 | 비고 |
|------|------|------|
| PPE 감지 | $0.001/이미지 | 처음 100만 이미지 |
| 얼굴 감지 | $0.001/이미지 | 처음 100만 이미지 |
| 얼굴 비교 | $0.001/이미지 | 처음 100만 이미지 |
| 비디오 분석 | $0.10/분 | PPE 감지 |

---

### Amazon Textract

문서 및 양식에서 텍스트 추출을 위한 서비스입니다.

```python
# textract_documents.py
import boto3

class DocumentProcessor:
    def __init__(self):
        self.client = boto3.client('textract')

    def analyze_safety_document(self, document_bytes):
        """안전 점검표 분석"""
        response = self.client.analyze_document(
            Document={'Bytes': document_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )

        # 양식 필드 추출
        forms = {}
        for block in response['Blocks']:
            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    key = self._get_text(block, response['Blocks'])
                    value = self._get_value(block, response['Blocks'])
                    forms[key] = value

        return forms

    def extract_checklist(self, document_bytes):
        """안전 체크리스트 추출"""
        response = self.client.analyze_document(
            Document={'Bytes': document_bytes},
            FeatureTypes=['TABLES']
        )

        tables = []
        for block in response['Blocks']:
            if block['BlockType'] == 'TABLE':
                table = self._parse_table(block, response['Blocks'])
                tables.append(table)

        return tables

    def _get_text(self, block, blocks):
        """블록의 텍스트 추출"""
        text = ''
        if 'Relationships' in block:
            for rel in block['Relationships']:
                if rel['Type'] == 'CHILD':
                    for child_id in rel['Ids']:
                        child = next(b for b in blocks if b['Id'] == child_id)
                        if child['BlockType'] == 'WORD':
                            text += child['Text'] + ' '
        return text.strip()
```

---

## 스토리지 & 데이터베이스

### Amazon DynamoDB

이벤트 및 메타데이터 저장을 위한 NoSQL 데이터베이스입니다.

```python
# dynamodb_events.py
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import uuid

class SafetyEventStore:
    def __init__(self, table_name='safety-events'):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def put_event(self, site_id, event_data):
        """안전 이벤트 저장"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        item = {
            'pk': f'SITE#{site_id}',
            'sk': f'EVENT#{timestamp}#{event_id}',
            'event_id': event_id,
            'site_id': site_id,
            'timestamp': timestamp,
            'event_type': event_data['type'],
            'severity': event_data['severity'],
            'device_id': event_data['device_id'],
            'details': event_data['details'],
            'ttl': int((datetime.now() + timedelta(days=90)).timestamp())
        }

        self.table.put_item(Item=item)
        return event_id

    def get_events_by_site(self, site_id, start_time, end_time):
        """사이트별 이벤트 조회"""
        response = self.table.query(
            KeyConditionExpression=Key('pk').eq(f'SITE#{site_id}') &
                                   Key('sk').between(
                                       f'EVENT#{start_time}',
                                       f'EVENT#{end_time}'
                                   )
        )
        return response['Items']

    def get_daily_summary(self, site_id, date):
        """일일 요약 조회"""
        start = f'{date}T00:00:00'
        end = f'{date}T23:59:59'

        events = self.get_events_by_site(site_id, start, end)

        summary = {
            'total_events': len(events),
            'by_type': {},
            'by_severity': {}
        }

        for event in events:
            event_type = event['event_type']
            severity = event['severity']

            summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1

        return summary


# DynamoDB 테이블 스키마
"""
테이블: safety-events
├─ 파티션 키: pk (String)  - SITE#{site_id}
├─ 정렬 키: sk (String)    - EVENT#{timestamp}#{event_id}
└─ GSI:
   ├─ severity-index: severity (파티션 키), timestamp (정렬 키)
   └─ device-index: device_id (파티션 키), timestamp (정렬 키)
"""
```

### Amazon Timestream

IoT 센서 데이터를 위한 시계열 데이터베이스입니다.

```python
# timestream_sensors.py
import boto3
from datetime import datetime

class SensorDataStore:
    def __init__(self, database='construction-safety', table='sensor-data'):
        self.write_client = boto3.client('timestream-write')
        self.query_client = boto3.client('timestream-query')
        self.database = database
        self.table = table

    def write_sensor_data(self, device_id, measurements):
        """센서 데이터 저장"""
        current_time = str(int(datetime.now().timestamp() * 1000))

        records = []
        for measure_name, value in measurements.items():
            records.append({
                'Dimensions': [
                    {'Name': 'device_id', 'Value': device_id},
                    {'Name': 'site_id', 'Value': measurements.get('site_id', 'unknown')}
                ],
                'MeasureName': measure_name,
                'MeasureValue': str(value),
                'MeasureValueType': 'DOUBLE',
                'Time': current_time
            })

        self.write_client.write_records(
            DatabaseName=self.database,
            TableName=self.table,
            Records=records
        )

    def query_sensor_history(self, device_id, measure_name, hours=24):
        """센서 이력 조회"""
        query = f"""
            SELECT time, measure_value::double as value
            FROM "{self.database}"."{self.table}"
            WHERE device_id = '{device_id}'
              AND measure_name = '{measure_name}'
              AND time > ago({hours}h)
            ORDER BY time DESC
        """

        response = self.query_client.query(QueryString=query)

        data = []
        for row in response['Rows']:
            data.append({
                'time': row['Data'][0]['ScalarValue'],
                'value': float(row['Data'][1]['ScalarValue'])
            })

        return data

    def get_anomalies(self, device_id, threshold_std=2):
        """이상치 감지"""
        query = f"""
            WITH stats AS (
                SELECT
                    AVG(measure_value::double) as avg_val,
                    STDDEV(measure_value::double) as std_val
                FROM "{self.database}"."{self.table}"
                WHERE device_id = '{device_id}'
                  AND time > ago(24h)
            )
            SELECT time, measure_name, measure_value::double as value
            FROM "{self.database}"."{self.table}", stats
            WHERE device_id = '{device_id}'
              AND time > ago(1h)
              AND ABS(measure_value::double - avg_val) > {threshold_std} * std_val
        """

        response = self.query_client.query(QueryString=query)
        return response['Rows']
```

---

## 알림 & 통신

### Amazon SNS

다양한 채널로 알림을 전송하는 서비스입니다.

```python
# sns_alerting.py
import boto3
import json

class AlertService:
    def __init__(self):
        self.sns = boto3.client('sns')
        self.topics = {
            'critical': 'arn:aws:sns:ap-northeast-2:123456789012:critical-alerts',
            'warning': 'arn:aws:sns:ap-northeast-2:123456789012:warning-alerts',
            'info': 'arn:aws:sns:ap-northeast-2:123456789012:info-alerts'
        }

    def send_alert(self, severity, message, attributes=None):
        """심각도에 따른 알림 전송"""
        topic_arn = self.topics.get(severity, self.topics['info'])

        msg_attributes = {}
        if attributes:
            for key, value in attributes.items():
                msg_attributes[key] = {
                    'DataType': 'String',
                    'StringValue': str(value)
                }

        response = self.sns.publish(
            TopicArn=topic_arn,
            Subject=f'[{severity.upper()}] 공사현장 안전 알림',
            Message=json.dumps(message, ensure_ascii=False, indent=2),
            MessageAttributes=msg_attributes
        )

        return response['MessageId']

    def send_sms(self, phone_number, message):
        """SMS 직접 발송"""
        response = self.sns.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': 'SAFETY'
                },
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        return response['MessageId']


# Lambda와 SNS 통합 예시
def alert_handler(event, context):
    """Kinesis 이벤트에서 알림 트리거"""
    alert_service = AlertService()

    for record in event['Records']:
        payload = json.loads(base64.b64decode(record['kinesis']['data']))

        if payload['event_type'] == 'SAFETY_VIOLATION':
            severity = 'critical' if payload['severity'] == 'HIGH' else 'warning'

            message = {
                'site': payload['site_id'],
                'device': payload['device_id'],
                'violation': payload['violation_type'],
                'timestamp': payload['timestamp'],
                'details': payload.get('details', {})
            }

            alert_service.send_alert(severity, message, {
                'site_id': payload['site_id'],
                'violation_type': payload['violation_type']
            })
```

### Amazon EventBridge

이벤트 기반 아키텍처를 위한 서버리스 이벤트 버스입니다.

```python
# eventbridge_rules.py
import boto3
import json

def create_safety_rules():
    events = boto3.client('events')

    # 규칙 1: 고위험 이벤트 즉시 처리
    events.put_rule(
        Name='high-severity-safety-events',
        EventPattern=json.dumps({
            'source': ['construction.safety'],
            'detail-type': ['Safety Violation'],
            'detail': {
                'severity': ['HIGH', 'CRITICAL']
            }
        }),
        State='ENABLED',
        Description='고위험 안전 이벤트 처리'
    )

    # 타겟 1: Lambda 함수
    events.put_targets(
        Rule='high-severity-safety-events',
        Targets=[
            {
                'Id': 'alert-lambda',
                'Arn': 'arn:aws:lambda:ap-northeast-2:123456789012:function:safety-alert',
                'Input': json.dumps({'action': 'immediate_alert'})
            },
            {
                'Id': 'incident-queue',
                'Arn': 'arn:aws:sqs:ap-northeast-2:123456789012:incident-queue'
            }
        ]
    )

    # 규칙 2: 일일 리포트 생성
    events.put_rule(
        Name='daily-safety-report',
        ScheduleExpression='cron(0 9 * * ? *)',  # 매일 오전 9시
        State='ENABLED',
        Description='일일 안전 리포트 생성'
    )

    events.put_targets(
        Rule='daily-safety-report',
        Targets=[
            {
                'Id': 'report-generator',
                'Arn': 'arn:aws:lambda:ap-northeast-2:123456789012:function:generate-report'
            }
        ]
    )
```

---

## 분석 & 시각화

### Amazon QuickSight

비즈니스 인텔리전스 대시보드 서비스입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    QuickSight 대시보드 구성                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  실시간 안전 현황 대시보드                                       │   │
│  │                                                                  │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │   │
│  │  │ 현재 작업자 수 │  │  금일 위반 수  │  │ 위험도 점수   │        │   │
│  │  │    ████████   │  │   █████████   │  │  ██████████   │        │   │
│  │  │      127명    │  │     23건      │  │     78점      │        │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘        │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────────┐    │   │
│  │  │  시간대별 위반 추이                                      │    │   │
│  │  │       ▲                                                  │    │   │
│  │  │      ╱│╲    ╱╲                                          │    │   │
│  │  │     ╱ │ ╲  ╱  ╲                                         │    │   │
│  │  │    ╱  │  ╲╱    ╲                                        │    │   │
│  │  │   ╱   │   ╲     ╲                                       │    │   │
│  │  │  ────┼────────────────────────────▶                     │    │   │
│  │  │      06   09   12   15   18   21                        │    │   │
│  │  └─────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────┐   │   │
│  │  │  위반 유형별 분포   │  │     구역별 위험도 히트맵        │   │   │
│  │  │  ┌───────┐         │  │  ┌─────────────────────────┐    │   │   │
│  │  │  │ 헬멧  │ 45%     │  │  │  A구역   B구역   C구역  │    │   │   │
│  │  │  │ 미착용│         │  │  │  ████    ████    ████   │    │   │   │
│  │  │  └───────┘         │  │  │  높음    중간    낮음   │    │   │   │
│  │  │  ┌───────┐         │  │  └─────────────────────────┘    │   │   │
│  │  │  │ 조끼  │ 30%     │  │                                  │   │   │
│  │  │  │ 미착용│         │  │                                  │   │   │
│  │  │  └───────┘         │  │                                  │   │   │
│  │  └─────────────────────┘  └─────────────────────────────────┘   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Amazon Athena

S3 데이터에 대한 SQL 쿼리 서비스입니다.

```sql
-- Athena 쿼리 예시

-- 1. 일일 위반 통계
SELECT
    date_trunc('day', from_iso8601_timestamp(timestamp)) as date,
    violation_type,
    COUNT(*) as violation_count,
    COUNT(DISTINCT device_id) as affected_devices
FROM safety_events
WHERE timestamp >= '2024-01-01'
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;

-- 2. 시간대별 위험 패턴
SELECT
    hour(from_iso8601_timestamp(timestamp)) as hour_of_day,
    violation_type,
    COUNT(*) as count,
    AVG(CAST(json_extract_scalar(details, '$.confidence') AS DOUBLE)) as avg_confidence
FROM safety_events
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- 3. 반복 위반자 식별
SELECT
    worker_id,
    COUNT(*) as total_violations,
    COUNT(DISTINCT date_trunc('day', from_iso8601_timestamp(timestamp))) as violation_days,
    array_agg(DISTINCT violation_type) as violation_types
FROM safety_events
WHERE worker_id IS NOT NULL
  AND timestamp >= date_add('day', -30, current_date)
GROUP BY 1
HAVING COUNT(*) > 5
ORDER BY 2 DESC;

-- 4. 위험 구역 분석
SELECT
    zone_id,
    COUNT(*) as incidents,
    COUNT(DISTINCT worker_id) as affected_workers,
    SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) as high_severity_count
FROM safety_events
WHERE zone_id IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
```

---

## AWS Lambda 활용

### 안전 이벤트 처리 Lambda

```python
# lambda_functions.py
import boto3
import json
import os
from datetime import datetime

# 환경 변수
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
SNS_TOPIC = os.environ['SNS_TOPIC_ARN']
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
sagemaker_runtime = boto3.client('sagemaker-runtime')

def process_safety_event(event, context):
    """안전 이벤트 종합 처리 Lambda"""
    table = dynamodb.Table(DYNAMODB_TABLE)

    results = {
        'processed': 0,
        'alerts_sent': 0,
        'errors': []
    }

    for record in event['Records']:
        try:
            # Kinesis/SQS 레코드 파싱
            if 'kinesis' in record:
                payload = json.loads(
                    base64.b64decode(record['kinesis']['data']).decode('utf-8')
                )
            elif 'body' in record:
                payload = json.loads(record['body'])
            else:
                continue

            # 이벤트 저장
            event_id = save_event(table, payload)

            # 위험도 평가
            risk_score = evaluate_risk(payload)

            # 고위험 이벤트 알림
            if risk_score >= 80:
                send_alert(payload, risk_score)
                results['alerts_sent'] += 1

            results['processed'] += 1

        except Exception as e:
            results['errors'].append(str(e))

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }


def save_event(table, payload):
    """DynamoDB에 이벤트 저장"""
    event_id = f"{payload['device_id']}_{payload['timestamp']}"

    table.put_item(Item={
        'pk': f"SITE#{payload.get('site_id', 'unknown')}",
        'sk': f"EVENT#{payload['timestamp']}",
        'event_id': event_id,
        **payload
    })

    return event_id


def evaluate_risk(payload):
    """위험도 점수 계산"""
    base_score = {
        'NO_HELMET': 90,
        'NO_VEST': 60,
        'NO_HARNESS': 95,
        'DANGER_ZONE': 85,
        'FALL_DETECTED': 100
    }.get(payload.get('violation_type'), 50)

    # 추가 요소 반영
    if payload.get('confidence', 0) > 0.9:
        base_score += 5

    # 반복 위반 체크 (별도 함수 필요)
    # if is_repeat_violation(payload):
    #     base_score += 10

    return min(base_score, 100)


def send_alert(payload, risk_score):
    """SNS 알림 발송"""
    message = {
        'alert_type': 'SAFETY_VIOLATION',
        'risk_score': risk_score,
        'site_id': payload.get('site_id'),
        'device_id': payload.get('device_id'),
        'violation_type': payload.get('violation_type'),
        'timestamp': payload.get('timestamp'),
        'message': f"위험도 {risk_score}점: {payload.get('violation_type')} 감지"
    }

    sns.publish(
        TopicArn=SNS_TOPIC,
        Subject=f"[긴급] 안전 위반 감지 - 위험도 {risk_score}",
        Message=json.dumps(message, ensure_ascii=False),
        MessageAttributes={
            'risk_score': {
                'DataType': 'Number',
                'StringValue': str(risk_score)
            }
        }
    )
```

---

## 서비스별 요금 요약

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    관련 서비스 월간 예상 비용                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AI/ML 서비스                                                            │
│  ├─ Rekognition (PPE): 1M 이미지 × $0.001 = $1,000                     │
│  └─ Textract: 10K 페이지 × $0.015 = $150                               │
│                                                                         │
│  스토리지 & DB                                                           │
│  ├─ DynamoDB: 10GB + 1M 요청 ≈ $30                                     │
│  ├─ Timestream: 10GB 수집 + 10GB 저장 ≈ $50                            │
│  └─ S3: 100GB 저장 + 전송 ≈ $10                                        │
│                                                                         │
│  컴퓨팅                                                                  │
│  ├─ Lambda: 1M 요청 × 1초 ≈ $20                                        │
│  └─ Step Functions: 10K 전환 ≈ $2.50                                   │
│                                                                         │
│  알림 & 분석                                                             │
│  ├─ SNS: 10K 알림 ≈ $5                                                 │
│  ├─ QuickSight: 1 Author + 10 Reader ≈ $34                             │
│  └─ Athena: 100GB 스캔 × $5/TB ≈ $0.50                                 │
│                                                                         │
│  예상 총액: 약 $1,300/월 (약 1,700,000원)                               │
│  ※ 사용량에 따라 크게 변동 가능                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [전체 아키텍처 설계](../03-integration/01-architecture-design.md)
2. [GreenGrass-Kinesis 연동](../03-integration/02-greengrass-kinesis.md)
