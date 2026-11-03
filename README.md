- Cách kích hoạt ADB trên điện thoại android
1) Mở Cài đặt.
2) Chọn Thông tin điện thoại.
3) Chọn Thông tin phần mềm.
4) Nhấn liên tục 7 lần vào Số hiệu bản tạo (Build number).
5) Nhập mã PIN nếu được yêu cầu.
6) Quay lại Cài đặt, mở Tùy chọn nhà phát triển.
7) Bật Gỡ lỗi USB (USB debugging).
=> Khi điện thoại hỏi xác nhận cho phép gỡ lỗi USB, chọn Cho phép sau khi kiểm tra máy tính đang kết nối.

- Kết nối điện thoại với laptop
Dùng cáp USB kết nối điện thoại với laptop.
Mở khóa màn hình điện thoại.
Nếu xuất hiện thông báo USB, chọn chế độ truyền dữ liệu là truyền file.
Chọn Cho phép gỡ lỗi USB khi có thông báo xác thực.

- Cách để kiểm tra đã kích hoạt ADB:
Cách 1: Trên VS Code, mở Terminal và nhập lần lượt: "cd C:\platform-tools" -> ".\adb.exe devices"
=> Nếu kết nối thành công, cậu sẽ thấy dạng:
List of devices attached
R58XXXXXXXX    device

Cách 2: Mở file adb trong thư mục "platform-tools.zip", bám vào file "adb.exe", sau đó nhấn vào địa chỉ phía trên ".....\demo_python\platform-tools" và thay thế bằng "cmd"
Nhập ".\adb.exe devices"
=> Nếu kết nối thành công, cậu sẽ thấy dạng:
List of devices attached
R58XXXXXXXX    device
