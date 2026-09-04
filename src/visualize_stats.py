import json
from pathlib import Path 
import pandas as pd # chuyển dữ liệu json thành dataframe 2 chiều
import matplotlib.pyplot as plt # Dựng khung vẽ chia lưới Subplots
import seaborn as sns # Tính toán mật độ xác suất vẽ Histogram và Bản đồ nhiệt Heatmap

# Thiết lập giao diện đồ họa
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = "Arial"
# Để hiển thị dấu trừ trong biểu đồ mà không bị lỗi font
plt.rcParams["axes.unicode_minus"] = False

REPORTS_DIR = Path(r"d:\SIC\reports")
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_PATH = REPORTS_DIR / "clean_metrics.json"

def load_metrics_data(json_path: Path) -> pd.DataFrame:
    """
    Nạp dữ liệu từ file clean_metrics.json vào DataFrame của pandas
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Gộp dữ liệu train và val thành một DataFrame duy nhất
    all_data = raw["train_metrics"] + raw["val_metrics"]
    return pd.DataFrame(all_data)

def plot_box_distribution(df: pd.DataFrame, output_dir: Path):
    """
    Vẽ biểu đồ phân bố diện tích hộp bàn tay và tỉ lệ w/h
    """
    # Thiết lập khung vẽ 1 hàng 2 cột kich thước 14x5 inch
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Vẽ biểu đồ phân bố diện tích hộp bàn tay
    sns.histplot(df["box_area"], bins=30, kde=True, ax=ax1, color="#2980b9")
    ax1.set_title("Phân bố diện tích hộp bàn tay", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Tỉ lệ diện tích hộp bàn tay / diện tích ảnh")
    ax1.set_ylabel("Số lượng mẫu ảnh")

    # Vẽ biểu đồ phân bố tỉ lệ w/h
    sns.histplot(df["aspect_ratio"], bins=30, kde=True, ax=ax2, color="#e74c3c")
    ax2.set_title("Phân bố tỉ lệ w/h của hộp bàn tay", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Tỉ lệ w/h của hộp bàn tay")
    ax2.set_ylabel("Số lượng mẫu ảnh")

    plt.tight_layout()
    # Lưu biểu đồ ra file PNG
    save_path = output_dir / "box_distribution.png"
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"Biểu đồ phân bố diện tích hộp bàn tay và tỉ lệ w/h đã lưu tại: {save_path}")

def plot_pinch_distribution(df: pd.DataFrame, output_dir: Path):
    """
    Vẽ biểu đồ phân bố khoảng cách giữa đầu ngón cái và đầu ngón trỏ
    """
    plt.figure(figsize=(10, 6))
    # Vẽ biểu đồ mật độ xác suất KDE (Kernel Density Estimation)
    sns.kdeplot(df["pinch_distance"], fill=True, alpha=0.4, linewidth=2, color="#27ae60")
    # Vẽ các đường thẳng dọc để đánh dấu ngưỡng Zoom Active và Zoom Inactive
    plt.axvline(x=0.12, color="red", linestyle="--", linewidth=2, label="Ngưỡng Zoom Active <= 0.12")
    plt.axvline(x=0.22, color="orange", linestyle="--", linewidth=2, label="Ngưỡng Zoom Inactive > 0.22")

    
    median_value = df["pinch_distance"].median()
    plt.axvline(x=median_value, color="blue", linestyle=":", label=f"Trung vị tự nhiên({median_value:.3f})")

    plt.title("Phân Bố Khoảng Cách Chụm Ngón P4 - P8 (Cơ Sở Thiết Lập Ngưỡng Zoom)", fontsize=13, fontweight="bold")
    plt.xlabel("Khoảng cách Euclid chuẩn hóa (0.0 - 1.0)")
    plt.ylabel("Mật độ xác suất (Density)")
    plt.legend(loc="upper right", fontsize=10)
    save_path = output_dir / "pinch_distance_distribution.png"
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[*] Đã lưu biểu đồ 2: {save_path}")

import matplotlib.patches as patches

def plot_spatial_heatmap(df: pd.DataFrame, output_dir: Path):
    """Vẽ bản đồ nhiệt 2D phân bố cổ tay và ngón trỏ trên khung ảnh 224x224."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Subplot 1: Mật độ vị trí Cổ tay (Wrist)
    sns.kdeplot(x=df["wrist_x"], y=df["wrist_y"], cmap="Blues", fill=True, levels=15, ax=ax1)
    ax1.set_title("Bản Đồ Nhiệt Vị Trí Cổ Tay (Wrist P0)", fontsize=12, fontweight="bold")
    ax1.set_xlim(0, 1)
    ax1.set_ylim(1, 0) # Đảo ngược trục Y để khớp với hệ tọa độ ảnh máy tính (gốc 0,0 ở góc trên trái)
    ax1.set_xlabel("Tọa độ X chuẩn hóa")
    ax1.set_ylabel("Tọa độ Y chuẩn hóa")

    # Subplot 2: Mật độ vị trí Đỉnh ngón trỏ (Index TIP)
    sns.kdeplot(x=df["index_tip_x"], y=df["index_tip_y"], cmap="Greens", fill=True, levels=15, ax=ax2)
    
    # Vẽ khung chữ nhật biểu diễn Vùng tương tác trung tâm (Active Interaction Box)
    rect = patches.Rectangle((0.25, 0.25), 0.40, 0.50, linewidth=2, edgecolor="red", facecolor="none", linestyle="--", label="Vùng Tương Tác Chuột [0.25-0.65]")
    ax2.add_patch(rect)
    ax2.set_title("Bản Đồ Nhiệt Đỉnh Ngón Trỏ (Index TIP P8)", fontsize=12, fontweight="bold")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(1, 0)
    ax2.set_xlabel("Tọa độ X chuẩn hóa")
    ax2.set_ylabel("Tọa độ Y chuẩn hóa")
    ax2.legend(loc="upper left")

    plt.tight_layout()
    save_path = output_dir / "spatial_heatmap.png"
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[*] Đã lưu biểu đồ 3: {save_path}")

def plot_swipe_span_distribution(df: pd.DataFrame, output_dir: Path):
    """Vẽ biểu đồ phân bố độ lệch ngang giữa ngón trỏ và cổ tay (Cơ sở nhận diện hướng Vuốt)."""
    plt.figure(figsize=(10, 6))

    # Tính độ lệch ngang Delta X = Index_X - Wrist_X
    delta_x = df["index_tip_x"] - df["wrist_x"]

    sns.kdeplot(delta_x, fill=True, color="#8e44ad", alpha=0.4, linewidth=2)

    # Đánh dấu các ngưỡng phân tách hướng Vuốt
    plt.axvline(x=0.15, color="green", linestyle="--", linewidth=2, label="Vùng hướng Tiến (Next: Delta X >= 0.15)")
    plt.axvline(x=-0.15, color="orange", linestyle="--", linewidth=2, label="Vùng hướng Lùi (Prev: Delta X <= -0.15)")
    plt.axvline(x=0.0, color="gray", linestyle=":", label="Trục trung hòa thẳng đứng")

    plt.title("Phân Bố Độ Lệch Ngang (Index X - Wrist X) Phục Vụ Hướng Vuốt Slide", fontsize=13, fontweight="bold")
    plt.xlabel("Độ lệch ngang Delta X (-1.0 đến +1.0)")
    plt.ylabel("Mật độ xác suất")
    plt.legend(loc="upper right", fontsize=10)

    save_path = output_dir / "swipe_span_distribution.png"
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"[*] Đã lưu biểu đồ 4: {save_path}")

def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("[*] Đang đọc dữ liệu sạch từ:", METRICS_PATH)
    df = load_metrics_data(METRICS_PATH)
    print(f"[*] Đã tải thành công {len(df)} mẫu hợp lệ.")

    # Vẽ lần lượt 3 biểu đồ
    plot_box_distribution(df, FIGURES_DIR)
    plot_pinch_distribution(df, FIGURES_DIR)
    plot_spatial_heatmap(df, FIGURES_DIR)
    plot_swipe_span_distribution(df, FIGURES_DIR)

    print("\n" + "="*50)
    print("HOÀN THÀNH XUẤT BẢN 4 BỘ BIỂU ĐỒ THỐNG KÊ")
    print(f"-> Thư mục lưu ảnh: {FIGURES_DIR}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()