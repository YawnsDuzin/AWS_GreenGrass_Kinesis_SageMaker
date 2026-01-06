# 2.1 AWS IoT GreenGrass 완벽 가이드

## 개요

### AWS IoT GreenGrass란?

AWS IoT GreenGrass는 **엣지 컴퓨팅**을 위한 오픈소스 엣지 런타임이자 클라우드 서비스입니다. IoT 디바이스에서 로컬로 데이터를 수집, 처리하고 AWS 클라우드와 원활하게 통신할 수 있게 해줍니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS IoT GreenGrass 개념도                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                         AWS Cloud                               │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │
│   │   │ IoT Core    │  │ Lambda      │  │ S3          │            │  │
│   │   └─────────────┘  └─────────────┘  └─────────────┘            │  │
│   └─────────────────────────────────────┬───────────────────────────┘  │
│                                         │                               │
│                                    Internet                             │
│                                         │                               │
│   ┌─────────────────────────────────────┴───────────────────────────┐  │
│   │                    GreenGrass Core Device                       │  │
│   │   ┌───────────────────────────────────────────────────────┐    │  │
│   │   │              GreenGrass Nucleus (Core)                │    │  │
│   │   ├───────────────────────────────────────────────────────┤    │  │
│   │   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │    │  │
│   │   │  │Component│  │Component│  │Component│  │Component│  │    │  │
│   │   │  │(Lambda) │  │(ML)     │  │(Custom) │  │(Stream) │  │    │  │
│   │   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │    │  │
│   │   └───────────────────────────────────────────────────────┘    │  │
│   │                            │                                    │  │
│   │              ┌─────────────┴─────────────┐                     │  │
│   │              ▼                           ▼                     │  │
│   │        ┌─────────┐               ┌─────────────┐               │  │
│   │        │ Sensor  │               │ IP Camera   │               │  │
│   │        └─────────┘               └─────────────┘               │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### GreenGrass V2 vs V1

| 특성 | GreenGrass V2 (현재) | GreenGrass V1 (레거시) |
|------|---------------------|----------------------|
| 아키텍처 | 모듈형 컴포넌트 | 모놀리식 |
| 배포 | 개별 컴포넌트 배포 | 전체 그룹 배포 |
| 개발 언어 | 모든 언어 지원 | Python, Node.js, Java |
| 오픈소스 | 예 (Apache 2.0) | 아니오 |
| 클라우드 연결 | 필수 아님 | 초기 설정 시 필수 |
| 리소스 | 더 가벼움 | 상대적으로 무거움 |

---

## 핵심 구성요소

### 1. GreenGrass Nucleus

GreenGrass의 핵심 런타임으로, 다른 모든 컴포넌트를 관리합니다.

```yaml
# nucleus 설정 예시 (config.yaml)
system:
  certificateFilePath: "/greengrass/v2/device.pem.crt"
  privateKeyPath: "/greengrass/v2/private.pem.key"
  rootCaPath: "/greengrass/v2/AmazonRootCA1.pem"
  rootpath: "/greengrass/v2"
  thingName: "construction-site-core-01"

services:
  aws.greengrass.Nucleus:
    componentType: "NUCLEUS"
    version: "2.12.0"
    configuration:
      awsRegion: "ap-northeast-2"
      iotRoleAlias: "GreengrassCoreTokenExchangeRoleAlias"
      iotDataEndpoint: "xxxxxx-ats.iot.ap-northeast-2.amazonaws.com"
      iotCredEndpoint: "xxxxxx.credentials.iot.ap-northeast-2.amazonaws.com"
```

### 2. 컴포넌트 (Components)

GreenGrass에서 실행되는 소프트웨어 모듈입니다.

#### 컴포넌트 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| **Nucleus** | 핵심 런타임 | aws.greengrass.Nucleus |
| **AWS 제공** | AWS에서 제공하는 컴포넌트 | StreamManager, MLInference |
| **커스텀** | 사용자 정의 컴포넌트 | SafetyDetection, DataFilter |
| **커뮤니티** | 오픈소스 커뮤니티 제공 | 다양한 프로토콜 어댑터 |

#### 컴포넌트 레시피 예시

```yaml
# recipe.yaml - 안전 감지 컴포넌트
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.construction.SafetyDetection
ComponentVersion: '1.0.0'
ComponentDescription: '안전장비 착용 감지 컴포넌트'
ComponentPublisher: 'Construction Safety Inc.'

ComponentDependencies:
  aws.greengrass.StreamManager:
    VersionRequirement: ">=2.0.0 <3.0.0"
    DependencyType: HARD
  aws.greengrass.TokenExchangeService:
    VersionRequirement: ">=2.0.0"
    DependencyType: HARD

ComponentConfiguration:
  DefaultConfiguration:
    modelPath: "/greengrass/v2/models/safety_detection.onnx"
    confidenceThreshold: 0.8
    inferenceInterval: 100  # ms
    cameraSource: "rtsp://192.168.1.100:554/stream1"

Manifests:
  - Platform:
      os: linux
      architecture: aarch64
    Lifecycle:
      Install:
        RequiresPrivilege: true
        Script: |
          pip3 install -r {artifacts:path}/requirements.txt
      Run:
        RequiresPrivilege: false
        Script: |
          python3 {artifacts:path}/safety_detector.py \
            --model {configuration:/modelPath} \
            --threshold {configuration:/confidenceThreshold}
    Artifacts:
      - URI: s3://my-bucket/artifacts/safety-detection/1.0.0/safety_detector.zip
        Unarchive: ZIP
```

### 3. Stream Manager

대용량 데이터를 효율적으로 AWS 클라우드로 전송하는 컴포넌트입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Stream Manager 아키텍처                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    GreenGrass Core Device                       │  │
│   │                                                                  │  │
│   │   ┌─────────┐   ┌─────────┐   ┌─────────┐                       │  │
│   │   │Component│   │Component│   │Component│                       │  │
│   │   │    A    │   │    B    │   │    C    │                       │  │
│   │   └────┬────┘   └────┬────┘   └────┬────┘                       │  │
│   │        │             │             │                             │  │
│   │        └─────────────┼─────────────┘                             │  │
│   │                      ▼                                           │  │
│   │   ┌─────────────────────────────────────────────────────────┐   │  │
│   │   │              Stream Manager                             │   │  │
│   │   │  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │   │  │
│   │   │  │ Stream1 │  │ Stream2 │  │ Stream3 │                 │   │  │
│   │   │  │ (video) │  │ (sensor)│  │ (event) │                 │   │  │
│   │   │  └─────────┘  └─────────┘  └─────────┘                 │   │  │
│   │   │                                                         │   │  │
│   │   │  Features:                                              │   │  │
│   │   │  • 자동 재시도 & 지수 백오프                            │   │  │
│   │   │  • 로컬 버퍼링 (연결 끊김 시)                           │   │  │
│   │   │  • 대역폭 관리                                          │   │  │
│   │   │  • 우선순위 기반 전송                                   │   │  │
│   │   └────────────────────────┬────────────────────────────────┘   │  │
│   │                            │                                    │  │
│   └────────────────────────────┼────────────────────────────────────┘  │
│                                │                                        │
│                           Internet                                      │
│                                │                                        │
│   ┌────────────────────────────┴────────────────────────────────────┐  │
│   │                       AWS Cloud                                 │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │
│   │   │ Kinesis     │  │ IoT         │  │ S3          │            │  │
│   │   │ Data Streams│  │ Analytics   │  │             │            │  │
│   │   └─────────────┘  └─────────────┘  └─────────────┘            │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Stream Manager 코드 예시

```python
# stream_manager_client.py
from stream_manager import (
    StreamManagerClient,
    ExportDefinition,
    KinesisConfig,
    MessageStreamDefinition,
    StrategyOnFull,
    Persistence
)

def setup_stream_manager():
    client = StreamManagerClient()

    # Kinesis로 내보내기 설정
    kinesis_export = ExportDefinition(
        kinesis=[
            KinesisConfig(
                identifier="KinesisExport",
                kinesis_stream_name="construction-safety-stream",
                batch_size=500,
                batch_interval_millis=1000
            )
        ]
    )

    # 스트림 생성
    client.create_message_stream(
        MessageStreamDefinition(
            name="SafetyEventStream",
            max_size=268435456,  # 256 MB
            stream_segment_size=16777216,  # 16 MB
            time_to_live_millis=3600000,  # 1 hour
            strategy_on_full=StrategyOnFull.OverwriteOldestData,
            persistence=Persistence.File,
            flush_on_write=False,
            export_definition=kinesis_export
        )
    )

    return client

def send_event(client, event_data):
    """이벤트를 스트림에 전송"""
    import json
    client.append_message(
        stream_name="SafetyEventStream",
        data=json.dumps(event_data).encode()
    )
```

### 4. ML Inference (기계학습 추론)

엣지 디바이스에서 ML 모델을 실행합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    엣지 ML 추론 파이프라인                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────┐     ┌─────────────────────────────────────────────────┐  │
│   │ Camera  │────▶│           GreenGrass ML Component              │  │
│   │ Input   │     │                                                 │  │
│   └─────────┘     │   ┌─────────────────────────────────────────┐  │  │
│                   │   │        Pre-processing                    │  │  │
│                   │   │  • 이미지 리사이징 (640x640)             │  │  │
│                   │   │  • 정규화                                │  │  │
│                   │   │  • 텐서 변환                             │  │  │
│                   │   └──────────────────┬──────────────────────┘  │  │
│                   │                      │                          │  │
│                   │                      ▼                          │  │
│                   │   ┌─────────────────────────────────────────┐  │  │
│                   │   │        ML Inference Engine              │  │  │
│                   │   │  • TensorFlow Lite                      │  │  │
│                   │   │  • ONNX Runtime                         │  │  │
│                   │   │  • PyTorch (TorchScript)                │  │  │
│                   │   │  • Amazon SageMaker Neo                 │  │  │
│                   │   └──────────────────┬──────────────────────┘  │  │
│                   │                      │                          │  │
│                   │                      ▼                          │  │
│                   │   ┌─────────────────────────────────────────┐  │  │
│                   │   │        Post-processing                  │  │  │
│                   │   │  • NMS (Non-Maximum Suppression)        │  │  │
│                   │   │  • 바운딩 박스 추출                      │  │  │
│                   │   │  • 클래스 분류                           │  │  │
│                   │   └──────────────────┬──────────────────────┘  │  │
│                   │                      │                          │  │
│                   └──────────────────────┼──────────────────────────┘  │
│                                          ▼                              │
│                   ┌─────────────────────────────────────────────────┐  │
│                   │  Detection Results                              │  │
│                   │  • person: 0.95, bbox: [100,200,300,400]       │  │
│                   │  • helmet: 0.92, bbox: [110,200,150,250]       │  │
│                   │  • no_vest: 0.88, bbox: [100,250,300,400]      │  │
│                   └─────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 하드웨어 요구사항

### 지원 디바이스

| 카테고리 | 디바이스 | CPU | RAM | 저장소 | GPU |
|----------|----------|-----|-----|--------|-----|
| **추천** | NVIDIA Jetson Xavier NX | 6-core ARM | 8GB | 16GB+ | 384 CUDA |
| **추천** | NVIDIA Jetson Orin Nano | 6-core ARM | 8GB | 16GB+ | 1024 CUDA |
| **표준** | Raspberry Pi 4 | 4-core ARM | 4GB+ | 32GB+ | 없음 |
| **산업용** | Intel NUC | i5/i7 | 16GB+ | 256GB+ | 옵션 |
| **AWS** | AWS Panorama | 4-core ARM | 4GB | 32GB | 2 NVDLA |

### 운영체제 요구사항

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    지원 운영체제                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Linux (권장)                                                            │
│  ├─ Ubuntu 18.04, 20.04, 22.04                                         │
│  ├─ Amazon Linux 2                                                      │
│  ├─ Debian 10, 11                                                       │
│  ├─ Raspberry Pi OS (64-bit)                                           │
│  └─ NVIDIA JetPack 4.x, 5.x                                            │
│                                                                         │
│  Windows (제한적)                                                        │
│  └─ Windows 10/11 (개발/테스트용)                                       │
│                                                                         │
│  필수 요구사항                                                           │
│  ├─ Java 8 이상 (Corretto 권장)                                        │
│  ├─ Python 3.7 이상                                                    │
│  ├─ 256MB RAM (최소), 1GB+ (권장)                                       │
│  └─ 1GB 디스크 공간 (최소)                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 공사현장 적용 시나리오

### 시나리오 1: 안전장비 미착용 감지

```python
# safety_detection_component.py
import cv2
import numpy as np
import onnxruntime as ort
from stream_manager import StreamManagerClient
import json
import time

class SafetyDetector:
    def __init__(self, model_path, confidence_threshold=0.8):
        self.session = ort.InferenceSession(model_path)
        self.threshold = confidence_threshold
        self.stream_client = StreamManagerClient()

        # 클래스 정의
        self.classes = {
            0: 'person',
            1: 'helmet',
            2: 'no_helmet',
            3: 'vest',
            4: 'no_vest',
            5: 'safety_harness',
            6: 'no_harness'
        }

    def preprocess(self, frame):
        """이미지 전처리"""
        img = cv2.resize(frame, (640, 640))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img

    def detect(self, frame):
        """객체 감지 수행"""
        input_tensor = self.preprocess(frame)

        outputs = self.session.run(
            None,
            {'images': input_tensor}
        )

        detections = self.postprocess(outputs, frame.shape)
        return detections

    def postprocess(self, outputs, original_shape):
        """후처리: NMS 및 좌표 변환"""
        # YOLO 출력 처리
        detections = []
        for output in outputs[0]:
            confidence = output[4]
            if confidence > self.threshold:
                class_id = np.argmax(output[5:])
                box = output[:4]
                detections.append({
                    'class': self.classes.get(class_id, 'unknown'),
                    'confidence': float(confidence),
                    'bbox': box.tolist()
                })
        return detections

    def check_safety_violations(self, detections):
        """안전 위반 확인"""
        violations = []
        persons = [d for d in detections if d['class'] == 'person']

        for person in persons:
            person_box = person['bbox']

            # 해당 사람 영역에서 안전장비 확인
            has_helmet = any(
                d['class'] == 'helmet' and self._overlap(d['bbox'], person_box)
                for d in detections
            )
            has_vest = any(
                d['class'] == 'vest' and self._overlap(d['bbox'], person_box)
                for d in detections
            )

            if not has_helmet:
                violations.append({
                    'type': 'NO_HELMET',
                    'severity': 'HIGH',
                    'location': person_box
                })
            if not has_vest:
                violations.append({
                    'type': 'NO_VEST',
                    'severity': 'MEDIUM',
                    'location': person_box
                })

        return violations

    def _overlap(self, box1, box2):
        """두 박스의 겹침 여부 확인"""
        # IoU 계산 또는 간단한 겹침 확인
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x1 < x2 and y1 < y2:
            return True
        return False

    def send_alert(self, violations, frame_id):
        """알림 전송"""
        if violations:
            event = {
                'timestamp': time.time(),
                'frame_id': frame_id,
                'device_id': 'construction-site-cam-01',
                'violations': violations,
                'total_violations': len(violations)
            }

            self.stream_client.append_message(
                stream_name="SafetyEventStream",
                data=json.dumps(event).encode()
            )

            print(f"Alert sent: {len(violations)} violations detected")

def main():
    detector = SafetyDetector(
        model_path="/greengrass/v2/models/safety_yolov8.onnx",
        confidence_threshold=0.8
    )

    # RTSP 스트림 연결
    cap = cv2.VideoCapture("rtsp://192.168.1.100:554/stream1")

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 감지 수행
        detections = detector.detect(frame)

        # 안전 위반 확인
        violations = detector.check_safety_violations(detections)

        # 위반 시 알림
        if violations:
            detector.send_alert(violations, frame_id)

        frame_id += 1
        time.sleep(0.1)  # 10 FPS

if __name__ == "__main__":
    main()
```

### 시나리오 2: 위험 구역 침입 감지

```python
# danger_zone_monitor.py
import cv2
import numpy as np
from shapely.geometry import Point, Polygon
import json

class DangerZoneMonitor:
    def __init__(self):
        # 위험 구역 정의 (다각형 좌표)
        self.danger_zones = {
            'crane_area': Polygon([
                (100, 100), (300, 100), (300, 400), (100, 400)
            ]),
            'excavation': Polygon([
                (500, 200), (700, 200), (700, 500), (500, 500)
            ]),
            'high_voltage': Polygon([
                (800, 100), (900, 100), (900, 300), (800, 300)
            ])
        }

        self.zone_severity = {
            'crane_area': 'HIGH',
            'excavation': 'CRITICAL',
            'high_voltage': 'CRITICAL'
        }

    def check_intrusion(self, person_detections):
        """위험 구역 침입 확인"""
        intrusions = []

        for person in person_detections:
            # 사람의 중심점 계산
            bbox = person['bbox']
            center = Point(
                (bbox[0] + bbox[2]) / 2,
                (bbox[1] + bbox[3]) / 2
            )

            # 각 위험 구역 확인
            for zone_name, zone_polygon in self.danger_zones.items():
                if zone_polygon.contains(center):
                    intrusions.append({
                        'zone': zone_name,
                        'severity': self.zone_severity[zone_name],
                        'person_location': [center.x, center.y]
                    })

        return intrusions

    def visualize(self, frame):
        """프레임에 위험 구역 표시"""
        for zone_name, zone_polygon in self.danger_zones.items():
            coords = np.array(zone_polygon.exterior.coords, dtype=np.int32)

            # 위험도에 따른 색상
            if self.zone_severity[zone_name] == 'CRITICAL':
                color = (0, 0, 255)  # 빨강
            else:
                color = (0, 165, 255)  # 주황

            cv2.polylines(frame, [coords], True, color, 2)
            cv2.putText(frame, zone_name, tuple(coords[0]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return frame
```

---

## 배포 및 관리

### CLI를 통한 배포

```bash
# 1. AWS CLI 설정
aws configure

# 2. GreenGrass 설치 (디바이스에서)
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller

# 3. 프로비저닝 및 설치
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --aws-region ap-northeast-2 \
  --thing-name construction-site-core-01 \
  --thing-group-name ConstructionSiteGroup \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true

# 4. 컴포넌트 배포
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:ap-northeast-2:123456789012:thinggroup/ConstructionSiteGroup" \
  --components '{
    "com.construction.SafetyDetection": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "merge": "{\"confidenceThreshold\": 0.85}"
      }
    }
  }'
```

### 배포 상태 확인

```bash
# 배포 상태 확인
aws greengrassv2 list-effective-deployments \
  --core-device-thing-name construction-site-core-01

# 컴포넌트 상태 확인
aws greengrassv2 list-installed-components \
  --core-device-thing-name construction-site-core-01

# 로그 확인 (디바이스에서)
sudo tail -f /greengrass/v2/logs/com.construction.SafetyDetection.log
```

---

## 모니터링 및 트러블슈팅

### CloudWatch 메트릭

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GreenGrass CloudWatch 메트릭                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  시스템 메트릭                                                           │
│  ├─ SystemMemoryUsage: 메모리 사용량                                    │
│  ├─ SystemDiskUsage: 디스크 사용량                                      │
│  └─ SystemCpuUsage: CPU 사용률                                          │
│                                                                         │
│  컴포넌트 메트릭                                                         │
│  ├─ NumberOfComponentsInstalled: 설치된 컴포넌트 수                     │
│  ├─ NumberOfComponentsRunning: 실행 중인 컴포넌트 수                    │
│  └─ NumberOfComponentsErrored: 오류 발생 컴포넌트 수                    │
│                                                                         │
│  연결 메트릭                                                             │
│  ├─ ConnectedClientDevices: 연결된 클라이언트 디바이스 수               │
│  └─ MqttClientState: MQTT 클라이언트 상태                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 일반적인 문제 해결

| 문제 | 원인 | 해결 방법 |
|------|------|-----------|
| 컴포넌트 시작 실패 | 의존성 누락 | 로그 확인 후 의존성 설치 |
| 클라우드 연결 실패 | 인증서/네트워크 문제 | 인증서 확인, 방화벽 설정 |
| ML 추론 느림 | 하드웨어 부족 | GPU 활성화, 모델 최적화 |
| 메모리 부족 | 컴포넌트 과다 | 불필요 컴포넌트 제거 |

---

## 요금 체계

### GreenGrass 요금 (2024년 기준)

| 항목 | 요금 | 비고 |
|------|------|------|
| GreenGrass Core | $0.16/디바이스/월 | 코어 디바이스당 |
| 클라이언트 디바이스 | $0.003/디바이스/월 | 연결된 디바이스당 |
| 메시지 | $1.00/백만 메시지 | IoT Core 요금 |

### 예상 비용 (월간)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    월간 예상 비용 (현장 1개 기준)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  구성                                                                    │
│  ├─ GreenGrass Core: 1대                                               │
│  ├─ 카메라: 10대                                                        │
│  ├─ 센서: 50개                                                          │
│  └─ 메시지: 1,000만/월                                                  │
│                                                                         │
│  비용 산출                                                               │
│  ├─ GreenGrass Core: $0.16 × 1 = $0.16                                 │
│  ├─ 클라이언트 디바이스: $0.003 × 60 = $0.18                           │
│  ├─ IoT Core 메시지: $1.00 × 10 = $10.00                               │
│  └─ 합계: 약 $10.34/월 (약 14,000원)                                   │
│                                                                         │
│  ※ 하드웨어 비용은 별도                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [Amazon Kinesis 완벽 가이드](02-kinesis.md) - 실시간 데이터 스트리밍
2. [GreenGrass-Kinesis 연동](../03-integration/02-greengrass-kinesis.md) - 통합 구성
