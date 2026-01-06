# AWS GreenGrass, Kinesis, SageMaker를 활용한 공사현장 안전관리 시스템

## 📋 프로젝트 개요

이 문서는 AWS의 IoT 및 ML 서비스(GreenGrass, Kinesis, SageMaker)를 활용하여 공사현장 안전관리 시스템을 구축하기 위한 종합 가이드입니다.

### 대상 독자
- AWS 서비스를 활용한 IoT/ML 시스템 구축을 검토하는 기업
- 공사현장 안전관리 솔루션을 도입하려는 건설사
- 엣지 컴퓨팅 및 실시간 데이터 처리 시스템을 학습하려는 개발자

---

## 📚 문서 목차

### 1. 개요 (Overview)
- [1.1 프로젝트 소개 및 목표](docs/01-overview/01-introduction.md)
- [1.2 시스템 아키텍처 개요](docs/01-overview/02-system-architecture.md)
- [1.3 공사현장 안전관리의 필요성](docs/01-overview/03-safety-management-needs.md)

### 2. AWS 서비스 상세 설명 (AWS Services)
- [2.1 AWS IoT GreenGrass 완벽 가이드](docs/02-aws-services/01-greengrass.md)
- [2.2 Amazon Kinesis 완벽 가이드](docs/02-aws-services/02-kinesis.md)
- [2.3 Amazon SageMaker 완벽 가이드](docs/02-aws-services/03-sagemaker.md)
- [2.4 기타 연관 AWS 서비스](docs/02-aws-services/04-related-services.md)

### 3. 서비스 통합 및 연동 (Integration)
- [3.1 전체 아키텍처 설계](docs/03-integration/01-architecture-design.md)
- [3.2 GreenGrass-Kinesis 연동](docs/03-integration/02-greengrass-kinesis.md)
- [3.3 Kinesis-SageMaker 연동](docs/03-integration/03-kinesis-sagemaker.md)
- [3.4 End-to-End 파이프라인 구축](docs/03-integration/04-end-to-end-pipeline.md)

### 4. 경쟁 서비스 비교 (Comparison)
- [4.1 클라우드 서비스 비교 (Azure, GCP)](docs/04-comparison/01-cloud-comparison.md)
- [4.2 오픈소스 솔루션 비교](docs/04-comparison/02-opensource-comparison.md)
- [4.3 종합 비교표 및 선택 가이드](docs/04-comparison/03-comprehensive-comparison.md)

### 5. 시작하기 (Getting Started)
- [5.1 AWS 계정 생성 및 초기 설정](docs/05-getting-started/01-aws-account-setup.md)
- [5.2 IAM 권한 설정](docs/05-getting-started/02-iam-setup.md)
- [5.3 개발 환경 구성](docs/05-getting-started/03-dev-environment.md)
- [5.4 필수 도구 설치](docs/05-getting-started/04-tools-installation.md)

### 6. 구현 예제 (Implementation)
- [6.1 엣지 디바이스 설정 (GreenGrass)](docs/06-implementation/01-edge-device-setup.md)
- [6.2 실시간 데이터 스트리밍 (Kinesis)](docs/06-implementation/02-realtime-streaming.md)
- [6.3 ML 모델 개발 및 배포 (SageMaker)](docs/06-implementation/03-ml-model-deployment.md)
- [6.4 안전 감지 시스템 구축](docs/06-implementation/04-safety-detection-system.md)
- [6.5 대시보드 및 알림 시스템](docs/06-implementation/05-dashboard-alerts.md)
- [6.6 전체 시스템 통합 테스트](docs/06-implementation/06-integration-testing.md)

### 7. 비즈니스 아이디어 (Business Ideas)
- [7.1 공사현장 안전관리 솔루션](docs/07-business-ideas/01-construction-safety.md)
- [7.2 확장 가능한 비즈니스 모델](docs/07-business-ideas/02-business-models.md)
- [7.3 산업별 적용 사례](docs/07-business-ideas/03-industry-applications.md)
- [7.4 수익화 전략](docs/07-business-ideas/04-monetization.md)

### 8. 비용 분석 (Cost Analysis)
- [8.1 AWS 서비스별 요금 체계](docs/08-cost-analysis/01-aws-pricing.md)
- [8.2 규모별 예상 비용](docs/08-cost-analysis/02-cost-estimation.md)
- [8.3 비용 최적화 전략](docs/08-cost-analysis/03-cost-optimization.md)
- [8.4 ROI 분석](docs/08-cost-analysis/04-roi-analysis.md)

---

## 🏗️ 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         공사현장 안전관리 시스템                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   카메라    │    │   센서      │    │   웨어러블  │    │   드론      │  │
│  │  (CCTV)    │    │ (온도/가스) │    │   디바이스  │    │   카메라    │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │                  │         │
│         └──────────────────┴──────────────────┴──────────────────┘         │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     AWS IoT GreenGrass (Edge)                       │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ 로컬 ML 추론  │  │ 데이터 필터링 │  │ 오프라인 처리 │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Amazon Kinesis (Stream)                        │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ Data Streams  │  │ Data Firehose │  │ Data Analytics│           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Amazon SageMaker (ML/AI)                        │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │  모델 학습    │  │  모델 배포    │  │ 실시간 추론   │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        출력 및 대응 시스템                           │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │  대시보드     │  │  알림 시스템  │  │  리포트 생성  │           │   │
│  │  │ (QuickSight) │  │  (SNS/Lambda) │  │    (S3)      │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 빠른 시작

### 사전 요구사항
- AWS 계정 (프리 티어 가능)
- Python 3.8 이상
- AWS CLI v2
- Docker (선택사항)

### 설치 및 실행
```bash
# 저장소 클론
git clone https://github.com/your-repo/aws-construction-safety.git
cd aws-construction-safety

# 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# AWS 자격증명 설정
aws configure
```

---

## 📊 주요 기능

| 기능 | 설명 | 관련 서비스 |
|------|------|-------------|
| 실시간 위험 감지 | 카메라 영상에서 위험 상황 자동 감지 | GreenGrass + SageMaker |
| 안전장비 착용 확인 | 헬멧, 안전조끼 등 착용 여부 확인 | SageMaker (Object Detection) |
| 출입 관리 | 작업자 신원 확인 및 출입 기록 | Rekognition + DynamoDB |
| 환경 모니터링 | 온도, 습도, 가스 농도 실시간 감시 | IoT Core + Kinesis |
| 사고 예측 | 과거 데이터 기반 사고 위험도 예측 | SageMaker (ML) |
| 긴급 알림 | 위험 감지 시 즉시 관리자 알림 | SNS + Lambda |

---

## 📁 프로젝트 구조

```
AWS_GreenGrass_Kinesis_SageMaker/
├── README.md                    # 이 파일
├── docs/                        # 문서
│   ├── 01-overview/            # 개요
│   ├── 02-aws-services/        # AWS 서비스 설명
│   ├── 03-integration/         # 서비스 통합
│   ├── 04-comparison/          # 경쟁 서비스 비교
│   ├── 05-getting-started/     # 시작 가이드
│   ├── 06-implementation/      # 구현 예제
│   ├── 07-business-ideas/      # 비즈니스 아이디어
│   └── 08-cost-analysis/       # 비용 분석
├── src/                         # 소스 코드
│   ├── greengrass/             # GreenGrass 컴포넌트
│   ├── kinesis/                # Kinesis 처리 코드
│   ├── sagemaker/              # SageMaker 노트북 및 스크립트
│   └── lambda/                 # Lambda 함수
├── infrastructure/              # IaC (Infrastructure as Code)
│   ├── cloudformation/         # CloudFormation 템플릿
│   └── terraform/              # Terraform 설정
└── tests/                       # 테스트 코드
```

---

## 📞 문의 및 지원

- 이슈 리포트: GitHub Issues
- 기술 문의: tech-support@example.com

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
