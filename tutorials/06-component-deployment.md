# Part 6: GreenGrass 컴포넌트 개발 및 배포

이 파트에서는 PPE 감지 컴포넌트를 개발하고 Raspberry Pi에 배포합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] GreenGrass 컴포넌트 구조 이해
- [x] PPE 감지 컴포넌트 개발
- [x] 컴포넌트 레시피 작성
- [x] 컴포넌트 아티팩트 업로드
- [x] 배포 생성 및 실행

---

## 1. 컴포넌트 구조 이해

### 1.1 GreenGrass V2 컴포넌트 개요

```
컴포넌트 = 레시피 + 아티팩트

├── recipe.yaml          # 컴포넌트 정의 (메타데이터, 라이프사이클)
└── artifacts/
    ├── ppe_detector.py  # 메인 코드
    ├── requirements.txt # 의존성
    └── models/
        └── model.onnx   # ONNX 모델
```

### 1.2 컴포넌트 레시피 구조

```yaml
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.MyComponent
ComponentVersion: '1.0.0'
ComponentDescription: 설명
ComponentPublisher: 게시자

# 설정 (런타임에 변경 가능)
ComponentConfiguration:
  DefaultConfiguration:
    key: value

# 의존성
ComponentDependencies:
  aws.greengrass.StreamManager:
    VersionRequirement: ">=2.0.0"

# 플랫폼별 라이프사이클
Manifests:
  - Platform:
      os: linux
      architecture: aarch64
    Lifecycle:
      Install: 설치 스크립트
      Run: 실행 스크립트
      Shutdown: 종료 스크립트
    Artifacts:
      - URI: s3://bucket/artifact.zip
```

---

## 2. 개발 환경 준비

### 2.1 PC에서 프로젝트 구조 생성

```bash
# 작업 디렉토리
mkdir -p ~/ppe-component
cd ~/ppe-component

# 디렉토리 구조
mkdir -p artifacts/models
mkdir -p recipes
```

### 2.2 S3 버킷 확인

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
COMPONENT_BUCKET="ppe-detection-models-${ACCOUNT_ID}"

# 버킷 존재 확인
aws s3 ls s3://${COMPONENT_BUCKET}/
```

---

## 3. PPE 감지 코드 작성

### 3.1 메인 감지 코드

```bash
cat > artifacts/ppe_detector.py << 'PYEOF'
#!/usr/bin/env python3
"""
PPE 감지 컴포넌트
Raspberry Pi 4 (64-bit) + GreenGrass V2
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import threading
from queue import Queue

import cv2
import numpy as np

# GreenGrass IPC
try:
    import awsiot.greengrasscoreipc
    from awsiot.greengrasscoreipc.model import (
        PublishToIoTCoreRequest,
        QOS
    )
    GG_AVAILABLE = True
except ImportError:
    GG_AVAILABLE = False

# Stream Manager
try:
    from stream_manager import StreamManagerClient
    from stream_manager.util import Util
    SM_AVAILABLE = True
except ImportError:
    SM_AVAILABLE = False

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("PPEDetector")


@dataclass
class Detection:
    """감지 결과"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]


class ONNXDetector:
    """ONNX 모델 추론기"""

    CLASS_NAMES = {
        0: 'person',
        1: 'hardhat',
        2: 'safety_vest',
        3: 'safety_shoes',
        4: 'no_hardhat',
        5: 'no_safety_vest'
    }

    def __init__(self, model_path: str, conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold

        logger.info(f"모델 로딩: {model_path}")

        # OpenCV DNN 사용
        self.net = cv2.dnn.readNetFromONNX(model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        logger.info("모델 로딩 완료")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """객체 감지"""
        h, w = frame.shape[:2]

        # 전처리
        blob = cv2.dnn.blobFromImage(
            frame, 1/255.0, (640, 640),
            swapRB=True, crop=False
        )

        # 추론
        self.net.setInput(blob)
        outputs = self.net.forward()[0].T

        # 후처리
        detections = []
        for output in outputs:
            x, y, w_box, h_box = output[:4]
            scores = output[4:]
            class_id = np.argmax(scores)
            conf = scores[class_id]

            if conf >= self.conf_threshold:
                x1 = int((x - w_box/2) * w / 640)
                y1 = int((y - h_box/2) * h / 640)
                x2 = int((x + w_box/2) * w / 640)
                y2 = int((y + h_box/2) * h / 640)

                detections.append(Detection(
                    class_id=int(class_id),
                    class_name=self.CLASS_NAMES.get(int(class_id), 'unknown'),
                    confidence=float(conf),
                    bbox=(x1, y1, x2-x1, y2-y1)
                ))

        return detections


class CameraCapture:
    """카메라 캡처"""

    def __init__(self, source: int = 0, width: int = 640, height: int = 480, fps: int = 15):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.running = False
        self.frame_queue = Queue(maxsize=2)

    def start(self) -> bool:
        """카메라 시작"""
        try:
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                logger.error("카메라 열기 실패")
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            self.running = True
            threading.Thread(target=self._capture_loop, daemon=True).start()

            logger.info(f"카메라 시작: {self.width}x{self.height}@{self.fps}fps")
            return True

        except Exception as e:
            logger.error(f"카메라 초기화 실패: {e}")
            return False

    def _capture_loop(self):
        """캡처 루프"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                self.frame_queue.put(frame)

    def read(self) -> np.ndarray:
        """프레임 읽기"""
        try:
            return self.frame_queue.get(timeout=1.0)
        except:
            return None

    def stop(self):
        """카메라 정지"""
        self.running = False
        if self.cap:
            self.cap.release()


class IoTPublisher:
    """IoT Core 발행"""

    def __init__(self, topic_prefix: str = "construction/safety"):
        self.topic_prefix = topic_prefix
        self.ipc_client = None

        if GG_AVAILABLE:
            try:
                self.ipc_client = awsiot.greengrasscoreipc.connect()
                logger.info("IoT Core IPC 연결 완료")
            except Exception as e:
                logger.error(f"IPC 연결 실패: {e}")

    def publish(self, device_id: str, data: Dict):
        """메시지 발행"""
        topic = f"{self.topic_prefix}/{device_id}/detections"
        payload = json.dumps(data, ensure_ascii=False).encode()

        if self.ipc_client:
            try:
                request = PublishToIoTCoreRequest(
                    topic_name=topic,
                    qos=QOS.AT_LEAST_ONCE,
                    payload=payload
                )
                op = self.ipc_client.new_publish_to_iot_core()
                op.activate(request)
                op.get_response().result(timeout=5.0)
            except Exception as e:
                logger.error(f"발행 실패: {e}")
        else:
            logger.info(f"[LOCAL] {topic}: {data}")


class PPEDetectorApp:
    """메인 애플리케이션"""

    def __init__(self, config: Dict):
        self.config = config
        self.device_id = os.environ.get('AWS_IOT_THING_NAME', 'ppe-detector-rpi4')
        self.running = False
        self.frame_count = 0

        # 컴포넌트 초기화
        self.camera = CameraCapture(
            source=config.get('camera_index', 0),
            width=config.get('width', 640),
            height=config.get('height', 480),
            fps=config.get('fps', 15)
        )

        self.detector = ONNXDetector(
            model_path=config.get('model_path', 'model.onnx'),
            conf_threshold=config.get('confidence', 0.5)
        )

        self.publisher = IoTPublisher()

    def run(self):
        """메인 루프"""
        logger.info(f"=== PPE 감지 시작 ({self.device_id}) ===")

        if not self.camera.start():
            logger.error("카메라 시작 실패")
            return

        self.running = True
        fps_time = time.time()
        fps_count = 0

        while self.running:
            try:
                frame = self.camera.read()
                if frame is None:
                    continue

                self.frame_count += 1
                fps_count += 1

                # 감지
                start = time.time()
                detections = self.detector.detect(frame)
                inference_time = (time.time() - start) * 1000

                # 결과 발행
                if detections:
                    data = {
                        "device_id": self.device_id,
                        "timestamp": datetime.now().isoformat(),
                        "frame_id": self.frame_count,
                        "inference_ms": round(inference_time, 1),
                        "detections": [asdict(d) for d in detections]
                    }
                    self.publisher.publish(self.device_id, data)

                    # 위반 로깅
                    violations = [d for d in detections if 'no_' in d.class_name]
                    if violations:
                        logger.warning(f"⚠️ 위반 감지: {[v.class_name for v in violations]}")

                # FPS 표시
                elapsed = time.time() - fps_time
                if elapsed >= 5.0:
                    fps = fps_count / elapsed
                    logger.info(f"FPS: {fps:.1f}, 추론: {inference_time:.1f}ms")
                    fps_time = time.time()
                    fps_count = 0

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"처리 오류: {e}")
                time.sleep(1)

        self.stop()

    def stop(self):
        """종료"""
        logger.info("종료 중...")
        self.running = False
        self.camera.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='{}')
    args = parser.parse_args()

    # 설정 파싱
    try:
        config = json.loads(args.config)
    except:
        config = {}

    # 기본 설정
    defaults = {
        'camera_index': 0,
        'width': 640,
        'height': 480,
        'fps': 15,
        'model_path': '/greengrass/v2/packages/artifacts/com.ppe.Detector/1.0.0/models/model.onnx',
        'confidence': 0.5
    }

    config = {**defaults, **config}

    # 실행
    app = PPEDetectorApp(config)
    app.run()


if __name__ == "__main__":
    main()
PYEOF
```

### 3.2 requirements.txt

```bash
cat > artifacts/requirements.txt << 'EOF'
numpy>=1.21.0
awsiotsdk>=1.12.0
awscrt>=0.16.0
python-dateutil>=2.8.0
EOF
```

---

## 4. 컴포넌트 레시피 작성

### 4.1 레시피 파일

```bash
cat > recipes/com.ppe.Detector-1.0.0.yaml << 'EOF'
---
RecipeFormatVersion: "2020-01-25"

ComponentName: com.ppe.Detector
ComponentVersion: "1.0.0"
ComponentDescription: |
  PPE(개인보호장비) 감지 컴포넌트
  - YOLOv8 기반 실시간 감지
  - Raspberry Pi 4 (64-bit) 최적화

ComponentPublisher: ConstructionSafety

ComponentConfiguration:
  DefaultConfiguration:
    camera_index: 0
    width: 640
    height: 480
    fps: 15
    confidence: 0.5

ComponentDependencies:
  aws.greengrass.StreamManager:
    VersionRequirement: ">=2.0.0"
    DependencyType: SOFT
  aws.greengrass.TokenExchangeService:
    VersionRequirement: ">=2.0.0"
    DependencyType: HARD

Manifests:
  - Platform:
      os: linux
      architecture: aarch64
    Lifecycle:
      Install:
        RequiresPrivilege: true
        Script: |
          #!/bin/bash
          set -e
          echo "=== PPE Detector 설치 ==="

          # Python 가상환경 생성
          python3 -m venv {artifacts:path}/venv

          # 패키지 설치
          {artifacts:path}/venv/bin/pip install --upgrade pip
          {artifacts:path}/venv/bin/pip install -r {artifacts:path}/requirements.txt

          # 카메라 권한
          usermod -aG video ggc_user || true

          echo "=== 설치 완료 ==="

      Run:
        Script: |
          #!/bin/bash
          cd {artifacts:path}

          export OPENBLAS_NUM_THREADS=4
          export OMP_NUM_THREADS=4

          {artifacts:path}/venv/bin/python3 {artifacts:path}/ppe_detector.py \
            --config '{configuration:/}'

      Shutdown:
        Script: |
          #!/bin/bash
          pkill -f "ppe_detector.py" || true

    Artifacts:
      - URI: s3://BUCKET_NAME/components/com.ppe.Detector/1.0.0/ppe_detector.zip
        Unarchive: ZIP
        Permission:
          Read: OWNER
          Execute: OWNER
EOF
```

---

## 5. 아티팩트 패키징 및 업로드

### 5.1 ONNX 모델 다운로드

```bash
# S3에서 모델 다운로드
aws s3 cp s3://${COMPONENT_BUCKET}/models/v1/model.onnx artifacts/models/
```

### 5.2 아티팩트 압축

```bash
cd artifacts
zip -r ../ppe_detector.zip .
cd ..

# 확인
unzip -l ppe_detector.zip
```

### 5.3 S3 업로드

```bash
# 아티팩트 업로드
aws s3 cp ppe_detector.zip \
    s3://${COMPONENT_BUCKET}/components/com.ppe.Detector/1.0.0/ppe_detector.zip

# 레시피의 버킷 이름 치환
sed -i "s/BUCKET_NAME/${COMPONENT_BUCKET}/g" recipes/com.ppe.Detector-1.0.0.yaml

# 레시피 업로드
aws s3 cp recipes/com.ppe.Detector-1.0.0.yaml \
    s3://${COMPONENT_BUCKET}/components/com.ppe.Detector/1.0.0/recipe.yaml

# 확인
aws s3 ls s3://${COMPONENT_BUCKET}/components/com.ppe.Detector/1.0.0/
```

---

## 6. 컴포넌트 등록

### 6.1 GreenGrass에 컴포넌트 등록

```bash
# 컴포넌트 생성
aws greengrassv2 create-component-version \
    --inline-recipe fileb://recipes/com.ppe.Detector-1.0.0.yaml \
    --region ap-northeast-2
```

### 6.2 등록 확인

```bash
aws greengrassv2 list-components \
    --query 'components[?componentName==`com.ppe.Detector`]'
```

---

## 7. 배포 생성 및 실행

### 7.1 배포 설정 파일

```bash
cat > deployment.json << EOF
{
    "targetArn": "arn:aws:iot:ap-northeast-2:${ACCOUNT_ID}:thing/ppe-detector-rpi4",
    "deploymentName": "ppe-detector-deployment-v1",
    "components": {
        "com.ppe.Detector": {
            "componentVersion": "1.0.0",
            "configurationUpdate": {
                "merge": "{\"camera_index\":0,\"fps\":15,\"confidence\":0.5}"
            }
        },
        "aws.greengrass.StreamManager": {
            "componentVersion": "2.1.0"
        }
    }
}
EOF
```

### 7.2 배포 실행

```bash
aws greengrassv2 create-deployment \
    --cli-input-json file://deployment.json \
    --region ap-northeast-2
```

### 7.3 배포 상태 확인

```bash
# 배포 목록
aws greengrassv2 list-deployments \
    --target-arn "arn:aws:iot:ap-northeast-2:${ACCOUNT_ID}:thing/ppe-detector-rpi4"

# 상태 확인 (Raspberry Pi에서)
ssh pi@ppe-detector.local "sudo greengrass-cli component list"
```

---

## 8. Raspberry Pi에서 확인

### 8.1 SSH 접속

```bash
ssh pi@ppe-detector.local
```

### 8.2 컴포넌트 상태 확인

```bash
# 컴포넌트 목록
sudo greengrass-cli component list

# PPE Detector 상태
sudo greengrass-cli component details -n com.ppe.Detector
```

### 8.3 로그 확인

```bash
# 컴포넌트 로그
sudo tail -f /greengrass/v2/logs/com.ppe.Detector.log

# 또는
sudo greengrass-cli logs get -n com.ppe.Detector
```

예상 로그:
```
2024-01-15 10:30:00 [INFO] === PPE 감지 시작 (ppe-detector-rpi4) ===
2024-01-15 10:30:01 [INFO] 모델 로딩: /greengrass/.../model.onnx
2024-01-15 10:30:02 [INFO] 모델 로딩 완료
2024-01-15 10:30:03 [INFO] 카메라 시작: 640x480@15fps
2024-01-15 10:30:08 [INFO] FPS: 12.3, 추론: 85.2ms
2024-01-15 10:30:10 [WARNING] ⚠️ 위반 감지: ['no_hardhat']
```

---

## 9. AWS 콘솔에서 확인

### 9.1 IoT Core MQTT 테스트

1. IoT Core → **테스트** → **MQTT 테스트 클라이언트**
2. 구독: `construction/safety/#`
3. 메시지 수신 확인

### 9.2 CloudWatch 로그

1. CloudWatch → **로그 그룹**
2. `/aws/greengrass/GreengrassSystemComponent/ppe-detector-rpi4`
3. 로그 스트림에서 상세 로그 확인

---

## ✅ 체크리스트

- [ ] 컴포넌트 코드 작성 완료
- [ ] 아티팩트 ZIP 생성 및 S3 업로드
- [ ] 컴포넌트 레시피 작성
- [ ] GreenGrass에 컴포넌트 등록
- [ ] 배포 생성 및 실행
- [ ] Raspberry Pi에서 컴포넌트 실행 확인
- [ ] IoT Core에서 메시지 수신 확인

---

## 🔧 문제 해결

### Q: 컴포넌트가 시작되지 않음

```bash
# 로그 확인
sudo tail -100 /greengrass/v2/logs/com.ppe.Detector.log

# 권한 확인
sudo -u ggc_user ls /greengrass/v2/packages/artifacts/
```

### Q: 카메라 접근 오류

```bash
# video 그룹에 ggc_user 추가
sudo usermod -aG video ggc_user
sudo systemctl restart greengrass
```

### Q: 모델 로딩 실패

```bash
# 모델 파일 확인
ls -la /greengrass/v2/packages/artifacts/com.ppe.Detector/1.0.0/models/
```

---

## 📚 다음 단계

[Part 7: PPE 감지 구현](./07-ppe-detection.md)으로 이동하여
실시간 감지 로직을 상세히 구현합니다.
