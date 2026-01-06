# Part 4: Amazon Kinesis 설정

이 파트에서는 실시간 데이터 스트리밍을 위한 Kinesis Data Streams, Firehose, 그리고 DynamoDB를 설정합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] Kinesis Data Streams 생성
- [x] Kinesis Data Firehose 설정 (S3 전송)
- [x] DynamoDB 테이블 생성
- [x] S3 버킷 생성
- [x] Lambda 함수 배포
- [x] 연동 테스트

---

## 1. S3 버킷 생성

### 1.1 데이터 저장용 버킷

```bash
# 변수 설정
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
REGION="ap-northeast-2"
BUCKET_NAME="ppe-detection-data-${ACCOUNT_ID}"

# 버킷 생성
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}

# 버전 관리 활성화
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# 퍼블릭 액세스 차단
aws s3api put-public-access-block \
    --bucket ${BUCKET_NAME} \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "버킷 생성 완료: ${BUCKET_NAME}"
```

### 1.2 모델 저장용 버킷

```bash
MODEL_BUCKET="ppe-detection-models-${ACCOUNT_ID}"

aws s3 mb s3://${MODEL_BUCKET} --region ${REGION}

echo "모델 버킷 생성 완료: ${MODEL_BUCKET}"
```

---

## 2. Kinesis Data Streams 생성

### 2.1 AWS CLI로 생성

```bash
# 스트림 생성
aws kinesis create-stream \
    --stream-name ppe-detection-stream \
    --shard-count 2 \
    --region ap-northeast-2

# 생성 확인 (ACTIVE 상태까지 대기)
aws kinesis describe-stream \
    --stream-name ppe-detection-stream \
    --query 'StreamDescription.StreamStatus'
```

### 2.2 AWS 콘솔에서 확인

1. AWS 콘솔 → **Kinesis** 검색
2. **데이터 스트림** 메뉴
3. `ppe-detection-stream` 확인

스트림 정보:
```
스트림 이름: ppe-detection-stream
상태: 활성
샤드: 2개
데이터 보존 기간: 24시간
```

### 2.3 스트림 ARN 저장

```bash
STREAM_ARN=$(aws kinesis describe-stream \
    --stream-name ppe-detection-stream \
    --query 'StreamDescription.StreamARN' \
    --output text)

echo "스트림 ARN: ${STREAM_ARN}"
```

---

## 3. DynamoDB 테이블 생성

### 3.1 이벤트 저장 테이블

```bash
# 테이블 생성
aws dynamodb create-table \
    --table-name ppe-safety-events \
    --attribute-definitions \
        AttributeName=pk,AttributeType=S \
        AttributeName=sk,AttributeType=S \
        AttributeName=severity,AttributeType=S \
    --key-schema \
        AttributeName=pk,KeyType=HASH \
        AttributeName=sk,KeyType=RANGE \
    --global-secondary-indexes \
        "[{
            \"IndexName\": \"severity-index\",
            \"KeySchema\": [{\"AttributeName\":\"severity\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"sk\",\"KeyType\":\"RANGE\"}],
            \"Projection\": {\"ProjectionType\":\"ALL\"}
        }]" \
    --billing-mode PAY_PER_REQUEST \
    --region ap-northeast-2

# 테이블 상태 확인
aws dynamodb describe-table \
    --table-name ppe-safety-events \
    --query 'Table.TableStatus'
```

### 3.2 TTL 설정

```bash
# 7일 후 자동 삭제
aws dynamodb update-time-to-live \
    --table-name ppe-safety-events \
    --time-to-live-specification "Enabled=true, AttributeName=ttl"
```

---

## 4. Kinesis Data Firehose 생성

### 4.1 IAM 역할 생성 (Firehose용)

```bash
# 신뢰 정책 생성
cat > firehose-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "firehose.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 역할 생성
aws iam create-role \
    --role-name ppe-firehose-role \
    --assume-role-policy-document file://firehose-trust-policy.json

# 정책 생성
cat > firehose-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:DescribeStream",
        "kinesis:GetShardIterator",
        "kinesis:GetRecords",
        "kinesis:ListShards"
      ],
      "Resource": "${STREAM_ARN}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:PutLogEvents",
        "logs:CreateLogGroup",
        "logs:CreateLogStream"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# 정책 연결
aws iam put-role-policy \
    --role-name ppe-firehose-role \
    --policy-name firehose-s3-access \
    --policy-document file://firehose-policy.json

# 역할 ARN 저장
FIREHOSE_ROLE_ARN=$(aws iam get-role --role-name ppe-firehose-role --query 'Role.Arn' --output text)
echo "Firehose 역할 ARN: ${FIREHOSE_ROLE_ARN}"

# 임시 파일 정리
rm firehose-trust-policy.json firehose-policy.json
```

### 4.2 Firehose 전송 스트림 생성

```bash
# Firehose 생성
aws firehose create-delivery-stream \
    --delivery-stream-name ppe-detection-to-s3 \
    --delivery-stream-type KinesisStreamAsSource \
    --kinesis-stream-source-configuration \
        "KinesisStreamARN=${STREAM_ARN},RoleARN=${FIREHOSE_ROLE_ARN}" \
    --s3-destination-configuration \
        "RoleARN=${FIREHOSE_ROLE_ARN},BucketARN=arn:aws:s3:::${BUCKET_NAME},Prefix=raw/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/,ErrorOutputPrefix=errors/,BufferingHints={SizeInMBs=5,IntervalInSeconds=300},CompressionFormat=GZIP"

# 상태 확인
aws firehose describe-delivery-stream \
    --delivery-stream-name ppe-detection-to-s3 \
    --query 'DeliveryStreamDescription.DeliveryStreamStatus'
```

---

## 5. Lambda 함수 배포

### 5.1 Lambda 코드 준비

```bash
# 작업 디렉토리 생성
mkdir -p ~/lambda-deployment
cd ~/lambda-deployment

# Lambda 핸들러 코드 생성
cat > handler.py << 'EOF'
import json
import base64
import boto3
import os
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'ppe-safety-events')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')


def lambda_handler(event, context):
    """Kinesis 이벤트 처리 Lambda"""

    logger.info(f"수신된 레코드 수: {len(event.get('Records', []))}")

    table = dynamodb.Table(TABLE_NAME)
    processed = 0
    violations = 0

    for record in event.get('Records', []):
        try:
            # Kinesis 데이터 디코딩
            payload = base64.b64decode(record['kinesis']['data'])
            data = json.loads(payload.decode('utf-8'))

            # 데이터 처리
            result = process_detection(data)

            # DynamoDB 저장
            save_to_dynamodb(table, result)

            # 위반 시 알림
            if result.get('has_violations'):
                violations += 1
                if SNS_TOPIC_ARN:
                    send_alert(result)

            processed += 1

        except Exception as e:
            logger.error(f"레코드 처리 오류: {e}")

    logger.info(f"처리 완료: {processed}개, 위반: {violations}개")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed,
            'violations': violations
        })
    }


def process_detection(data):
    """감지 데이터 처리"""
    detections = data.get('detections', [])

    # 위반 확인
    violations = [d for d in detections if 'no_' in d.get('class_name', '')]

    severity = 'NONE'
    if len(violations) >= 2:
        severity = 'HIGH'
    elif len(violations) == 1:
        severity = 'MEDIUM'
    elif detections:
        severity = 'LOW'

    return {
        'device_id': data.get('device_id', 'unknown'),
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
        'detection_count': len(detections),
        'has_violations': len(violations) > 0,
        'violation_count': len(violations),
        'violation_types': list(set(v.get('class_name') for v in violations)),
        'severity': severity
    }


def save_to_dynamodb(table, result):
    """DynamoDB에 저장"""
    item = {
        'pk': result['device_id'],
        'sk': result['timestamp'],
        'detection_count': result['detection_count'],
        'has_violations': result['has_violations'],
        'violation_count': result['violation_count'],
        'severity': result['severity'],
        'ttl': int(datetime.now().timestamp()) + (7 * 24 * 60 * 60)
    }

    # Decimal 변환
    item = json.loads(json.dumps(item), parse_float=Decimal)

    table.put_item(Item=item)


def send_alert(result):
    """SNS 알림 발송"""
    message = {
        'alert_type': 'SAFETY_VIOLATION',
        'device_id': result['device_id'],
        'severity': result['severity'],
        'violation_types': result['violation_types'],
        'timestamp': result['timestamp']
    }

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message, ensure_ascii=False),
        Subject=f"[{result['severity']}] 안전 위반 감지 - {result['device_id']}"
    )

    logger.info(f"알림 발송: {result['device_id']}")
EOF

# 패키지 생성
zip handler.zip handler.py

echo "Lambda 패키지 생성 완료"
```

### 5.2 Lambda 함수 생성

```bash
# Lambda 실행 역할 ARN
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name ConstructionSafety-LambdaRole --query 'Role.Arn' --output text)

# Lambda 함수 생성
aws lambda create-function \
    --function-name ppe-kinesis-processor \
    --runtime python3.11 \
    --handler handler.lambda_handler \
    --role ${LAMBDA_ROLE_ARN} \
    --zip-file fileb://handler.zip \
    --timeout 60 \
    --memory-size 256 \
    --environment "Variables={DYNAMODB_TABLE=ppe-safety-events,SNS_TOPIC_ARN=}" \
    --region ap-northeast-2

echo "Lambda 함수 생성 완료"
```

### 5.3 Kinesis 트리거 추가

```bash
# 이벤트 소스 매핑 생성
aws lambda create-event-source-mapping \
    --function-name ppe-kinesis-processor \
    --event-source-arn ${STREAM_ARN} \
    --starting-position LATEST \
    --batch-size 100 \
    --maximum-batching-window-in-seconds 5

echo "Kinesis 트리거 추가 완료"
```

---

## 6. IoT Core 규칙 생성

IoT Core에서 Kinesis로 자동 전달:

### 6.1 규칙 생성

```bash
# IoT 규칙 역할 생성
cat > iot-rule-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "iot.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
    --role-name ppe-iot-kinesis-role \
    --assume-role-policy-document file://iot-rule-trust-policy.json

# 정책 연결
cat > iot-kinesis-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ],
      "Resource": "${STREAM_ARN}"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name ppe-iot-kinesis-role \
    --policy-name kinesis-put \
    --policy-document file://iot-kinesis-policy.json

IOT_KINESIS_ROLE_ARN=$(aws iam get-role --role-name ppe-iot-kinesis-role --query 'Role.Arn' --output text)

# 임시 파일 정리
rm iot-rule-trust-policy.json iot-kinesis-policy.json
```

### 6.2 IoT 규칙 생성

```bash
# 규칙 생성
aws iot create-topic-rule \
    --rule-name ppe_detection_to_kinesis \
    --topic-rule-payload "{
        \"sql\": \"SELECT * FROM 'construction/safety/+/detections'\",
        \"actions\": [{
            \"kinesis\": {
                \"streamName\": \"ppe-detection-stream\",
                \"partitionKey\": \"\${device_id}\",
                \"roleArn\": \"${IOT_KINESIS_ROLE_ARN}\"
            }
        }],
        \"ruleDisabled\": false
    }"

echo "IoT 규칙 생성 완료"
```

---

## 7. 연동 테스트

### 7.1 테스트 데이터 발행 (Raspberry Pi)

```bash
# Raspberry Pi에서 실행
cat > ~/test_kinesis.py << 'EOF'
#!/usr/bin/env python3
import json
import time
import boto3
from datetime import datetime

kinesis = boto3.client('kinesis', region_name='ap-northeast-2')
stream_name = 'ppe-detection-stream'

# 테스트 데이터
test_data = {
    "device_id": "ppe-detector-rpi4",
    "timestamp": datetime.now().isoformat(),
    "frame_id": 1,
    "detections": [
        {"class_name": "person", "confidence": 0.95, "bbox": [100, 100, 200, 300]},
        {"class_name": "no_hardhat", "confidence": 0.82, "bbox": [110, 80, 60, 40]}
    ]
}

# Kinesis로 전송
response = kinesis.put_record(
    StreamName=stream_name,
    Data=json.dumps(test_data).encode('utf-8'),
    PartitionKey=test_data['device_id']
)

print(f"전송 완료!")
print(f"ShardId: {response['ShardId']}")
print(f"SequenceNumber: {response['SequenceNumber']}")
print(f"데이터: {json.dumps(test_data, indent=2)}")
EOF

python3 ~/test_kinesis.py
```

### 7.2 DynamoDB 확인

```bash
# 저장된 데이터 조회
aws dynamodb scan \
    --table-name ppe-safety-events \
    --limit 5
```

### 7.3 S3 확인 (Firehose 배치 후)

```bash
# 5분 후 확인 (Firehose 버퍼링)
aws s3 ls s3://${BUCKET_NAME}/raw/ --recursive
```

### 7.4 Lambda 로그 확인

```bash
# CloudWatch 로그 확인
aws logs tail /aws/lambda/ppe-kinesis-processor --since 1h
```

---

## 8. 모니터링 대시보드 (선택)

### 8.1 CloudWatch 지표 확인

```bash
# Kinesis 지표
aws cloudwatch get-metric-statistics \
    --namespace AWS/Kinesis \
    --metric-name IncomingRecords \
    --dimensions Name=StreamName,Value=ppe-detection-stream \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum
```

---

## 9. 리소스 정리 (선택)

개발 중 비용 절감을 위한 일시 중지:

```bash
# Kinesis 스트림 삭제 (테스트 후)
# aws kinesis delete-stream --stream-name ppe-detection-stream

# Firehose 삭제
# aws firehose delete-delivery-stream --delivery-stream-name ppe-detection-to-s3

# 주의: 프로덕션 데이터는 백업 후 삭제
```

---

## ✅ 체크리스트

이 파트를 완료하면 다음 항목들이 준비되어야 합니다:

- [ ] S3 버킷 생성 완료
  - [ ] `ppe-detection-data-{ACCOUNT_ID}`
  - [ ] `ppe-detection-models-{ACCOUNT_ID}`
- [ ] Kinesis Data Stream `ppe-detection-stream` 생성 (ACTIVE)
- [ ] DynamoDB 테이블 `ppe-safety-events` 생성
- [ ] Kinesis Firehose `ppe-detection-to-s3` 생성
- [ ] Lambda 함수 `ppe-kinesis-processor` 배포
- [ ] IoT Core 규칙 `ppe_detection_to_kinesis` 생성
- [ ] 테스트 데이터 전송 및 확인 완료

---

## 🔧 문제 해결

### Q: Kinesis PutRecord 실패

```bash
# 스트림 상태 확인
aws kinesis describe-stream --stream-name ppe-detection-stream

# IAM 권한 확인
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::ACCOUNT_ID:user/ppe-detection-admin \
    --action-names kinesis:PutRecord \
    --resource-arns ${STREAM_ARN}
```

### Q: Lambda 함수 오류

```bash
# 로그 확인
aws logs tail /aws/lambda/ppe-kinesis-processor --follow

# 함수 테스트
aws lambda invoke \
    --function-name ppe-kinesis-processor \
    --payload '{"Records":[]}' \
    response.json
```

### Q: Firehose에서 S3로 데이터가 안 감

```bash
# Firehose 상태 확인
aws firehose describe-delivery-stream \
    --delivery-stream-name ppe-detection-to-s3

# 버퍼링 간격이 5분이므로 기다리기
# 또는 버퍼 크기/간격 줄이기
```

---

## 📚 다음 단계

[Part 5: SageMaker 모델 학습](./05-sagemaker-training.md)으로 이동하여
YOLOv8 기반 PPE 감지 모델을 학습합니다.
