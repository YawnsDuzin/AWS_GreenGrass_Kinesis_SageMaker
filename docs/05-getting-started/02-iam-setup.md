# 5.2 IAM 권한 설정

## IAM 개요

AWS Identity and Access Management (IAM)를 사용하여 AWS 서비스에 대한 접근 권한을 안전하게 관리합니다.

---

## IAM 역할 및 정책 설계

### 역할 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IAM 역할 구조                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  사용자 그룹                                                             │
│  ├─ Administrators     (관리자)                                         │
│  ├─ Developers         (개발자)                                         │
│  ├─ DataScientists     (데이터 사이언티스트)                            │
│  └─ ReadOnlyUsers      (읽기 전용)                                      │
│                                                                         │
│  서비스 역할                                                             │
│  ├─ GreengrassRole            (GreenGrass 서비스용)                    │
│  ├─ GreengrassDeviceRole      (GreenGrass 디바이스용)                  │
│  ├─ KinesisProcessingRole     (Kinesis 처리용)                         │
│  ├─ SageMakerExecutionRole    (SageMaker 실행용)                       │
│  ├─ LambdaExecutionRole       (Lambda 실행용)                          │
│  └─ EC2InstanceRole           (EC2 인스턴스용)                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## GreenGrass IAM 설정

### GreenGrass 서비스 역할

```json
// greengrass-service-role-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iot:*",
                "greengrass:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::my-greengrass-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:PutRecord",
                "kinesis:PutRecords",
                "kinesis:DescribeStream"
            ],
            "Resource": "arn:aws:kinesis:*:*:stream/safety-*"
        }
    ]
}
```

### GreenGrass Token Exchange Role

```json
// greengrass-token-exchange-role.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iot:DescribeCertificate",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "s3:GetBucketLocation"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::*greengrass*"
        }
    ]
}
```

### CLI로 GreenGrass 역할 생성

```bash
# 1. 신뢰 정책 생성
cat > greengrass-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "greengrass.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# 2. IAM 역할 생성
aws iam create-role \
    --role-name GreengrassServiceRole \
    --assume-role-policy-document file://greengrass-trust-policy.json

# 3. 정책 연결
aws iam attach-role-policy \
    --role-name GreengrassServiceRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSGreengrassResourceAccessRolePolicy

# 4. GreenGrass와 역할 연결
aws greengrass associate-service-role-to-account \
    --role-arn arn:aws:iam::123456789012:role/GreengrassServiceRole
```

---

## Kinesis IAM 설정

### Kinesis 처리 역할

```json
// kinesis-processing-role-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:GetRecords",
                "kinesis:GetShardIterator",
                "kinesis:DescribeStream",
                "kinesis:DescribeStreamSummary",
                "kinesis:ListShards",
                "kinesis:ListStreams"
            ],
            "Resource": [
                "arn:aws:kinesis:ap-northeast-2:*:stream/safety-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:PutRecord",
                "kinesis:PutRecords"
            ],
            "Resource": [
                "arn:aws:kinesis:ap-northeast-2:*:stream/safety-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "firehose:PutRecord",
                "firehose:PutRecordBatch"
            ],
            "Resource": [
                "arn:aws:firehose:ap-northeast-2:*:deliverystream/safety-*"
            ]
        }
    ]
}
```

### Kinesis Firehose 역할

```json
// firehose-delivery-role-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:AbortMultipartUpload",
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::safety-data-bucket",
                "arn:aws:s3:::safety-data-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:DescribeStream",
                "kinesis:GetShardIterator",
                "kinesis:GetRecords",
                "kinesis:ListShards"
            ],
            "Resource": [
                "arn:aws:kinesis:ap-northeast-2:*:stream/safety-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunctionConfiguration"
            ],
            "Resource": [
                "arn:aws:lambda:ap-northeast-2:*:function:firehose-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:ap-northeast-2:*:log-group:/aws/kinesisfirehose/*:log-stream:*"
            ]
        }
    ]
}
```

---

## SageMaker IAM 설정

### SageMaker 실행 역할

```json
// sagemaker-execution-role-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::sagemaker-*",
                "arn:aws:s3:::sagemaker-*/*",
                "arn:aws:s3:::safety-ml-*",
                "arn:aws:s3:::safety-ml-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "sagemaker.amazonaws.com"
                }
            }
        }
    ]
}
```

### CLI로 SageMaker 역할 생성

```bash
# 1. 신뢰 정책
cat > sagemaker-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# 2. 역할 생성
aws iam create-role \
    --role-name SageMakerExecutionRole \
    --assume-role-policy-document file://sagemaker-trust-policy.json

# 3. AWS 관리형 정책 연결
aws iam attach-role-policy \
    --role-name SageMakerExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

# 4. S3 접근 정책 추가
aws iam put-role-policy \
    --role-name SageMakerExecutionRole \
    --policy-name S3AccessPolicy \
    --policy-document file://sagemaker-s3-policy.json
```

---

## Lambda IAM 설정

### Lambda 실행 역할

```json
// lambda-execution-role-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kinesis:GetRecords",
                "kinesis:GetShardIterator",
                "kinesis:DescribeStream",
                "kinesis:ListShards"
            ],
            "Resource": "arn:aws:kinesis:*:*:stream/safety-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/safety-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": "arn:aws:sagemaker:*:*:endpoint/safety-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": "arn:aws:sns:*:*:safety-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::safety-*/*"
        }
    ]
}
```

---

## 개발자용 IAM 정책

### 개발자 그룹 정책

```json
// developer-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DevelopmentAccess",
            "Effect": "Allow",
            "Action": [
                "iot:*",
                "greengrass:*",
                "kinesis:*",
                "firehose:*",
                "sagemaker:*",
                "lambda:*",
                "dynamodb:*",
                "s3:*",
                "sns:*",
                "sqs:*",
                "logs:*",
                "cloudwatch:*",
                "ecr:*"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "ap-northeast-2"
                }
            }
        },
        {
            "Sid": "DenyProductionChanges",
            "Effect": "Deny",
            "Action": [
                "iam:*",
                "organizations:*",
                "account:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "DenyDeleteProduction",
            "Effect": "Deny",
            "Action": [
                "kinesis:DeleteStream",
                "dynamodb:DeleteTable",
                "s3:DeleteBucket"
            ],
            "Resource": [
                "arn:aws:kinesis:*:*:stream/prod-*",
                "arn:aws:dynamodb:*:*:table/prod-*",
                "arn:aws:s3:::prod-*"
            ]
        }
    ]
}
```

---

## IAM 베스트 프랙티스

### 보안 권장사항

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IAM 보안 베스트 프랙티스                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 최소 권한 원칙 (Least Privilege)                                    │
│     ├─ 필요한 권한만 부여                                               │
│     ├─ 리소스 ARN으로 범위 제한                                         │
│     └─ 조건(Condition)으로 추가 제한                                    │
│                                                                         │
│  2. 역할(Role) 우선 사용                                                 │
│     ├─ 장기 자격 증명(액세스 키) 대신 역할 사용                         │
│     ├─ EC2, Lambda 등 서비스에 역할 할당                                │
│     └─ 크로스 계정 접근도 역할로 관리                                   │
│                                                                         │
│  3. MFA 강제                                                             │
│     ├─ 모든 IAM 사용자에게 MFA 필수                                     │
│     ├─ 민감한 작업에 MFA 조건 추가                                      │
│     └─ 루트 계정 MFA 필수                                               │
│                                                                         │
│  4. 정기적인 검토                                                        │
│     ├─ 사용하지 않는 사용자/역할 제거                                   │
│     ├─ 액세스 키 정기 교체 (90일 권장)                                  │
│     └─ IAM Access Analyzer 활용                                         │
│                                                                         │
│  5. 정책 관리                                                            │
│     ├─ 인라인 정책보다 관리형 정책 사용                                 │
│     ├─ 그룹을 통한 권한 관리                                            │
│     └─ 서비스 제어 정책(SCP)으로 조직 제어                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 다음 단계

1. [개발 환경 구성](03-dev-environment.md) - 개발 도구 설정
2. [필수 도구 설치](04-tools-installation.md) - CLI 및 SDK 설치
