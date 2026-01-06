#!/usr/bin/env python3
"""
Kinesis Data Streams 실시간 처리기
건설현장 안전 감지 데이터 처리
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Generator
from dataclasses import dataclass, asdict
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KinesisProcessor")


@dataclass
class SafetyEvent:
    """안전 이벤트 데이터"""
    device_id: str
    event_type: str
    timestamp: str
    detections: List[Dict]
    location: str
    severity: str


class KinesisDataProcessor:
    """
    Kinesis Data Streams 데이터 처리기
    실시간으로 안전 감지 데이터를 처리하고 분석
    """

    def __init__(
        self,
        stream_name: str,
        region: str = "ap-northeast-2"
    ):
        self.stream_name = stream_name
        self.region = region
        self.kinesis_client = boto3.client('kinesis', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.sns_client = boto3.client('sns', region_name=region)

    def get_shard_iterator(self, shard_id: str, iterator_type: str = "LATEST") -> str:
        """샤드 반복자 획득"""
        response = self.kinesis_client.get_shard_iterator(
            StreamName=self.stream_name,
            ShardId=shard_id,
            ShardIteratorType=iterator_type
        )
        return response['ShardIterator']

    def get_shard_ids(self) -> List[str]:
        """스트림의 모든 샤드 ID 조회"""
        response = self.kinesis_client.describe_stream(
            StreamName=self.stream_name
        )
        return [shard['ShardId'] for shard in response['StreamDescription']['Shards']]

    def process_records(self, records: List[Dict]) -> List[SafetyEvent]:
        """
        레코드 배치 처리

        Args:
            records: Kinesis 레코드 리스트

        Returns:
            처리된 안전 이벤트 리스트
        """
        events = []

        for record in records:
            try:
                # 데이터 디코딩
                data = json.loads(record['Data'].decode('utf-8'))

                # 이벤트 분류 및 처리
                event = self._classify_event(data)
                if event:
                    events.append(event)

                    # 심각도가 높은 이벤트 알림
                    if event.severity == "HIGH":
                        self._send_alert(event)

            except Exception as e:
                logger.error(f"레코드 처리 오류: {e}")

        return events

    def _classify_event(self, data: Dict) -> SafetyEvent:
        """이벤트 분류 및 심각도 판단"""
        detections = data.get('detections', [])

        # 위반 유형 확인
        violations = [d for d in detections if 'no_' in d.get('class_name', '')]

        if not violations:
            severity = "LOW"
            event_type = "NORMAL"
        elif len(violations) == 1:
            severity = "MEDIUM"
            event_type = "SINGLE_VIOLATION"
        else:
            severity = "HIGH"
            event_type = "MULTIPLE_VIOLATIONS"

        return SafetyEvent(
            device_id=data.get('device_id', 'unknown'),
            event_type=event_type,
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            detections=detections,
            location=data.get('location', 'unknown'),
            severity=severity
        )

    def _send_alert(self, event: SafetyEvent):
        """심각도 높은 이벤트 알림 발송"""
        try:
            message = {
                "alert_type": "SAFETY_VIOLATION",
                "device_id": event.device_id,
                "location": event.location,
                "severity": event.severity,
                "details": event.detections,
                "timestamp": event.timestamp
            }

            self.sns_client.publish(
                TopicArn=f"arn:aws:sns:{self.region}:*:safety-alerts",
                Message=json.dumps(message),
                Subject=f"[ALERT] Safety Violation - {event.location}"
            )
            logger.warning(f"알림 발송: {event.device_id} - {event.severity}")

        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")

    def save_to_dynamodb(self, events: List[SafetyEvent], table_name: str):
        """DynamoDB에 이벤트 저장"""
        table = self.dynamodb.Table(table_name)

        with table.batch_writer() as batch:
            for event in events:
                item = asdict(event)
                item['pk'] = event.device_id
                item['sk'] = event.timestamp
                batch.put_item(Item=item)

        logger.info(f"{len(events)}개 이벤트 저장됨")

    def run_consumer(self, table_name: str = "safety-events"):
        """
        지속적인 데이터 소비 루프

        Args:
            table_name: DynamoDB 테이블명
        """
        logger.info(f"Kinesis Consumer 시작: {self.stream_name}")

        shard_ids = self.get_shard_ids()
        iterators = {
            shard_id: self.get_shard_iterator(shard_id)
            for shard_id in shard_ids
        }

        while True:
            for shard_id, iterator in iterators.items():
                try:
                    response = self.kinesis_client.get_records(
                        ShardIterator=iterator,
                        Limit=100
                    )

                    records = response['Records']
                    if records:
                        events = self.process_records(records)
                        if events:
                            self.save_to_dynamodb(events, table_name)

                    # 다음 반복자 업데이트
                    iterators[shard_id] = response['NextShardIterator']

                except Exception as e:
                    logger.error(f"샤드 {shard_id} 처리 오류: {e}")
                    # 반복자 재획득
                    iterators[shard_id] = self.get_shard_iterator(shard_id)

            # 처리 간격
            time.sleep(1)


class KinesisAnalyticsQuery:
    """
    Kinesis Data Analytics SQL 쿼리 템플릿
    """

    @staticmethod
    def get_realtime_violation_query() -> str:
        """실시간 위반 감지 쿼리"""
        return """
        -- 실시간 안전 위반 감지
        CREATE OR REPLACE STREAM "VIOLATIONS_STREAM" (
            device_id VARCHAR(64),
            violation_type VARCHAR(32),
            violation_count INTEGER,
            window_start TIMESTAMP,
            window_end TIMESTAMP
        );

        CREATE OR REPLACE PUMP "VIOLATIONS_PUMP" AS
        INSERT INTO "VIOLATIONS_STREAM"
        SELECT STREAM
            device_id,
            violation_type,
            COUNT(*) AS violation_count,
            STEP(s.ROWTIME BY INTERVAL '1' MINUTE) AS window_start,
            STEP(s.ROWTIME BY INTERVAL '1' MINUTE) + INTERVAL '1' MINUTE AS window_end
        FROM "SOURCE_SQL_STREAM_001" AS s
        WHERE violation_type IS NOT NULL
        GROUP BY
            device_id,
            violation_type,
            STEP(s.ROWTIME BY INTERVAL '1' MINUTE);
        """

    @staticmethod
    def get_anomaly_detection_query() -> str:
        """이상 감지 쿼리"""
        return """
        -- 이상 감지 (Random Cut Forest)
        CREATE OR REPLACE STREAM "ANOMALY_STREAM" (
            device_id VARCHAR(64),
            anomaly_score DOUBLE,
            detection_time TIMESTAMP
        );

        CREATE OR REPLACE PUMP "ANOMALY_PUMP" AS
        INSERT INTO "ANOMALY_STREAM"
        SELECT STREAM
            device_id,
            ANOMALY_SCORE,
            ROWTIME AS detection_time
        FROM TABLE(
            RANDOM_CUT_FOREST(
                CURSOR(SELECT STREAM * FROM "SOURCE_SQL_STREAM_001"),
                100,  -- subSampleSize
                256,  -- numberOfTrees
                100000,  -- timeDecay
                1  -- shingleSize
            )
        )
        WHERE ANOMALY_SCORE > 2.0;
        """


def main():
    """테스트용 메인 함수"""
    processor = KinesisDataProcessor(
        stream_name="safety-detection-stream",
        region="ap-northeast-2"
    )

    print("Kinesis Data Processor 시작...")
    processor.run_consumer()


if __name__ == "__main__":
    main()
