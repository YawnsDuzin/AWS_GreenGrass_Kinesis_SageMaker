# Part 8: 알림 시스템 구축

이 파트에서는 SNS, Lambda를 사용하여 실시간 안전 위반 알림 시스템을 구축합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] SNS 토픽 생성 및 구독 설정
- [x] Lambda 알림 처리 함수 배포
- [x] 이메일/SMS 알림 구성
- [x] Slack/Teams 연동 (선택)
- [x] 알림 대시보드 구축

---

## 1. SNS 토픽 생성

### 1.1 CLI로 토픽 생성

```bash
# SNS 토픽 생성
aws sns create-topic \
    --name ppe-safety-alerts \
    --region ap-northeast-2

# 토픽 ARN 저장
SNS_TOPIC_ARN=$(aws sns list-topics \
    --query "Topics[?contains(TopicArn, 'ppe-safety-alerts')].TopicArn" \
    --output text)

echo "SNS 토픽 ARN: ${SNS_TOPIC_ARN}"
```

### 1.2 이메일 구독 추가

```bash
# 이메일 구독
aws sns subscribe \
    --topic-arn ${SNS_TOPIC_ARN} \
    --protocol email \
    --notification-endpoint your-email@example.com

# ⚠️ 이메일 확인 필요: 수신함에서 확인 링크 클릭
```

### 1.3 SMS 구독 추가 (선택)

```bash
# SMS 구독 (한국 번호 예시)
aws sns subscribe \
    --topic-arn ${SNS_TOPIC_ARN} \
    --protocol sms \
    --notification-endpoint +821012345678
```

---

## 2. Lambda 알림 함수

### 2.1 알림 처리 Lambda 코드

```bash
mkdir -p ~/alert-lambda
cd ~/alert-lambda

cat > handler.py << 'EOF'
"""
안전 위반 알림 Lambda
DynamoDB 스트림 또는 Kinesis에서 트리거
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'ppe-safety-events')


def lambda_handler(event, context):
    """메인 핸들러"""

    alerts_sent = 0

    for record in event.get('Records', []):
        try:
            # 이벤트 소스에 따른 처리
            if 'kinesis' in record:
                data = process_kinesis_record(record)
            elif 'dynamodb' in record:
                data = process_dynamodb_record(record)
            else:
                continue

            # 위반 확인 및 알림
            if data and data.get('has_violations'):
                send_alert(data)
                alerts_sent += 1

        except Exception as e:
            logger.error(f"레코드 처리 오류: {e}")

    return {
        'statusCode': 200,
        'alerts_sent': alerts_sent
    }


def process_kinesis_record(record: Dict) -> Dict:
    """Kinesis 레코드 처리"""
    import base64

    payload = base64.b64decode(record['kinesis']['data'])
    data = json.loads(payload.decode('utf-8'))

    # 위반 확인
    detections = data.get('detections', [])
    violations = [d for d in detections if 'no_' in d.get('class_name', '')]

    if violations:
        return {
            'device_id': data.get('device_id'),
            'timestamp': data.get('timestamp'),
            'has_violations': True,
            'violation_count': len(violations),
            'violation_types': list(set(v.get('class_name') for v in violations)),
            'severity': 'HIGH' if len(violations) >= 2 else 'MEDIUM'
        }

    return None


def process_dynamodb_record(record: Dict) -> Dict:
    """DynamoDB 스트림 레코드 처리"""
    if record['eventName'] not in ['INSERT', 'MODIFY']:
        return None

    new_image = record['dynamodb'].get('NewImage', {})

    # DynamoDB 형식에서 값 추출
    has_violations = new_image.get('has_violations', {}).get('BOOL', False)

    if has_violations:
        return {
            'device_id': new_image.get('pk', {}).get('S'),
            'timestamp': new_image.get('sk', {}).get('S'),
            'has_violations': True,
            'violation_count': int(new_image.get('violation_count', {}).get('N', 0)),
            'severity': new_image.get('severity', {}).get('S', 'MEDIUM')
        }

    return None


def send_alert(data: Dict):
    """SNS 알림 발송"""

    severity = data.get('severity', 'MEDIUM')
    device_id = data.get('device_id', 'unknown')

    # 심각도별 이모지
    emoji = "🔴" if severity == 'HIGH' else "🟡"

    # 알림 메시지 구성
    subject = f"{emoji} [{severity}] 안전 위반 감지 - {device_id}"

    message = f"""
========================================
⚠️ 건설현장 안전 위반 알림
========================================

📍 디바이스: {device_id}
⏰ 감지 시간: {data.get('timestamp', 'N/A')}
🚨 심각도: {severity}
📊 위반 건수: {data.get('violation_count', 0)}

위반 유형:
"""

    violation_types = data.get('violation_types', [])
    for vtype in violation_types:
        if vtype == 'no_hardhat':
            message += "  ❌ 안전모 미착용\n"
        elif vtype == 'no_safety_vest':
            message += "  ❌ 안전조끼 미착용\n"

    message += """
----------------------------------------
즉시 현장 확인이 필요합니다.

AWS IoT Construction Safety System
"""

    # SNS 발행
    if SNS_TOPIC_ARN:
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
            MessageAttributes={
                'severity': {
                    'DataType': 'String',
                    'StringValue': severity
                },
                'device_id': {
                    'DataType': 'String',
                    'StringValue': device_id
                }
            }
        )

        logger.info(f"알림 발송 완료: {response['MessageId']}")

    # DynamoDB에 알림 기록 저장
    save_alert_record(data)


def save_alert_record(data: Dict):
    """알림 기록 저장"""
    try:
        table = dynamodb.Table('ppe-alert-history')
        table.put_item(Item={
            'pk': data.get('device_id'),
            'sk': f"ALERT#{data.get('timestamp')}",
            'severity': data.get('severity'),
            'violation_count': data.get('violation_count'),
            'created_at': datetime.now().isoformat(),
            'ttl': int(datetime.now().timestamp()) + (30 * 24 * 60 * 60)  # 30일
        })
    except Exception as e:
        logger.warning(f"알림 기록 저장 실패: {e}")
EOF

# 패키징
zip handler.zip handler.py
```

### 2.2 Lambda 함수 배포

```bash
# 환경 변수
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
LAMBDA_ROLE_ARN=$(aws iam get-role --role-name ConstructionSafety-LambdaRole --query 'Role.Arn' --output text)

# Lambda 함수 생성
aws lambda create-function \
    --function-name ppe-alert-sender \
    --runtime python3.11 \
    --handler handler.lambda_handler \
    --role ${LAMBDA_ROLE_ARN} \
    --zip-file fileb://handler.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={SNS_TOPIC_ARN=${SNS_TOPIC_ARN},DYNAMODB_TABLE=ppe-safety-events}" \
    --region ap-northeast-2

echo "Lambda 함수 생성 완료"
```

### 2.3 기존 Lambda에 SNS 환경 변수 추가

```bash
# Part 4에서 생성한 Kinesis 처리 Lambda 업데이트
aws lambda update-function-configuration \
    --function-name ppe-kinesis-processor \
    --environment "Variables={DYNAMODB_TABLE=ppe-safety-events,SNS_TOPIC_ARN=${SNS_TOPIC_ARN}}"
```

---

## 3. 심각도 기반 알림 필터링

### 3.1 SNS 필터 정책 설정

```bash
# 구독 ARN 확인
SUBSCRIPTION_ARN=$(aws sns list-subscriptions-by-topic \
    --topic-arn ${SNS_TOPIC_ARN} \
    --query "Subscriptions[0].SubscriptionArn" \
    --output text)

# HIGH 심각도만 수신하는 필터 (이메일용)
aws sns set-subscription-attributes \
    --subscription-arn ${SUBSCRIPTION_ARN} \
    --attribute-name FilterPolicy \
    --attribute-value '{"severity": ["HIGH"]}'
```

### 3.2 모든 심각도 수신 구독 추가 (관리자용)

```bash
# 관리자 이메일 - 모든 알림
aws sns subscribe \
    --topic-arn ${SNS_TOPIC_ARN} \
    --protocol email \
    --notification-endpoint admin@example.com

# 확인 후 필터 없이 모든 알림 수신
```

---

## 4. Slack 연동 (선택)

### 4.1 Slack Webhook 설정

1. Slack 워크스페이스에서 앱 생성
2. **Incoming Webhooks** 활성화
3. Webhook URL 복사

### 4.2 Slack 알림 Lambda

```bash
cat > slack_handler.py << 'EOF'
"""
Slack 알림 Lambda
SNS에서 트리거
"""

import json
import urllib.request
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')


def lambda_handler(event, context):
    """SNS 메시지를 Slack으로 전달"""

    for record in event.get('Records', []):
        try:
            sns_message = record['Sns']['Message']
            subject = record['Sns'].get('Subject', '알림')

            # Slack 메시지 구성
            slack_message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": subject
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{sns_message}```"
                        }
                    }
                ]
            }

            # Slack으로 전송
            send_to_slack(slack_message)

        except Exception as e:
            logger.error(f"Slack 알림 실패: {e}")

    return {'statusCode': 200}


def send_to_slack(message: dict):
    """Slack Webhook으로 메시지 전송"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL 미설정")
        return

    data = json.dumps(message).encode('utf-8')
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={'Content-Type': 'application/json'}
    )

    with urllib.request.urlopen(req) as response:
        logger.info(f"Slack 응답: {response.status}")
EOF

zip slack_handler.zip slack_handler.py

# Lambda 생성
aws lambda create-function \
    --function-name ppe-slack-notifier \
    --runtime python3.11 \
    --handler slack_handler.lambda_handler \
    --role ${LAMBDA_ROLE_ARN} \
    --zip-file fileb://slack_handler.zip \
    --timeout 10 \
    --environment "Variables={SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL}"

# SNS 구독 추가
aws sns subscribe \
    --topic-arn ${SNS_TOPIC_ARN} \
    --protocol lambda \
    --notification-endpoint "arn:aws:lambda:ap-northeast-2:${ACCOUNT_ID}:function:ppe-slack-notifier"

# Lambda 권한 추가
aws lambda add-permission \
    --function-name ppe-slack-notifier \
    --statement-id sns-trigger \
    --action lambda:InvokeFunction \
    --principal sns.amazonaws.com \
    --source-arn ${SNS_TOPIC_ARN}
```

---

## 5. 알림 대시보드 (API Gateway + Lambda)

### 5.1 알림 조회 API

```bash
cat > api_handler.py << 'EOF'
"""
알림 조회 REST API
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def lambda_handler(event, context):
    """API Gateway 핸들러"""

    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')

    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    try:
        if path == '/alerts':
            result = get_recent_alerts()
        elif path == '/alerts/stats':
            result = get_alert_statistics()
        elif path == '/alerts/devices':
            result = get_device_summary()
        else:
            return {'statusCode': 404, 'headers': headers, 'body': '{"error": "Not Found"}'}

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result, cls=DecimalEncoder, ensure_ascii=False)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }


def get_recent_alerts(limit: int = 50) -> dict:
    """최근 알림 조회"""
    table = dynamodb.Table('ppe-safety-events')

    response = table.scan(
        FilterExpression='has_violations = :v',
        ExpressionAttributeValues={':v': True},
        Limit=limit
    )

    items = sorted(
        response.get('Items', []),
        key=lambda x: x.get('sk', ''),
        reverse=True
    )

    return {
        'alerts': items[:limit],
        'count': len(items)
    }


def get_alert_statistics() -> dict:
    """알림 통계"""
    table = dynamodb.Table('ppe-safety-events')

    response = table.scan()
    items = response.get('Items', [])

    total = len(items)
    violations = [i for i in items if i.get('has_violations')]

    severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for item in violations:
        sev = item.get('severity', 'LOW')
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        'total_events': total,
        'total_violations': len(violations),
        'violation_rate': round(len(violations) / total * 100, 2) if total > 0 else 0,
        'severity_breakdown': severity_counts,
        'last_updated': datetime.now().isoformat()
    }


def get_device_summary() -> dict:
    """디바이스별 요약"""
    table = dynamodb.Table('ppe-safety-events')

    response = table.scan()
    items = response.get('Items', [])

    devices = {}
    for item in items:
        device_id = item.get('pk', 'unknown')
        if device_id not in devices:
            devices[device_id] = {'total': 0, 'violations': 0}

        devices[device_id]['total'] += 1
        if item.get('has_violations'):
            devices[device_id]['violations'] += 1

    return {
        'devices': [
            {
                'device_id': k,
                'total_events': v['total'],
                'violation_count': v['violations'],
                'violation_rate': round(v['violations'] / v['total'] * 100, 2) if v['total'] > 0 else 0
            }
            for k, v in devices.items()
        ]
    }
EOF

zip api_handler.zip api_handler.py

# API Lambda 생성
aws lambda create-function \
    --function-name ppe-alert-api \
    --runtime python3.11 \
    --handler api_handler.lambda_handler \
    --role ${LAMBDA_ROLE_ARN} \
    --zip-file fileb://api_handler.zip \
    --timeout 30
```

### 5.2 API Gateway 생성

```bash
# REST API 생성
API_ID=$(aws apigateway create-rest-api \
    --name "PPE Safety Alert API" \
    --query 'id' --output text)

# 루트 리소스 ID
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id ${API_ID} \
    --query 'items[0].id' --output text)

# /alerts 리소스
ALERTS_ID=$(aws apigateway create-resource \
    --rest-api-id ${API_ID} \
    --parent-id ${ROOT_ID} \
    --path-part alerts \
    --query 'id' --output text)

# GET 메서드
aws apigateway put-method \
    --rest-api-id ${API_ID} \
    --resource-id ${ALERTS_ID} \
    --http-method GET \
    --authorization-type NONE

# Lambda 통합
aws apigateway put-integration \
    --rest-api-id ${API_ID} \
    --resource-id ${ALERTS_ID} \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:ap-northeast-2:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-northeast-2:${ACCOUNT_ID}:function:ppe-alert-api/invocations"

# 배포
aws apigateway create-deployment \
    --rest-api-id ${API_ID} \
    --stage-name prod

echo "API URL: https://${API_ID}.execute-api.ap-northeast-2.amazonaws.com/prod/alerts"
```

---

## 6. 테스트

### 6.1 수동 알림 테스트

```bash
# SNS 직접 발행
aws sns publish \
    --topic-arn ${SNS_TOPIC_ARN} \
    --subject "[TEST] 안전 위반 테스트" \
    --message "테스트 알림입니다."

# 이메일 확인
```

### 6.2 Kinesis를 통한 E2E 테스트

```bash
# 테스트 데이터 전송
STREAM_NAME="ppe-detection-stream"

aws kinesis put-record \
    --stream-name ${STREAM_NAME} \
    --partition-key "test-device" \
    --data "$(echo '{"device_id":"test-rpi4","timestamp":"2024-01-15T12:00:00Z","detections":[{"class_name":"no_hardhat","confidence":0.85}]}' | base64)"

# 알림 수신 확인
```

---

## ✅ 체크리스트

- [ ] SNS 토픽 `ppe-safety-alerts` 생성
- [ ] 이메일 구독 및 확인 완료
- [ ] Lambda `ppe-alert-sender` 배포
- [ ] Kinesis 처리 Lambda에 SNS 환경 변수 추가
- [ ] 테스트 알림 수신 확인
- [ ] (선택) Slack 연동
- [ ] (선택) API Gateway 대시보드

---

## 📚 다음 단계

[Part 9: 테스트 및 모니터링](./09-testing-monitoring.md)으로 이동하여
전체 시스템 테스트 및 CloudWatch 모니터링을 설정합니다.
