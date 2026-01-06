# Part 3: AWS IoT Core 및 GreenGrass V2 설정

이 파트에서는 Raspberry Pi를 AWS IoT Core에 등록하고 GreenGrass V2를 설치합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] AWS IoT Core Thing 생성
- [x] 인증서 생성 및 다운로드
- [x] IoT 정책 생성 및 연결
- [x] GreenGrass V2 Core 디바이스 설치
- [x] GreenGrass 동작 확인

---

## 1. AWS IoT Core Thing 생성

### 1.1 AWS 콘솔에서 IoT Core 접속

1. AWS 콘솔 로그인
2. 검색창에 **IoT Core** 입력하여 접속
3. 리전이 **서울 (ap-northeast-2)**인지 확인

### 1.2 Thing 생성

1. 좌측 메뉴: **관리** → **모든 디바이스** → **사물**
2. **사물 생성** 클릭
3. **단일 사물 생성** 선택 → **다음**

### 1.3 사물 속성 지정

```
사물 이름: ppe-detector-rpi4
```

> 📝 이 이름은 나중에 GreenGrass Core 이름으로 사용됩니다.

추가 구성 (선택):
```
사물 유형: (비워둠)
사물 그룹: (비워둠)
```

**다음** 클릭

### 1.4 디바이스 인증서 구성

**새 인증서 자동 생성 (권장)** 선택

**다음** 클릭

### 1.5 정책 연결 (나중에)

지금은 스킵하고 **사물 생성** 클릭

---

## 2. 인증서 다운로드

⚠️ **매우 중요**: 이 화면은 한 번만 표시됩니다!

### 2.1 다운로드할 파일들

다음 4개 파일을 모두 다운로드:

1. **디바이스 인증서** (`xxxxxxxxxx-certificate.pem.crt`)
2. **퍼블릭 키 파일** (`xxxxxxxxxx-public.pem.key`)
3. **프라이빗 키 파일** (`xxxxxxxxxx-private.pem.key`)
4. **Amazon Root CA 1** (`AmazonRootCA1.pem`)

### 2.2 로컬에 저장

```
📁 다운로드 폴더 구조:
iot-certs/
├── xxxxxxxxxx-certificate.pem.crt
├── xxxxxxxxxx-public.pem.key
├── xxxxxxxxxx-private.pem.key
└── AmazonRootCA1.pem
```

### 2.3 인증서 활성화

다운로드 완료 후 **완료** 클릭

인증서가 자동으로 활성화됨

---

## 3. IoT 정책 생성

### 3.1 정책 생성 페이지

1. 좌측 메뉴: **보안** → **정책**
2. **정책 생성** 클릭

### 3.2 정책 내용 입력

```
정책 이름: ppe-detector-policy
```

### 3.3 정책 문서 (JSON 편집기)

**JSON** 탭 클릭 후 다음 내용 입력:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:ap-northeast-2:*:client/${iot:Connection.Thing.ThingName}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Receive"
      ],
      "Resource": [
        "arn:aws:iot:ap-northeast-2:*:topic/$aws/things/${iot:Connection.Thing.ThingName}/*",
        "arn:aws:iot:ap-northeast-2:*:topic/construction/safety/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": [
        "arn:aws:iot:ap-northeast-2:*:topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/*",
        "arn:aws:iot:ap-northeast-2:*:topicfilter/construction/safety/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "greengrass:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**생성** 클릭

### 3.4 인증서에 정책 연결

1. **보안** → **인증서**
2. 생성한 인증서 ID 클릭
3. **정책** 탭 → **정책 연결**
4. `ppe-detector-policy` 선택 → **연결**

### 3.5 인증서에 Thing 연결

1. 같은 인증서 페이지에서 **사물** 탭
2. **사물 연결**
3. `ppe-detector-rpi4` 선택 → **연결**

---

## 4. IoT 엔드포인트 확인

### 4.1 엔드포인트 조회

1. 좌측 메뉴: **설정**
2. **디바이스 데이터 엔드포인트** 확인

```
xxxxxxxxxx-ats.iot.ap-northeast-2.amazonaws.com
```

이 값을 메모해 두세요!

### 4.2 CLI로 확인

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text
```

---

## 5. Raspberry Pi에 인증서 전송

### 5.1 로컬 PC에서 Raspberry Pi로 전송

```bash
# PC에서 실행
cd ~/Downloads/iot-certs/

# 인증서 전송
scp *.pem* pi@ppe-detector.local:~/

# 또는 IP 주소 사용
scp *.pem* pi@192.168.0.xxx:~/
```

### 5.2 Raspberry Pi에서 인증서 정리

```bash
# Raspberry Pi에 SSH 접속
ssh pi@ppe-detector.local

# 인증서 디렉토리 생성
sudo mkdir -p /greengrass/v2/certs
sudo mkdir -p /greengrass/v2/config

# 인증서 이동
sudo mv ~/*.pem* /greengrass/v2/certs/

# 파일명 단순화
cd /greengrass/v2/certs/
sudo mv *-certificate.pem.crt device.pem.crt
sudo mv *-private.pem.key private.pem.key
sudo mv *-public.pem.key public.pem.key

# 권한 설정
sudo chmod 644 /greengrass/v2/certs/*
sudo chmod 600 /greengrass/v2/certs/private.pem.key

# 확인
ls -la /greengrass/v2/certs/
```

예상 출력:
```
-rw-r--r-- 1 root root 1220 Jan 15 10:00 AmazonRootCA1.pem
-rw-r--r-- 1 root root 1224 Jan 15 10:00 device.pem.crt
-rw------- 1 root root 1679 Jan 15 10:00 private.pem.key
-rw-r--r-- 1 root root  451 Jan 15 10:00 public.pem.key
```

---

## 6. GreenGrass V2 설치

### 6.1 설치 파일 다운로드

```bash
# Raspberry Pi에서 실행
cd ~

# GreenGrass Core 소프트웨어 다운로드
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip -o greengrass-nucleus-latest.zip

# 압축 해제
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller

# 확인
ls GreengrassInstaller/
```

### 6.2 설치 설정 파일 생성

```bash
# 계정 ID 확인
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
echo "계정 ID: $ACCOUNT_ID"

# IoT 엔드포인트 확인
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)
echo "IoT 엔드포인트: $IOT_ENDPOINT"
```

### 6.3 GreenGrass 설치 실행

```bash
# 환경 변수 설정
export AWS_REGION="ap-northeast-2"
export THING_NAME="ppe-detector-rpi4"
export THING_GROUP_NAME="ppe-detectors"
export TES_ROLE_NAME="ConstructionSafety-TokenExchangeRole"
export TES_ROLE_ALIAS="ConstructionSafety-TokenExchangeRoleAlias"

# 설치 실행
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --aws-region $AWS_REGION \
  --thing-name $THING_NAME \
  --thing-group-name $THING_GROUP_NAME \
  --tes-role-name $TES_ROLE_NAME \
  --tes-role-alias-name $TES_ROLE_ALIAS \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true \
  --deploy-dev-tools true
```

설치 중 출력:
```
Provisioning AWS IoT resources for the device...
Creating new IoT policy "GreengrassV2IoTThingPolicy"
Creating keys and certificate...
Attaching policy to certificate...
Creating IoT Thing "ppe-detector-rpi4"...
Attaching certificate to IoT thing...
Successfully configured Nucleus with provisioned resource details!
Creating a deployment for Greengrass Nucleus component...
Deployment has been created.
Successfully set up Nucleus as a system service
```

### 6.4 설치 확인

```bash
# GreenGrass 서비스 상태 확인
sudo systemctl status greengrass

# 로그 확인
sudo tail -f /greengrass/v2/logs/greengrass.log
```

예상 출력 (정상):
```
● greengrass.service - Greengrass Core
     Loaded: loaded (/etc/systemd/system/greengrass.service; enabled)
     Active: active (running) since ...
```

---

## 7. GreenGrass CLI 설치

### 7.1 CLI 설치

```bash
# GreenGrass CLI 경로 추가
echo 'export PATH=$PATH:/greengrass/v2/bin' >> ~/.bashrc
source ~/.bashrc

# 확인
greengrass-cli --version
```

### 7.2 컴포넌트 목록 확인

```bash
sudo greengrass-cli component list
```

예상 출력:
```
Components currently running in Greengrass:
Component Name: aws.greengrass.Nucleus
    Version: 2.x.x
    State: RUNNING
Component Name: aws.greengrass.Cli
    Version: 2.x.x
    State: RUNNING
```

---

## 8. AWS 콘솔에서 확인

### 8.1 GreenGrass 콘솔

1. AWS 콘솔 → **IoT Greengrass** 검색
2. 좌측 메뉴: **Greengrass 디바이스** → **Core 디바이스**
3. `ppe-detector-rpi4` 확인

### 8.2 상태 확인

```
상태: 정상 (Healthy)
마지막 상태 업데이트: 방금
```

---

## 9. MQTT 통신 테스트

### 9.1 AWS IoT 콘솔에서 테스트

1. IoT Core → **테스트** → **MQTT 테스트 클라이언트**
2. **주제 구독** 탭:
   ```
   주제 필터: construction/safety/#
   ```
3. **구독** 클릭

### 9.2 Raspberry Pi에서 메시지 발행 테스트

```bash
# Raspberry Pi에서 실행

# 테스트 메시지 발행 스크립트 생성
cat > ~/test_mqtt.py << 'EOF'
#!/usr/bin/env python3
import json
import time
from awsiot.greengrasscoreipc import connect
from awsiot.greengrasscoreipc.model import (
    PublishToIoTCoreRequest,
    QOS
)

# GreenGrass IPC 연결
ipc_client = connect()

# 테스트 메시지
topic = "construction/safety/ppe-detector-rpi4/test"
message = {
    "device_id": "ppe-detector-rpi4",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "message": "Hello from Raspberry Pi 4!",
    "status": "connected"
}

# 발행
request = PublishToIoTCoreRequest(
    topic_name=topic,
    qos=QOS.AT_LEAST_ONCE,
    payload=json.dumps(message).encode()
)

operation = ipc_client.new_publish_to_iot_core()
operation.activate(request)
future = operation.get_response()
future.result(timeout=5.0)

print(f"메시지 발행 완료: {topic}")
print(json.dumps(message, indent=2))
EOF

chmod +x ~/test_mqtt.py
```

### 9.3 테스트 실행

```bash
# GreenGrass 컴포넌트로 실행
sudo greengrass-cli deployment create \
  --merge "{ \"run-test\": { \"script\": \"python3 /home/pi/test_mqtt.py\" }}"
```

또는 직접 실행:
```bash
source ~/ppe-detection/venv/bin/activate
python3 ~/test_mqtt.py
```

### 9.4 AWS 콘솔에서 메시지 확인

MQTT 테스트 클라이언트에서 메시지 수신 확인:
```json
{
    "device_id": "ppe-detector-rpi4",
    "timestamp": "2024-01-15T10:00:00Z",
    "message": "Hello from Raspberry Pi 4!",
    "status": "connected"
}
```

---

## 10. Stream Manager 설치 (선택)

Kinesis 연동을 위해 Stream Manager 컴포넌트 설치:

### 10.1 배포 생성

```bash
# 배포 파일 생성
cat > ~/stream-manager-deployment.json << 'EOF'
{
  "targetArn": "arn:aws:iot:ap-northeast-2:ACCOUNT_ID:thinggroup/ppe-detectors",
  "components": {
    "aws.greengrass.StreamManager": {
      "componentVersion": "2.1.0",
      "configurationUpdate": {
        "merge": "{\"STREAM_MANAGER_STORE_ROOT_DIR\":\"/greengrass/v2/stream_manager\"}"
      }
    }
  }
}
EOF

# ACCOUNT_ID 치환
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" ~/stream-manager-deployment.json

# 배포 생성
aws greengrassv2 create-deployment --cli-input-json file://stream-manager-deployment.json
```

### 10.2 배포 확인

```bash
# 컴포넌트 상태 확인
sudo greengrass-cli component list
```

---

## 11. 자동 시작 설정

### 11.1 시스템 서비스 확인

```bash
# 서비스 활성화 확인
sudo systemctl is-enabled greengrass
# 출력: enabled

# 부팅 시 자동 시작
sudo systemctl enable greengrass
```

### 11.2 재부팅 테스트

```bash
sudo reboot
```

재부팅 후 SSH 접속하여 확인:
```bash
sudo systemctl status greengrass
```

---

## ✅ 체크리스트

이 파트를 완료하면 다음 항목들이 준비되어야 합니다:

- [ ] IoT Thing `ppe-detector-rpi4` 생성 완료
- [ ] 인증서 4개 다운로드 및 Raspberry Pi에 저장
- [ ] IoT 정책 `ppe-detector-policy` 생성 및 연결
- [ ] GreenGrass V2 Core 설치 완료
- [ ] GreenGrass 서비스 실행 중 (`systemctl status greengrass`)
- [ ] AWS 콘솔에서 Core 디바이스 "정상" 상태
- [ ] MQTT 테스트 메시지 발행/수신 성공
- [ ] Stream Manager 컴포넌트 설치 (선택)

---

## 🔧 문제 해결

### Q: "Unable to provision device" 오류

```bash
# IAM 역할 확인
aws iam get-role --role-name ConstructionSafety-TokenExchangeRole

# 없으면 생성 (Part 1 참조)
```

### Q: GreenGrass 서비스가 시작되지 않음

```bash
# 로그 확인
sudo journalctl -u greengrass -f

# 일반적인 원인: Java 버전
java -version
# 17 이상이어야 함
```

### Q: MQTT 연결 실패

```bash
# 인증서 확인
ls -la /greengrass/v2/certs/

# 엔드포인트 연결 테스트
openssl s_client -connect $(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text):8443
```

### Q: "Connection refused" 오류

```bash
# 방화벽 확인
sudo iptables -L

# 포트 8883 (MQTT) 열기
sudo iptables -A INPUT -p tcp --dport 8883 -j ACCEPT
```

---

## 📚 다음 단계

[Part 4: Kinesis 설정](./04-kinesis-setup.md)으로 이동하여
Kinesis Data Streams, Firehose를 설정합니다.
