# PHP CSV 다운로드 보안 개선 기록

2026년 9월 29일

권한 확인과 SQL 조회 방식을 설명하기 위한 **일반화된 예제**입니다. 실제 서비스의 주소, 계정, DB 접속 정보, 회사명, 테이블 구조는 포함하지 않았습니다. `secure_csv_example.php`의 테이블·컬럼 이름은 가상 이름이므로 그대로 배포하는 코드는 아닙니다.

## 1. 역할 확인 방식 변경

기존에는 요청 URL의 값을 역할로 사용했습니다.

```php
// 이전 방식의 핵심 부분(설명용, 사용 금지)
$role = $_GET['role'] ?? 'viewer';
```

URL은 요청자가 바꿀 수 있으므로 `role=admin`을 적으면 관리자용 CSV 항목이 선택될 수 있었습니다.

변경 후에는 로그인할 때 서버에 저장한 세션을 확인합니다.

```php
$role = $_SESSION['user_role'] ?? '';
```

`secure_csv_example.php`의 `requireCsvRole()`은 로그인 여부를 확인하고 `admin` 또는 `viewer`만 허용합니다. 관리자용 항목은 **세션 역할이 `admin`일 때만** 조회 목록에 추가합니다.

## 2. SQL 조회 방식 변경

기존에는 날짜를 SQL 문장 안에 직접 이어 붙였습니다.

```php
// 이전 방식의 핵심 부분(설명용, 사용 금지)
$sql = "SELECT value FROM example_readings WHERE measured_at BETWEEN '{$date} 00:00:00' AND '{$date} 23:59:59'";
```

변경 후에는 SQL에 `?` 자리를 만들고, `bind_param()`으로 장비 번호와 시작·끝 시각을 **값으로 따로 전달**합니다.

```php
$sql = 'SELECT value FROM example_readings WHERE device_id = ? AND measured_at >= ? AND measured_at < ?';
$stmt = $db->prepare($sql);
$stmt->bind_param('iss', $deviceId, $start, $end);
```

`i`는 정수, `s`는 문자열입니다. 사용자가 보낸 날짜는 SQL 명령으로 해석되지 않습니다. 예제에는 `YYYY-MM-DD` 형식과 실제 날짜 검사도 포함했습니다. 조회 끝 시각은 다음 날 00:00 **직전**으로 잡아 소수점 이하 초가 있는 측정값도 포함합니다.

## 파일

- `secure_csv_example.php`: 세션 역할 확인과 준비된 SQL 조회를 보여 주는 코드. DB 연결과 실제 CSV 출력은 포함하지 않습니다.

## 확인한 범위

PHP 문법만 검사했습니다. 실제 DB 스키마 및 운영 서버에서의 실행은 검증하지 않았습니다.