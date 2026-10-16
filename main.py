import os
import sys
import time
import random
import threading
import customtkinter as ctk
from playwright.sync_api import sync_playwright

# Cấu hình giao diện CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FacebookBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Facebook Interaction Manager")
        self.geometry("720x540")
        self.resizable(False, False)

        self.is_running = False

        # --- Giao diện bên trái (Điều khiển & Cài đặt) ---
        self.left_frame = ctk.CTkFrame(self, width=320, corner_radius=10)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(
            self.left_frame, text="Quản Lý Tương Tác", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(padx=10, pady=(15, 10))

        # Tên profile / UID
        self.lbl_profile = ctk.CTkLabel(self.left_frame, text="Tên Profile / UID:")
        self.lbl_profile.pack(anchor="w", padx=15, pady=(5, 0))
        self.entry_profile = ctk.CTkEntry(self.left_frame, placeholder_text="acc_01")
        self.entry_profile.insert(0, "acc_01")
        self.entry_profile.pack(fill="x", padx=15, pady=(0, 10))

        # Giới hạn số Like
        self.lbl_likes = ctk.CTkLabel(self.left_frame, text="Số lượt Like tối đa:")
        self.lbl_likes.pack(anchor="w", padx=15, pady=(5, 0))
        self.entry_likes = ctk.CTkEntry(self.left_frame, placeholder_text="5")
        self.entry_likes.insert(0, "5")
        self.entry_likes.pack(fill="x", padx=15, pady=(0, 10))

        # Danh sách bình luận (Mỗi câu một dòng)
        self.lbl_comments = ctk.CTkLabel(self.left_frame, text="Nội dung Comment (mỗi dòng 1 câu):")
        self.lbl_comments.pack(anchor="w", padx=15, pady=(5, 0))
        self.txt_comments = ctk.CTkTextbox(self.left_frame, height=120)
        self.txt_comments.pack(fill="x", padx=15, pady=(0, 15))
        self.txt_comments.insert("1.0", "Hay quá bạn ơi!\nBài viết rất ý nghĩa 👍\nTương tác cùng phát triển nhé!")

        # Nút Bắt đầu / Dừng
        self.btn_toggle = ctk.CTkButton(
            self.left_frame, text="Bắt đầu Chạy", command=self.toggle_process, fg_color="green"
        )
        self.btn_toggle.pack(fill="x", padx=15, pady=10)

        # --- Giao diện bên phải (Nhật ký hoạt động / Logs) ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

        self.log_title = ctk.CTkLabel(
            self.right_frame, text="Nhật ký hoạt động", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.log_title.pack(anchor="w", padx=15, pady=(15, 5))

        self.txt_log = ctk.CTkTextbox(self.right_frame)
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def log(self, message: str):
        """Ghi log hiển thị lên giao diện"""
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.insert("end", f"[{timestamp}] {message}\n")
        self.txt_log.see("end")

    def toggle_process(self):
        if not self.is_running:
            self.is_running = True
            self.btn_toggle.configure(text="Dừng lại", fg_color="red")
            # Chạy logic bot trên 1 thread riêng biệt để không làm đơ giao diện
            threading.Thread(target=self.bot_worker, daemon=True).start()
        else:
            self.is_running = False
            self.btn_toggle.configure(text="Bắt đầu Chạy", fg_color="green")
            self.log("Đã gửi yêu cầu dừng bot.")

    def bot_worker(self):
        profile_name = self.entry_profile.get().strip() or "default_profile"
        try:
            max_likes = int(self.entry_likes.get().strip())
        except ValueError:
            max_likes = 3

        comments_raw = self.txt_comments.get("1.0", "end").strip().split("\n")
        comments = [c.strip() for c in comments_raw if c.strip()]

        profile_dir = os.path.abspath(f"./profiles/{profile_name}")
        os.makedirs(profile_dir, exist_ok=True)

        self.log(f"Khởi động profile: {profile_name}")
        self.log("Đang mở trình duyệt Edge...")

        try:
            with sync_playwright() as p:
                # Sử dụng kênh msedge tích hợp sẵn trên Windows
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="msedge",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )

                page = context.new_page()
                self.log("Truy cập m.facebook.com...")
                page.goto("https://m.facebook.com", timeout=60000)
                time.sleep(3)

                likes_count = 0
                while self.is_running and likes_count < max_likes:
                    # Cuộn trang ngẫu nhiên
                    scroll_distance = random.randint(400, 800)
                    page.mouse.wheel(0, scroll_distance)
                    time.sleep(random.uniform(3.0, 6.0))

                    # Quét nút Thích / Like
                    like_buttons = page.query_selector_all('div[aria-label="Thích"], div[aria-label="Like"]')
                    if like_buttons:
                        btn = random.choice(like_buttons)
                        try:
                            btn.click()
                            likes_count += 1
                            self.log(f"-> Đã thả Thích ({likes_count}/{max_likes})")
                            time.sleep(random.uniform(4.0, 7.0))
                        except Exception:
                            pass

                self.log("Hoàn thành tác vụ hoặc phiên chạy kết thúc.")
                context.close()

        except Exception as e:
            self.log(f"Lỗi: {e}")
        finally:
            self.is_running = False
            self.btn_toggle.configure(text="Bắt đầu Chạy", fg_color="green")

if __name__ == "__main__":
    app = FacebookBotApp()
    app.mainloop()
