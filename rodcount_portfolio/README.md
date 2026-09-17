# Rod-count 추론 파이프라인 최적화 포트폴리오

합성 데이터와 작은 공개용 예제 모델로 최적화 방법을 재현합니다. 실제 데이터셋을 가져올 필요가 없습니다. 회사 코드 원본, 학습 가중치, 고객 정보는 포함하지 않습니다.

## Problem

본래 사측에서는 추론 모델을 따로 변경하지 못하고 기본적으로 ONNX Runtime과 PyTorch를 모두 import한 뒤, 두 엔진을 번갈아 사용했습니다. 이로 인해 메모리 사용량이 증가하고, 작은 입력에 대한 PyTorch DataLoader의 overhead가 커졌습니다. 또한, 전체 행을 복사·스케일링하고 Python 리스트에 결과를 기록하는 방식은 불필요한 연산과 메모리 사용을 초래했습니다.

## Changes

- `backend='onnx'` / `backend='torch'`로 선택한 추론 모델만 초기화합니다.
- 전체 행 복사·스케일링을 필요한 구간으로 한정합니다. 음수 값이나 겹치는 구간도 보존합니다.
- 행별 Python 리스트 대신 사전 할당한 NumPy 배열에 구간 단위로 결과를 기록합니다.
- 작은 CPU 입력의 PyTorch DataLoader를 `num_workers=4`에서 `0`으로 변경합니다.
- ONNX Runtime과 PyTorch가 실제로 실행되며, 입력과 출력 동등성을 검증합니다.
- 이번 데모에는 선택 backend만 import하는 추가 개선도 포함합니다. 

## Evidence

`benchmark_results.json`은 이번 합성 데이터 실행의 반복 측정값, 중앙값, 감소율, 출력 해시 일치 여부와 환경 버전을 담습니다. 음수 감소율은 성능 악화를 뜻하며 숨기거나 0으로 보정하지 않습니다. 이 결과는 실제 장비 데이터에서의 과거 성능 개선율이 아닙니다.

비교 대상:

| 경우 | 초기화 | 전처리/매핑 | 추론 |
|---|---|---|---|
| baseline_onnx_dual | 두 런타임/모델 | 전체 스케일링·행별 리스트 | ONNX |
| optimized_onnx | ONNX만 | 필요한 구간·배열 슬라이스 | ONNX |
| baseline_torch_w4 | PyTorch만 | 전체 스케일링·행별 리스트 | PyTorch, workers=4 |
| optimized_torch | PyTorch만 | 필요한 구간·배열 슬라이스 | PyTorch, workers=0 |

기준 구현도 공개용 재구성이며 원본 파일 그대로가 아닙니다. 여러 변경을 함께 비교하므로 개별 변경의 기여율을 분리한 실험은 아닙니다. 모델은 시퀀스 평균을 이용한 동일한 작은 분류 계산이며 실제 rod count 정확도를 평가하지 않습니다.

각 측정은 새 프로세스에서 실행하고 순서를 번갈아 바꿉니다. 기본 3회 중앙값을 보고하며 cold-start 비용을 포함하므로 워밍업 실행을 제외하지 않습니다. 연산시간은 전처리+추론 파이프라인+매핑이고, 추론 파이프라인 시간에는 DataLoader 생성·순회 비용이 포함됩니다. 전체시간은 프로세스 시작/종료와 합성 데이터 생성도 포함합니다. CSV 저장은 양쪽 모두 하지 않습니다.

최대 메모리는 10ms 간격으로 측정한 부모+자식 RSS 합계입니다. 라이브러리 로딩과 데이터 생성도 포함하고, 공유 메모리 중복 집계 및 순간 피크 누락이 가능하며 GPU 메모리 측정은 아닙니다. CPU 스레드 수는 두 엔진 모두 1로 맞췄습니다.

## Run

```bash
python -m pip install -r requirements.txt
python -m unittest test_inference_demo.py
python benchmark_rodcount_sanitized.py --repeat 3 --rows 300000
```

현재 PC에서는 Python 3.11에 필요한 패키지가 설치되어 있으므로 `py -3.11`로 실행할 수 있습니다. Python 3.12에는 일부 패키지가 없습니다.

`inference_demo.py`에 backend 선택 및 최적화 전후 구현이 있고, `benchmark_comparison.py`가 측정을 수행합니다. `benchmark_rodcount_sanitized.py`는 기존 이름으로 실행하는 진입점입니다. 이전 `rodcount_pipeline.py`와 해당 테스트는 단순 sliding-window 학습 예제로 남아 있으며 이번 벤치마크에는 사용하지 않습니다.
