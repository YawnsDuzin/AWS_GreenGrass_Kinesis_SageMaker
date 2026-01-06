# 2.2 Amazon Kinesis 완벽 가이드

## 개요

### Amazon Kinesis란?

Amazon Kinesis는 **실시간 스트리밍 데이터**를 수집, 처리, 분석하기 위한 완전관리형 서비스입니다. 대용량의 데이터 스트림을 실시간으로 처리할 수 있어 IoT, 로그 분석, 실시간 대시보드 등에 활용됩니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Amazon Kinesis 서비스 제품군                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 Kinesis Data Streams                            │   │
│  │  • 실시간 데이터 스트림 수집 및 저장                             │   │
│  │  • 여러 소비자가 동시에 데이터 읽기 가능                         │   │
│  │  • 밀리초 단위 지연 시간                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 Kinesis Data Firehose                           │   │
│  │  • 데이터를 대상 서비스로 자동 전송                              │   │
│  │  • ETL 변환 기능 내장                                           │   │
│  │  • S3, Redshift, OpenSearch 등 연동                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 Kinesis Data Analytics                          │   │
│  │  • SQL 또는 Apache Flink로 실시간 분석                          │   │
│  │  • 스트림 데이터에 대한 즉시 쿼리                               │   │
│  │  • 이상 감지, 집계, 필터링                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 Kinesis Video Streams                           │   │
│  │  • 비디오 스트림 수집 및 저장                                   │   │
│  │  • 실시간 및 배치 비디오 분석                                   │   │
│  │  • ML 모델과 통합                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Kinesis Data Streams

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kinesis Data Streams 아키텍처                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Producers                    Kinesis Stream                Consumers  │
│   (데이터 생성)                (데이터 저장)                 (데이터 소비)│
│                                                                         │
│   ┌─────────┐                 ┌────────────────────┐      ┌─────────┐  │
│   │ IoT     │────────┐       │ ┌────────────────┐ │      │ Lambda  │  │
│   │ Device  │        │       │ │   Shard 1      │ │  ┌──▶│         │  │
│   └─────────┘        │       │ │ ┌──┬──┬──┬──┐  │ │  │   └─────────┘  │
│                      │       │ │ │R1│R2│R3│..│  │ │  │                │
│   ┌─────────┐        │       │ │ └──┴──┴──┴──┘  │ │  │   ┌─────────┐  │
│   │ App     │────────┼──────▶│ └────────────────┘ │──┼──▶│ Kinesis │  │
│   │ Server  │        │       │ ┌────────────────┐ │  │   │Analytics│  │
│   └─────────┘        │       │ │   Shard 2      │ │  │   └─────────┘  │
│                      │       │ │ ┌──┬──┬──┬──┐  │ │  │                │
│   ┌─────────┐        │       │ │ │R1│R2│R3│..│  │ │  │   ┌─────────┐  │
│   │ SDK/    │────────┘       │ │ └──┴──┴──┴──┘  │ │  └──▶│ EC2 /   │  │
│   │ Agent   │                │ └────────────────┘ │      │ ECS     │  │
│   └─────────┘                │        ...         │      └─────────┘  │
│                              │ ┌────────────────┐ │                   │
│                              │ │   Shard N      │ │                   │
│                              │ └────────────────┘ │                   │
│                              └────────────────────┘                   │
│                                                                         │
│   Partition Key로              24시간 ~ 365일             Enhanced     │
│   샤드 결정                     데이터 보존                Fan-Out 지원 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 핵심 개념

| 개념 | 설명 | 특징 |
|------|------|------|
| **Shard** | 스트림의 기본 처리 단위 | 1MB/s 입력, 2MB/s 출력 |
| **Record** | 데이터의 기본 단위 | 최대 1MB, Partition Key 포함 |
| **Partition Key** | 샤드 선택을 위한 키 | 해시 함수로 샤드 결정 |
| **Sequence Number** | 레코드 고유 식별자 | 샤드 내 순서 보장 |
| **Consumer** | 데이터 소비자 | 표준/Enhanced Fan-Out |

### 용량 계획

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kinesis 용량 계획 가이드                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  샤드 수 계산 공식                                                       │
│                                                                         │
│  입력 기준:                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  필요 샤드 수 = max(입력 데이터량 / 1MB/s,                       │   │
│  │                     입력 레코드 수 / 1000/s)                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  출력 기준 (표준 소비자):                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  필요 샤드 수 = (출력 데이터량 × 소비자 수) / 2MB/s              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  예시: 공사현장 센서 데이터                                              │
│  ├─ 센서 100개 × 100바이트/초 = 10KB/s                                 │
│  ├─ 카메라 10대 × 이벤트 1KB/초 = 10KB/s                               │
│  ├─ 총 입력: 약 20KB/s                                                  │
│  └─ 필요 샤드: 1개 (최소 구성)                                          │
│                                                                         │
│  ※ On-Demand 모드 사용 시 자동 확장                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Python SDK 사용 예시

```python
# kinesis_producer.py
import boto3
import json
import time
from datetime import datetime

class KinesisProducer:
    def __init__(self, stream_name, region='ap-northeast-2'):
        self.client = boto3.client('kinesis', region_name=region)
        self.stream_name = stream_name

    def put_record(self, data, partition_key):
        """단일 레코드 전송"""
        response = self.client.put_record(
            StreamName=self.stream_name,
            Data=json.dumps(data).encode('utf-8'),
            PartitionKey=partition_key
        )
        return response

    def put_records_batch(self, records):
        """배치 레코드 전송 (최대 500개)"""
        kinesis_records = [
            {
                'Data': json.dumps(r['data']).encode('utf-8'),
                'PartitionKey': r['partition_key']
            }
            for r in records
        ]

        response = self.client.put_records(
            StreamName=self.stream_name,
            Records=kinesis_records
        )

        # 실패한 레코드 재시도
        if response['FailedRecordCount'] > 0:
            self._retry_failed_records(records, response)

        return response

    def _retry_failed_records(self, records, response, max_retries=3):
        """실패한 레코드 재시도"""
        failed_records = []
        for i, result in enumerate(response['Records']):
            if 'ErrorCode' in result:
                failed_records.append(records[i])

        if failed_records and max_retries > 0:
            time.sleep(0.5)  # 백오프
            self.put_records_batch(failed_records)


# 사용 예시
def send_safety_event():
    producer = KinesisProducer('construction-safety-stream')

    event = {
        'event_type': 'SAFETY_VIOLATION',
        'timestamp': datetime.now().isoformat(),
        'device_id': 'camera-site-a-01',
        'site_id': 'construction-site-001',
        'violation': {
            'type': 'NO_HELMET',
            'confidence': 0.95,
            'location': {'x': 100, 'y': 200, 'width': 50, 'height': 100}
        },
        'metadata': {
            'weather': 'sunny',
            'temperature': 25,
            'worker_count': 15
        }
    }

    response = producer.put_record(
        data=event,
        partition_key=event['device_id']  # 디바이스별 순서 보장
    )

    print(f"Record sent: {response['ShardId']}, Sequence: {response['SequenceNumber']}")


# kinesis_consumer.py
import boto3
import json
import time

class KinesisConsumer:
    def __init__(self, stream_name, region='ap-northeast-2'):
        self.client = boto3.client('kinesis', region_name=region)
        self.stream_name = stream_name

    def get_shard_iterator(self, shard_id, iterator_type='LATEST'):
        """샤드 이터레이터 획득"""
        response = self.client.get_shard_iterator(
            StreamName=self.stream_name,
            ShardId=shard_id,
            ShardIteratorType=iterator_type
        )
        return response['ShardIterator']

    def consume(self, shard_id, handler_func):
        """지속적으로 레코드 소비"""
        shard_iterator = self.get_shard_iterator(shard_id)

        while True:
            response = self.client.get_records(
                ShardIterator=shard_iterator,
                Limit=100
            )

            for record in response['Records']:
                data = json.loads(record['Data'].decode('utf-8'))
                handler_func(data, record['SequenceNumber'])

            shard_iterator = response['NextShardIterator']

            if not response['Records']:
                time.sleep(1)  # 레코드 없으면 대기


def process_safety_event(data, sequence_number):
    """안전 이벤트 처리"""
    if data['event_type'] == 'SAFETY_VIOLATION':
        print(f"[{data['timestamp']}] 위반 감지: {data['violation']['type']}")
        print(f"  - 위치: {data['device_id']}")
        print(f"  - 신뢰도: {data['violation']['confidence']}")

        # 심각도에 따른 추가 처리
        if data['violation']['type'] in ['NO_HELMET', 'DANGER_ZONE']:
            trigger_alert(data)

def trigger_alert(data):
    """알림 트리거"""
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:ap-northeast-2:123456789012:safety-alerts',
        Message=json.dumps(data),
        Subject=f"[긴급] 안전 위반 감지: {data['violation']['type']}"
    )
```

---

## Kinesis Data Firehose

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kinesis Data Firehose 아키텍처                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Sources                    Firehose                     Destinations  │
│                                                                         │
│  ┌─────────────┐     ┌─────────────────────────┐     ┌─────────────┐  │
│  │ Kinesis     │────▶│                         │────▶│ Amazon S3   │  │
│  │ Data Streams│     │                         │     └─────────────┘  │
│  └─────────────┘     │                         │                       │
│                      │   ┌─────────────────┐   │     ┌─────────────┐  │
│  ┌─────────────┐     │   │  Buffer         │   │────▶│ Redshift    │  │
│  │ Direct PUT  │────▶│   │  (Size/Time)    │   │     └─────────────┘  │
│  │ (SDK/Agent) │     │   └────────┬────────┘   │                       │
│  └─────────────┘     │            │            │     ┌─────────────┐  │
│                      │            ▼            │────▶│ OpenSearch  │  │
│  ┌─────────────┐     │   ┌─────────────────┐   │     └─────────────┘  │
│  │ CloudWatch  │────▶│   │  Transform      │   │                       │
│  │ Logs        │     │   │  (Lambda)       │   │     ┌─────────────┐  │
│  └─────────────┘     │   └────────┬────────┘   │────▶│ HTTP        │  │
│                      │            │            │     │ Endpoint    │  │
│  ┌─────────────┐     │            ▼            │     └─────────────┘  │
│  │ IoT         │────▶│   ┌─────────────────┐   │                       │
│  │             │     │   │  Compress       │   │     ┌─────────────┐  │
│  └─────────────┘     │   │  (GZIP/Snappy)  │   │────▶│ Splunk      │  │
│                      │   └─────────────────┘   │     └─────────────┘  │
│                      │                         │                       │
│                      └─────────────────────────┘                       │
│                                                                         │
│                      자동 확장, 완전 관리형                              │
│                      Near Real-time (60초 버퍼)                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Firehose 설정 예시 (CloudFormation)

```yaml
# firehose-template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Kinesis Firehose for Construction Safety Data'

Resources:
  SafetyDataFirehose:
    Type: AWS::KinesisFirehose::DeliveryStream
    Properties:
      DeliveryStreamName: construction-safety-firehose
      DeliveryStreamType: KinesisStreamAsSource

      KinesisStreamSourceConfiguration:
        KinesisStreamARN: !Sub 'arn:aws:kinesis:${AWS::Region}:${AWS::AccountId}:stream/construction-safety-stream'
        RoleARN: !GetAtt FirehoseRole.Arn

      ExtendedS3DestinationConfiguration:
        BucketARN: !GetAtt SafetyDataBucket.Arn
        RoleARN: !GetAtt FirehoseRole.Arn

        # 버퍼 설정
        BufferingHints:
          SizeInMBs: 64
          IntervalInSeconds: 60

        # 압축
        CompressionFormat: GZIP

        # 파티셔닝
        Prefix: 'raw/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/'
        ErrorOutputPrefix: 'error/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/'

        # Lambda 변환
        ProcessingConfiguration:
          Enabled: true
          Processors:
            - Type: Lambda
              Parameters:
                - ParameterName: LambdaArn
                  ParameterValue: !GetAtt TransformLambda.Arn

  TransformLambda:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: firehose-transform
      Runtime: python3.9
      Handler: index.handler
      Timeout: 60
      MemorySize: 128
      Role: !GetAtt LambdaRole.Arn
      Code:
        ZipFile: |
          import base64
          import json

          def handler(event, context):
              output = []

              for record in event['records']:
                  # 데이터 디코딩
                  payload = base64.b64decode(record['data']).decode('utf-8')
                  data = json.loads(payload)

                  # 데이터 변환/보강
                  transformed = {
                      **data,
                      'processed_at': context.aws_request_id,
                      'severity_level': get_severity(data)
                  }

                  # 인코딩하여 반환
                  output.append({
                      'recordId': record['recordId'],
                      'result': 'Ok',
                      'data': base64.b64encode(
                          (json.dumps(transformed) + '\n').encode('utf-8')
                      ).decode('utf-8')
                  })

              return {'records': output}

          def get_severity(data):
              violation_type = data.get('violation', {}).get('type', '')
              if violation_type in ['NO_HELMET', 'DANGER_ZONE']:
                  return 'HIGH'
              elif violation_type in ['NO_VEST']:
                  return 'MEDIUM'
              return 'LOW'

  SafetyDataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'construction-safety-data-${AWS::AccountId}'
      LifecycleConfiguration:
        Rules:
          - Id: ArchiveRule
            Status: Enabled
            Transitions:
              - TransitionInDays: 30
                StorageClass: STANDARD_IA
              - TransitionInDays: 90
                StorageClass: GLACIER
```

---

## Kinesis Data Analytics

### SQL 기반 분석

```sql
-- 실시간 안전 위반 집계
CREATE OR REPLACE STREAM "AGGREGATED_VIOLATIONS" (
    site_id VARCHAR(50),
    violation_type VARCHAR(50),
    violation_count INTEGER,
    window_start TIMESTAMP,
    window_end TIMESTAMP
);

CREATE OR REPLACE PUMP "VIOLATION_AGGREGATOR" AS
INSERT INTO "AGGREGATED_VIOLATIONS"
SELECT STREAM
    site_id,
    violation_type,
    COUNT(*) AS violation_count,
    STEP("SOURCE_STREAM".ROWTIME BY INTERVAL '1' MINUTE) AS window_start,
    STEP("SOURCE_STREAM".ROWTIME BY INTERVAL '1' MINUTE) + INTERVAL '1' MINUTE AS window_end
FROM "SOURCE_STREAM"
WHERE event_type = 'SAFETY_VIOLATION'
GROUP BY
    site_id,
    violation_type,
    STEP("SOURCE_STREAM".ROWTIME BY INTERVAL '1' MINUTE);

-- 이상 감지: 급격한 위반 증가
CREATE OR REPLACE STREAM "ANOMALY_DETECTION" (
    site_id VARCHAR(50),
    anomaly_score DOUBLE,
    detection_time TIMESTAMP
);

CREATE OR REPLACE PUMP "ANOMALY_PUMP" AS
INSERT INTO "ANOMALY_DETECTION"
SELECT STREAM
    site_id,
    ANOMALY_SCORE AS anomaly_score,
    ROWTIME AS detection_time
FROM TABLE(
    RANDOM_CUT_FOREST(
        CURSOR(
            SELECT STREAM site_id, violation_count
            FROM "AGGREGATED_VIOLATIONS"
        ),
        100,  -- 트리 수
        256,  -- 샘플 크기
        100000,  -- 시간 감쇠
        1  -- 샤드 수
    )
)
WHERE ANOMALY_SCORE > 2.0;  -- 이상치 임계값
```

### Apache Flink 기반 분석

```java
// FlinkSafetyAnalytics.java
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kinesis.FlinkKinesisConsumer;
import org.apache.flink.streaming.api.windowing.time.Time;

public class FlinkSafetyAnalytics {

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Kinesis 소스 설정
        Properties consumerConfig = new Properties();
        consumerConfig.setProperty("aws.region", "ap-northeast-2");
        consumerConfig.setProperty("stream.initial.position", "LATEST");

        DataStream<SafetyEvent> eventStream = env.addSource(
            new FlinkKinesisConsumer<>(
                "construction-safety-stream",
                new SafetyEventSchema(),
                consumerConfig
            )
        );

        // 5분 슬라이딩 윈도우로 위반 집계
        DataStream<ViolationSummary> aggregated = eventStream
            .filter(e -> e.getEventType().equals("SAFETY_VIOLATION"))
            .keyBy(SafetyEvent::getSiteId)
            .timeWindow(Time.minutes(5), Time.minutes(1))
            .aggregate(new ViolationAggregator());

        // 임계값 초과 시 알림
        aggregated
            .filter(summary -> summary.getViolationCount() > 10)
            .addSink(new SNSAlertSink());

        env.execute("Construction Safety Real-time Analytics");
    }
}
```

---

## Kinesis Video Streams

### 비디오 스트림 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kinesis Video Streams 아키텍처                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Producers                 KVS                         Consumers       │
│                                                                         │
│   ┌─────────────┐      ┌─────────────────┐        ┌─────────────────┐  │
│   │ IP Camera   │─────▶│                 │───────▶│ HLS Playback    │  │
│   │ (RTSP)      │      │   Video         │        │ (웹 브라우저)    │  │
│   └─────────────┘      │   Stream        │        └─────────────────┘  │
│                        │                 │                              │
│   ┌─────────────┐      │   ┌─────────┐   │        ┌─────────────────┐  │
│   │ GStreamer   │─────▶│   │ Fragment│   │───────▶│ Rekognition     │  │
│   │ Producer    │      │   │ Storage │   │        │ Video           │  │
│   └─────────────┘      │   └─────────┘   │        └─────────────────┘  │
│                        │                 │                              │
│   ┌─────────────┐      │   ┌─────────┐   │        ┌─────────────────┐  │
│   │ WebRTC      │─────▶│   │ Index   │   │───────▶│ SageMaker       │  │
│   │ Producer    │      │   └─────────┘   │        │ Inference       │  │
│   └─────────────┘      │                 │        └─────────────────┘  │
│                        │   Retention:    │                              │
│   ┌─────────────┐      │   Hours ~ Days  │        ┌─────────────────┐  │
│   │ Mobile App  │─────▶│                 │───────▶│ Custom App      │  │
│   │             │      │                 │        │ (GetMedia API)  │  │
│   └─────────────┘      └─────────────────┘        └─────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 비디오 프로듀서 예시

```python
# kvs_producer.py
import boto3
import cv2
import time
from amazon_kinesis_video_streams_producer import KinesisVideoStreamProducer

class VideoStreamProducer:
    def __init__(self, stream_name, region='ap-northeast-2'):
        self.stream_name = stream_name
        self.region = region
        self.kvs_client = boto3.client('kinesisvideo', region_name=region)

        # 스트림 엔드포인트 획득
        endpoint = self.kvs_client.get_data_endpoint(
            StreamName=stream_name,
            APIName='PUT_MEDIA'
        )['DataEndpoint']

        self.producer = KinesisVideoStreamProducer(
            stream_name=stream_name,
            region=region,
            endpoint=endpoint
        )

    def stream_from_rtsp(self, rtsp_url):
        """RTSP 소스에서 KVS로 스트리밍"""
        cap = cv2.VideoCapture(rtsp_url)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 프레임 인코딩
            _, encoded = cv2.imencode('.jpg', frame)

            # KVS로 전송
            self.producer.put_frame(
                frame_data=encoded.tobytes(),
                timestamp_ms=int(time.time() * 1000)
            )

        cap.release()


# GStreamer 파이프라인 (Linux)
"""
gst-launch-1.0 \
    rtspsrc location=rtsp://192.168.1.100:554/stream1 ! \
    rtph264depay ! h264parse ! \
    kvssink stream-name="construction-camera-01" \
    storage-size=512 \
    access-key="AKIAXXXXXXXX" \
    secret-key="XXXXXXXXXX" \
    aws-region="ap-northeast-2"
"""
```

---

## 공사현장 적용 아키텍처

### 통합 스트리밍 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│               공사현장 Kinesis 통합 아키텍처                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    현장 (Edge Layer)                            │   │
│  │                                                                  │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │ Camera  │  │ Sensor  │  │Wearable │  │  Drone  │            │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │   │
│  │       │            │            │            │                  │   │
│  │       └────────────┴────────────┴────────────┘                  │   │
│  │                          │                                      │   │
│  │                          ▼                                      │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │              AWS IoT GreenGrass                         │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐                    │   │   │
│  │  │  │ ML Inference │  │ Stream Mgr   │                    │   │   │
│  │  │  └──────────────┘  └──────────────┘                    │   │   │
│  │  └─────────────────────────┬───────────────────────────────┘   │   │
│  └────────────────────────────┼───────────────────────────────────┘   │
│                               │                                        │
│  ┌────────────────────────────┼────────────────────────────────────┐  │
│  │                    AWS Cloud                                    │  │
│  │                            │                                    │  │
│  │                            ▼                                    │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │              Kinesis Data Streams                       │   │  │
│  │  │                                                          │   │  │
│  │  │  ┌───────────────┐  ┌───────────────┐                   │   │  │
│  │  │  │ safety-events │  │ sensor-data   │                   │   │  │
│  │  │  │   (이벤트)    │  │   (센서)      │                   │   │  │
│  │  │  └───────┬───────┘  └───────┬───────┘                   │   │  │
│  │  └──────────┼──────────────────┼────────────────────────────┘   │  │
│  │             │                  │                                │  │
│  │             ▼                  ▼                                │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                    │  │
│  │  │ Kinesis Data     │  │ Kinesis Data     │                    │  │
│  │  │ Analytics        │  │ Firehose         │                    │  │
│  │  │ (실시간 분석)    │  │ (장기 저장)      │                    │  │
│  │  └────────┬─────────┘  └────────┬─────────┘                    │  │
│  │           │                     │                               │  │
│  │           ▼                     ▼                               │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                    │  │
│  │  │ Lambda           │  │ S3               │                    │  │
│  │  │ (알림/처리)      │  │ (데이터 레이크)  │                    │  │
│  │  └──────────────────┘  └──────────────────┘                    │  │
│  │                                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │              Kinesis Video Streams                      │   │  │
│  │  │                                                          │   │  │
│  │  │  ┌────────────────────────────────────────────────┐     │   │  │
│  │  │  │  construction-camera-01, 02, 03, ...           │     │   │  │
│  │  │  └───────────────────────┬────────────────────────┘     │   │  │
│  │  └──────────────────────────┼───────────────────────────────┘   │  │
│  │                             │                                   │  │
│  │                             ▼                                   │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │                  분석 및 응용                             │  │  │
│  │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │  │  │
│  │  │  │Rekognition│  │ SageMaker │  │QuickSight │            │  │  │
│  │  │  │  Video    │  │ Endpoint  │  │ Dashboard │            │  │  │
│  │  │  └───────────┘  └───────────┘  └───────────┘            │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 요금 체계

### Kinesis Data Streams 요금

| 항목 | On-Demand 모드 | Provisioned 모드 |
|------|---------------|-----------------|
| 데이터 입력 | $0.08/GB | $0.015/샤드시간 |
| 데이터 출력 | $0.05/GB | 포함 |
| Extended 보존 | $0.02/GB/월 | $0.02/GB/월 |
| Enhanced Fan-Out | $0.013/GB | $0.013/GB |

### 월간 비용 예시

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    월간 예상 비용 (Kinesis)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  시나리오: 중형 공사현장                                                 │
│  ├─ 이벤트 데이터: 100GB/월                                            │
│  ├─ 센서 데이터: 50GB/월                                               │
│  ├─ 비디오 스트림: 5TB/월 (10대 카메라)                                │
│                                                                         │
│  Kinesis Data Streams (On-Demand)                                       │
│  ├─ 입력: 150GB × $0.08 = $12.00                                       │
│  ├─ 출력: 150GB × $0.05 = $7.50                                        │
│  └─ 소계: $19.50                                                        │
│                                                                         │
│  Kinesis Data Firehose                                                  │
│  ├─ 데이터 처리: 150GB × $0.029 = $4.35                                │
│  └─ 소계: $4.35                                                         │
│                                                                         │
│  Kinesis Video Streams                                                  │
│  ├─ 입력: 5TB × $0.0085/GB = $43.52                                    │
│  ├─ 출력: 1TB × $0.0085/GB = $8.70                                     │
│  ├─ 저장 (7일): 5TB × $0.023/GB = $117.76                              │
│  └─ 소계: $169.98                                                       │
│                                                                         │
│  총 예상 비용: 약 $194/월 (약 260,000원)                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 모범 사례

### 성능 최적화

1. **Partition Key 설계**
   - 균등한 데이터 분산을 위해 카디널리티 높은 키 사용
   - device_id, site_id 조합 권장

2. **배치 처리**
   - PutRecords API로 배치 전송 (최대 500개)
   - 네트워크 효율성 향상

3. **재시도 로직**
   - 지수 백오프 적용
   - ProvisionedThroughputExceeded 처리

### 비용 최적화

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    비용 최적화 전략                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 데이터 압축                                                          │
│     • 프로듀서 측에서 GZIP 압축 적용                                     │
│     • 최대 70% 비용 절감 가능                                           │
│                                                                         │
│  2. 적절한 보존 기간                                                     │
│     • 기본 24시간 사용 (추가 비용 없음)                                  │
│     • 장기 보존 필요 시 S3로 이관                                       │
│                                                                         │
│  3. On-Demand vs Provisioned                                            │
│     • 변동이 큰 워크로드: On-Demand                                     │
│     • 예측 가능한 워크로드: Provisioned (30% 저렴)                      │
│                                                                         │
│  4. Enhanced Fan-Out 선택적 사용                                        │
│     • 다수 소비자 필요 시만 활성화                                       │
│     • 단일 소비자는 표준 사용                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [Amazon SageMaker 완벽 가이드](03-sagemaker.md) - ML 모델 개발
2. [Kinesis-SageMaker 연동](../03-integration/03-kinesis-sagemaker.md) - 실시간 추론
