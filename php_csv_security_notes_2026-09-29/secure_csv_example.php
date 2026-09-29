<?php
declare(strict_types=1);

/** 로그인 세션에 저장된 역할만 사용한다. */
function requireCsvRole(): string
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }

    if (empty($_SESSION['user_id'])) {
        http_response_code(401);
        exit('로그인이 필요합니다.');
    }

    $role = $_SESSION['user_role'] ?? '';
    if (!in_array($role, ['admin', 'viewer'], true)) {
        http_response_code(403);
        exit('CSV 조회 권한이 없습니다.');
    }

    return $role;
}

/** 가상 측정 테이블에서 하루치 데이터를 안전하게 조회하는 예제. */
function fetchDailyReadings(mysqli $db, int $deviceId, string $date): mysqli_result
{
    $role = requireCsvRole();

    // 형식과 실제 달력 날짜를 모두 확인한다.
    $parsedDate = preg_match('/^\d{4}-\d{2}-\d{2}$/D', $date)
        ? DateTimeImmutable::createFromFormat('!Y-m-d', $date)
        : false;
    if ($parsedDate === false || $parsedDate->format('Y-m-d') !== $date) {
        http_response_code(400);
        exit('날짜 형식이 올바르지 않습니다.');
    }

    $start = $parsedDate->format('Y-m-d H:i:s');
    $end = $parsedDate->modify('+1 day')->format('Y-m-d H:i:s');

    // 컬럼 이름은 서버 코드에 고정되어 있고 요청값으로 만들지 않는다.
    $columns = ['id', 'device_id', 'measured_at', 'value'];
    if ($role === 'admin') {
        $columns[] = 'admin_metric_a';
        $columns[] = 'admin_metric_b';
    }
    $selectColumns = implode(', ', $columns);

    $sql = "SELECT {$selectColumns} FROM example_readings
            WHERE device_id = ? AND measured_at >= ? AND measured_at < ?
            ORDER BY measured_at ASC";

    $stmt = $db->prepare($sql);
    $stmt->bind_param('iss', $deviceId, $start, $end);
    $stmt->execute();
    $result = $stmt->get_result();
    $stmt->close();

    if ($result === false) {
        throw new RuntimeException('측정 데이터 조회에 실패했습니다.');
    }

    return $result;
}
