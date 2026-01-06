#!/usr/bin/env python3
"""
스트림 데이터 내보내기 컴포넌트
로컬에서 수집된 데이터를 Kinesis로 안정적으로 전송
"""

import json
import time
import logging
import argparse
from typing import Dict, List
from datetime import datetime

try:
    from stream_manager import (
        StreamManagerClient,
        MessageStreamDefinition,
        StrategyOnFull,
        ExportDefinition,
        KinesisConfig,
        Persistence,
        ReadMessagesOptions
    )
    STREAM_MANAGER_AVAILABLE = True
except ImportError:
    STREAM_MANAGER_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StreamExporter")


class StreamExporter:
    """스트림 데이터 익스포터"""

    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        self.stream_name = config.get("kinesis_stream_name", "safety-detection-stream")
        self.local_stream = f"local-export-{self.stream_name}"

    def setup(self) -> bool:
        """Stream Manager 설정"""
        if not STREAM_MANAGER_AVAILABLE:
            logger.error("Stream Manager 라이브러리 없음")
            return False

        try:
            self.client = StreamManagerClient()

            # Kinesis 내보내기 스트림 생성
            try:
                self.client.create_message_stream(
                    MessageStreamDefinition(
                        name=self.local_stream,
                        max_size=self.config.get("buffer_size_mb", 256) * 1024 * 1024,
                        stream_segment_size=16 * 1024 * 1024,
                        strategy_on_full=StrategyOnFull.OverwriteOldestData,
                        persistence=Persistence.File,
                        flush_on_write=False,
                        export_definition=ExportDefinition(
                            kinesis=[
                                KinesisConfig(
                                    identifier=f"kinesis-export-{self.stream_name}",
                                    kinesis_stream_name=self.stream_name,
                                    batch_size=self.config.get("batch_size", 100),
                                    batch_interval_millis=self.config.get("batch_interval_ms", 5000)
                                )
                            ]
                        )
                    )
                )
                logger.info(f"스트림 생성됨: {self.local_stream}")
            except Exception as e:
                if "exist" in str(e).lower():
                    logger.info(f"기존 스트림 사용: {self.local_stream}")
                else:
                    raise

            return True

        except Exception as e:
            logger.error(f"설정 실패: {e}")
            return False

    def run(self):
        """메인 루프"""
        logger.info("Stream Exporter 시작")

        while True:
            try:
                # 상태 모니터링
                self._log_status()
                time.sleep(30)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"오류: {e}")
                time.sleep(5)

    def _log_status(self):
        """스트림 상태 로깅"""
        if self.client:
            try:
                info = self.client.describe_message_stream(self.local_stream)
                logger.info(
                    f"스트림 상태: {info.definition.name}, "
                    f"저장된 바이트: {info.storage_status.stored_bytes}"
                )
            except Exception as e:
                logger.warning(f"상태 확인 실패: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="{}")
    args = parser.parse_args()

    config = json.loads(args.config) if args.config else {}

    exporter = StreamExporter(config)
    if exporter.setup():
        exporter.run()


if __name__ == "__main__":
    main()
