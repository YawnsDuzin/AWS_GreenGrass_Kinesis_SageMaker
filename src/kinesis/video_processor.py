#!/usr/bin/env python3
"""
Kinesis Video Streams 처리기
실시간 비디오 스트림 처리 및 분석
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Generator
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VideoProcessor")


class KinesisVideoProcessor:
    """
    Kinesis Video Streams 처리기
    건설현장 CCTV 영상 처리
    """

    def __init__(
        self,
        stream_name: str,
        region: str = "ap-northeast-2"
    ):
        self.stream_name = stream_name
        self.region = region
        self.kvs_client = boto3.client('kinesisvideo', region_name=region)

    def get_data_endpoint(self, api_name: str = "GET_MEDIA") -> str:
        """
        데이터 엔드포인트 획득

        Args:
            api_name: API 유형 (GET_MEDIA, PUT_MEDIA, GET_HLS_STREAMING_SESSION_URL 등)

        Returns:
            엔드포인트 URL
        """
        response = self.kvs_client.get_data_endpoint(
            StreamName=self.stream_name,
            APIName=api_name
        )
        return response['DataEndpoint']

    def get_hls_url(
        self,
        expires_in: int = 3600,
        playback_mode: str = "LIVE"
    ) -> str:
        """
        HLS 스트리밍 URL 생성

        Args:
            expires_in: URL 만료 시간 (초)
            playback_mode: LIVE 또는 ON_DEMAND

        Returns:
            HLS 스트리밍 URL
        """
        endpoint = self.get_data_endpoint("GET_HLS_STREAMING_SESSION_URL")

        kvam_client = boto3.client(
            'kinesis-video-archived-media',
            endpoint_url=endpoint,
            region_name=self.region
        )

        response = kvam_client.get_hls_streaming_session_url(
            StreamName=self.stream_name,
            PlaybackMode=playback_mode,
            HLSFragmentSelector={
                'FragmentSelectorType': 'PRODUCER_TIMESTAMP' if playback_mode == 'ON_DEMAND' else 'SERVER_TIMESTAMP'
            },
            ContainerFormat='FRAGMENTED_MP4',
            DiscontinuityMode='ALWAYS',
            DisplayFragmentTimestamp='ALWAYS',
            Expires=expires_in
        )

        return response['HLSStreamingSessionURL']

    def get_clip(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: str
    ) -> bool:
        """
        특정 시간대의 비디오 클립 다운로드

        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            output_path: 출력 파일 경로

        Returns:
            성공 여부
        """
        try:
            endpoint = self.get_data_endpoint("GET_CLIP")

            kvam_client = boto3.client(
                'kinesis-video-archived-media',
                endpoint_url=endpoint,
                region_name=self.region
            )

            response = kvam_client.get_clip(
                StreamName=self.stream_name,
                ClipFragmentSelector={
                    'FragmentSelectorType': 'PRODUCER_TIMESTAMP',
                    'TimestampRange': {
                        'StartTimestamp': start_time,
                        'EndTimestamp': end_time
                    }
                }
            )

            # 클립 저장
            with open(output_path, 'wb') as f:
                for chunk in response['Payload'].iter_chunks():
                    f.write(chunk)

            logger.info(f"클립 저장됨: {output_path}")
            return True

        except Exception as e:
            logger.error(f"클립 다운로드 실패: {e}")
            return False

    def create_stream(
        self,
        data_retention_hours: int = 24,
        media_type: str = "video/h264"
    ) -> Dict:
        """
        비디오 스트림 생성

        Args:
            data_retention_hours: 데이터 보존 기간 (시간)
            media_type: 미디어 유형

        Returns:
            생성된 스트림 정보
        """
        try:
            response = self.kvs_client.create_stream(
                StreamName=self.stream_name,
                DataRetentionInHours=data_retention_hours,
                MediaType=media_type,
                Tags={
                    'Project': 'ConstructionSafety',
                    'Environment': 'Production'
                }
            )

            logger.info(f"스트림 생성됨: {self.stream_name}")
            return response

        except self.kvs_client.exceptions.ResourceInUseException:
            logger.info(f"스트림 이미 존재: {self.stream_name}")
            return self.get_stream_info()

    def get_stream_info(self) -> Dict:
        """스트림 정보 조회"""
        response = self.kvs_client.describe_stream(
            StreamName=self.stream_name
        )
        return response['StreamInfo']


class VideoUploader:
    """
    Raspberry Pi에서 Kinesis Video Streams로 업로드
    GStreamer 파이프라인 생성
    """

    @staticmethod
    def get_gstreamer_pipeline(
        stream_name: str,
        region: str = "ap-northeast-2",
        width: int = 640,
        height: int = 480,
        fps: int = 15
    ) -> str:
        """
        GStreamer 파이프라인 명령어 생성 (Raspberry Pi 4)

        Args:
            stream_name: Kinesis Video Streams 이름
            region: AWS 리전
            width: 영상 너비
            height: 영상 높이
            fps: 프레임 레이트

        Returns:
            GStreamer 파이프라인 명령어
        """
        # Raspberry Pi 4 (64-bit) 최적화 파이프라인
        pipeline = f"""
gst-launch-1.0 -v \\
    libcamerasrc ! \\
    video/x-raw,width={width},height={height},framerate={fps}/1 ! \\
    videoconvert ! \\
    video/x-raw,format=I420 ! \\
    x264enc bframes=0 speed-preset=ultrafast tune=zerolatency byte-stream=true ! \\
    video/x-h264,stream-format=avc,alignment=au,profile=baseline ! \\
    kvssink stream-name="{stream_name}" storage-size=512 \\
        aws-region="{region}" \\
        access-key="$AWS_ACCESS_KEY_ID" \\
        secret-key="$AWS_SECRET_ACCESS_KEY"
"""
        return pipeline.strip()

    @staticmethod
    def get_usb_camera_pipeline(
        stream_name: str,
        region: str = "ap-northeast-2",
        device: str = "/dev/video0",
        width: int = 640,
        height: int = 480,
        fps: int = 15
    ) -> str:
        """
        USB 카메라용 GStreamer 파이프라인

        Args:
            stream_name: Kinesis Video Streams 이름
            region: AWS 리전
            device: 카메라 디바이스 경로
            width: 영상 너비
            height: 영상 높이
            fps: 프레임 레이트

        Returns:
            GStreamer 파이프라인 명령어
        """
        pipeline = f"""
gst-launch-1.0 -v \\
    v4l2src device={device} ! \\
    video/x-raw,width={width},height={height},framerate={fps}/1 ! \\
    videoconvert ! \\
    video/x-raw,format=I420 ! \\
    x264enc bframes=0 speed-preset=ultrafast tune=zerolatency ! \\
    h264parse ! \\
    video/x-h264,stream-format=avc,alignment=au ! \\
    kvssink stream-name="{stream_name}" storage-size=512 \\
        aws-region="{region}"
"""
        return pipeline.strip()


class VideoAnalyzer:
    """
    Kinesis Video Streams + Rekognition 통합
    비디오 분석 및 객체 감지
    """

    def __init__(self, region: str = "ap-northeast-2"):
        self.region = region
        self.rekognition = boto3.client('rekognition', region_name=region)

    def start_stream_processor(
        self,
        stream_name: str,
        processor_name: str,
        output_stream: str
    ) -> Dict:
        """
        스트림 프로세서 시작 (Rekognition 연동)

        Args:
            stream_name: 입력 비디오 스트림
            processor_name: 프로세서 이름
            output_stream: 출력 Kinesis 스트림

        Returns:
            프로세서 정보
        """
        response = self.rekognition.create_stream_processor(
            Input={
                'KinesisVideoStream': {
                    'Arn': f'arn:aws:kinesisvideo:{self.region}:*:stream/{stream_name}/*'
                }
            },
            Output={
                'KinesisDataStream': {
                    'Arn': f'arn:aws:kinesis:{self.region}:*:stream/{output_stream}'
                }
            },
            Name=processor_name,
            Settings={
                'FaceSearch': {
                    'CollectionId': 'construction-workers',
                    'FaceMatchThreshold': 80
                }
            },
            RoleArn=f'arn:aws:iam::*:role/RekognitionStreamProcessorRole'
        )

        return response


def main():
    """테스트"""
    processor = KinesisVideoProcessor(
        stream_name="construction-site-1",
        region="ap-northeast-2"
    )

    # 스트림 정보 조회
    info = processor.create_stream()
    print(json.dumps(info, indent=2, default=str))

    # HLS URL 생성
    try:
        hls_url = processor.get_hls_url()
        print(f"HLS URL: {hls_url}")
    except Exception as e:
        print(f"HLS URL 생성 불가: {e}")

    # GStreamer 파이프라인 출력
    print("\n=== Raspberry Pi 4 GStreamer Pipeline ===")
    print(VideoUploader.get_gstreamer_pipeline("construction-site-1"))


if __name__ == "__main__":
    main()
