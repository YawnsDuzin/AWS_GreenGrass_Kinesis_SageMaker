# Part 2: Raspberry Pi 4 하드웨어 및 OS 설정

이 파트에서는 Raspberry Pi 4에 64비트 OS를 설치하고, 카메라와 필수 소프트웨어를 설정합니다.

---

## 📋 이 파트에서 다루는 내용

- [x] Raspberry Pi OS 64-bit 설치
- [x] 초기 설정 (SSH, WiFi, 로케일)
- [x] 카메라 모듈 연결 및 설정
- [x] 필수 패키지 설치
- [x] Python 환경 구성
- [x] 성능 최적화 설정

---

## 1. 준비물 확인

### 필수 하드웨어

| 품목 | 설명 |
|------|------|
| Raspberry Pi 4 Model B | 4GB 또는 8GB RAM 권장 |
| microSD 카드 | 32GB 이상, Class 10/U3 |
| SD 카드 리더 | PC에 연결용 |
| USB-C 전원 어댑터 | 5V 3A (15W) 이상 |
| Pi Camera V2 또는 USB 웹캠 | 권장: Pi Camera V2 |
| 이더넷 케이블 (선택) | 안정적인 연결용 |
| 모니터 + HDMI 케이블 (선택) | 초기 설정용 |
| 키보드 + 마우스 (선택) | 초기 설정용 |

---

## 2. Raspberry Pi OS 설치

### 2.1 Raspberry Pi Imager 다운로드

PC에서 공식 이미저 다운로드:

- **Windows/macOS/Linux**: https://www.raspberrypi.com/software/

### 2.2 OS 이미지 굽기

1. **Raspberry Pi Imager** 실행

2. **디바이스 선택**: `Raspberry Pi 4`

3. **OS 선택**:
   ```
   Raspberry Pi OS (other)
     → Raspberry Pi OS (64-bit)
   ```

   > ⚠️ **중요**: 반드시 **64-bit** 버전을 선택하세요!

4. **저장소 선택**: microSD 카드

5. **설정 편집** (⚙️ 아이콘) 클릭:

### 2.3 사전 설정 (매우 중요!)

**일반** 탭:
```
✅ 호스트이름 설정: ppe-detector
✅ 사용자 이름과 비밀번호 설정
   사용자 이름: pi
   비밀번호: (강력한 비밀번호 입력)
✅ WiFi 설정
   SSID: (WiFi 이름)
   비밀번호: (WiFi 비밀번호)
   WiFi 국가: KR
✅ 로케일 설정
   시간대: Asia/Seoul
   키보드 레이아웃: kr
```

**서비스** 탭:
```
✅ SSH 사용
   ○ 비밀번호 인증 사용
```

6. **저장** → **예** → **쓰기**

7. 완료까지 대기 (약 5-10분)

### 2.4 Raspberry Pi 부팅

1. microSD 카드를 Raspberry Pi에 삽입
2. 이더넷 케이블 연결 (선택)
3. 전원 연결
4. 녹색 LED가 깜빡이며 부팅 (약 1-2분)

---

## 3. SSH 접속

### 3.1 IP 주소 확인

**방법 1: 공유기 관리 페이지**
- 공유기 접속 (보통 192.168.0.1 또는 192.168.1.1)
- 연결된 기기 목록에서 `ppe-detector` 찾기

**방법 2: 네트워크 스캔 (Windows)**
```powershell
# PowerShell
arp -a | findstr "b8-27-eb dc-a6-32 e4-5f-01"
```

**방법 3: 네트워크 스캔 (macOS/Linux)**
```bash
# 호스트이름으로 접속 시도
ping ppe-detector.local

# 또는 nmap 사용
nmap -sn 192.168.0.0/24 | grep -i "raspberry\|pi"
```

### 3.2 SSH 접속

```bash
ssh pi@ppe-detector.local
# 또는
ssh pi@192.168.0.xxx
```

비밀번호 입력 후 접속 완료

### 3.3 초기 접속 화면

```
Linux ppe-detector 6.1.0-rpi7-rpi-v8 #1 SMP PREEMPT Debian 1:6.1.63-1+rpt1 aarch64

Last login: ...
pi@ppe-detector:~ $
```

---

## 4. 시스템 업데이트

### 4.1 패키지 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

약 5-10분 소요

### 4.2 재부팅

```bash
sudo reboot
```

30초 후 다시 SSH 접속

---

## 5. 카메라 설정

### 5.1 Pi Camera V2 연결 (CSI 카메라)

1. Raspberry Pi 전원 OFF
2. 카메라 리본 케이블을 CSI 포트에 연결
   - 파란색 면이 이더넷 포트 방향
3. 커넥터 클립으로 고정
4. 전원 ON

### 5.2 USB 웹캠 연결

USB 포트에 직접 연결 (추가 설정 불필요)

### 5.3 카메라 인터페이스 활성화

```bash
sudo raspi-config
```

메뉴 이동:
```
Interface Options
  → Legacy Camera → <No> (새로운 libcamera 사용)
  → I2C → <Yes>
```

재부팅:
```bash
sudo reboot
```

### 5.4 카메라 테스트

**libcamera (Pi Camera V2용)**:
```bash
# 이미지 촬영 테스트
libcamera-still -o test.jpg

# 비디오 테스트 (5초)
libcamera-vid -t 5000 -o test.h264

# 카메라 정보 확인
libcamera-hello --list-cameras
```

예상 출력:
```
Available cameras
-----------------
0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1/imx219@10)
    Modes: 'SRGGB10_CSI2P' : 640x480 1640x1232 1920x1080 3280x2464
```

**USB 웹캠용**:
```bash
# 디바이스 확인
v4l2-ctl --list-devices

# 지원 해상도 확인
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

---

## 6. 필수 패키지 설치

### 6.1 시스템 패키지

```bash
# 기본 개발 도구
sudo apt install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    pkg-config

# Python 개발 패키지
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-numpy

# OpenCV 의존성
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev \
    libhdf5-serial-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test

# 카메라 관련
sudo apt install -y \
    v4l-utils \
    libcamera-apps

# 네트워크/보안
sudo apt install -y \
    libssl-dev \
    libffi-dev \
    ca-certificates
```

### 6.2 Java 설치 (GreenGrass용)

```bash
# Amazon Corretto 17 설치
sudo apt install -y java-17-amazon-corretto-jdk

# 확인
java -version
```

예상 출력:
```
openjdk version "17.0.x" ...
```

---

## 7. Python 환경 구성

### 7.1 가상환경 생성

```bash
# 프로젝트 디렉토리 생성
mkdir -p ~/ppe-detection
cd ~/ppe-detection

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

### 7.2 필수 Python 패키지 설치

```bash
# 기본 패키지
pip install numpy==1.24.0
pip install Pillow>=9.0.0

# AWS SDK
pip install boto3>=1.26.0
pip install awsiotsdk>=1.12.0
pip install awscrt>=0.16.0

# 기타
pip install python-dateutil
pip install pyyaml
```

### 7.3 OpenCV 확인

```bash
python3 -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
```

예상 출력:
```
OpenCV version: 4.6.0
```

---

## 8. 시스템 최적화

### 8.1 스왑 크기 증가

ML 추론에 더 많은 메모리 필요:

```bash
# 현재 스왑 확인
free -h

# 스왑 설정 편집
sudo nano /etc/dphys-swapfile
```

다음 라인 수정:
```
CONF_SWAPSIZE=2048
```

적용:
```bash
sudo systemctl restart dphys-swapfile
```

### 8.2 GPU 메모리 할당

```bash
sudo raspi-config
```

메뉴 이동:
```
Performance Options
  → GPU Memory → 128
```

### 8.3 CPU 거버너 설정

```bash
# 현재 설정 확인
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# performance 모드로 변경
echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 영구 적용
sudo nano /etc/rc.local
```

`exit 0` 앞에 추가:
```bash
echo "performance" | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### 8.4 발열 관리

```bash
# 현재 온도 확인
vcgencmd measure_temp
```

쿨링 팬이 있다면:
```bash
sudo nano /boot/config.txt
```

추가:
```
# 60도 이상에서 팬 작동
dtoverlay=gpio-fan,gpiopin=14,temp=60000
```

---

## 9. 네트워크 설정

### 9.1 고정 IP 설정 (선택)

```bash
sudo nano /etc/dhcpcd.conf
```

파일 끝에 추가:
```
# 이더넷 고정 IP
interface eth0
static ip_address=192.168.0.100/24
static routers=192.168.0.1
static domain_name_servers=8.8.8.8 8.8.4.4

# WiFi 고정 IP
interface wlan0
static ip_address=192.168.0.101/24
static routers=192.168.0.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

적용:
```bash
sudo systemctl restart dhcpcd
```

### 9.2 호스트이름 DNS (mDNS)

이미 설정되어 있음:
```bash
ping ppe-detector.local
```

---

## 10. AWS CLI 설치 (Raspberry Pi)

### 10.1 AWS CLI v2 설치

```bash
# ARM64용 설치 스크립트
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 정리
rm -rf awscliv2.zip aws/
```

### 10.2 구성

```bash
aws configure
```

Part 1에서 저장한 액세스 키 입력:
```
AWS Access Key ID: AKIAXXXXXXXXXXXXXXXX
AWS Secret Access Key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
Default region name: ap-northeast-2
Default output format: json
```

### 10.3 확인

```bash
aws sts get-caller-identity
```

---

## 11. 시스템 정보 확인 스크립트

### 11.1 시스템 체크 스크립트 생성

```bash
cat > ~/check_system.sh << 'EOF'
#!/bin/bash

echo "========================================="
echo "    Raspberry Pi 4 시스템 정보"
echo "========================================="
echo ""

echo "📌 하드웨어 정보"
echo "-----------------------------------------"
echo "모델: $(cat /proc/device-tree/model)"
echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)"
echo "코어: $(nproc)"
echo "메모리: $(free -h | grep Mem | awk '{print $2}')"
echo ""

echo "📌 OS 정보"
echo "-----------------------------------------"
cat /etc/os-release | grep -E "^(PRETTY_NAME|VERSION)="
echo "커널: $(uname -r)"
echo "아키텍처: $(uname -m)"
echo ""

echo "📌 온도 및 클럭"
echo "-----------------------------------------"
echo "CPU 온도: $(vcgencmd measure_temp | cut -d= -f2)"
echo "CPU 클럭: $(vcgencmd measure_clock arm | awk -F= '{print $2/1000000 " MHz"}')"
echo ""

echo "📌 카메라"
echo "-----------------------------------------"
libcamera-hello --list-cameras 2>/dev/null || echo "카메라 감지 안됨 (USB 웹캠 확인: v4l2-ctl --list-devices)"
echo ""

echo "📌 Python"
echo "-----------------------------------------"
echo "Python: $(python3 --version)"
echo "pip: $(pip3 --version | awk '{print $2}')"
echo ""

echo "📌 Java"
echo "-----------------------------------------"
java -version 2>&1 | head -1
echo ""

echo "📌 AWS CLI"
echo "-----------------------------------------"
aws --version
echo ""

echo "📌 네트워크"
echo "-----------------------------------------"
echo "IP (eth0): $(ip -4 addr show eth0 2>/dev/null | grep inet | awk '{print $2}' || echo 'N/A')"
echo "IP (wlan0): $(ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' || echo 'N/A')"
echo ""

echo "========================================="
echo "              확인 완료"
echo "========================================="
EOF

chmod +x ~/check_system.sh
```

### 11.2 스크립트 실행

```bash
~/check_system.sh
```

예상 출력:
```
=========================================
    Raspberry Pi 4 시스템 정보
=========================================

📌 하드웨어 정보
-----------------------------------------
모델: Raspberry Pi 4 Model B Rev 1.4
CPU: Cortex-A72
코어: 4
메모리: 3.7Gi

📌 OS 정보
-----------------------------------------
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
VERSION="12 (bookworm)"
커널: 6.1.0-rpi7-rpi-v8
아키텍처: aarch64

...
```

---

## ✅ 체크리스트

이 파트를 완료하면 다음 항목들이 준비되어야 합니다:

- [ ] Raspberry Pi OS 64-bit 설치 완료
- [ ] SSH 접속 가능
- [ ] 시스템 업데이트 완료
- [ ] 카메라 연결 및 테스트 성공
- [ ] 필수 패키지 설치 완료
- [ ] Java 17 설치 확인
- [ ] Python 가상환경 생성
- [ ] AWS CLI 설치 및 구성
- [ ] 시스템 최적화 적용

---

## 🔧 문제 해결

### Q: SSH 접속 안 됨

```bash
# PC에서 핑 테스트
ping ppe-detector.local

# 안 되면 SD 카드를 PC에 다시 연결하고
# boot 파티션에 빈 'ssh' 파일 생성
touch /Volumes/boot/ssh  # macOS
# 또는
touch /media/user/boot/ssh  # Linux
```

### Q: 카메라가 감지되지 않음

```bash
# CSI 연결 확인
vcgencmd get_camera
# 출력: supported=1 detected=1 이어야 함

# USB 웹캠 확인
lsusb
v4l2-ctl --list-devices
```

### Q: WiFi 연결 안 됨

```bash
# WiFi 상태 확인
iwconfig wlan0

# 수동 연결
sudo nmcli device wifi connect "SSID" password "PASSWORD"
```

### Q: 메모리 부족 에러

```bash
# 스왑 확인
free -h

# 스왑 즉시 늘리기
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📚 다음 단계

[Part 3: AWS IoT Core & GreenGrass 설정](./03-iot-greengrass-setup.md)으로 이동하여
AWS IoT에 Raspberry Pi를 등록하고 GreenGrass V2를 설치합니다.
