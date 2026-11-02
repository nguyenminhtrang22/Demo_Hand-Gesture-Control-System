import os
import subprocess
import time
import cv2
import numpy as np
import math
import urllib.request

# 1. Chặn thông báo Warning/Info từ TensorFlow / MediaPipe
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '3'

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ==================================================
# PHẦN 1: KẾT NỐI ĐIỆN THOẠI BẰNG ADB
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADB_PATH = os.path.join(BASE_DIR, "platform-tools", "adb.exe")


def check_phone():
    """Kiểm tra điện thoại đã kết nối ADB chưa."""
    if not os.path.exists(ADB_PATH):
        print("Không tìm thấy adb.exe:", ADB_PATH)
        return False

    try:
        result = subprocess.run(
            [ADB_PATH, "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        for line in result.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                return True

    except Exception as e:
        print("Lỗi ADB:", e)

    return False


def control_phone(key):
    """Gửi lệnh keyevent đến điện thoại."""
    try:
        result = subprocess.run(
            [ADB_PATH, "shell", "input", "keyevent", str(key)],
            capture_output=True,
            text=True,
            timeout=3
        )
        return result.returncode == 0
    except Exception as e:
        print("Không thể gửi lệnh keyevent:", e)
        return False


def tap_phone(x=500, y=1000):
    """Gửi lệnh chạm màn hình ADB (Dành cho TikTok/Reels)."""
    try:
        cmd = [ADB_PATH, "shell", "input", "tap", str(x), str(y)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return result.returncode == 0
    except Exception as e:
        print("Không thể gửi lệnh tap:", e)
        return False


def swipe_phone(direction):
    """Gửi lệnh vuốt màn hình qua ADB."""
    try:
        if direction == "up":
            cmd = [ADB_PATH, "shell", "input", "swipe", "500", "1500", "500", "500", "300"]
        elif direction == "down":
            cmd = [ADB_PATH, "shell", "input", "swipe", "500", "500", "500", "1500", "300"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        return result.returncode == 0
    except Exception as e:
        print("Không thể gửi lệnh swipe:", e)
        return False


APP_MAP = {
    "Số 1 (Mở YouTube)": "com.google.android.youtube",
    "Số 2 (Mở TikTok)": "com.ss.android.ugc.trill",
    "Số 3 (Mở Camera)": "com.sec.android.app.camera",
    "Số 4 (Mở Thư viện)": "com.sec.android.gallery3d",
    "Số 5 (Mở Chrome)": "com.android.chrome"
}


def open_app_by_package(package_name, app_label):
    """Kiểm tra và mở ứng dụng cụ thể qua ADB."""
    try:
        check = subprocess.run(
            [ADB_PATH, "shell", "pm", "path", package_name],
            capture_output=True,
            text=True,
            timeout=5
        )

        if not check.stdout.strip():
            print(f"⚠️ [CẢNH BÁO] Không tìm thấy package '{package_name}' trên điện thoại!")
            print(f"Không thể mở: {app_label}")
            return

        result = subprocess.run(
            [
                ADB_PATH, "shell", "monkey",
                "-p", package_name,
                "-c", "android.intent.category.LAUNCHER",
                "1"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Đã mở ứng dụng: {app_label}")
        else:
            print(f"❌ Lỗi mở ứng dụng {app_label}: {result.stderr}")
    except Exception as e:
        print("Lỗi khi gửi lệnh mở app:", e)


gesture_commands = {
    "Tăng âm lượng": 24,        # VOLUME_UP
    "Giảm âm lượng": 25,        # VOLUME_DOWN
    "Về màn hình chính": 3,     # HOME
    "Quay lại": 4               # BACK
}

phone_connected = check_phone()
if phone_connected:
    print("Đã kết nối điện thoại thành công!")
else:
    print("Chưa kết nối điện thoại qua ADB (Chế độ nhận diện độc lập).")


# ==================================================
# PHẦN 2: TẢI VÀ KHỞI TẠO MÔ HÌNH MEDIAPIPE
# ==================================================

model_path = os.path.join(BASE_DIR, "hand_landmarker.task")

if not os.path.exists(model_path):
    print("Đang tải file mô hình AI MediaPipe...")
    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    )
    urllib.request.urlretrieve(url, model_path)
    print("Tải mô hình thành công!")

base_options = python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7
)
detector = vision.HandLandmarker.create_from_options(options)


# ==================================================
# PHẦN 3: KHỞI TẠO CAMERA VÀ CÁC HÀM BỔ TRỢ
# ==================================================

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Không thể mở Camera với CAP_DSHOW, thử mở mặc định...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        detector.close()
        raise SystemExit("Không tìm thấy Camera!")


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


def distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]


# ==================================================
# PHẦN 4: NHẬN DIỆN ỔN ĐỊNH & CẤU HÌNH GIAO DIỆN
# ==================================================

STABLE_SECONDS = 0.4
candidate_gesture = None
candidate_since = 0
last_triggered_gesture = None

ui_scale = 1.0


# ==================================================
# PHẦN 5: VÒNG LẬP NHẬN DIỆN VÀ ĐIỀU KHIỂN
# ==================================================

while cap.isOpened():

    ret, frame = cap.read()
    if not ret:
        print("Không thể đọc hình ảnh từ Camera!")
        break

    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    detection_result = detector.detect(mp_image)
    gesture = "Unknown"

    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:

            for p1_idx, p2_idx in HAND_CONNECTIONS:
                pt1 = (int(hand_landmarks[p1_idx].x * w), int(hand_landmarks[p1_idx].y * h))
                pt2 = (int(hand_landmarks[p2_idx].x * w), int(hand_landmarks[p2_idx].y * h))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

            for point in hand_landmarks:
                cv2.circle(frame, (int(point.x * w), int(point.y * h)), 4, (0, 0, 255), -1)

            lm = [Point(p.x, p.y) for p in hand_landmarks]
            s_palm = distance(lm[0], lm[9])

            if s_palm > 0:

                index_extended = distance(lm[8], lm[0]) > distance(lm[6], lm[0])
                middle_extended = distance(lm[12], lm[0]) > distance(lm[10], lm[0])
                ring_extended = distance(lm[16], lm[0]) > distance(lm[14], lm[0])
                pinky_extended = distance(lm[20], lm[0]) > distance(lm[18], lm[0])

                index_open = 1 if index_extended else 0
                middle_open = 1 if middle_extended else 0
                ring_open = 1 if ring_extended else 0
                pinky_open = 1 if pinky_extended else 0

                thumb_dist_ratio = distance(lm[4], lm[2]) / s_palm
                thumb_open = 1 if thumb_dist_ratio > 0.45 else 0

                thumb_index_dist = distance(lm[4], lm[8]) / s_palm

                # 1. Cử chỉ OK (Phát video)
                if thumb_index_dist < 0.35 and middle_open and ring_open and pinky_open:
                    gesture = "Phát video"

                # 2. Nắm tay (Tạm dừng video)
                elif not thumb_open and not index_open and not middle_open and not ring_open and not pinky_open:
                    gesture = "Tạm dừng video"

                # 3. I Love You (Về màn hình chính)
                elif thumb_open and index_open and pinky_open and not middle_open and not ring_open:
                    gesture = "Về màn hình chính"

                # 4. Quay lại (Ngón trỏ + Ngón út giơ lên)
                elif index_open and pinky_open and not middle_open and not ring_open and not thumb_open:
                    gesture = "Quay lại"

                # 5. Cử chỉ Ngón cái + Ngón trỏ (Lướt lên / Lướt xuống)
                elif index_open and thumb_open and not middle_open and not ring_open and not pinky_open:
                    if lm[8].y < lm[4].y:
                        gesture = "Lướt lên"
                    else:
                        gesture = "Lướt xuống"

                # 6. Các cử chỉ 1 - 5 mở app
                elif index_open and not middle_open and not ring_open and not pinky_open and not thumb_open:
                    gesture = "Số 1 (Mở YouTube)"

                elif index_open and middle_open and not ring_open and not pinky_open and not thumb_open:
                    gesture = "Số 2 (Mở TikTok)"

                elif index_open and middle_open and ring_open and not pinky_open and not thumb_open:
                    gesture = "Số 3 (Mở Camera)"

                elif index_open and middle_open and ring_open and pinky_open and not thumb_open:
                    gesture = "Số 4 (Mở Thư viện)"

                elif thumb_open and index_open and middle_open and ring_open and pinky_open:
                    gesture = "Số 5 (Mở Chrome)"

                # 7. Tăng / Giảm âm lượng
                elif thumb_open and not index_open and not middle_open and not ring_open and not pinky_open:
                    if lm[4].y < lm[0].y:
                        gesture = "Tăng âm lượng"
                    else:
                        gesture = "Giảm âm lượng"

    # --------------------------------------------------
    # BƯỚC 2: XÁC NHẬN CỬ CHỈ ỔN ĐỊNH VÀ GỬI LỆNH TỐI ƯU
    # --------------------------------------------------

    current_time = time.time()
    valid_gestures = set(gesture_commands.keys()) | set(APP_MAP.keys()) | {"Lướt lên", "Lướt xuống", "Phát video", "Tạm dừng video"}

    if gesture in valid_gestures:

        if gesture != candidate_gesture:
            candidate_gesture = gesture
            candidate_since = current_time

        elif (current_time - candidate_since >= STABLE_SECONDS) and (gesture != last_triggered_gesture):

            if phone_connected:
                if gesture in APP_MAP:
                    open_app_by_package(APP_MAP[gesture], gesture)
                elif gesture == "Lướt lên":
                    swipe_phone("up")
                    print("Đã lướt lên")
                elif gesture == "Lướt xuống":
                    swipe_phone("down")
                    print("Đã lướt xuống")
                
                # -----------------------------------------------------------
                # XỬ LÝ PHÁT / TẠM DÙNG KẾT HỢP (YOUTUBE + TIKTOK DEU CHẠY TỐT)
                # -----------------------------------------------------------
                elif gesture == "Phát video":
                    control_phone(126)  # Lệnh MEDIA_PLAY chuẩn cho YouTube/Nhạc
                    tap_phone(500, 1000) # Lệnh Tap giữa màn hình cho TikTok
                    print("Đã thực hiện: Phát video")
                
                elif gesture == "Tạm dừng video":
                    control_phone(127)  # Lệnh MEDIA_PAUSE chuẩn cho YouTube/Nhạc
                    tap_phone(500, 1000) # Lệnh Tap giữa màn hình cho TikTok
                    print("Đã thực hiện: Tạm dừng video")
                # -----------------------------------------------------------

                elif gesture in gesture_commands:
                    control_phone(gesture_commands[gesture])
                    print("Đã gửi lệnh:", gesture)
            else:
                print("Lệnh đã nhận diện (Chưa kết nối ADB):", gesture)

            last_triggered_gesture = gesture

    else:
        candidate_gesture = None
        candidate_since = 0
        last_triggered_gesture = None

    # --------------------------------------------------
    # BƯỚC 3: HIỂN THỊ VÀ THU NHỎ KÍCH THƯỚC CỬA SỔ
    # --------------------------------------------------

    phone_status = "Connected" if phone_connected else "Disconnected"

    cv2.putText(frame, f"Cu chi: {gesture}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    cv2.putText(frame, f"Phone: {phone_status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 150, 0), 2)

    panel_w = int(340 * ui_scale)
    panel_x = max(10, w - panel_w - 10)

    font_scale = 0.4 * ui_scale
    line_step = int(24 * ui_scale)

    panel1_lines = [
        "--- MO UNG DUNG ---",
        "So 1 : Mo YouTube",
        "So 2 : Mo TikTok",
        "So 3 : Mo Samsung Camera",
        "So 4 : Mo Thu vien",
        "So 5 : Mo Chrome"
    ]

    panel2_lines = [
        "--- DIEU KHIEN ---",
        "Cu chi OK            : Phat video",
        "Nam tay              : Tam dung video",
        "Cai + Tro (Tro cao)  : Luot len",
        "Cai + Tro (Tro thap) : Luot xuong",
        "Ngon tro + Ngon ut   : Quay lai",
        "Ngon cai len/xuong   : Tang/Giam vol",
        "I Love You           : Man hinh chinh"
    ]

    panel1_y = 10
    panel1_h = int(170 * ui_scale)
    overlay1 = frame.copy()
    cv2.rectangle(overlay1, (panel_x, panel1_y), (panel_x + panel_w, panel1_y + panel1_h), (25, 25, 25), -1)
    cv2.addWeighted(overlay1, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (panel_x, panel1_y), (panel_x + panel_w, panel1_y + panel1_h), (0, 255, 255), 1)

    y_text = panel1_y + int(22 * ui_scale)
    for i, line in enumerate(panel1_lines):
        color = (0, 255, 255) if i == 0 else (245, 245, 245)
        thickness = 2 if i == 0 else 1
        cv2.putText(frame, line, (panel_x + 8, y_text), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
        y_text += line_step

    panel2_y = panel1_y + panel1_h + 10
    panel2_h = int(210 * ui_scale)
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (panel_x, panel2_y), (panel_x + panel_w, panel2_y + panel2_h), (25, 25, 25), -1)
    cv2.addWeighted(overlay2, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (panel_x, panel2_y), (panel_x + panel_w, panel2_y + panel2_h), (0, 255, 0), 1)

    y_text = panel2_y + int(22 * ui_scale)
    for i, line in enumerate(panel2_lines):
        color = (0, 255, 0) if i == 0 else (245, 245, 245)
        thickness = 2 if i == 0 else 1
        cv2.putText(frame, line, (panel_x + 8, y_text), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
        y_text += line_step

    cv2.putText(frame, "Phim: '+' To bang | '-' Nho bang | 'f' Fullscreen | 'q' Thoat", 
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    display_frame = cv2.resize(frame, (800, 450))

    cv2.namedWindow("Hand Gesture Recognition", cv2.WINDOW_NORMAL)
    cv2.imshow("Hand Gesture Recognition", display_frame)
    cv2.setWindowProperty("Hand Gesture Recognition", cv2.WND_PROP_TOPMOST, 1)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('+') or key == ord('='):
        ui_scale = min(2.0, ui_scale + 0.1)
    elif key == ord('-') or key == ord('_'):
        ui_scale = max(0.6, ui_scale - 0.1)
    elif key == ord('f'):
        is_fullscreen = cv2.getWindowProperty("Hand Gesture Recognition", cv2.WND_PROP_FULLSCREEN)
        if is_fullscreen == cv2.WINDOW_FULLSCREEN:
            cv2.setWindowProperty("Hand Gesture Recognition", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        else:
            cv2.setWindowProperty("Hand Gesture Recognition", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ==================================================
# PHẦN 6: GIẢI PHÓNG TÀI NGUYÊN
# ==================================================

cap.release()
detector.close()
cv2.destroyAllWindows()
print("Đã đóng chương trình!")