# hỗ trợ tìm kiếm tệp và thao tác hdh
import os 
import glob 
import json # đọc ghi dữ liệu ra tệp .json
from PIL import Image # kiểm tra tính toàn vẹn nhị phân tệp ảnh JPEG 
from pathlib import Path # thao tác tệp tin hdt 
from tqdm import tqdm # hiển thị thanh tiến trình tg thực

#CẤU HÌNH THƯ MỤC
DATASET_ROOT = Path (r"d:\SIC\data\hand-keypoints")
REPORTS_DIR = Path (r"d:\SIC\reports")

# 1 CLASS ID + 4 BBOX + 21 KEYPOINTS * 3 GIÁ
EXPECTED_TOKENS = 68
# DIỆN TÍCH HỘP NHỎ HƠN 0.5% KHUNG HÌNH COI LÀ NHIỄU
MIN_BOX_AREA = 0.005
# TỈ LỆ W/H HOẶC H/W VƯỢT QUÁ 4:1 COI LÀ HỘP BIẾN DẠNG
MAX_ASPECT_RATIO = 4.0

def verify_image(image_path: Path) -> bool :
    """
    Kiểm tra tính toàn vẹn nhị phân của tệp ảnh JPEG.
    Trả về True nếu tệp ảnh hợp lệ, False nếu bị hỏng.
    """
    try:
        with Image.open(image_path) as img:
            # .verify() chỉ đọc header và marker mà không decode pixel
            img.verify()
        return True
    except (IOError, SyntaxError, Image.UnidentifiedImageError):
        print(f"Ảnh bị hỏng: {image_path}")
        return False

def validate_label(label_path: Path) -> tuple[bool, str, dict]:
    """
    Thẩm định tính hợp lệ của file nhãn YOLO Pose của 68 tham số
    Trả về (is_valid, error_code, metrics_dict)
    """
    if not label_path.exists():
        return False, "MISSING_LABEL",{}
    try: 
        with open(label_path, "r" , encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
    except Exception:
        return False, "CANNOT_READ_LABEL",{}

    # 1 kiểm tra file rỗng 
    if len(lines) == 0:
        return False, "EMPTY_LABEL",{}

    # lấy dòng đầu tiên (mỗi ảnh tương ứng 1 bàn tay)
    # hàm split() tách chuỗi thành danh sách các token dựa trên khoảng trắng
    tokens_str = lines[0].split()
    if len(tokens_str) != EXPECTED_TOKENS:
        return False, f"INVALID_TOKEN_COUNT_{len(tokens_str)}",{}

    try:
        # chuyển đổi các token sang float lưu vào danh sách tokens 
        # nếu có lỗi ValueError (giá trị không phải số) thì trả về False
        tokens = [float(token) for token in tokens_str] 
    except ValueError: # lỗi giá trị không phải số
        return False, "NON_NUMERIC_TOKEN",{}

    # 2 kiểm tra classID 
    class_id = int(tokens[0])
    if class_id !=0 :
        # nếu class_id khác 0 thì trả về False và mã lỗi INVALID_CLASS_ID
        return False,
    f"INVALID_CLASS_ID_{class_id}",{}

    # 3 kiểm tra Bounding Box: cx, cy, w, h
    cx , cy, w, h = tokens[1:5]
    if w <= 0.0 or h <= 0.0:
        # nếu chiều rộng hoặc chiều cao <= 0 thì trả về False và mã lỗi ZERO_OR_NEGATIVE_BBOX
        return False, "ZERO_OR_NEGATIVE_BBOX",{}
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
        # nếu tâm hộp nằm ngoài phạm vi [0,1] thì trả về False và mã lỗi BBOX_CENTER_OUT_OF_RANGE
        return False, "BBOX_CENTER_OUT_OF_RANGE",{}

    box_area = w * h
    if box_area < MIN_BOX_AREA:
        # nếu diện tích hộp nhỏ hơn 0.5% khung hình thì trả về False và mã lỗi BBOX_TOO_SMALL
        return False, "BBOX_TOO_SMALL",{}

    aspect_ratio = w / h if h > 0 else 999.0
    if aspect_ratio > MAX_ASPECT_RATIO or aspect_ratio < (1.0 / MAX_ASPECT_RATIO):
        # nếu tỉ lệ w/h hoặc h/w vượt quá 4:1 thì trả về False và mã lỗi ABNORMAL_ASPECT_RATIO
        return False, "ABNORMAL_ASPECT_RATIO",{}

    # 4 kiểm tra Keypoints: 21 keypoints (tọa độ và visibility)
    # Duyệt qua 21 khớp xương Với mỗi khớp i vị trí trong mảng bắt đầu từ vị trí thứ 5 + i * 3
    for i in range(21):
        idx = 5 + i * 3
        # lấy tọa độ x, y và visibility của keypoint thứ i
        kx,ky,kv= tokens[idx], tokens[idx+1], tokens[idx+2]

        # nếu tọa độ keypoint nằm ngoài phạm vi [0,1] thì trả về False và mã lỗi KEYPOINT_OUT_OF_RANGE
        if not (0.0 <= kx <= 1.0 and 0.0 <= ky <= 1.0):
            return False, f"KEYPOINT_{i}_OUT_OF_RANGE",{}

        # nếu visibility không phải 0,1,2 thì trả về False và mã lỗi KEYPOINT_INVALID_VISIBILITY
        if kv not in (0, 1, 2):
            return False, f"KEYPOINT_{i}_INVALID_VISIBILITY",{}

    # 5 trích xuất khoảng cách Pinch ngón cái (kpt 4) và ngón trỏ (kpt 8)
    thumb_x, thumb_y = tokens[5 + 4 * 3], tokens[5 + 4 * 3 + 1]
    index_x, index_y = tokens[5 + 8 * 3], tokens[5 + 8 * 3 + 1]
    # tính khoảng cách Euclidean giữa ngón cái và ngón trỏ
    pinch_dist = ((thumb_x - index_x) ** 2 + (thumb_y - index_y) ** 2) ** 0.5

    metrics = {
        "box_area": round(box_area, 5),
        "aspect_ratio": round(aspect_ratio, 3),
        "pinch_distance": round(pinch_dist, 5),
        "wrist_x": round(tokens[5], 4),
        "wrist_y": round(tokens[6], 4),
        "index_tip_x": round(index_x, 4),
        "index_tip_y": round(index_y, 4),
    }
    return True, "VALID", metrics

def clean_split(split_name: str) -> dict:
    """
    Quét và làm sạch một tập dữ liệu (train hoặc val)
    """
    # xác định đường dẫn thư mục ảnh và nhãn dựa trên tên split
    img_dir = DATASET_ROOT / "images" / split_name
    lbl_dir = DATASET_ROOT / "labels" / split_name

    
    img_files = sorted(list(img_dir.glob("*.jpg")))
    print(f"\[*n] Quét [{split_name.upper()}]: Tổng cộng {len(img_files)} ảnh JPG trong {img_dir}")

    clean_samples = []
    error_logs = {}
    metrics_list = []

    for img_path in tqdm(img_files, desc=f"Đang làm sạch [{split_name}]"):
        # Lấy tên tệp ảnh (không có phần mở rộng) để tìm tệp nhãn tương ứng
        file_stem = img_path.stem
        lbl_path = lbl_dir / f"{file_stem}.txt"

        #Bước 1: Kiểm tra ảnh 
        if not verify_image(img_path):
            error_logs[img_path.name] = "CORRUPT_IMAGE"
            continue

        #Bước 2: Kiểm tra nhãn
        is_valid, reason, metrics = validate_label(lbl_path)
        if not is_valid:
            error_logs[img_path.name] = reason
            continue

        # Đạt chuẩn -> lưu thông tin ảnh và nhãn vào danh sách clean_samples
        clean_samples.append({
            "image_path": str(img_path),
            "label_path": str(lbl_path),
            "stem": file_stem
        })
        metrics["stem"] = file_stem
        metrics_list.append(metrics)

    # Tạo báo cáo tổng hợp
    sumary = {
        "split": split_name,
        "total_images": len(img_files),
        "clean_count": len(clean_samples),
        "error_count": len(error_logs),
        "clean_ratio": round(len(clean_samples) / len(img_files)*100, 2) if img_files else 0.0,
        "error_breakdown": error_logs,
        "clean_samples": clean_samples,
        "metrics": metrics_list
    }
    return sumary

def main():
    # Tạo thư mục báo cáo nếu chưa tồn tại
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Làm sạch tập train và val
    train_summary= clean_split("train")
    val_summary = clean_split("val")

    # 2. Xuất danh sách các file sạch ra file .txt để các module sau sử dụng
    train_clean_txt = REPORTS_DIR / "clean_train_files.txt"
    with open(train_clean_txt, "w", encoding="utf-8") as f:
        for s in train_summary["clean_samples"]:
            f.write(f"{s['image_path']},{s['label_path']}\n")
    val_clean_txt = REPORTS_DIR / "clean_val_files.txt"
    with open(val_clean_txt, "w", encoding="utf-8") as f:
        for s in val_summary["clean_samples"]:
            f.write(f"{s['image_path']},{s['label_path']}\n")
    # 3. Xuất báo cáo JSON tổng hợp
    full_report = {
        "train": {
            "total": train_summary["total_images"],
            "clean": train_summary["clean_count"],
            "errors": train_summary["error_count"],
            "error_details": train_summary["error_breakdown"],
            "clean_ratio": train_summary["clean_ratio"]
        },
        "val": {
            "total": val_summary["total_images"],
            "clean": val_summary["clean_count"],
            "errors": val_summary["error_count"],
            "error_details": train_summary["error_breakdown"],
            "clean_ratio": val_summary["clean_ratio"]
        }
    }
    report_json_path = REPORTS_DIR / "data_cleaning_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)
    # 4. Xuất metrics ra file JSON riêng để module visualize vẽ biểu đồ
    metrics_json_path = REPORTS_DIR / "clean_metrics.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "train_metrics": train_summary["metrics"],
            "val_metrics": val_summary["metrics"]
        }, f, indent=2)
    # In kết quả tổng kết ra màn hình
    print("\n" + "="*50)
    print("           KẾT QUẢ LÀM SẠCH DỮ LIỆU")
    print("="*50)
    print(f" Tập TRAIN : {train_summary['clean_count']}/{train_summary['total_images']} hợp lệ ({train_summary['clean_ratio']}%)")
    print(f" Tập VAL   : {val_summary['clean_count']}/{val_summary['total_images']} hợp lệ ({val_summary['clean_ratio']}%)")
    print(f"-> Danh sách file sạch đã lưu tại: {REPORTS_DIR}")
    print(f"-> Báo cáo tổng hợp đã lưu tại: {report_json_path}")
    print("="*50 + "\n")
if __name__ == "__main__":
    main()
