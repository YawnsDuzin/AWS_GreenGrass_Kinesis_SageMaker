# 🏗️ Raspberry Pi 4 PPE 감지 시스템 구축 튜토리얼

## AWS GreenGrass + Kinesis + SageMaker 완전 가이드

이 튜토리얼은 Raspberry Pi 4를 사용하여 건설현장 PPE(개인보호장비) 감지 시스템을
처음부터 끝까지 구축하는 방법을 안내합니다.

---

## 📋 목차

| 파트 | 제목 | 설명 | 예상 시간 |
|------|------|------|-----------|
| 1 | [AWS 계정 및 IAM 설정](./01-aws-account-setup.md) | AWS 가입, IAM 사용자/역할 생성 | 30분 |
| 2 | [Raspberry Pi 4 설정](./02-raspberry-pi-setup.md) | OS 설치, 카메라, 네트워크 설정 | 1시간 |
| 3 | [AWS IoT Core & GreenGrass](./03-iot-greengrass-setup.md) | IoT Thing 등록, GreenGrass V2 설치 | 1시간 |
| 4 | [Kinesis 설정](./04-kinesis-setup.md) | Data Streams, Firehose, Video Streams | 30분 |
| 5 | [SageMaker 모델 학습](./05-sagemaker-training.md) | YOLOv8 PPE 감지 모델 학습 | 2-3시간 |
| 6 | [GreenGrass 컴포넌트 배포](./06-component-deployment.md) | 감지 컴포넌트 개발 및 배포 | 1시간 |
| 7 | [PPE 감지 구현](./07-ppe-detection.md) | 실시간 감지 로직 구현 | 1시간 |
| 8 | [알림 시스템 구축](./08-alert-system.md) | SNS, Lambda를 통한 알림 | 30분 |
| 9 | [테스트 및 모니터링](./09-testing-monitoring.md) | 시스템 테스트, CloudWatch 설정 | 30분 |

---

## 🎯 최종 목표

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        건설현장 PPE 감지 시스템                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   [Raspberry Pi 4]          [AWS Cloud]                                │
│   ┌──────────────┐          ┌────────────────────────────────┐         │
│   │   카메라      │          │                                │         │
│   │      ↓       │          │  ┌──────────┐   ┌───────────┐  │         │
│   │  YOLOv8 추론  │ ──────→  │  │ Kinesis  │ → │  Lambda   │  │         │
│   │      ↓       │          │  │ Streams  │   │           │  │         │
│   │  GreenGrass  │          │  └──────────┘   └─────┬─────┘  │         │
│   │  컴포넌트     │          │                       ↓        │         │
│   └──────────────┘          │  ┌──────────┐   ┌───────────┐  │         │
│                             │  │    S3    │   │    SNS    │  │         │
│                             │  │ (저장소)  │   │  (알림)    │  │         │
│                             │  └──────────┘   └───────────┘  │         │
│                             └────────────────────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 필요 장비 및 준비물

### 하드웨어
| 품목 | 권장 사양 | 예상 가격 |
|------|----------|----------|
| Raspberry Pi 4 | Model B, 4GB 이상 RAM | ~$55 |
| microSD 카드 | 32GB 이상, Class 10 | ~$10 |
| 카메라 모듈 | Pi Camera V2 또는 USB 웹캠 | ~$25 |
| 전원 어댑터 | 5V 3A USB-C | ~$10 |
| 방열판/케이스 | (선택) 쿨링 팬 포함 | ~$15 |
| 이더넷 케이블 | (선택) WiFi 대신 유선 | ~$5 |

### 소프트웨어
- Raspberry Pi OS (64-bit) Bullseye 이상
- Python 3.9+
- AWS CLI v2
- AWS IoT GreenGrass V2

### AWS 계정
- AWS 계정 (신규 가입 시 프리티어 사용 가능)
- 신용카드 (계정 인증용)

---

## 💰 예상 AWS 비용 (월간)

| 서비스 | 사용량 | 예상 비용 |
|--------|--------|----------|
| IoT Core | 100만 메시지 | ~$1 |
| Kinesis Data Streams | 2 샤드 | ~$30 |
| Lambda | 100만 요청 | 프리티어 |
| S3 | 10GB 저장 | ~$0.25 |
| SageMaker | ml.g4dn.xlarge 5시간 | ~$3 |
| SNS | 1000 알림 | 프리티어 |
| **총계** | | **~$35/월** |

> ⚠️ 개발/테스트 중에는 리소스를 꺼두면 비용을 절감할 수 있습니다.

---

## 🚀 빠른 시작

모든 파트를 순서대로 진행하거나, 필요한 부분만 선택적으로 참고할 수 있습니다.

### 순서대로 진행하기
```bash
# 1. 이 저장소 클론
git clone https://github.com/your-repo/AWS_GreenGrass_Kinesis_SageMaker.git
cd AWS_GreenGrass_Kinesis_SageMaker/tutorials

# 2. Part 1부터 순서대로 진행
# 각 파트의 마크다운 문서를 따라하세요
```

### 이미 일부 설정이 완료된 경우
- AWS 계정이 있다면 → [Part 2](./02-raspberry-pi-setup.md)부터 시작
- Raspberry Pi 설정 완료 → [Part 3](./03-iot-greengrass-setup.md)부터 시작
- GreenGrass 설치 완료 → [Part 5](./05-sagemaker-training.md)부터 시작

---

## 📞 문제 해결

튜토리얼 진행 중 문제가 발생하면:

1. 각 파트의 "문제 해결" 섹션 확인
2. [FAQ](./faq.md) 문서 참고
3. GitHub Issues에 질문 등록

---

## 📝 라이선스

이 튜토리얼은 MIT 라이선스로 제공됩니다.
