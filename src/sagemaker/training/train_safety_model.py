#!/usr/bin/env python3
"""
SageMaker 커스텀 학습 스크립트
YOLOv8 기반 안전장비 감지 모델 학습
"""

import os
import json
import argparse
import logging
from pathlib import Path

import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SafetyModelTraining")


def parse_args():
    """SageMaker 학습 인자 파싱"""
    parser = argparse.ArgumentParser()

    # 하이퍼파라미터
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--img-size', type=int, default=640)
    parser.add_argument('--learning-rate', type=float, default=0.01)
    parser.add_argument('--model-size', type=str, default='n',
                        choices=['n', 's', 'm', 'l', 'x'])
    parser.add_argument('--patience', type=int, default=50)
    parser.add_argument('--optimizer', type=str, default='SGD')

    # SageMaker 환경 변수
    parser.add_argument('--model-dir', type=str,
                        default=os.environ.get('SM_MODEL_DIR', '/opt/ml/model'))
    parser.add_argument('--train', type=str,
                        default=os.environ.get('SM_CHANNEL_TRAIN', '/opt/ml/input/data/train'))
    parser.add_argument('--val', type=str,
                        default=os.environ.get('SM_CHANNEL_VAL', '/opt/ml/input/data/val'))
    parser.add_argument('--output-dir', type=str,
                        default=os.environ.get('SM_OUTPUT_DATA_DIR', '/opt/ml/output'))

    return parser.parse_args()


def create_data_yaml(train_path: str, val_path: str, output_path: str) -> str:
    """
    YOLOv8 데이터 설정 파일 생성

    Args:
        train_path: 학습 데이터 경로
        val_path: 검증 데이터 경로
        output_path: 출력 경로

    Returns:
        data.yaml 파일 경로
    """
    # 안전장비 클래스 정의
    data_config = {
        'path': output_path,
        'train': train_path,
        'val': val_path,
        'names': {
            0: 'person',
            1: 'hardhat',
            2: 'safety_vest',
            3: 'safety_shoes',
            4: 'no_hardhat',
            5: 'no_safety_vest'
        },
        'nc': 6  # 클래스 수
    }

    yaml_path = os.path.join(output_path, 'data.yaml')

    # YAML 형식으로 저장
    with open(yaml_path, 'w') as f:
        for key, value in data_config.items():
            if isinstance(value, dict):
                f.write(f'{key}:\n')
                for k, v in value.items():
                    f.write(f'  {k}: {v}\n')
            else:
                f.write(f'{key}: {value}\n')

    logger.info(f"데이터 설정 생성: {yaml_path}")
    return yaml_path


def train(args):
    """
    모델 학습 메인 함수

    Args:
        args: 학습 인자
    """
    logger.info("=== 안전장비 감지 모델 학습 시작 ===")
    logger.info(f"설정: epochs={args.epochs}, batch={args.batch_size}, img={args.img_size}")

    # 디바이스 설정
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"학습 디바이스: {device}")

    if device == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")

    # 데이터 설정 파일 생성
    data_yaml = create_data_yaml(
        args.train,
        args.val,
        args.output_dir
    )

    # 사전 학습 모델 로드
    model_name = f'yolov8{args.model_size}.pt'
    logger.info(f"기본 모델: {model_name}")

    model = YOLO(model_name)

    # 학습 실행
    results = model.train(
        data=data_yaml,
        epochs=args.epochs,
        batch=args.batch_size,
        imgsz=args.img_size,
        lr0=args.learning_rate,
        patience=args.patience,
        optimizer=args.optimizer,
        device=device,
        project=args.output_dir,
        name='safety_model',
        exist_ok=True,
        pretrained=True,
        verbose=True,
        save=True,
        plots=True
    )

    logger.info("학습 완료")

    # 모델 저장
    save_model(model, args)

    # 메트릭 저장
    save_metrics(results, args)

    return results


def save_model(model, args):
    """
    학습된 모델 저장

    Args:
        model: YOLOv8 모델
        args: 학습 인자
    """
    # PyTorch 모델 저장
    best_model_path = os.path.join(args.output_dir, 'safety_model', 'weights', 'best.pt')

    if os.path.exists(best_model_path):
        # SageMaker 모델 디렉토리로 복사
        import shutil
        shutil.copy(best_model_path, os.path.join(args.model_dir, 'best.pt'))
        logger.info(f"PyTorch 모델 저장: {args.model_dir}/best.pt")

    # ONNX 내보내기 (Raspberry Pi 배포용)
    try:
        model_for_export = YOLO(best_model_path)
        onnx_path = model_for_export.export(
            format='onnx',
            imgsz=args.img_size,
            simplify=True,
            opset=12,
            dynamic=False
        )

        # ONNX 모델 복사
        import shutil
        shutil.copy(onnx_path, os.path.join(args.model_dir, 'model.onnx'))
        logger.info(f"ONNX 모델 저장: {args.model_dir}/model.onnx")

    except Exception as e:
        logger.warning(f"ONNX 내보내기 실패: {e}")

    # 모델 메타데이터 저장
    metadata = {
        'model_type': 'yolov8',
        'model_size': args.model_size,
        'input_size': args.img_size,
        'classes': {
            0: 'person',
            1: 'hardhat',
            2: 'safety_vest',
            3: 'safety_shoes',
            4: 'no_hardhat',
            5: 'no_safety_vest'
        },
        'target_device': 'raspberry_pi_4_64bit'
    }

    with open(os.path.join(args.model_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)


def save_metrics(results, args):
    """
    학습 메트릭 저장

    Args:
        results: 학습 결과
        args: 학습 인자
    """
    metrics = {
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'image_size': args.img_size,
        'learning_rate': args.learning_rate
    }

    # 결과에서 메트릭 추출
    try:
        if hasattr(results, 'results_dict'):
            metrics.update(results.results_dict)
    except Exception as e:
        logger.warning(f"메트릭 추출 실패: {e}")

    metrics_path = os.path.join(args.output_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"메트릭 저장: {metrics_path}")


def main():
    """메인 함수"""
    args = parse_args()

    # 환경 정보 출력
    logger.info("=== 환경 정보 ===")
    logger.info(f"Python: {os.sys.version}")
    logger.info(f"PyTorch: {torch.__version__}")
    logger.info(f"CUDA 사용 가능: {torch.cuda.is_available()}")

    # 학습 실행
    train(args)

    logger.info("=== 학습 완료 ===")


if __name__ == "__main__":
    main()
