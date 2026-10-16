# Facebook Interaction Manager (Desktop GUI)

Phần mềm tự động hóa tương tác Facebook cá nhân chạy trên Windows, xây dựng bằng Python, CustomTkinter và Playwright.

## Cách đưa lên GitHub để tự động xuất file .exe:
1. Tạo một repository mới trên GitHub.
2. Đẩy toàn bộ cấu trúc thư mục này lên nhánh `main`.
3. GitHub Actions sẽ tự động kích hoạt workflow `Build Windows App`.
4. Sau khi build hoàn tất, truy cập tab **Actions** > Nhấn vào lần chạy gần nhất > Tải file zip tại mục **Artifacts**.

## Lưu ý khi sử dụng:
- Ứng dụng tận dụng trình duyệt **Microsoft Edge** mặc định của Windows, do đó không yêu cầu cài đặt thêm driver ngoài.
- Dữ liệu đăng nhập cho từng tài khoản sẽ được tự động lưu trong thư mục `profiles/` ngay bên cạnh file ứng dụng sau lần đăng nhập đầu tiên.
