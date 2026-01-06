# 2.3 Amazon SageMaker 완벽 가이드

## 개요

### Amazon SageMaker란?

Amazon SageMaker는 **완전관리형 머신러닝 플랫폼**으로, ML 모델의 구축, 학습, 배포를 위한 종합적인 도구와 인프라를 제공합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Amazon SageMaker 생태계                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Data Preparation                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Ground Truth│  │ Data Wrangler│  │ Feature    │             │   │
│  │  │ (라벨링)    │  │ (전처리)     │  │ Store      │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Model Development                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Studio      │  │ Notebooks   │  │ Autopilot   │             │   │
│  │  │ (통합 IDE)  │  │ (Jupyter)   │  │ (AutoML)    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Training                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Training    │  │ Debugger    │  │ Distributed │             │   │
│  │  │ Jobs        │  │ (디버깅)    │  │ Training    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Deployment & Inference                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Endpoints   │  │ Batch       │  │ Neo         │             │   │
│  │  │ (실시간)    │  │ Transform   │  │ (최적화)    │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MLOps                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │ Pipelines   │  │ Model       │  │ Model       │             │   │
│  │  │             │  │ Registry    │  │ Monitor     │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 핵심 기능

### 1. SageMaker Studio

통합 ML 개발 환경으로, 모든 ML 작업을 한 곳에서 수행할 수 있습니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SageMaker Studio 인터페이스                          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │         │  │  ┌─────────────────────────────────────────────────┐│  │
│  │ Launcher│  │  │                 Notebook                        ││  │
│  │         │  │  │  import sagemaker                               ││  │
│  │ ┌─────┐ │  │  │  from sagemaker import get_execution_role      ││  │
│  │ │Note │ │  │  │                                                 ││  │
│  │ │book │ │  │  │  role = get_execution_role()                   ││  │
│  │ └─────┘ │  │  │  sess = sagemaker.Session()                    ││  │
│  │         │  │  │                                                 ││  │
│  │ ┌─────┐ │  │  │  # 데이터 로드                                  ││  │
│  │ │Expe │ │  │  │  data = pd.read_csv('s3://bucket/data.csv')   ││  │
│  │ │riment│ │  │  │                                                 ││  │
│  │ └─────┘ │  │  └─────────────────────────────────────────────────┘│  │
│  │         │  │                                                     │  │
│  │ ┌─────┐ │  │  ┌─────────────────────────────────────────────────┐│  │
│  │ │Pipe │ │  │  │  File Browser | Git | Terminal                 ││  │
│  │ │line │ │  │  │  └─ project/                                    ││  │
│  │ └─────┘ │  │  │     ├─ notebooks/                               ││  │
│  │         │  │  │     ├─ src/                                     ││  │
│  │ ┌─────┐ │  │  │     └─ data/                                    ││  │
│  │ │Model│ │  │  └─────────────────────────────────────────────────┘│  │
│  │ └─────┘ │  │                                                     │  │
│  └─────────┘  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. 내장 알고리즘 (Built-in Algorithms)

| 카테고리 | 알고리즘 | 용도 |
|----------|----------|------|
| **컴퓨터 비전** | Image Classification | 이미지 분류 |
| | Object Detection | 객체 감지 |
| | Semantic Segmentation | 영역 분할 |
| **자연어 처리** | BlazingText | 텍스트 분류, Word2Vec |
| | Sequence-to-Sequence | 번역, 요약 |
| **표 형식 데이터** | XGBoost | 분류, 회귀 |
| | Linear Learner | 선형 모델 |
| | K-Means | 클러스터링 |
| **시계열** | DeepAR | 시계열 예측 |
| **이상 탐지** | Random Cut Forest | 이상 감지 |

### 3. 프레임워크 지원

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    지원 ML 프레임워크                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  딥러닝 프레임워크                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  TensorFlow  │  │   PyTorch    │  │    MXNet     │                  │
│  │  2.x         │  │   2.x        │  │   1.x        │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│  ML 프레임워크                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Scikit-learn│  │   XGBoost    │  │   Hugging    │                  │
│  │              │  │              │  │   Face       │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│  추론 최적화                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   ONNX       │  │  TensorRT    │  │   OpenVINO   │                  │
│  │              │  │   (NVIDIA)   │  │   (Intel)    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 공사현장 안전 감지 모델 개발

### 1. 데이터 준비 (Ground Truth)

```python
# ground_truth_labeling.py
import boto3
import json

def create_labeling_job():
    sagemaker = boto3.client('sagemaker')

    # 라벨링 작업 생성
    response = sagemaker.create_labeling_job(
        LabelingJobName='construction-safety-labeling',

        # 입력 데이터 설정
        InputConfig={
            'DataSource': {
                'S3DataSource': {
                    'ManifestS3Uri': 's3://my-bucket/labeling/input/manifest.json'
                }
            },
            'DataAttributes': {
                'ContentClassifiers': ['FreeOfPersonallyIdentifiableInformation']
            }
        },

        # 출력 설정
        OutputConfig={
            'S3OutputPath': 's3://my-bucket/labeling/output/'
        },

        # 라벨링 UI 설정 (바운딩 박스)
        LabelAttributeName='safety-equipment',
        HumanTaskConfig={
            'WorkteamArn': 'arn:aws:sagemaker:ap-northeast-2:123456789012:workteam/private-crowd/my-team',
            'UiConfig': {
                'UiTemplateS3Uri': 's3://my-bucket/labeling/template.html'
            },
            'PreHumanTaskLambdaArn': 'arn:aws:lambda:...',
            'TaskTitle': '안전장비 라벨링',
            'TaskDescription': '이미지에서 안전모, 안전조끼 등을 바운딩 박스로 표시하세요',
            'NumberOfHumanWorkersPerDataObject': 3,
            'TaskTimeLimitInSeconds': 300,
            'MaxConcurrentTaskCount': 100,

            # 라벨 카테고리
            'AnnotationConsolidationConfig': {
                'AnnotationConsolidationLambdaArn': 'arn:aws:lambda:...'
            }
        },

        # 라벨 카테고리 정의
        LabelCategoryConfigS3Uri='s3://my-bucket/labeling/label-categories.json',

        # IAM 역할
        RoleArn='arn:aws:iam::123456789012:role/SageMakerRole'
    )

    return response

# 라벨 카테고리 설정
label_categories = {
    "document-version": "2018-11-28",
    "labels": [
        {"label": "person"},
        {"label": "helmet"},
        {"label": "no_helmet"},
        {"label": "safety_vest"},
        {"label": "no_vest"},
        {"label": "safety_harness"},
        {"label": "no_harness"},
        {"label": "safety_glasses"},
        {"label": "gloves"}
    ]
}
```

### 2. 커스텀 모델 학습 (YOLOv8)

```python
# train_safety_model.py
import sagemaker
from sagemaker.pytorch import PyTorch
from sagemaker.inputs import TrainingInput

def train_yolo_model():
    sess = sagemaker.Session()
    role = sagemaker.get_execution_role()

    # 학습 스크립트 정의
    pytorch_estimator = PyTorch(
        entry_point='train.py',
        source_dir='./src',
        role=role,
        framework_version='2.0.0',
        py_version='py310',

        # 인스턴스 설정
        instance_count=1,
        instance_type='ml.p3.2xlarge',  # V100 GPU

        # 하이퍼파라미터
        hyperparameters={
            'model': 'yolov8m.pt',  # 중간 크기 모델
            'data': '/opt/ml/input/data/training/data.yaml',
            'epochs': 100,
            'batch': 16,
            'imgsz': 640,
            'patience': 20,
            'device': 0
        },

        # 메트릭 정의
        metric_definitions=[
            {'Name': 'mAP50', 'Regex': 'mAP50\(B\): ([0-9\\.]+)'},
            {'Name': 'mAP50-95', 'Regex': 'mAP50-95\(B\): ([0-9\\.]+)'},
            {'Name': 'loss', 'Regex': 'train/box_loss: ([0-9\\.]+)'}
        ],

        # 체크포인트
        checkpoint_s3_uri='s3://my-bucket/checkpoints/',

        # 태그
        tags=[
            {'Key': 'Project', 'Value': 'ConstructionSafety'},
            {'Key': 'Model', 'Value': 'YOLOv8'}
        ]
    )

    # 데이터 채널 설정
    training_input = TrainingInput(
        s3_data='s3://my-bucket/training-data/',
        content_type='application/x-image'
    )

    validation_input = TrainingInput(
        s3_data='s3://my-bucket/validation-data/',
        content_type='application/x-image'
    )

    # 학습 시작
    pytorch_estimator.fit({
        'training': training_input,
        'validation': validation_input
    })

    return pytorch_estimator


# src/train.py (학습 스크립트)
"""
import os
import argparse
from ultralytics import YOLO

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='yolov8m.pt')
    parser.add_argument('--data', type=str, required=True)
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--patience', type=int, default=20)
    parser.add_argument('--device', type=int, default=0)
    return parser.parse_args()

def main():
    args = parse_args()

    # 모델 로드
    model = YOLO(args.model)

    # 학습
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        device=args.device,
        project='/opt/ml/model',
        name='safety_detection'
    )

    # 모델 저장
    model.export(format='onnx', opset=12)

if __name__ == '__main__':
    main()
"""
```

### 3. 모델 배포 (Endpoint)

```python
# deploy_model.py
import sagemaker
from sagemaker.pytorch import PyTorchModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer

def deploy_safety_model():
    sess = sagemaker.Session()
    role = sagemaker.get_execution_role()

    # 모델 생성
    model = PyTorchModel(
        model_data='s3://my-bucket/models/safety-detection/model.tar.gz',
        role=role,
        framework_version='2.0.0',
        py_version='py310',
        entry_point='inference.py',
        source_dir='./src'
    )

    # 엔드포인트 배포
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type='ml.g4dn.xlarge',  # T4 GPU
        endpoint_name='safety-detection-endpoint',
        serializer=JSONSerializer(),
        deserializer=JSONDeserializer()
    )

    return predictor


# src/inference.py (추론 스크립트)
"""
import os
import json
import torch
import numpy as np
from ultralytics import YOLO
import base64
from PIL import Image
import io

def model_fn(model_dir):
    '''모델 로드'''
    model_path = os.path.join(model_dir, 'best.pt')
    model = YOLO(model_path)
    return model

def input_fn(request_body, request_content_type):
    '''입력 전처리'''
    if request_content_type == 'application/json':
        data = json.loads(request_body)
        # Base64 이미지 디코딩
        image_bytes = base64.b64decode(data['image'])
        image = Image.open(io.BytesIO(image_bytes))
        return np.array(image)

    raise ValueError(f'Unsupported content type: {request_content_type}')

def predict_fn(input_data, model):
    '''추론 수행'''
    results = model(input_data, conf=0.5)

    detections = []
    for result in results:
        for box in result.boxes:
            detections.append({
                'class': result.names[int(box.cls)],
                'confidence': float(box.conf),
                'bbox': box.xyxy[0].tolist()
            })

    return detections

def output_fn(prediction, response_content_type):
    '''출력 후처리'''
    if response_content_type == 'application/json':
        return json.dumps({
            'detections': prediction,
            'count': len(prediction)
        })

    raise ValueError(f'Unsupported content type: {response_content_type}')
"""


# 엔드포인트 호출 예시
def invoke_endpoint():
    import boto3
    import base64

    runtime = boto3.client('sagemaker-runtime')

    # 이미지 로드 및 인코딩
    with open('test_image.jpg', 'rb') as f:
        image_bytes = base64.b64encode(f.read()).decode('utf-8')

    # 엔드포인트 호출
    response = runtime.invoke_endpoint(
        EndpointName='safety-detection-endpoint',
        ContentType='application/json',
        Body=json.dumps({'image': image_bytes})
    )

    result = json.loads(response['Body'].read().decode())
    print(f"감지된 객체: {result['count']}개")
    for det in result['detections']:
        print(f"  - {det['class']}: {det['confidence']:.2f}")
```

---

## SageMaker Neo (엣지 최적화)

### 모델 컴파일

```python
# compile_for_edge.py
import boto3

def compile_model_for_greengrass():
    sagemaker = boto3.client('sagemaker')

    response = sagemaker.create_compilation_job(
        CompilationJobName='safety-model-jetson',

        # 입력 모델
        InputConfig={
            'S3Uri': 's3://my-bucket/models/safety-detection/model.tar.gz',
            'DataInputConfig': '{"input": [1, 3, 640, 640]}',
            'Framework': 'PYTORCH'
        },

        # 출력 설정
        OutputConfig={
            'S3OutputLocation': 's3://my-bucket/compiled-models/',
            'TargetDevice': 'jetson_xavier',  # Jetson Xavier NX
            'CompilerOptions': '{"trt-ver": "8.4", "cuda-ver": "11.4"}'
        },

        # IAM 역할
        RoleArn='arn:aws:iam::123456789012:role/SageMakerRole',

        StoppingCondition={
            'MaxRuntimeInSeconds': 900
        }
    )

    return response


# 지원 타겟 디바이스
"""
┌─────────────────────────────────────────────────────────────────────────┐
│                    SageMaker Neo 지원 디바이스                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NVIDIA                                                                 │
│  ├─ jetson_tx1, jetson_tx2                                            │
│  ├─ jetson_nano                                                        │
│  ├─ jetson_xavier (NX, AGX)                                           │
│  └─ jetson_orin                                                        │
│                                                                         │
│  Intel                                                                  │
│  ├─ deeplens                                                           │
│  └─ intel_openvino                                                     │
│                                                                         │
│  ARM                                                                    │
│  ├─ rasp3b, rasp4b (Raspberry Pi)                                     │
│  └─ imx8qm                                                             │
│                                                                         │
│  AWS                                                                    │
│  ├─ panorama                                                           │
│  └─ inf1, inf2 (Inferentia)                                           │
│                                                                         │
│  모바일                                                                  │
│  ├─ android (TFLite)                                                   │
│  └─ ios (CoreML)                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
"""
```

---

## 실시간 추론 아키텍처

### Kinesis와 SageMaker 연동

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    실시간 추론 아키텍처                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────┐      ┌─────────────────┐      ┌─────────────────┐        │
│   │ Kinesis │─────▶│ Lambda          │─────▶│ SageMaker       │        │
│   │ Stream  │      │ (이미지 추출)    │      │ Endpoint        │        │
│   └─────────┘      └─────────────────┘      └────────┬────────┘        │
│                                                       │                 │
│                                                       ▼                 │
│                                              ┌─────────────────┐        │
│                                              │ 추론 결과       │        │
│                                              │ (감지 결과)     │        │
│                                              └────────┬────────┘        │
│                                                       │                 │
│                           ┌───────────────────────────┼───────────────┐│
│                           │                           │               ││
│                           ▼                           ▼               ││
│                  ┌─────────────────┐        ┌─────────────────┐       ││
│                  │ DynamoDB        │        │ SNS (알림)      │       ││
│                  │ (이벤트 저장)   │        │                 │       ││
│                  └─────────────────┘        └─────────────────┘       ││
│                                                                        ││
└────────────────────────────────────────────────────────────────────────┘│
```

### Lambda 추론 코드

```python
# lambda_inference.py
import boto3
import json
import base64
import os

# SageMaker 런타임 클라이언트
runtime = boto3.client('sagemaker-runtime')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

ENDPOINT_NAME = os.environ['SAGEMAKER_ENDPOINT']
TABLE_NAME = os.environ['DYNAMODB_TABLE']
SNS_TOPIC = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    """Kinesis 이벤트 처리 및 SageMaker 추론"""

    table = dynamodb.Table(TABLE_NAME)
    processed_count = 0
    alert_count = 0

    for record in event['Records']:
        # Kinesis 레코드 디코딩
        payload = base64.b64decode(record['kinesis']['data'])
        data = json.loads(payload)

        # 이미지 데이터 추출
        if 'image' not in data:
            continue

        # SageMaker 엔드포인트 호출
        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps({'image': data['image']})
        )

        result = json.loads(response['Body'].read().decode())

        # 안전 위반 확인
        violations = check_violations(result['detections'])

        if violations:
            # DynamoDB에 이벤트 저장
            table.put_item(Item={
                'event_id': record['eventID'],
                'timestamp': data['timestamp'],
                'device_id': data['device_id'],
                'site_id': data['site_id'],
                'violations': violations,
                'detections': result['detections']
            })

            # 심각한 위반 시 알림
            if any(v['severity'] == 'HIGH' for v in violations):
                send_alert(data, violations)
                alert_count += 1

        processed_count += 1

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'alerts': alert_count
        })
    }


def check_violations(detections):
    """감지 결과에서 안전 위반 확인"""
    violations = []

    # 사람과 안전장비 매핑
    persons = [d for d in detections if d['class'] == 'person']

    for person in persons:
        person_bbox = person['bbox']

        # 헬멧 확인
        has_helmet = any(
            d['class'] == 'helmet' and is_overlapping(d['bbox'], person_bbox)
            for d in detections
        )

        # 조끼 확인
        has_vest = any(
            d['class'] == 'safety_vest' and is_overlapping(d['bbox'], person_bbox)
            for d in detections
        )

        if not has_helmet:
            violations.append({
                'type': 'NO_HELMET',
                'severity': 'HIGH',
                'location': person_bbox
            })

        if not has_vest:
            violations.append({
                'type': 'NO_VEST',
                'severity': 'MEDIUM',
                'location': person_bbox
            })

    return violations


def is_overlapping(box1, box2):
    """두 바운딩 박스의 겹침 확인"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    return x1 < x2 and y1 < y2


def send_alert(data, violations):
    """SNS 알림 전송"""
    message = {
        'timestamp': data['timestamp'],
        'site_id': data['site_id'],
        'device_id': data['device_id'],
        'violations': violations,
        'message': f"[긴급] {len(violations)}건의 안전 위반이 감지되었습니다."
    }

    sns.publish(
        TopicArn=SNS_TOPIC,
        Subject=f"[안전알림] {data['site_id']} - 위반 감지",
        Message=json.dumps(message, ensure_ascii=False)
    )
```

---

## MLOps 파이프라인

### SageMaker Pipelines

```python
# mlops_pipeline.py
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, CreateModelStep
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.parameters import ParameterString, ParameterInteger
from sagemaker.processing import ScriptProcessor
from sagemaker.pytorch import PyTorch

def create_ml_pipeline():
    # 파이프라인 파라미터
    input_data = ParameterString(name="InputData", default_value="s3://my-bucket/data/")
    model_approval_status = ParameterString(name="ModelApprovalStatus", default_value="PendingManualApproval")
    training_epochs = ParameterInteger(name="TrainingEpochs", default_value=100)

    # Step 1: 데이터 전처리
    processor = ScriptProcessor(
        image_uri='123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/preprocessing:latest',
        role=role,
        instance_type='ml.m5.xlarge',
        instance_count=1
    )

    processing_step = ProcessingStep(
        name="PreprocessData",
        processor=processor,
        inputs=[
            ProcessingInput(source=input_data, destination="/opt/ml/processing/input")
        ],
        outputs=[
            ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
            ProcessingOutput(output_name="validation", source="/opt/ml/processing/validation")
        ],
        code="preprocess.py"
    )

    # Step 2: 모델 학습
    estimator = PyTorch(
        entry_point='train.py',
        source_dir='./src',
        role=role,
        framework_version='2.0.0',
        py_version='py310',
        instance_type='ml.p3.2xlarge',
        instance_count=1,
        hyperparameters={
            'epochs': training_epochs,
            'batch-size': 16
        }
    )

    training_step = TrainingStep(
        name="TrainModel",
        estimator=estimator,
        inputs={
            "training": TrainingInput(
                s3_data=processing_step.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri
            )
        }
    )

    # Step 3: 모델 평가
    evaluation_step = ProcessingStep(
        name="EvaluateModel",
        processor=processor,
        inputs=[
            ProcessingInput(
                source=training_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model"
            ),
            ProcessingInput(
                source=processing_step.properties.ProcessingOutputConfig.Outputs["validation"].S3Output.S3Uri,
                destination="/opt/ml/processing/validation"
            )
        ],
        outputs=[
            ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")
        ],
        code="evaluate.py"
    )

    # Step 4: 모델 등록
    model_metrics = ModelMetrics(
        model_statistics=MetricsSource(
            s3_uri=evaluation_step.properties.ProcessingOutputConfig.Outputs["evaluation"].S3Output.S3Uri,
            content_type="application/json"
        )
    )

    register_step = RegisterModel(
        name="RegisterModel",
        estimator=estimator,
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["application/json"],
        response_types=["application/json"],
        inference_instances=["ml.g4dn.xlarge"],
        transform_instances=["ml.m5.xlarge"],
        model_package_group_name="SafetyDetectionModels",
        approval_status=model_approval_status,
        model_metrics=model_metrics
    )

    # 파이프라인 생성
    pipeline = Pipeline(
        name="SafetyDetectionPipeline",
        parameters=[input_data, model_approval_status, training_epochs],
        steps=[processing_step, training_step, evaluation_step, register_step]
    )

    return pipeline


# 파이프라인 실행
def run_pipeline():
    pipeline = create_ml_pipeline()
    pipeline.upsert(role_arn=role)

    execution = pipeline.start(
        parameters={
            "InputData": "s3://my-bucket/new-data/",
            "TrainingEpochs": 150
        }
    )

    execution.wait()
    print(f"Pipeline execution status: {execution.describe()['PipelineExecutionStatus']}")
```

---

## 모델 모니터링

### Model Monitor 설정

```python
# model_monitor.py
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

def setup_model_monitor(endpoint_name):
    # 기본 모니터 생성
    monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type='ml.m5.xlarge',
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600
    )

    # 기준선 (Baseline) 생성
    monitor.suggest_baseline(
        baseline_dataset='s3://my-bucket/baseline-data/baseline.csv',
        dataset_format=DatasetFormat.csv(header=True),
        output_s3_uri='s3://my-bucket/baseline-results/'
    )

    # 스케줄 모니터링 설정
    monitor.create_monitoring_schedule(
        monitor_schedule_name='safety-model-monitor',
        endpoint_input=endpoint_name,
        output_s3_uri='s3://my-bucket/monitoring-results/',
        statistics='s3://my-bucket/baseline-results/statistics.json',
        constraints='s3://my-bucket/baseline-results/constraints.json',
        schedule_cron_expression='cron(0 * ? * * *)'  # 매시간
    )

    return monitor
```

---

## 요금 체계

### SageMaker 요금

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SageMaker 요금 체계 (서울 리전)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  노트북 인스턴스 (시간당)                                                 │
│  ├─ ml.t3.medium:   $0.05                                              │
│  ├─ ml.m5.xlarge:   $0.23                                              │
│  └─ ml.p3.2xlarge:  $3.825                                             │
│                                                                         │
│  학습 인스턴스 (시간당)                                                   │
│  ├─ ml.m5.xlarge:   $0.23                                              │
│  ├─ ml.p3.2xlarge:  $3.825                                             │
│  └─ ml.p3.8xlarge:  $14.688                                            │
│                                                                         │
│  추론 엔드포인트 (시간당)                                                 │
│  ├─ ml.t2.medium:   $0.056                                             │
│  ├─ ml.m5.xlarge:   $0.23                                              │
│  └─ ml.g4dn.xlarge: $0.736                                             │
│                                                                         │
│  데이터 라벨링 (Ground Truth)                                            │
│  └─ 객체당: $0.08 (바운딩 박스)                                         │
│                                                                         │
│  모델 모니터링                                                           │
│  └─ 시간당: $0.06 (ml.m5.xlarge 기준)                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 월간 비용 예시

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    월간 예상 비용 (SageMaker)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  개발 단계 (1회성)                                                       │
│  ├─ 데이터 라벨링: 10,000장 × $0.08 = $800                             │
│  ├─ 모델 학습: 10시간 × $3.825 = $38.25                                │
│  └─ 소계: $838.25                                                       │
│                                                                         │
│  운영 단계 (월간)                                                        │
│  ├─ 실시간 엔드포인트: 720시간 × $0.736 = $530                         │
│  ├─ 모델 모니터링: 720시간 × $0.06 = $43.20                            │
│  ├─ 재학습 (분기 1회): $38.25 / 3 = $12.75                             │
│  └─ 소계: 약 $586/월 (약 780,000원)                                    │
│                                                                         │
│  비용 최적화 옵션                                                        │
│  ├─ Spot 인스턴스 (학습): 최대 90% 절감                                │
│  ├─ 오토스케일링: 비수요 시간 인스턴스 감소                             │
│  └─ Inference Recommender: 최적 인스턴스 추천                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [기타 연관 AWS 서비스](04-related-services.md) - 추가 서비스 활용
2. [End-to-End 파이프라인 구축](../03-integration/04-end-to-end-pipeline.md) - 전체 시스템 구축
