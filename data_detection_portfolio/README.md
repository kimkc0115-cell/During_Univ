# 시계열 구간 탐지 포트폴리오

사용 승인을 받은 헤더 없는 `all_day_list.csv`를 읽어 구간을 탐지합니다.

열은 순서대로 `signal_01`~`signal_10`으로 부르며, 그래프와 탐지 입력에는 `signal_08`을 사용합니다.
원래 열 이름 대응표는 포함하지 않습니다. CSV 수치와 열 순서는 변경하지 않았으므로 열 이름 변경은 데이터 익명화가 아닙니다.


## 실행

이 폴더에서 다음 명령을 실행하세요.

```bash
python -m pip install -r requirements.txt
python testfile.py
```

상단 그래프를 드래그하면 아래 그래프가 확대됩니다. 색칠한 부분은 검출 구간입니다.
CSV 위치는 실행 파일 기준으로 찾습니다. 파일이 없으면 오류를 표시하며 자동으로 데이터를 만들지 않습니다.

창 없이 확인하려면 `python testfile.py --check`를 실행하세요.
입력의 유효성, 검출 구간의 범위, 확대 함수를 점검하고 `detection_preview.png`를 저장합니다.
이 검사는 실제 데이터 전체에 대한 탐지 정확도나 정답 일치를 보장하지 않습니다.

## 파일

- `data_detection.py`: 기존 탐지 알고리즘. 이번 변경에서 수정하지 않았습니다.
- `testfile.py`: CSV 열 매핑, 실행, 그래프 표시.
- `all_day_list.csv`: 실제 입력 데이터. 헤더 없음, 10열.
- `requirements.txt`: 필요한 패키지.
- `detection_preview.png`: 현재 입력으로 생성한 확인용 그래프.

