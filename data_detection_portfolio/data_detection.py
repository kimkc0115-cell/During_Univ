import numpy as np

def detect_peak_crater_regions(data: np.ndarray, min_switch: float = 0.5, threshold_offset: float = 1.0) -> list[tuple[int, int]]:

    get_switch = (data >= min_switch).astype(int) 
    diff = np.diff(get_switch, prepend=0, append=0) 
    segments = list(zip(np.where(diff == 1)[0], np.where(diff == -1)[0]))

    target_regions = [] 
    for start, end in segments: 
        segment_bit = data[start:end] 
        if len(segment_bit) < 3:
            continue

        #peak 검출기
        peaks = []
        peak_length_option = 30
        j = 1
        tolerance = 0.005
        while j < len(segment_bit)-1:
            val = segment_bit[j]

            if segment_bit[j-1] >= val:
                j+= 1
                continue
            
            left_max = np.max(segment_bit[max(0,j-10):j])
            if left_max >= val:
                j += 1
                continue
            peak_start = j
            peak_end = j

            while(peak_end + 1 < len(segment_bit) and abs(segment_bit[peak_end + 1] - val) <= tolerance):
                peak_end +=1

            if peak_end + 1 >= len(segment_bit):
                break

            right_max = np.max(
                segment_bit[peak_end+1:min(len(segment_bit), peak_end+11)]
            )
            peak_height = np.max(segment_bit[peak_start:peak_end+1])

            if peak_height >= right_max:
                peaks.append((peak_start, peak_end, peak_height,1 if peak_end - peak_start + 1 >= peak_length_option else 0,))

            j = peak_end + 1
        #crater 검출기
        crater_idx = []
        min_depth = 0.1
        min_valley_length = 10
        temp = 0

        while temp < len(peaks)-1:
            peak_start_idx, peak_end_idx, peak_val, peak_type = peaks[temp]
            next_peak_start_idx, next_peak_end_idx, next_peak_val, next_peak_type = peaks[temp+1]

            # 두 peak보다 0.1 이상 낮은 상태가 10행 연속인지 검사
            valley_threshold = min(peak_val, next_peak_val) - min_depth
            valley_data = segment_bit[peak_end_idx + 1:next_peak_start_idx]
            count = 0
            valid_valley = False

            for value in valley_data:
                if value <= valley_threshold:
                    count += 1
                    if count >= min_valley_length:
                        valid_valley = True
                        break
                else:
                    count = 0

            if (
                next_peak_start_idx - peak_end_idx >= 10
                and abs(peak_val - next_peak_val) < 0.1
                and valid_valley):

                if peak_type == 0 and next_peak_type == 0:
                    # 짧은 peak + 짧은 peak
                    crater_start = peak_start_idx
                    crater_end = next_peak_end_idx

                elif peak_type == 1 and next_peak_type == 0:
                    # 긴 peak + 짧은 peak
                    crater_start = (peak_start_idx + peak_end_idx) // 2
                    crater_end = next_peak_end_idx

                elif peak_type == 0 and next_peak_type == 1:
                    # 짧은 peak + 긴 peak
                    crater_start = peak_start_idx
                    crater_end = (next_peak_start_idx + next_peak_end_idx) // 2

                else:
                    # 긴 peak + 긴 peak
                    crater_start = (peak_start_idx + peak_end_idx) // 2
                    crater_end = (next_peak_start_idx + next_peak_end_idx) // 2

                crater_idx.append((crater_start, crater_end))

            temp += 1
        #===
        for i, (crater_start, crater_end) in enumerate(crater_idx):
            seq_start = start + crater_start
            seq_end = start + crater_end + 1  # 마지막 행까지 포함

            # 이전 crater와 겹치면 같은 중앙 경계를 사용
            if i > 0:
                prev_end = crater_idx[i - 1][1]
                if prev_end >= crater_start:
                    seq_start = start + (prev_end + crater_start) // 2

            # 다음 crater와 겹치면 같은 중앙 경계를 사용
            if i + 1 < len(crater_idx):
                next_start = crater_idx[i + 1][0]
                if crater_end >= next_start:
                    seq_end = start + (crater_end + next_start) // 2

            target_regions.append((seq_start, seq_end))

    return target_regions