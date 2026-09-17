"""CSV를 읽어 신호의 검출 구간을 표시합니다. 이 파일을 실행하세요."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from data_detection import detect_peak_crater_regions
COLUMNS = [f"signal_{i:02d}" for i in range(1, 11)]
TARGET_COLUMN = "signal_08"

ROOT = Path(__file__).resolve().parent


def load_data():
    path = ROOT / "all_day_list.csv"
    if not path.exists():
        raise FileNotFoundError(f"CSV 파일을 같은 폴더에 넣어주세요: {path}")
    frame = pd.read_csv(path, header=None)
    if frame.shape[1] != len(COLUMNS) or len(frame) < 3:
        raise ValueError("CSV는 헤더 없이 10열, 최소 3행이어야 합니다.")
    frame.columns = COLUMNS
    data = pd.to_numeric(frame[TARGET_COLUMN], errors="raise").to_numpy()
    if not np.isfinite(data).all():
        raise ValueError("선택한 신호에 결측값 또는 무한대가 있습니다.")
    return data


def create_plot(data, regions, min_switch):
    import matplotlib.pyplot as plt
    from matplotlib.widgets import SpanSelector

    fig, (overview, detail) = plt.subplots(2, 1, figsize=(13, 7))
    fig.canvas.manager.set_window_title("Data detection portfolio")
    colors = ("tab:red", "tab:orange")
    for ax in (overview, detail):
        ax.plot(data, color="steelblue", linewidth=1, label=TARGET_COLUMN)
        ax.axhline(min_switch, color="gray", linestyle="--", label="min_switch")
        for i, (start, end) in enumerate(regions):
            ax.axvspan(start, end, color=colors[i % 2], alpha=.2,
                       label="Detected regions" if i == 0 else "_nolegend_")
        ax.set_ylabel(TARGET_COLUMN)
        ax.grid(alpha=.25)
    overview.set_xlim(0, len(data) - 1)
    overview.set_title(f"Data: {len(data)} rows / {len(regions)} regions - drag to zoom")
    detail.set_xlabel("Row index")
    detail.legend(loc="lower center")

    def show_detail(left, right):
        left, right = sorted((int(left), int(right)))
        left, right = max(0, left), min(len(data) - 1, right)
        if right <= left:
            return
        detail.set_xlim(left, right)
        detail.set_title(f"Selected rows: {left} - {right}")
        fig.canvas.draw_idle()

    if regions:
        show_detail(regions[0][0] - 50, regions[min(1, len(regions) - 1)][1] + 50)
    else:
        show_detail(0, len(data) - 1)
    # Keep the selector alive for as long as the figure is open.
    fig._portfolio_selector = SpanSelector(
        overview, show_detail, "horizontal", useblit=True, interactive=True)
    fig.tight_layout()
    return fig, show_detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Validate input and detected bounds, then save a preview without opening a window")
    args = parser.parse_args()
    import matplotlib
    if args.check:
        matplotlib.use("Agg")
    else:
        matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt

    data = load_data()
    regions = [(int(start), int(end)) for start, end in
               detect_peak_crater_regions(data, min_switch=0.4)]
    print(f"Running file: {Path(__file__).resolve()}")
    print(f"CSV: {ROOT / 'all_day_list.csv'}")
    print(f"Rows: {len(data)}, regions: {regions}")
    fig, show_detail = create_plot(data, regions, 0.4)
    if args.check:
        assert all(0 <= start < end <= len(data) for start, end in regions)
        left, right = 0, min(940, len(data) - 1)
        show_detail(left, right)
        assert tuple(fig.axes[1].get_xlim()) == (left, right)
        if regions:
            show_detail(regions[0][0] - 50, regions[min(1, len(regions) - 1)][1] + 50)
        fig.savefig(ROOT / "detection_preview.png", dpi=130)
        plt.close(fig)
        print("PASS: finite input, valid region bounds, zoom callback, preview saved")
    else:
        plt.show()


if __name__ == "__main__":
    main()
