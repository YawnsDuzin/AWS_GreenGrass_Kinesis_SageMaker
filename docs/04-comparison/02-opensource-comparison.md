# 4.2 오픈소스 솔루션 비교

## 개요

AWS 서비스 대신 사용할 수 있는 오픈소스 솔루션들을 비교합니다. 자체 인프라 구축이나 하이브리드 환경에서 활용 가능합니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS vs 오픈소스 매핑                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AWS 서비스           │    오픈소스 대안                                │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  IoT GreenGrass       │ EdgeX Foundry, Eclipse Kura, K3s + KubeEdge    │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  IoT Core             │ Eclipse Mosquitto, EMQX, HiveMQ (Community)    │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  Kinesis Streams      │ Apache Kafka, Apache Pulsar, Redpanda          │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  Kinesis Analytics    │ Apache Flink, Apache Spark Streaming, ksqlDB   │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  SageMaker            │ MLflow, Kubeflow, Ray, BentoML                 │
│  ─────────────────────┼─────────────────────────────────────────────────│
│  Rekognition          │ OpenCV, YOLO, MediaPipe, TensorFlow Hub        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 엣지 컴퓨팅 오픈소스

### EdgeX Foundry

Linux Foundation에서 관리하는 벤더 중립적 IoT 엣지 플랫폼입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EdgeX Foundry 아키텍처                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                      Application Services                       │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │
│   │  │ Rules Engine│  │ Export      │  │ Analytics   │             │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘             │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                       Core Services                             │  │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐      │  │
│   │  │ Data      │ │ Metadata  │ │ Command   │ │ Registry  │      │  │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘      │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                      Device Services                            │  │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐      │  │
│   │  │ MQTT      │ │ Modbus    │ │ Camera    │ │ REST      │      │  │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘      │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                            Physical Devices                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 특징 및 비교

| 항목 | EdgeX Foundry | AWS GreenGrass |
|------|---------------|----------------|
| **라이선스** | Apache 2.0 | 독점 (V2는 일부 오픈소스) |
| **벤더 종속** | 없음 | AWS 종속 |
| **프로토콜 지원** | 매우 다양 | 제한적 |
| **ML 통합** | 별도 구현 필요 | 네이티브 지원 |
| **커뮤니티** | 활발 | AWS 지원 |
| **학습 곡선** | 중간 | 낮음 |
| **운영 비용** | 인프라만 | 서비스 비용 |

#### 설치 및 구성

```bash
# Docker Compose로 EdgeX 설치
git clone https://github.com/edgexfoundry/edgex-compose.git
cd edgex-compose

# 최신 릴리즈 (Minnesota 버전)
docker-compose -f docker-compose-no-secty.yml up -d

# 상태 확인
docker-compose ps

# 디바이스 서비스 추가 (카메라)
docker-compose -f docker-compose-no-secty.yml \
  -f add-device-camera.yml up -d
```

```yaml
# device-camera.yaml - 카메라 디바이스 정의
name: "safety-camera-01"
description: "공사현장 안전 카메라"
protocols:
  camera:
    Address: "rtsp://192.168.1.100:554/stream1"
    AuthMode: "usernametoken"
    Username: "admin"
    Password: "password"
```

---

### KubeEdge

Kubernetes를 엣지로 확장하는 CNCF 프로젝트입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    KubeEdge 아키텍처                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Cloud Side                              │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                    Kubernetes Cluster                   │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │   │
│  │  │  │ CloudCore   │  │ EdgeCtrl    │  │ DeviceCtrl  │     │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                              WebSocket                                  │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Edge Side                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │                      EdgeCore                           │   │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐             │   │   │
│  │  │  │ Edged     │ │ EventBus  │ │ DeviceTwin│             │   │   │
│  │  │  │(kubelet)  │ │ (MQTT)    │ │           │             │   │   │
│  │  │  └───────────┘ └───────────┘ └───────────┘             │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                         │                                       │   │
│  │                    ┌────┴────┐                                  │   │
│  │                    │ Devices │                                  │   │
│  │                    └─────────┘                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 설치

```bash
# Cloud Side 설치 (Kubernetes 클러스터에)
keadm init --advertise-address="<cloud-ip>" --kubeedge-version=1.15.0

# Edge Side 설치 (엣지 디바이스에)
keadm join --cloudcore-ipport="<cloud-ip>:10000" \
  --token=<token> --kubeedge-version=1.15.0
```

---

### 엣지 컴퓨팅 오픈소스 비교표

| 항목 | EdgeX Foundry | KubeEdge | Eclipse Kura | K3s |
|------|---------------|----------|--------------|-----|
| **관리 주체** | Linux Foundation | CNCF | Eclipse | Rancher |
| **아키텍처** | 마이크로서비스 | Kubernetes 확장 | OSGi 기반 | 경량 K8s |
| **리소스 요구** | 중간 (512MB+) | 높음 (1GB+) | 낮음 (256MB) | 중간 (512MB+) |
| **프로토콜** | 다양 | 제한적 | 다양 | 컨테이너 기반 |
| **ML 지원** | 플러그인 | KubeFlow 연동 | 제한적 | 컨테이너 |
| **학습 곡선** | 중간 | 높음 | 중간 | 낮음 |
| **오프라인** | 지원 | 지원 | 지원 | 지원 |
| **적합 규모** | 중소형 | 대규모 | 소형 | 중소형 |

---

## 2. 메시징/스트리밍 오픈소스

### Apache Kafka

가장 널리 사용되는 분산 스트리밍 플랫폼입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Apache Kafka 아키텍처                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Producers                   Kafka Cluster                Consumers   │
│                                                                         │
│   ┌─────────┐       ┌─────────────────────────────────┐  ┌─────────┐  │
│   │ IoT     │       │   Topic: safety-events          │  │ Flink   │  │
│   │ Gateway │──────▶│   ┌─────┐ ┌─────┐ ┌─────┐      │─▶│ Job     │  │
│   └─────────┘       │   │ P0  │ │ P1  │ │ P2  │      │  └─────────┘  │
│                     │   └─────┘ └─────┘ └─────┘      │                │
│   ┌─────────┐       │                                 │  ┌─────────┐  │
│   │ Edge    │──────▶│   Brokers: broker-1, 2, 3       │─▶│ Spark   │  │
│   │ Device  │       │                                 │  │ Streaming│ │
│   └─────────┘       │   Zookeeper / KRaft             │  └─────────┘  │
│                     └─────────────────────────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Kafka vs Kinesis 비교

| 항목 | Apache Kafka | Amazon Kinesis |
|------|--------------|----------------|
| **유형** | 오픈소스 | 관리형 서비스 |
| **처리량** | 무제한 (확장 가능) | 샤드당 1MB/s |
| **지연 시간** | ~2ms | ~70ms |
| **보존 기간** | 무제한 | 최대 365일 |
| **운영 복잡도** | 높음 | 매우 낮음 |
| **비용 모델** | 인프라 비용 | 사용량 기반 |
| **스키마 관리** | Schema Registry | Glue Schema Registry |
| **생태계** | 매우 넓음 | AWS 통합 |

#### Kafka 설치 (Docker)

```yaml
# docker-compose.yml
version: '3'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
```

#### Kafka Producer 예시

```python
# kafka_producer.py
from confluent_kafka import Producer
import json

def create_producer():
    config = {
        'bootstrap.servers': 'localhost:9092',
        'client.id': 'safety-producer'
    }
    return Producer(config)

def send_safety_event(producer, event):
    def delivery_callback(err, msg):
        if err:
            print(f'Delivery failed: {err}')
        else:
            print(f'Delivered to {msg.topic()} [{msg.partition()}]')

    producer.produce(
        topic='safety-events',
        key=event['device_id'].encode('utf-8'),
        value=json.dumps(event).encode('utf-8'),
        callback=delivery_callback
    )
    producer.flush()

# 사용 예시
producer = create_producer()
event = {
    'device_id': 'camera-01',
    'timestamp': '2024-01-15T10:30:00Z',
    'event_type': 'SAFETY_VIOLATION',
    'violation_type': 'NO_HELMET'
}
send_safety_event(producer, event)
```

---

### Apache Pulsar

차세대 메시징/스트리밍 플랫폼으로, Kafka의 대안입니다.

| 항목 | Apache Kafka | Apache Pulsar |
|------|--------------|---------------|
| **아키텍처** | 단일 계층 | 컴퓨팅/스토리지 분리 |
| **멀티테넌시** | 제한적 | 네이티브 지원 |
| **지역 복제** | MirrorMaker 필요 | 내장 |
| **스키마** | 별도 레지스트리 | 내장 |
| **프로토콜** | Kafka 프로토콜 | 자체 + Kafka 호환 |
| **성숙도** | 매우 높음 | 성장 중 |

### MQTT 브로커 비교

| 항목 | Eclipse Mosquitto | EMQX | HiveMQ |
|------|------------------|------|--------|
| **라이선스** | EPL 2.0 | Apache 2.0 | Community: Apache |
| **클러스터링** | 미지원 (브릿지) | 네이티브 | Enterprise만 |
| **처리량** | 낮음 | 매우 높음 | 높음 |
| **규칙 엔진** | 미지원 | 지원 | Enterprise |
| **모니터링** | 기본 | 대시보드 | 대시보드 |
| **적합 규모** | 소형 | 대규모 | 중대형 |

---

## 3. 실시간 분석 오픈소스

### Apache Flink

스트림 및 배치 처리를 위한 분산 처리 엔진입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Apache Flink 아키텍처                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Flink Cluster                              │   │
│  │                                                                  │   │
│  │  ┌─────────────┐                                                │   │
│  │  │ JobManager  │  ← 클러스터 코디네이터                         │   │
│  │  └─────────────┘                                                │   │
│  │         │                                                        │   │
│  │  ┌──────┴──────┐                                                │   │
│  │  │             │                                                 │   │
│  │  ▼             ▼                                                 │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐                     │   │
│  │  │TaskManager│ │TaskManager│ │TaskManager│  ← 워커 노드         │   │
│  │  │  ┌─────┐  │ │  ┌─────┐  │ │  ┌─────┐  │                     │   │
│  │  │  │Slot │  │ │  │Slot │  │ │  │Slot │  │                     │   │
│  │  │  └─────┘  │ │  └─────┘  │ │  └─────┘  │                     │   │
│  │  │  ┌─────┐  │ │  ┌─────┐  │ │  ┌─────┐  │                     │   │
│  │  │  │Slot │  │ │  │Slot │  │ │  │Slot │  │                     │   │
│  │  │  └─────┘  │ │  └─────┘  │ │  └─────┘  │                     │   │
│  │  └───────────┘ └───────────┘ └───────────┘                     │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Source (Kafka) ──▶ Transformation ──▶ Sink (DB, Kafka, etc.)        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Flink 안전 이벤트 처리 예시

```java
// SafetyEventProcessor.java
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;

public class SafetyEventProcessor {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Kafka 소스
        Properties props = new Properties();
        props.setProperty("bootstrap.servers", "localhost:9092");
        props.setProperty("group.id", "safety-processor");

        FlinkKafkaConsumer<SafetyEvent> consumer = new FlinkKafkaConsumer<>(
            "safety-events",
            new SafetyEventSchema(),
            props
        );

        DataStream<SafetyEvent> events = env.addSource(consumer);

        // 5분 윈도우로 위반 집계
        DataStream<ViolationSummary> violations = events
            .filter(e -> e.getEventType().equals("SAFETY_VIOLATION"))
            .keyBy(SafetyEvent::getSiteId)
            .timeWindow(Time.minutes(5))
            .aggregate(new ViolationAggregator());

        // 임계값 초과 시 알림
        violations
            .filter(v -> v.getCount() > 10)
            .addSink(new AlertSink());

        env.execute("Safety Event Processing");
    }
}
```

### 스트림 처리 엔진 비교

| 항목 | Apache Flink | Apache Spark Streaming | ksqlDB |
|------|--------------|----------------------|--------|
| **처리 모델** | 진정한 스트림 | 마이크로배치 | 스트림 SQL |
| **지연 시간** | 밀리초 | 초 단위 | 밀리초 |
| **상태 관리** | 우수 | 양호 | Kafka 기반 |
| **정확성 보장** | Exactly-once | Exactly-once | Exactly-once |
| **학습 곡선** | 높음 | 중간 | 낮음 (SQL) |
| **복잡한 이벤트** | 매우 강력 | 제한적 | 중간 |
| **ML 통합** | FlinkML | MLlib | 제한적 |

---

## 4. ML 플랫폼 오픈소스

### MLflow

ML 실험 추적 및 모델 관리를 위한 오픈소스 플랫폼입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MLflow 구성요소                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MLflow Tracking                            │   │
│  │  • 실험 파라미터, 메트릭 기록                                    │   │
│  │  • 소스 코드 버전 관리                                           │   │
│  │  • 아티팩트 (모델, 데이터) 저장                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MLflow Projects                            │   │
│  │  • 재현 가능한 ML 코드 패키징                                    │   │
│  │  • 환경 정의 (conda, docker)                                     │   │
│  │  • 멀티 스텝 워크플로우                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MLflow Models                              │   │
│  │  • 모델 패키징 표준                                              │   │
│  │  • 다양한 배포 대상 지원                                         │   │
│  │  • 모델 서빙 (REST API)                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      MLflow Registry                            │   │
│  │  • 중앙 모델 저장소                                              │   │
│  │  • 모델 버전 관리                                                │   │
│  │  • 스테이지 관리 (Staging, Production)                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### MLflow 사용 예시

```python
# train_with_mlflow.py
import mlflow
import mlflow.pytorch
from ultralytics import YOLO

# MLflow 설정
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("safety-detection")

with mlflow.start_run(run_name="yolov8-safety-v1"):
    # 하이퍼파라미터 로깅
    params = {
        "model": "yolov8m",
        "epochs": 100,
        "batch_size": 16,
        "imgsz": 640
    }
    mlflow.log_params(params)

    # 모델 학습
    model = YOLO("yolov8m.pt")
    results = model.train(
        data="safety_data.yaml",
        epochs=params["epochs"],
        batch=params["batch_size"],
        imgsz=params["imgsz"]
    )

    # 메트릭 로깅
    mlflow.log_metrics({
        "mAP50": results.results_dict["metrics/mAP50(B)"],
        "mAP50-95": results.results_dict["metrics/mAP50-95(B)"],
        "precision": results.results_dict["metrics/precision(B)"],
        "recall": results.results_dict["metrics/recall(B)"]
    })

    # 모델 등록
    mlflow.pytorch.log_model(
        model,
        "model",
        registered_model_name="safety-detection-model"
    )
```

### Kubeflow

Kubernetes 기반의 ML 파이프라인 플랫폼입니다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kubeflow 구성요소                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Kubeflow Central Dashboard                     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │          │          │          │          │          │          │  │
│  │ Notebooks│ Pipelines│ Training │ Serving  │ AutoML   │ Feature  │  │
│  │ (Jupyter)│ (Argo)   │ (TFJob)  │ (KServe) │ (Katib)  │ Store    │  │
│  │          │          │          │          │          │ (Feast)  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘  │
│                                    │                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      Kubernetes Cluster                           │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### ML 플랫폼 오픈소스 비교

| 항목 | MLflow | Kubeflow | Ray | BentoML |
|------|--------|----------|-----|---------|
| **초점** | 실험 추적 | End-to-End | 분산 컴퓨팅 | 모델 서빙 |
| **인프라** | 독립적 | Kubernetes | 독립/K8s | 독립/K8s |
| **학습 곡선** | 낮음 | 높음 | 중간 | 낮음 |
| **파이프라인** | 기본 | 강력 (Argo) | Ray Workflows | Yatai |
| **서빙** | 기본 | KServe | Ray Serve | 우수 |
| **스케일링** | 제한적 | 우수 | 우수 | 우수 |
| **커뮤니티** | 넓음 | 넓음 | 성장 중 | 성장 중 |

---

## 5. 컴퓨터 비전 오픈소스

### YOLO (Ultralytics)

실시간 객체 감지를 위한 최신 모델입니다.

```python
# yolo_safety_detection.py
from ultralytics import YOLO
import cv2

class SafetyDetector:
    def __init__(self, model_path="yolov8m.pt"):
        self.model = YOLO(model_path)
        self.safety_classes = {
            'person': 0,
            'helmet': 1,
            'vest': 2,
            'no_helmet': 3,
            'no_vest': 4
        }

    def detect(self, frame, conf_threshold=0.5):
        results = self.model(frame, conf=conf_threshold)

        detections = []
        for r in results:
            for box in r.boxes:
                detections.append({
                    'class': r.names[int(box.cls)],
                    'confidence': float(box.conf),
                    'bbox': box.xyxy[0].tolist()
                })

        return detections

    def train_custom(self, data_yaml, epochs=100):
        """커스텀 모델 학습"""
        results = self.model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=640,
            batch=16,
            device=0  # GPU
        )
        return results

    def export_for_edge(self, format='onnx'):
        """엣지 배포용 모델 내보내기"""
        self.model.export(
            format=format,
            opset=12,
            simplify=True,
            dynamic=False,
            imgsz=640
        )
```

### 컴퓨터 비전 라이브러리 비교

| 항목 | YOLOv8 | MediaPipe | OpenCV DNN | TensorFlow Hub |
|------|--------|-----------|------------|----------------|
| **용도** | 객체 감지 | 포즈/얼굴 | 범용 | 사전학습 모델 |
| **속도** | 매우 빠름 | 빠름 | 중간 | 다양 |
| **정확도** | 높음 | 높음 | 다양 | 다양 |
| **커스텀 학습** | 매우 쉬움 | 제한적 | 모델 의존 | 가능 |
| **엣지 배포** | 우수 | 우수 | 양호 | 양호 |
| **라이선스** | AGPL-3.0 | Apache 2.0 | Apache 2.0 | 모델별 |

---

## 6. 종합 비용 비교

### 인프라 기반 구축 vs AWS 관리형 서비스

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    월간 비용 비교 (중형 규모)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AWS 관리형 서비스                                                       │
│  ├─ IoT GreenGrass + IoT Core: $50                                     │
│  ├─ Kinesis (Data Streams + Analytics): $200                           │
│  ├─ SageMaker (엔드포인트): $550                                       │
│  ├─ 기타 (S3, DynamoDB, Lambda): $100                                  │
│  └─ 합계: 약 $900/월                                                    │
│                                                                         │
│  오픈소스 + 자체 인프라 (AWS EC2)                                        │
│  ├─ EdgeX (엣지 디바이스): $0 (소프트웨어)                             │
│  ├─ Kafka 클러스터 (3x m5.large): $230                                 │
│  ├─ Flink 클러스터 (3x m5.xlarge): $345                                │
│  ├─ ML 서빙 (g4dn.xlarge): $530                                        │
│  ├─ 기타 인프라: $100                                                   │
│  ├─ 운영 인력 (부분): $500 (추정)                                      │
│  └─ 합계: 약 $1,705/월                                                  │
│                                                                         │
│  오픈소스 + On-Premise                                                   │
│  ├─ 초기 하드웨어 투자: $10,000 (서버 3대)                             │
│  ├─ 월간 전기/냉각: $200                                                │
│  ├─ 운영 인력: $1,000 (추정)                                           │
│  ├─ 소프트웨어: $0                                                      │
│  └─ 합계: 약 $1,200/월 + 초기투자                                       │
│                                                                         │
│  결론:                                                                   │
│  • 단기/중소규모: AWS 관리형 서비스 유리                                │
│  • 대규모/장기: 오픈소스 + 자체 인프라 유리                             │
│  • 운영 역량 중요: 오픈소스는 전문 인력 필요                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 오픈소스 선택 가이드

### 시나리오별 추천

| 시나리오 | 엣지 | 메시징 | 분석 | ML |
|----------|------|--------|------|-----|
| **빠른 PoC** | K3s | Kafka (Confluent Cloud) | ksqlDB | MLflow |
| **소규모 운영** | EdgeX | Mosquitto | Flink (단일) | MLflow + BentoML |
| **중규모 운영** | KubeEdge | Kafka | Flink (클러스터) | Kubeflow |
| **대규모 운영** | KubeEdge + Anthos | Kafka + Pulsar | Flink + Spark | Kubeflow |
| **비용 최소화** | K3s | Mosquitto | ksqlDB | MLflow |

### 하이브리드 접근법 (추천)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    권장 하이브리드 아키텍처                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  엣지 (현장)                                                             │
│  ├─ 런타임: EdgeX Foundry 또는 K3s                                     │
│  ├─ ML 추론: YOLO (ONNX Runtime)                                       │
│  └─ 메시징: MQTT (Mosquitto)                                            │
│                                                                         │
│  클라우드 (데이터 처리)                                                  │
│  ├─ 스트리밍: Amazon Kinesis 또는 Confluent Kafka                      │
│  ├─ 분석: Kinesis Analytics 또는 자체 Flink                            │
│  └─ 저장: S3 + DynamoDB                                                 │
│                                                                         │
│  ML 파이프라인                                                           │
│  ├─ 실험 추적: MLflow (자체 호스팅)                                    │
│  ├─ 학습: SageMaker 또는 자체 GPU 서버                                 │
│  └─ 서빙: SageMaker 엔드포인트 또는 BentoML                            │
│                                                                         │
│  이점:                                                                   │
│  • 벤더 종속성 최소화                                                    │
│  • 비용 최적화 (관리형과 자체 운영 혼합)                                │
│  • 기술 역량에 맞는 유연한 선택                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [종합 비교표 및 선택 가이드](03-comprehensive-comparison.md) - 최종 결정
2. [AWS 계정 생성 및 초기 설정](../05-getting-started/01-aws-account-setup.md) - 구축 시작
