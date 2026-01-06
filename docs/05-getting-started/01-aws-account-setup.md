# 5.1 AWS 계정 생성 및 초기 설정

## AWS 계정 생성

### Step 1: AWS 가입 페이지 접속

1. [AWS 공식 웹사이트](https://aws.amazon.com/ko/) 접속
2. 우측 상단 **"AWS 계정 생성"** 클릭

### Step 2: 계정 정보 입력

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS 계정 생성 단계                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1단계: 이메일 및 계정 이름                                              │
│  ├─ 루트 사용자 이메일: company-aws@example.com                         │
│  ├─ AWS 계정 이름: MyCompany-Production                                │
│  └─ 이메일 확인 코드 입력                                               │
│                                                                         │
│  2단계: 루트 사용자 암호 설정                                            │
│  ├─ 최소 8자, 대소문자, 숫자, 특수문자 포함                             │
│  └─ 강력한 암호 사용 권장                                               │
│                                                                         │
│  3단계: 연락처 정보                                                      │
│  ├─ 계정 유형: 비즈니스 (권장) 또는 개인                                │
│  ├─ 회사명, 전화번호, 주소 입력                                         │
│  └─ 국가: 대한민국 선택                                                 │
│                                                                         │
│  4단계: 결제 정보                                                        │
│  ├─ 신용카드/체크카드 등록                                              │
│  ├─ $1 임시 결제 후 환불 (카드 확인용)                                  │
│  └─ 청구지 주소 입력                                                    │
│                                                                         │
│  5단계: 자격 증명 확인                                                   │
│  ├─ 전화번호 인증 (SMS 또는 음성)                                       │
│  └─ 보안 문자 입력                                                      │
│                                                                         │
│  6단계: 지원 플랜 선택                                                   │
│  ├─ Basic (무료): 개발/테스트용                                         │
│  ├─ Developer ($29/월): 이메일 지원                                     │
│  ├─ Business ($100/월~): 24/7 전화/채팅 지원                           │
│  └─ Enterprise: 전담 TAM 배정                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 3: 프리 티어 확인

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS 프리 티어 (12개월)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  컴퓨팅                                                                  │
│  ├─ EC2: t2.micro 750시간/월                                           │
│  └─ Lambda: 100만 요청/월                                               │
│                                                                         │
│  스토리지                                                                │
│  ├─ S3: 5GB 표준 스토리지                                              │
│  └─ EBS: 30GB SSD                                                      │
│                                                                         │
│  데이터베이스                                                            │
│  ├─ RDS: db.t2.micro 750시간/월                                        │
│  └─ DynamoDB: 25GB 스토리지, 25 WCU/RCU                                │
│                                                                         │
│  IoT                                                                     │
│  ├─ IoT Core: 250,000 메시지/월                                        │
│  └─ GreenGrass: 3 디바이스 무료                                        │
│                                                                         │
│  ML                                                                      │
│  ├─ SageMaker: 250시간 t2.medium 노트북                                │
│  └─ Rekognition: 5,000 이미지/월                                       │
│                                                                         │
│  ⚠️ 프리 티어 초과 시 요금 청구됨                                        │
│  ⚠️ 예산 알림 설정 필수 권장                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 초기 보안 설정

### Step 1: MFA (Multi-Factor Authentication) 활성화

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    루트 계정 MFA 설정                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. AWS 콘솔 로그인 후 우측 상단 계정명 클릭                             │
│  2. "보안 자격 증명" 선택                                               │
│  3. "MFA 디바이스 할당" 클릭                                            │
│  4. MFA 디바이스 유형 선택:                                             │
│     ├─ 가상 MFA 디바이스 (Google Authenticator, Authy) - 권장          │
│     ├─ 하드웨어 TOTP 토큰                                              │
│     └─ 하드웨어 키 (YubiKey 등)                                        │
│  5. QR 코드 스캔 후 연속 2개 코드 입력                                  │
│  6. MFA 활성화 완료                                                     │
│                                                                         │
│  ⚠️ 루트 계정은 일상 작업에 사용하지 않음                                │
│  ⚠️ MFA 백업 코드 안전하게 보관                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 2: IAM 사용자 생성

```bash
# AWS CLI로 IAM 사용자 생성 (콘솔에서도 가능)

# 1. 관리자 그룹 생성
aws iam create-group --group-name Administrators

# 2. 관리자 정책 연결
aws iam attach-group-policy \
  --group-name Administrators \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 3. IAM 사용자 생성
aws iam create-user --user-name admin-user

# 4. 사용자를 관리자 그룹에 추가
aws iam add-user-to-group \
  --user-name admin-user \
  --group-name Administrators

# 5. 콘솔 로그인 암호 설정
aws iam create-login-profile \
  --user-name admin-user \
  --password 'StrongPassword123!' \
  --password-reset-required

# 6. 액세스 키 생성 (CLI/SDK 용)
aws iam create-access-key --user-name admin-user
```

### Step 3: 비용 알림 설정

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    예산 및 비용 알림 설정                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AWS Budgets 설정                                                        │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. AWS 콘솔 > "Billing and Cost Management" > "Budgets"               │
│  2. "Create budget" 클릭                                                │
│  3. 예산 유형: "Cost budget" 선택                                       │
│  4. 예산 설정:                                                          │
│     ├─ 이름: Monthly-Budget                                            │
│     ├─ 기간: Monthly                                                   │
│     ├─ 예산 금액: $100 (또는 원하는 금액)                               │
│     └─ 시작일: 현재 월                                                 │
│  5. 알림 임계값 설정:                                                   │
│     ├─ 50% 도달 시: 이메일 알림                                        │
│     ├─ 80% 도달 시: 이메일 + SMS                                       │
│     └─ 100% 도달 시: 이메일 + SMS                                      │
│                                                                         │
│  Cost Explorer 활성화                                                    │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. "Cost Explorer" 메뉴 접속                                          │
│  2. "Enable Cost Explorer" 클릭                                        │
│  3. 24시간 후 데이터 확인 가능                                          │
│                                                                         │
│  Free Tier 사용량 알림                                                   │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. "Billing preferences" 접속                                         │
│  2. "Receive Free Tier Usage Alerts" 체크                              │
│  3. 알림 수신 이메일 입력                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 리전 선택

### 서울 리전 (ap-northeast-2) 설정

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    리전 선택 가이드                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  권장 리전: 서울 (ap-northeast-2)                                        │
│                                                                         │
│  선택 이유:                                                              │
│  ├─ 가장 낮은 지연 시간 (한국 내)                                       │
│  ├─ 데이터 주권 (국내 데이터 보관)                                      │
│  ├─ 대부분의 서비스 사용 가능                                           │
│  └─ 한국어 기술 지원                                                    │
│                                                                         │
│  서울 리전 가용 영역 (AZ):                                               │
│  ├─ ap-northeast-2a                                                    │
│  ├─ ap-northeast-2b                                                    │
│  ├─ ap-northeast-2c                                                    │
│  └─ ap-northeast-2d                                                    │
│                                                                         │
│  ⚠️ 일부 서비스는 서울 리전 미지원                                       │
│     (대체 리전: 도쿄 ap-northeast-1)                                    │
│                                                                         │
│  리전 변경 방법:                                                         │
│  1. AWS 콘솔 우측 상단 리전 선택 드롭다운                               │
│  2. "아시아 태평양 (서울)" 선택                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AWS CLI 설정

### CLI 설치

```bash
# macOS
brew install awscli

# Linux (Ubuntu/Debian)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Windows (PowerShell 관리자 권한)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# 설치 확인
aws --version
# aws-cli/2.x.x Python/3.x.x ...
```

### CLI 자격 증명 설정

```bash
# 방법 1: aws configure 명령어
aws configure
# AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name [None]: ap-northeast-2
# Default output format [None]: json

# 방법 2: 프로필 지정
aws configure --profile production
aws configure --profile development

# 프로필 사용
aws s3 ls --profile production

# 환경 변수 설정 (임시)
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=ap-northeast-2
```

### 자격 증명 파일 구조

```
~/.aws/
├── config
│   [default]
│   region = ap-northeast-2
│   output = json
│
│   [profile production]
│   region = ap-northeast-2
│   output = json
│
└── credentials
    [default]
    aws_access_key_id = AKIAIOSFODNN7EXAMPLE
    aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

    [production]
    aws_access_key_id = AKIAI44QH8DHBEXAMPLE
    aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
```

---

## VPC 설정

### 기본 VPC 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VPC 아키텍처 (권장 구성)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  VPC: 10.0.0.0/16                                                       │
│  ├─────────────────────────────────────────────────────────────────────│
│  │                                                                      │
│  │  AZ-a (ap-northeast-2a)         AZ-c (ap-northeast-2c)              │
│  │  ┌───────────────────────────┐  ┌───────────────────────────┐       │
│  │  │ Public Subnet             │  │ Public Subnet             │       │
│  │  │ 10.0.1.0/24               │  │ 10.0.2.0/24               │       │
│  │  │ ┌─────────┐ ┌─────────┐   │  │ ┌─────────┐ ┌─────────┐   │       │
│  │  │ │   NAT   │ │   ALB   │   │  │ │   NAT   │ │   ALB   │   │       │
│  │  │ │ Gateway │ │         │   │  │ │ Gateway │ │         │   │       │
│  │  │ └─────────┘ └─────────┘   │  │ └─────────┘ └─────────┘   │       │
│  │  └───────────────────────────┘  └───────────────────────────┘       │
│  │                                                                      │
│  │  ┌───────────────────────────┐  ┌───────────────────────────┐       │
│  │  │ Private Subnet            │  │ Private Subnet            │       │
│  │  │ 10.0.11.0/24              │  │ 10.0.12.0/24              │       │
│  │  │ ┌─────────┐ ┌─────────┐   │  │ ┌─────────┐ ┌─────────┐   │       │
│  │  │ │   EC2   │ │  Lambda │   │  │ │   EC2   │ │  Lambda │   │       │
│  │  │ └─────────┘ └─────────┘   │  │ └─────────┘ └─────────┘   │       │
│  │  └───────────────────────────┘  └───────────────────────────┘       │
│  │                                                                      │
│  │  ┌───────────────────────────┐  ┌───────────────────────────┐       │
│  │  │ Data Subnet               │  │ Data Subnet               │       │
│  │  │ 10.0.21.0/24              │  │ 10.0.22.0/24              │       │
│  │  │ ┌─────────┐ ┌─────────┐   │  │ ┌─────────┐ ┌─────────┐   │       │
│  │  │ │   RDS   │ │DynamoDB │   │  │ │   RDS   │ │ElastiCache  │       │
│  │  │ └─────────┘ └─────────┘   │  │ └─────────┘ └─────────┘   │       │
│  │  └───────────────────────────┘  └───────────────────────────┘       │
│  │                                                                      │
│  └─────────────────────────────────────────────────────────────────────│
│                                                                         │
│  Internet Gateway: igw-xxxxxx                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### CloudFormation으로 VPC 생성

```yaml
# vpc-template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'VPC for Construction Safety System'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues:
      - development
      - staging
      - production

Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-safety-vpc'

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-igw'

  AttachGateway:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs '']
      CidrBlock: 10.0.1.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-public-1'

  PublicSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [2, !GetAZs '']
      CidrBlock: 10.0.2.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-public-2'

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs '']
      CidrBlock: 10.0.11.0/24
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-private-1'

  PrivateSubnet2:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [2, !GetAZs '']
      CidrBlock: 10.0.12.0/24
      Tags:
        - Key: Name
          Value: !Sub '${Environment}-private-2'

Outputs:
  VpcId:
    Description: VPC ID
    Value: !Ref VPC
    Export:
      Name: !Sub '${Environment}-VpcId'
  PublicSubnet1:
    Description: Public Subnet 1 ID
    Value: !Ref PublicSubnet1
    Export:
      Name: !Sub '${Environment}-PublicSubnet1'
  PrivateSubnet1:
    Description: Private Subnet 1 ID
    Value: !Ref PrivateSubnet1
    Export:
      Name: !Sub '${Environment}-PrivateSubnet1'
```

```bash
# CloudFormation 스택 생성
aws cloudformation create-stack \
  --stack-name safety-system-vpc \
  --template-body file://vpc-template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production
```

---

## 필수 서비스 활성화

### 서비스 활성화 체크리스트

```bash
# 1. IoT Core 설정
aws iot describe-endpoint --endpoint-type iot:Data-ATS

# 2. Kinesis 스트림 생성 테스트
aws kinesis create-stream \
  --stream-name test-stream \
  --shard-count 1

# 3. S3 버킷 생성
aws s3 mb s3://my-safety-data-bucket-unique-name

# 4. DynamoDB 테이블 생성 테스트
aws dynamodb create-table \
  --table-name test-table \
  --attribute-definitions AttributeName=pk,AttributeType=S \
  --key-schema AttributeName=pk,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# 5. Lambda 테스트 함수 생성
# (별도 ZIP 파일 필요)

# 테스트 리소스 정리
aws kinesis delete-stream --stream-name test-stream
aws dynamodb delete-table --table-name test-table
```

---

## 다음 단계

1. [IAM 권한 설정](02-iam-setup.md) - 상세 권한 구성
2. [개발 환경 구성](03-dev-environment.md) - 개발 도구 설정
