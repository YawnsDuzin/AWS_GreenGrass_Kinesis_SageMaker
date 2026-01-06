# Part 5: SageMaker 모델 학습

이 파트에서는 Amazon SageMaker를 사용하여 YOLOv8 기반 PPE(개인보호장비) 감지 모델을 학습합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] 학습 데이터셋 준비
- [x] SageMaker 노트북 인스턴스 생성
- [x] YOLOv8 모델 학습
- [x] 모델 평가 및 최적화
- [x] ONNX 형식 변환 (Raspberry Pi용)
- [x] S3에 모델 업로드

---

## 1. 데이터셋 준비

### 1.1 PPE 데이터셋 다운로드

공개된 PPE 감지 데이터셋을 사용합니다:

```bash
# PC에서 실행 (Roboflow 데이터셋)
# https://universe.roboflow.com/search?q=ppe+detection

# 또는 직접 다운로드할 수 있는 데이터셋:
# - Safety Helmet Dataset
# - Construction Site Safety Dataset
```

### 1.2 데이터셋 구조

```
dataset/
├── train/
│   ├── images/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   └── labels/
│       ├── img001.txt
│       ├── img002.txt
│       └── ...
├── val/
│   ├── images/
│   └── labels/
└── data.yaml
```

### 1.3 data.yaml 생성

```yaml
# data.yaml
path: /opt/ml/input/data
train: train/images
val: val/images

# 클래스 정의
names:
  0: person
  1: hardhat
  2: safety_vest
  3: safety_shoes
  4: no_hardhat
  5: no_safety_vest

nc: 6  # 클래스 수
```

### 1.4 S3에 데이터셋 업로드

```bash
# 변수 설정
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
DATA_BUCKET="ppe-detection-data-${ACCOUNT_ID}"

# 데이터셋 업로드
aws s3 sync ./dataset s3://${DATA_BUCKET}/dataset/ --exclude "*.DS_Store"

# 확인
aws s3 ls s3://${DATA_BUCKET}/dataset/ --recursive | head -20
```

---

## 2. SageMaker 노트북 인스턴스 생성

### 2.1 AWS 콘솔에서 생성

1. AWS 콘솔 → **SageMaker** 검색
2. 좌측 메뉴: **노트북** → **노트북 인스턴스**
3. **노트북 인스턴스 생성** 클릭

### 2.2 인스턴스 설정

```
노트북 인스턴스 이름: ppe-detection-notebook
노트북 인스턴스 유형: ml.t3.medium (개발용) 또는 ml.g4dn.xlarge (학습용)
Elastic Inference: 없음
플랫폼 식별자: Amazon Linux 2, Jupyter Lab 3
```

### 2.3 권한 및 암호화

```
IAM 역할: ConstructionSafety-SageMakerRole (Part 1에서 생성)
루트 액세스: 활성화
암호화 키: 기본값 사용
```

### 2.4 네트워크 (선택)

```
VPC: 기본 VPC 사용
직접 인터넷 액세스: 활성화
```

**노트북 인스턴스 생성** 클릭 (약 5분 소요)

### 2.5 Jupyter 접속

상태가 **InService**가 되면:
1. **JupyterLab 열기** 클릭
2. 새 Python 3 노트북 생성

---

## 3. 학습 환경 설정

### 3.1 필요 라이브러리 설치

JupyterLab에서 새 노트북 생성 후:

```python
# 셀 1: 라이브러리 설치
!pip install -q ultralytics==8.0.200
!pip install -q onnx onnxruntime
!pip install -q boto3 sagemaker
```

### 3.2 환경 설정

```python
# 셀 2: 환경 설정
import os
import json
import boto3
import sagemaker
from sagemaker import get_execution_role

# SageMaker 세션
session = sagemaker.Session()
role = get_execution_role()
region = session.boto_region_name
bucket = session.default_bucket()

print(f"Role: {role}")
print(f"Region: {region}")
print(f"Bucket: {bucket}")
```

---

## 4. 데이터셋 다운로드 및 확인

### 4.1 S3에서 다운로드

```python
# 셀 3: 데이터 다운로드
import subprocess

ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']
DATA_BUCKET = f"ppe-detection-data-{ACCOUNT_ID}"

# 로컬로 다운로드
!mkdir -p /home/ec2-user/SageMaker/dataset
!aws s3 sync s3://{DATA_BUCKET}/dataset/ /home/ec2-user/SageMaker/dataset/
```

### 4.2 데이터셋 확인

```python
# 셀 4: 데이터 확인
import os
from pathlib import Path

dataset_path = Path("/home/ec2-user/SageMaker/dataset")

train_images = list((dataset_path / "train" / "images").glob("*.jpg"))
val_images = list((dataset_path / "val" / "images").glob("*.jpg"))

print(f"학습 이미지: {len(train_images)}개")
print(f"검증 이미지: {len(val_images)}개")
```

### 4.3 샘플 이미지 시각화

```python
# 셀 5: 이미지 시각화
import matplotlib.pyplot as plt
import cv2
import numpy as np

def visualize_sample(image_path, label_path, class_names):
    """샘플 이미지와 바운딩 박스 시각화"""
    img = cv2.imread(str(image_path))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]

    # 라벨 로드
    if label_path.exists():
        with open(label_path) as f:
            for line in f:
                parts = line.strip().split()
                cls_id = int(parts[0])
                x_center, y_center, box_w, box_h = map(float, parts[1:5])

                # 좌표 변환
                x1 = int((x_center - box_w/2) * w)
                y1 = int((y_center - box_h/2) * h)
                x2 = int((x_center + box_w/2) * w)
                y2 = int((y_center + box_h/2) * h)

                # 박스 그리기
                color = (255, 0, 0) if 'no_' in class_names[cls_id] else (0, 255, 0)
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, class_names[cls_id], (x1, y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return img

# 클래스 이름
class_names = ['person', 'hardhat', 'safety_vest', 'safety_shoes', 'no_hardhat', 'no_safety_vest']

# 샘플 표시
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
for i, ax in enumerate(axes.flatten()):
    if i < len(train_images):
        img_path = train_images[i]
        label_path = dataset_path / "train" / "labels" / f"{img_path.stem}.txt"
        img = visualize_sample(img_path, label_path, class_names)
        ax.imshow(img)
        ax.set_title(img_path.name)
        ax.axis('off')

plt.tight_layout()
plt.show()
```

---

## 5. YOLOv8 모델 학습

### 5.1 data.yaml 생성

```python
# 셀 6: data.yaml 생성
data_yaml = """
path: /home/ec2-user/SageMaker/dataset
train: train/images
val: val/images

names:
  0: person
  1: hardhat
  2: safety_vest
  3: safety_shoes
  4: no_hardhat
  5: no_safety_vest

nc: 6
"""

with open("/home/ec2-user/SageMaker/dataset/data.yaml", "w") as f:
    f.write(data_yaml)

print("data.yaml 생성 완료")
```

### 5.2 모델 학습

```python
# 셀 7: YOLOv8 학습
from ultralytics import YOLO

# YOLOv8 nano 모델 (Raspberry Pi 최적화)
model = YOLO('yolov8n.pt')

# 학습 실행
results = model.train(
    data='/home/ec2-user/SageMaker/dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    patience=50,
    device=0,  # GPU 사용 (있는 경우)
    project='/home/ec2-user/SageMaker/runs',
    name='ppe_detection',
    exist_ok=True,

    # 학습 파라미터
    lr0=0.01,
    lrf=0.01,
    momentum=0.937,
    weight_decay=0.0005,

    # 데이터 증강
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=0.0,
    translate=0.1,
    scale=0.5,
    shear=0.0,
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.0
)

print("학습 완료!")
```

### 5.3 학습 결과 확인

```python
# 셀 8: 결과 확인
from IPython.display import Image, display

# 학습 결과 이미지
results_path = "/home/ec2-user/SageMaker/runs/ppe_detection"

# 학습 곡선
display(Image(filename=f"{results_path}/results.png"))

# 혼동 행렬
display(Image(filename=f"{results_path}/confusion_matrix.png"))

# 예측 결과
display(Image(filename=f"{results_path}/val_batch0_pred.jpg"))
```

---

## 6. 모델 평가

### 6.1 검증 데이터로 평가

```python
# 셀 9: 모델 평가
# 최적 모델 로드
best_model = YOLO(f"{results_path}/weights/best.pt")

# 검증
metrics = best_model.val(data='/home/ec2-user/SageMaker/dataset/data.yaml')

print(f"mAP50: {metrics.box.map50:.4f}")
print(f"mAP50-95: {metrics.box.map:.4f}")
print(f"Precision: {metrics.box.mp:.4f}")
print(f"Recall: {metrics.box.mr:.4f}")
```

### 6.2 클래스별 성능

```python
# 셀 10: 클래스별 성능
import pandas as pd

class_names = ['person', 'hardhat', 'safety_vest', 'safety_shoes', 'no_hardhat', 'no_safety_vest']

class_metrics = []
for i, name in enumerate(class_names):
    class_metrics.append({
        'Class': name,
        'Precision': metrics.box.p[i],
        'Recall': metrics.box.r[i],
        'mAP50': metrics.box.ap50[i],
        'mAP50-95': metrics.box.ap[i]
    })

df = pd.DataFrame(class_metrics)
print(df.to_string(index=False))
```

---

## 7. ONNX 변환 (Raspberry Pi용)

### 7.1 ONNX 내보내기

```python
# 셀 11: ONNX 변환
# 최적 모델 로드
best_model = YOLO(f"{results_path}/weights/best.pt")

# ONNX 내보내기
onnx_path = best_model.export(
    format='onnx',
    imgsz=640,
    simplify=True,
    opset=12,
    dynamic=False
)

print(f"ONNX 모델 저장: {onnx_path}")
```

### 7.2 ONNX 모델 검증

```python
# 셀 12: ONNX 검증
import onnx
import onnxruntime as ort

# 모델 로드
onnx_model = onnx.load(onnx_path)
onnx.checker.check_model(onnx_model)
print("ONNX 모델 검증 완료")

# 추론 테스트
session = ort.InferenceSession(onnx_path)
input_name = session.get_inputs()[0].name
input_shape = session.get_inputs()[0].shape

print(f"입력 이름: {input_name}")
print(f"입력 형태: {input_shape}")

# 더미 입력으로 테스트
import numpy as np
dummy_input = np.random.randn(1, 3, 640, 640).astype(np.float32)
output = session.run(None, {input_name: dummy_input})
print(f"출력 형태: {output[0].shape}")
```

---

## 8. S3에 모델 업로드

### 8.1 모델 및 메타데이터 저장

```python
# 셀 13: 모델 저장 준비
import json
from datetime import datetime

# 모델 메타데이터
metadata = {
    "model_type": "yolov8n",
    "input_size": 640,
    "classes": {
        "0": "person",
        "1": "hardhat",
        "2": "safety_vest",
        "3": "safety_shoes",
        "4": "no_hardhat",
        "5": "no_safety_vest"
    },
    "target_device": "raspberry_pi_4_64bit",
    "training_date": datetime.now().isoformat(),
    "metrics": {
        "mAP50": float(metrics.box.map50),
        "mAP50-95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr)
    }
}

# 메타데이터 저장
with open(f"{results_path}/weights/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

print("메타데이터 저장 완료")
```

### 8.2 S3 업로드

```python
# 셀 14: S3 업로드
MODEL_BUCKET = f"ppe-detection-models-{ACCOUNT_ID}"
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

# PyTorch 모델 업로드
!aws s3 cp {results_path}/weights/best.pt s3://{MODEL_BUCKET}/models/v1/best.pt
!aws s3 cp {results_path}/weights/last.pt s3://{MODEL_BUCKET}/models/v1/last.pt

# ONNX 모델 업로드
!aws s3 cp {onnx_path} s3://{MODEL_BUCKET}/models/v1/model.onnx

# 메타데이터 업로드
!aws s3 cp {results_path}/weights/metadata.json s3://{MODEL_BUCKET}/models/v1/metadata.json

# 학습 결과 업로드
!aws s3 sync {results_path}/ s3://{MODEL_BUCKET}/training-runs/{timestamp}/ --exclude "*.pt"

print(f"모델 업로드 완료: s3://{MODEL_BUCKET}/models/v1/")
```

### 8.3 업로드 확인

```python
# 셀 15: 업로드 확인
!aws s3 ls s3://{MODEL_BUCKET}/models/v1/
```

예상 출력:
```
2024-01-15 10:30:00    6234567 best.pt
2024-01-15 10:30:01   12345678 last.pt
2024-01-15 10:30:02    5876543 model.onnx
2024-01-15 10:30:03        456 metadata.json
```

---

## 9. 모델 다운로드 URL 생성

### 9.1 Presigned URL 생성 (Raspberry Pi 다운로드용)

```python
# 셀 16: Presigned URL
s3_client = boto3.client('s3')

# ONNX 모델 다운로드 URL (24시간 유효)
onnx_url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': MODEL_BUCKET, 'Key': 'models/v1/model.onnx'},
    ExpiresIn=86400
)

print("Raspberry Pi에서 다운로드:")
print(f"curl -o model.onnx '{onnx_url}'")
```

---

## 10. 노트북 인스턴스 정리

### 10.1 비용 절감

학습 완료 후:

```python
# 셀 17: 정리
# 로컬 데이터 정리 (선택)
!rm -rf /home/ec2-user/SageMaker/dataset
!rm -rf /home/ec2-user/SageMaker/runs

print("정리 완료")
```

### 10.2 인스턴스 중지

1. SageMaker 콘솔 → 노트북 인스턴스
2. `ppe-detection-notebook` 선택
3. **작업** → **중지**

> 💡 중지된 인스턴스는 스토리지 비용만 발생합니다.

---

## ✅ 체크리스트

이 파트를 완료하면 다음 항목들이 준비되어야 합니다:

- [ ] 학습 데이터셋 S3 업로드 완료
- [ ] SageMaker 노트북 인스턴스 생성
- [ ] YOLOv8 모델 학습 완료
- [ ] 모델 평가 (mAP50 > 0.5 권장)
- [ ] ONNX 형식 변환 완료
- [ ] S3에 모델 파일 업로드:
  - [ ] `best.pt`
  - [ ] `model.onnx`
  - [ ] `metadata.json`
- [ ] 노트북 인스턴스 중지 (비용 절감)

---

## 🔧 문제 해결

### Q: GPU 메모리 부족

```python
# 배치 크기 줄이기
model.train(batch=8, ...)

# 또는 더 큰 인스턴스 사용
# ml.g4dn.xlarge → ml.g4dn.2xlarge
```

### Q: 학습 속도가 느림

```python
# CPU 학습 확인
import torch
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")

# GPU 인스턴스로 변경 필요
```

### Q: 데이터셋 형식 오류

```bash
# YOLO 형식 확인
# 라벨 파일: class_id x_center y_center width height (0-1 정규화)
head dataset/train/labels/sample.txt
```

---

## 📚 다음 단계

[Part 6: GreenGrass 컴포넌트 배포](./06-component-deployment.md)로 이동하여
학습된 모델을 Raspberry Pi에 배포합니다.
