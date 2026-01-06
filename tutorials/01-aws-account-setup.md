# Part 1: AWS 계정 생성 및 IAM 설정

이 파트에서는 AWS 계정을 생성하고, PPE 감지 시스템에 필요한 IAM 사용자와 역할을 설정합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] AWS 계정 생성
- [x] 루트 계정 보안 설정
- [x] IAM 사용자 생성
- [x] IAM 역할 생성 (GreenGrass, Lambda, SageMaker)
- [x] AWS CLI 설치 및 구성

---

## 1. AWS 계정 생성

### 1.1 AWS 웹사이트 접속

1. 브라우저에서 [https://aws.amazon.com](https://aws.amazon.com) 접속
2. 우측 상단의 **"AWS 계정 생성"** 클릭

### 1.2 계정 정보 입력

```
이메일 주소: your-email@example.com
계정 이름: ConstructionSafetyProject (원하는 이름)
```

![AWS 계정 생성](https://via.placeholder.com/600x300?text=AWS+Account+Creation)

### 1.3 연락처 정보 입력

- **계정 유형**: 개인 (Personal) 선택
- 이름, 주소, 전화번호 입력

### 1.4 결제 정보 입력

```
⚠️ 주의: 신용카드/체크카드 정보가 필요합니다.
   프리티어를 사용하더라도 계정 인증을 위해 $1이 임시 청구됩니다.
   (며칠 후 자동 취소됨)
```

### 1.5 본인 인증

- 전화번호로 SMS 또는 음성 통화 인증

### 1.6 Support 플랜 선택

```
✅ 기본 지원 - 무료 선택
   (개발/학습 용도로 충분합니다)
```

### 1.7 계정 생성 완료

- 계정 활성화에 최대 24시간 소요될 수 있음 (보통 몇 분 내)
- 활성화 완료 이메일 확인

---

## 2. 루트 계정 보안 설정

⚠️ **중요**: 루트 계정은 모든 권한을 가지므로 반드시 보안 설정을 해야 합니다.

### 2.1 AWS 콘솔 로그인

1. [https://console.aws.amazon.com](https://console.aws.amazon.com) 접속
2. **루트 사용자** 선택
3. 이메일과 비밀번호로 로그인

### 2.2 MFA(다중 인증) 활성화

1. 우측 상단 **계정 이름** 클릭 → **보안 자격 증명**
2. **다중 인증(MFA)** 섹션 → **MFA 활성화**
3. **가상 MFA 디바이스** 선택

```
📱 스마트폰에 Google Authenticator 또는 Authy 앱 설치 필요
```

4. QR 코드 스캔
5. 연속된 두 개의 MFA 코드 입력
6. **MFA 할당** 클릭

### 2.3 루트 계정 사용 제한

```
✅ 모범 사례: 루트 계정은 결제/계정 설정에만 사용
   일상적인 작업은 IAM 사용자로 수행
```

---

## 3. IAM 사용자 생성

### 3.1 IAM 콘솔 접속

1. AWS 콘솔에서 **IAM** 검색하여 접속
2. 좌측 메뉴에서 **사용자** 클릭
3. **사용자 생성** 클릭

### 3.2 사용자 세부 정보 설정

```
사용자 이름: ppe-detection-admin
```

### 3.3 권한 설정

1. **직접 정책 연결** 선택
2. 다음 정책들을 검색하여 선택:

```
✅ AmazonS3FullAccess
✅ AmazonKinesisFullAccess
✅ AWSIoTFullAccess
✅ AWSGreengrassFullAccess
✅ AmazonSageMakerFullAccess
✅ AWSLambda_FullAccess
✅ AmazonSNSFullAccess
✅ AmazonDynamoDBFullAccess
✅ CloudWatchFullAccess
✅ IAMFullAccess
```

> 📝 프로덕션 환경에서는 최소 권한 원칙에 따라 필요한 권한만 부여하세요.

### 3.4 사용자 생성 완료

1. **사용자 생성** 클릭
2. 생성된 사용자 클릭 → **보안 자격 증명** 탭
3. **액세스 키 만들기** 클릭

```
사용 사례: Command Line Interface (CLI)
```

4. **액세스 키 생성** 완료

### 3.5 액세스 키 저장

```
⚠️ 중요: 이 정보는 한 번만 표시됩니다!
   안전한 곳에 저장하세요.

Access Key ID: AKIAXXXXXXXXXXXXXXXX
Secret Access Key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**CSV 다운로드**하여 안전하게 보관

---

## 4. IAM 역할 생성

### 4.1 GreenGrass 서비스 역할

1. IAM 콘솔 → **역할** → **역할 생성**
2. 신뢰할 수 있는 엔터티: **AWS 서비스**
3. 사용 사례: **Greengrass**

```
역할 이름: ConstructionSafety-GreengrassRole
```

4. 정책 연결:
```
✅ AWSGreengrassResourceAccessRolePolicy
✅ AmazonS3ReadOnlyAccess
✅ AmazonKinesisFullAccess
```

5. **역할 생성** 클릭

### 4.2 GreenGrass 토큰 교환 역할

1. IAM → **역할** → **역할 생성**
2. 신뢰할 수 있는 엔터티: **사용자 지정 신뢰 정책**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "credentials.iot.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. 역할 이름: `ConstructionSafety-TokenExchangeRole`

4. 역할 생성 후, **인라인 정책 추가**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:*",
        "greengrass:*",
        "s3:GetObject",
        "s3:PutObject",
        "kinesis:PutRecord",
        "kinesis:PutRecords",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4.3 Lambda 실행 역할

1. IAM → **역할** → **역할 생성**
2. 신뢰할 수 있는 엔터티: **AWS 서비스** → **Lambda**
3. 역할 이름: `ConstructionSafety-LambdaRole`

4. 정책 연결:
```
✅ AWSLambdaBasicExecutionRole
✅ AWSLambdaKinesisExecutionRole
✅ AmazonDynamoDBFullAccess
✅ AmazonSNSFullAccess
```

### 4.4 SageMaker 실행 역할

1. IAM → **역할** → **역할 생성**
2. 신뢰할 수 있는 엔터티: **AWS 서비스** → **SageMaker**
3. 역할 이름: `ConstructionSafety-SageMakerRole`

4. 정책 연결:
```
✅ AmazonSageMakerFullAccess
✅ AmazonS3FullAccess
```

---

## 5. AWS CLI 설치 및 구성

### 5.1 로컬 PC에 AWS CLI 설치

#### Windows
```powershell
# MSI 설치 프로그램 다운로드 및 실행
https://awscli.amazonaws.com/AWSCLIV2.msi
```

#### macOS
```bash
# Homebrew 사용
brew install awscli

# 또는 공식 설치 프로그램
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

#### Linux (Ubuntu/Debian)
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### 5.2 설치 확인

```bash
aws --version
# 출력: aws-cli/2.x.x Python/3.x.x ...
```

### 5.3 AWS CLI 구성

```bash
aws configure
```

프롬프트에 다음 정보 입력:

```
AWS Access Key ID [None]: AKIAXXXXXXXXXXXXXXXX
AWS Secret Access Key [None]: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
Default region name [None]: ap-northeast-2
Default output format [None]: json
```

### 5.4 구성 확인

```bash
# 자격 증명 확인
aws sts get-caller-identity
```

예상 출력:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/ppe-detection-admin"
}
```

### 5.5 리전 설정 확인

```bash
# 서울 리전 사용 확인
aws configure get region
# 출력: ap-northeast-2
```

---

## 6. 추가 보안 설정 (권장)

### 6.1 비밀번호 정책 설정

IAM 콘솔 → **계정 설정** → **비밀번호 정책 편집**

```
✅ 최소 12자
✅ 대문자 포함
✅ 소문자 포함
✅ 숫자 포함
✅ 특수문자 포함
✅ 90일마다 만료
```

### 6.2 CloudTrail 활성화

모든 API 호출 기록을 위해:

1. CloudTrail 콘솔 접속
2. **추적 생성**
3. 추적 이름: `construction-safety-trail`
4. S3 버킷 새로 생성
5. **추적 생성** 클릭

### 6.3 예산 알림 설정

예상치 못한 요금 방지:

1. **결제 및 비용 관리** → **예산**
2. **예산 생성**
3. 월별 비용 예산: $50 (원하는 금액)
4. 80%, 100% 도달 시 이메일 알림

---

## ✅ 체크리스트

이 파트를 완료하면 다음 항목들이 준비되어야 합니다:

- [ ] AWS 계정 생성 및 활성화 완료
- [ ] 루트 계정 MFA 활성화
- [ ] IAM 사용자 `ppe-detection-admin` 생성
- [ ] 액세스 키 저장 (안전한 곳에)
- [ ] IAM 역할 4개 생성:
  - [ ] `ConstructionSafety-GreengrassRole`
  - [ ] `ConstructionSafety-TokenExchangeRole`
  - [ ] `ConstructionSafety-LambdaRole`
  - [ ] `ConstructionSafety-SageMakerRole`
- [ ] AWS CLI 설치 및 구성
- [ ] `aws sts get-caller-identity` 정상 실행

---

## 🔧 문제 해결

### Q: "aws: command not found" 오류

```bash
# PATH 확인
echo $PATH

# AWS CLI 경로 추가 (Linux/macOS)
export PATH=$PATH:/usr/local/bin

# 영구 적용
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

### Q: "Unable to locate credentials" 오류

```bash
# 자격 증명 파일 확인
cat ~/.aws/credentials

# 다시 구성
aws configure
```

### Q: 계정 활성화가 안 됨

- 이메일 스팸함 확인
- 24시간 기다리기
- AWS 지원에 문의

---

## 📚 다음 단계

[Part 2: Raspberry Pi 4 설정](./02-raspberry-pi-setup.md)으로 이동하여
Raspberry Pi 하드웨어 및 운영체제를 설정합니다.
