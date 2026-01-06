# Part 9: 테스트 및 모니터링

이 파트에서는 전체 시스템을 테스트하고 CloudWatch를 통한 모니터링을 설정합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] End-to-End 시스템 테스트
- [x] 성능 테스트
- [x] CloudWatch 대시보드 구성
- [x] 알람 설정
- [x] 로그 분석
- [x] 비용 모니터링

---

## 1. End-to-End 테스트

### 1.1 전체 시스템 테스트 체크리스트

```bash
#!/bin/bash
# e2e_test.sh - End-to-End 테스트 스크립트

echo "========================================="
echo "  PPE 감지 시스템 E2E 테스트"
echo "========================================="
echo ""

# 변수 설정
THING_NAME="ppe-detector-rpi4"
STREAM_NAME="ppe-detection-stream"
TABLE_NAME="ppe-safety-events"
REGION="ap-northeast-2"

echo "1️⃣ GreenGrass Core 상태 확인..."
GG_STATUS=$(aws greengrassv2 get-core-device \
    --core-device-thing-name ${THING_NAME} \
    --query 'status' --output text 2>/dev/null || echo "ERROR")

if [ "$GG_STATUS" == "HEALTHY" ]; then
    echo "   ✅ GreenGrass Core: 정상 (HEALTHY)"
else
    echo "   ❌ GreenGrass Core: ${GG_STATUS}"
fi

echo ""
echo "2️⃣ PPE Detector 컴포넌트 상태..."
# Raspberry Pi에서 확인 필요
echo "   ℹ️  Raspberry Pi에서 실행: sudo greengrass-cli component list"

echo ""
echo "3️⃣ Kinesis 스트림 상태..."
KINESIS_STATUS=$(aws kinesis describe-stream \
    --stream-name ${STREAM_NAME} \
    --query 'StreamDescription.StreamStatus' --output text 2>/dev/null || echo "ERROR")

if [ "$KINESIS_STATUS" == "ACTIVE" ]; then
    echo "   ✅ Kinesis Stream: 활성 (ACTIVE)"
else
    echo "   ❌ Kinesis Stream: ${KINESIS_STATUS}"
fi

echo ""
echo "4️⃣ 최근 Kinesis 레코드 확인..."
SHARD_ID=$(aws kinesis describe-stream \
    --stream-name ${STREAM_NAME} \
    --query 'StreamDescription.Shards[0].ShardId' --output text)

ITERATOR=$(aws kinesis get-shard-iterator \
    --stream-name ${STREAM_NAME} \
    --shard-id ${SHARD_ID} \
    --shard-iterator-type LATEST \
    --query 'ShardIterator' --output text)

RECORD_COUNT=$(aws kinesis get-records \
    --shard-iterator ${ITERATOR} \
    --query 'length(Records)' --output text)

echo "   ℹ️  최근 레코드 수: ${RECORD_COUNT}"

echo ""
echo "5️⃣ DynamoDB 테이블 상태..."
ITEM_COUNT=$(aws dynamodb scan \
    --table-name ${TABLE_NAME} \
    --select COUNT \
    --query 'Count' --output text 2>/dev/null || echo "0")

echo "   ℹ️  저장된 이벤트 수: ${ITEM_COUNT}"

# 최근 위반 건수
VIOLATION_COUNT=$(aws dynamodb scan \
    --table-name ${TABLE_NAME} \
    --filter-expression "has_violations = :v" \
    --expression-attribute-values '{":v": {"BOOL": true}}' \
    --select COUNT \
    --query 'Count' --output text 2>/dev/null || echo "0")

echo "   ℹ️  위반 이벤트 수: ${VIOLATION_COUNT}"

echo ""
echo "6️⃣ Lambda 함수 상태..."
for func in "ppe-kinesis-processor" "ppe-alert-sender"; do
    STATUS=$(aws lambda get-function \
        --function-name ${func} \
        --query 'Configuration.State' --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "$STATUS" == "Active" ]; then
        echo "   ✅ ${func}: Active"
    else
        echo "   ❌ ${func}: ${STATUS}"
    fi
done

echo ""
echo "7️⃣ SNS 토픽 상태..."
SNS_ARN=$(aws sns list-topics \
    --query "Topics[?contains(TopicArn, 'ppe-safety-alerts')].TopicArn" \
    --output text)

if [ -n "$SNS_ARN" ]; then
    SUB_COUNT=$(aws sns list-subscriptions-by-topic \
        --topic-arn ${SNS_ARN} \
        --query 'length(Subscriptions)' --output text)
    echo "   ✅ SNS 토픽 존재, 구독 수: ${SUB_COUNT}"
else
    echo "   ❌ SNS 토픽 없음"
fi

echo ""
echo "========================================="
echo "           테스트 완료"
echo "========================================="
```

### 1.2 테스트 데이터 생성

```python
#!/usr/bin/env python3
"""
테스트 데이터 생성기
Kinesis로 샘플 감지 데이터 전송
"""

import boto3
import json
import time
from datetime import datetime
import random

kinesis = boto3.client('kinesis', region_name='ap-northeast-2')
STREAM_NAME = 'ppe-detection-stream'

def generate_test_data(device_id: str, with_violation: bool = False):
    """테스트 데이터 생성"""

    detections = [
        {"class_name": "person", "confidence": random.uniform(0.8, 0.99), "bbox": [100, 100, 200, 300]}
    ]

    if with_violation:
        # 위반 추가
        violation_type = random.choice(['no_hardhat', 'no_safety_vest'])
        detections.append({
            "class_name": violation_type,
            "confidence": random.uniform(0.7, 0.95),
            "bbox": [110, 80, 60, 40]
        })
    else:
        # 정상 장비
        detections.extend([
            {"class_name": "hardhat", "confidence": random.uniform(0.8, 0.95), "bbox": [110, 80, 60, 40]},
            {"class_name": "safety_vest", "confidence": random.uniform(0.8, 0.95), "bbox": [105, 110, 90, 120]}
        ])

    return {
        "device_id": device_id,
        "timestamp": datetime.now().isoformat(),
        "frame_id": random.randint(1, 10000),
        "inference_ms": random.uniform(70, 120),
        "detections": detections
    }


def send_test_data(count: int = 10, violation_rate: float = 0.3):
    """테스트 데이터 전송"""

    print(f"테스트 데이터 {count}개 전송 중...")

    for i in range(count):
        with_violation = random.random() < violation_rate
        data = generate_test_data(
            device_id="test-rpi4-001",
            with_violation=with_violation
        )

        response = kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(data).encode('utf-8'),
            PartitionKey=data['device_id']
        )

        status = "⚠️ 위반" if with_violation else "✅ 정상"
        print(f"  [{i+1}/{count}] {status} - SequenceNumber: {response['SequenceNumber'][:20]}...")

        time.sleep(0.5)

    print(f"\n전송 완료: {count}개 레코드")


if __name__ == "__main__":
    send_test_data(count=20, violation_rate=0.4)
```

---

## 2. 성능 테스트

### 2.1 Raspberry Pi 성능 측정

```python
#!/usr/bin/env python3
"""
Raspberry Pi 성능 벤치마크
"""

import time
import numpy as np
import cv2
import psutil
import os

def benchmark_inference(model_path: str, num_iterations: int = 100):
    """추론 성능 벤치마크"""

    # 모델 로드
    net = cv2.dnn.readNetFromONNX(model_path)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    # 더미 입력
    dummy_input = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # 워밍업
    for _ in range(10):
        blob = cv2.dnn.blobFromImage(dummy_input, 1/255.0, (640, 640), swapRB=True)
        net.setInput(blob)
        net.forward()

    # 벤치마크
    inference_times = []
    cpu_usages = []
    memory_usages = []

    for i in range(num_iterations):
        # CPU/메모리 측정
        cpu_usages.append(psutil.cpu_percent())
        memory_usages.append(psutil.virtual_memory().percent)

        # 추론 시간 측정
        start = time.time()
        blob = cv2.dnn.blobFromImage(dummy_input, 1/255.0, (640, 640), swapRB=True)
        net.setInput(blob)
        net.forward()
        inference_times.append((time.time() - start) * 1000)

    # 결과 출력
    print("=" * 50)
    print("  Raspberry Pi 4 성능 벤치마크 결과")
    print("=" * 50)
    print(f"\n📊 추론 성능 ({num_iterations} iterations)")
    print(f"   평균: {np.mean(inference_times):.1f}ms")
    print(f"   표준편차: {np.std(inference_times):.1f}ms")
    print(f"   최소: {np.min(inference_times):.1f}ms")
    print(f"   최대: {np.max(inference_times):.1f}ms")
    print(f"   FPS: {1000 / np.mean(inference_times):.1f}")

    print(f"\n💻 시스템 리소스")
    print(f"   평균 CPU: {np.mean(cpu_usages):.1f}%")
    print(f"   평균 메모리: {np.mean(memory_usages):.1f}%")

    # 온도 (Raspberry Pi 전용)
    try:
        temp = float(os.popen("vcgencmd measure_temp").readline().replace("temp=","").replace("'C\n",""))
        print(f"   CPU 온도: {temp}°C")
    except:
        pass

    print("=" * 50)

    return {
        'avg_inference_ms': np.mean(inference_times),
        'fps': 1000 / np.mean(inference_times),
        'avg_cpu': np.mean(cpu_usages),
        'avg_memory': np.mean(memory_usages)
    }


if __name__ == "__main__":
    results = benchmark_inference(
        model_path="/greengrass/v2/packages/artifacts/com.ppe.Detector/1.0.0/models/model.onnx",
        num_iterations=100
    )
```

예상 결과:
```
==================================================
  Raspberry Pi 4 성능 벤치마크 결과
==================================================

📊 추론 성능 (100 iterations)
   평균: 82.5ms
   표준편차: 4.3ms
   최소: 76.2ms
   최대: 98.7ms
   FPS: 12.1

💻 시스템 리소스
   평균 CPU: 78.5%
   평균 메모리: 42.3%
   CPU 온도: 58°C
==================================================
```

---

## 3. CloudWatch 대시보드

### 3.1 대시보드 생성

```bash
cat > dashboard.json << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "Kinesis - 수신 레코드",
                "metrics": [
                    ["AWS/Kinesis", "IncomingRecords", "StreamName", "ppe-detection-stream", {"stat": "Sum", "period": 60}]
                ],
                "region": "ap-northeast-2",
                "view": "timeSeries"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "Lambda - 호출 수",
                "metrics": [
                    ["AWS/Lambda", "Invocations", "FunctionName", "ppe-kinesis-processor", {"stat": "Sum", "period": 60}]
                ],
                "region": "ap-northeast-2"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "Lambda - 오류",
                "metrics": [
                    ["AWS/Lambda", "Errors", "FunctionName", "ppe-kinesis-processor", {"stat": "Sum", "period": 60, "color": "#d62728"}]
                ],
                "region": "ap-northeast-2"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "Lambda - 실행 시간",
                "metrics": [
                    ["AWS/Lambda", "Duration", "FunctionName", "ppe-kinesis-processor", {"stat": "Average", "period": 60}]
                ],
                "region": "ap-northeast-2"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "DynamoDB - 읽기/쓰기 용량",
                "metrics": [
                    ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "ppe-safety-events"],
                    ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "ppe-safety-events"]
                ],
                "region": "ap-northeast-2"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "title": "SNS - 발행 메시지",
                "metrics": [
                    ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", "ppe-safety-alerts"]
                ],
                "region": "ap-northeast-2"
            }
        },
        {
            "type": "text",
            "x": 0,
            "y": 18,
            "width": 24,
            "height": 2,
            "properties": {
                "markdown": "## 🏗️ PPE Safety Detection System Dashboard\n시스템 상태: **운영 중** | 리전: ap-northeast-2"
            }
        }
    ]
}
EOF

# 대시보드 생성
aws cloudwatch put-dashboard \
    --dashboard-name "PPE-Safety-Monitoring" \
    --dashboard-body file://dashboard.json

echo "대시보드 URL: https://ap-northeast-2.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-2#dashboards:name=PPE-Safety-Monitoring"
```

### 3.2 커스텀 메트릭 발행 (Raspberry Pi)

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='ap-northeast-2')

def publish_custom_metrics(device_id: str, metrics: dict):
    """커스텀 메트릭 발행"""

    cloudwatch.put_metric_data(
        Namespace='PPESafety/EdgeDevice',
        MetricData=[
            {
                'MetricName': 'InferenceTime',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': metrics['inference_ms'],
                'Unit': 'Milliseconds'
            },
            {
                'MetricName': 'DetectionCount',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': metrics['detection_count'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'ViolationCount',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': metrics['violation_count'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'FPS',
                'Dimensions': [{'Name': 'DeviceId', 'Value': device_id}],
                'Value': metrics['fps'],
                'Unit': 'Count/Second'
            }
        ]
    )
```

---

## 4. 알람 설정

### 4.1 Lambda 오류 알람

```bash
# Lambda 오류 알람
aws cloudwatch put-metric-alarm \
    --alarm-name "PPE-Lambda-Errors" \
    --alarm-description "Lambda 함수 오류 발생" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --dimensions Name=FunctionName,Value=ppe-kinesis-processor \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions ${SNS_TOPIC_ARN}
```

### 4.2 높은 위반율 알람

```bash
# 커스텀 위반율 알람
aws cloudwatch put-metric-alarm \
    --alarm-name "PPE-High-Violation-Rate" \
    --alarm-description "높은 안전 위반율 감지" \
    --metric-name ViolationCount \
    --namespace PPESafety/EdgeDevice \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions ${SNS_TOPIC_ARN}
```

### 4.3 GreenGrass 연결 끊김 알람

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "PPE-GreenGrass-Disconnected" \
    --alarm-description "GreenGrass Core 연결 끊김" \
    --metric-name Success \
    --namespace AWS/IoT \
    --dimensions Name=Protocol,Value=MQTT \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator LessThanThreshold \
    --evaluation-periods 3 \
    --alarm-actions ${SNS_TOPIC_ARN}
```

---

## 5. 로그 분석

### 5.1 CloudWatch Logs Insights 쿼리

```bash
# GreenGrass 컴포넌트 로그 분석
aws logs start-query \
    --log-group-name "/aws/greengrass/GreengrassSystemComponent/ppe-detector-rpi4/com.ppe.Detector" \
    --start-time $(date -d '1 hour ago' +%s) \
    --end-time $(date +%s) \
    --query-string 'fields @timestamp, @message
        | filter @message like /위반|violation|ERROR/
        | sort @timestamp desc
        | limit 50'
```

### 5.2 유용한 Logs Insights 쿼리

```sql
-- 시간대별 위반 건수
fields @timestamp, @message
| filter @message like /위반 감지/
| stats count(*) as violations by bin(1h)

-- 디바이스별 에러
fields @timestamp, @message
| filter @message like /ERROR|Exception/
| stats count(*) as errors by device_id

-- 평균 추론 시간
fields @timestamp, inference_ms
| stats avg(inference_ms) as avg_inference by bin(5m)
```

---

## 6. 비용 모니터링

### 6.1 비용 탐색기 설정

```bash
# 태그 기반 비용 추적 활성화
aws ce update-cost-allocation-tags-status \
    --cost-allocation-tags-status \
    TagKey=Project,Status=Active
```

### 6.2 예산 알람

```bash
# 월별 예산 $50 설정
aws budgets create-budget \
    --account-id ${ACCOUNT_ID} \
    --budget '{
        "BudgetName": "PPE-Safety-Monthly",
        "BudgetLimit": {
            "Amount": "50",
            "Unit": "USD"
        },
        "BudgetType": "COST",
        "TimeUnit": "MONTHLY"
    }' \
    --notifications-with-subscribers '[{
        "Notification": {
            "NotificationType": "ACTUAL",
            "ComparisonOperator": "GREATER_THAN",
            "Threshold": 80
        },
        "Subscribers": [{
            "SubscriptionType": "EMAIL",
            "Address": "your-email@example.com"
        }]
    }]'
```

---

## 7. 운영 체크리스트

### 7.1 일일 점검

```bash
#!/bin/bash
# daily_check.sh

echo "📅 일일 시스템 점검 - $(date)"
echo ""

# 1. GreenGrass 상태
echo "1. GreenGrass Core 상태"
aws greengrassv2 get-core-device \
    --core-device-thing-name ppe-detector-rpi4 \
    --query '{Status: status, LastUpdate: lastStatusUpdateTimestamp}'

# 2. 최근 24시간 이벤트
echo ""
echo "2. 최근 24시간 이벤트 통계"
aws dynamodb scan \
    --table-name ppe-safety-events \
    --select COUNT \
    --filter-expression "sk > :yesterday" \
    --expression-attribute-values '{":yesterday": {"S": "'$(date -d '1 day ago' -Iseconds)'"}}'

# 3. Lambda 오류
echo ""
echo "3. Lambda 오류 (최근 24시간)"
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Errors \
    --dimensions Name=FunctionName,Value=ppe-kinesis-processor \
    --start-time $(date -d '1 day ago' -Iseconds) \
    --end-time $(date -Iseconds) \
    --period 86400 \
    --statistics Sum

# 4. 비용
echo ""
echo "4. 예상 일일 비용"
aws ce get-cost-and-usage \
    --time-period Start=$(date -d '1 day ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
    --granularity DAILY \
    --metrics BlendedCost \
    --filter '{"Tags": {"Key": "Project", "Values": ["ConstructionSafety"]}}'
```

---

## ✅ 최종 체크리스트

전체 시스템이 정상 작동하는지 확인:

- [ ] GreenGrass Core 상태: HEALTHY
- [ ] PPE Detector 컴포넌트: RUNNING
- [ ] 카메라 캡처: 정상
- [ ] 추론 성능: 10+ FPS
- [ ] Kinesis 데이터 수신: 확인
- [ ] DynamoDB 저장: 확인
- [ ] SNS 알림: 수신 확인
- [ ] CloudWatch 대시보드: 정상
- [ ] 알람 설정: 완료
- [ ] 비용 모니터링: 활성화

---

## 🎉 튜토리얼 완료!

축하합니다! Raspberry Pi 4 기반 PPE 감지 시스템 구축을 완료했습니다.

### 구축된 시스템 요약

```
┌─────────────────────────────────────────────────────────────────┐
│                    PPE 감지 시스템 아키텍처                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Raspberry Pi 4]                [AWS Cloud]                   │
│  ┌─────────────┐                 ┌─────────────────────┐       │
│  │ 카메라       │                 │ IoT Core            │       │
│  │    ↓        │     MQTT        │    ↓                │       │
│  │ YOLOv8      │ ──────────────→ │ Kinesis Streams     │       │
│  │ (ONNX)      │                 │    ↓                │       │
│  │    ↓        │                 │ Lambda              │       │
│  │ GreenGrass  │                 │    ↓        ↓       │       │
│  └─────────────┘                 │ DynamoDB   SNS      │       │
│                                  │    ↓        ↓       │       │
│                                  │ S3      Email/SMS   │       │
│                                  └─────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 다음 단계 (선택)

1. **모델 개선**: 더 많은 데이터로 재학습
2. **다중 디바이스**: 여러 Raspberry Pi 배포
3. **대시보드**: Grafana 또는 QuickSight 연동
4. **AI/ML 분석**: SageMaker로 추가 분석
5. **모바일 앱**: 현장 관리자용 앱 개발

---

문제가 있거나 질문이 있으면 GitHub Issues에 등록해 주세요!
