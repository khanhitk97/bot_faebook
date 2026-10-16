import os
import sys
import time
import math
import random
import threading
import numpy as np
import customtkinter as ctk
from playwright.sync_api import sync_playwright

# Cấu hình giao diện
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==========================================
# 1. HỆ THỐNG MÔ PHỎNG HÀNH VI SINH HỌC
# ==========================================
class HumanSimulator:
    @staticmethod
    def bezier_curve(p0, p1, p2, p3, num_points=25):
        """Tạo đường cong Bezier bậc 3 để mô phỏng quỹ đạo tay di chuyển chuột"""
        t = np.linspace(0, 1, num_points)
        curve = (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2
            + t ** 3 * p3
        )
        return curve

    @classmethod
    def move_mouse_naturally(cls, page, target_x, target_y):
        """Di chuyển chuột từ vị trí hiện tại đến mục tiêu với gia tốc tự nhiên"""
        # Giả định điểm xuất phát ngẫu nhiên nếu chưa có
        start_x = random.randint(100, 500)
        start_y = random.randint(100, 500)
        
        # 2 điểm điều khiển ngẫu nhiên tạo độ võng đường cong
        ctrl_x1 = start_x + (target_x - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        ctrl_y1 = start_y + (target_y - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
        ctrl_x2 = start_x + (target_x - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
        ctrl_y2 = start_y + (target_y - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)

        curve_x = cls.bezier_curve(start_x, ctrl_x1, ctrl_x2, target_x)
        curve_y = cls.bezier_curve(start_y, ctrl_y1, ctrl_y2, target_y)

        for x, y in zip(curve_x, curve_y):
            page.mouse.move(float(x), float(y))
            time.sleep(random.uniform(0.005, 0.015))

    @staticmethod
    def human_type(page, selector, text):
        """Gõ chữ mô phỏng hành vi: ngẫu nhiên tốc độ, thỉnh thoảng gõ sai rồi xóa"""
        elem = page.locator(selector).first
        elem.click()
        time.sleep(random.uniform(0.3, 0.7))

        i = 0
        while i < len(text):
            char = text[i]
            # Xác suất 3% gõ nhầm 1 phím bên cạnh
            if random.random() < 0.03 and char.isalpha():
                typo_char = chr(ord(char) + 1)
                elem.press_sequentially(typo_char, delay=random.randint(80, 150))
                time.sleep(random.uniform(0.2, 0.5))
                elem.press("Backspace")
                time.sleep(random.uniform(0.15, 0.3))

            elem.press_sequentially(char, delay=random.randint(60, 200))
            if char in [",", ".", " ", "!"]:
                time.sleep(random.uniform(0.25, 0.55))
            i += 1

    @staticmethod
    def human_scroll(page):
        """Cuộn trang có quán tính, ngẫu nhiên đảo chiều cuộn lên lại"""
        scroll_steps = random.randint(4, 8)
        direction = 1 if random.random() > 0.15 else -1 # 15% cuộn ngược lại để đọc
        distance = random.randint(300, 700) * direction

        for _ in range(scroll_steps):
            step = distance / scroll_steps
            page.mouse.wheel(0, step)
            time.sleep(random.uniform(0.05, 0.15))
        time.sleep(random.uniform(1.5, 4.0))

# ==========================================
# 2. XỬ LÝ TRÍ TUỆ NHÂN TẠO (LLM ENGINE)
# ==========================================
class AIEngine:
    @staticmethod
    def generate_reply(post_content: str, api_key: str = None) -> str:
        """Đọc văn bản bài viết và tạo câu trả lời chuẩn ngữ cảnh mạng xã hội"""
        if not post_content or len(post_content.strip()) < 10:
            return ""

        if not api_key:
            # Dự phòng câu chào tự nhiên nếu người dùng chưa điền API Key
            fallback = [
                "Bài viết ý nghĩa quá bạn ơi!", 
                "Cảm ơn bạn đã chia sẻ nhé 👍", 
                "Tuyệt vời quá, chúc bạn ngày mới nhiều năng lượng nha!"
            ]
            return random.choice(fallback)

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                "Bạn là một người dùng Facebook bình thường tại Việt Nam. "
                "Đọc nội dung bài viết dưới đây và viết đúng 01 câu bình luận ngắn (dưới 12 từ) "
                "phù hợp cảm xúc bài viết, thân thiện, không dùng giọng văn máy móc/trịnh trọng. "
                "Nếu bài viết thể hiện sự buồn đau, tai nạn hoặc tiêu cực, hãy trả về chữ: [IGNORE]\n\n"
                f"Nội dung bài viết: \"{post_content}\""
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt
            )
            res_text = response.text.strip()
            if "[IGNORE]" in res_text:
                return ""
            return res_text
        except Exception:
            return "Bài viết hay quá bạn ơi 👍"

# ==========================================
# 3. GIAO DIỆN PHẦN MỀM (CUSTOMTKINTER)
# ==========================================
class AdvancedBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Facebook AI Human-Behavior Agent")
        self.geometry("820x600")
        self.resizable(False, False)

        self.is_running = False

        # Khung Cài đặt bên trái
        self.left_panel = ctk.CTkFrame(self, width=360, corner_radius=12)
        self.left_panel.pack(side="left", fill="y", padx=12, pady=12)

        self.title_lbl = ctk.CTkLabel(
            self.left_panel, text="CẤU HÌNH HỆ THỐNG", font=ctk.CTkFont(size=17, weight="bold")
        )
        self.title_lbl.pack(padx=15, pady=(15, 12))

        # Profile / Cookie
        self.lbl_profile = ctk.CTkLabel(self.left_panel, text="Tên Profile (cô lập dữ liệu):")
        self.lbl_profile.pack(anchor="w", padx=15, pady=(3, 0))
        self.entry_profile = ctk.CTkEntry(self.left_panel, placeholder_text="acc_vip_01")
        self.entry_profile.insert(0, "acc_vip_01")
        self.entry_profile.pack(fill="x", padx=15, pady=(0, 8))

        # API Key AI (Gemini)
        self.lbl_ai = ctk.CTkLabel(self.left_panel, text="Gemini API Key (Tự sinh comment thông minh):")
        self.lbl_ai.pack(anchor="w", padx=15, pady=(3, 0))
        self.entry_ai_key = ctk.CTkEntry(self.left_panel, placeholder_text="AIzaSy...", show="*")
        self.entry_ai_key.pack(fill="x", padx=15, pady=(0, 8))

        # Chỉ tiêu tương tác
        self.slider_likes_lbl = ctk.CTkLabel(self.left_panel, text="Số Like tối đa mỗi phiên: 5")
        self.slider_likes_lbl.pack(anchor="w", padx=15, pady=(3, 0))
        self.slider_likes = ctk.CTkSlider(self.left_panel, from_=1, to=20, number_of_steps=19, command=self.update_like_lbl)
        self.slider_likes.set(5)
        self.slider_likes.pack(fill="x", padx=15, pady=(0, 8))

        # Tùy chọn Bật/Tắt Bình luận AI
        self.switch_comment = ctk.CTkSwitch(self.left_panel, text="Tự động bình luận theo ngữ cảnh AI")
        self.switch_comment.select()
        self.switch_comment.pack(anchor="w", padx=15, pady=8)

        # Chế độ tương tác ngầm (Headless)
        self.switch_headless = ctk.CTkSwitch(self.left_panel, text="Chạy ẩn (Headless Mode)")
        self.switch_headless.pack(anchor="w", padx=15, pady=8)

        # Nút Hành động
        self.btn_run = ctk.CTkButton(
            self.left_panel, text="Bắt đầu Tương tác", height=42, command=self.toggle_task, fg_color="#107C41"
        )
        self.btn_run.pack(fill="x", padx=15, pady=(20, 10))

        # Khung Nhật ký Logs bên phải
        self.right_panel = ctk.CTkFrame(self, corner_radius=12)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)

        self.log_lbl = ctk.CTkLabel(
            self.right_panel, text="NHẬT KÝ THAO TÁC THỜI GIAN THỰC", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.log_lbl.pack(anchor="w", padx=15, pady=(15, 8))

        self.console = ctk.CTkTextbox(self.right_panel, font=("Consolas", 12))
        self.console.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def update_like_lbl(self, val):
        self.slider_likes_lbl.configure(text=f"Số Like tối đa mỗi phiên: {int(val)}")

    def log(self, text: str):
        now = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{now}] {text}\n")
        self.console.see("end")

    def toggle_task(self):
        if not self.is_running:
            self.is_running = True
            self.btn_run.configure(text="Dừng Hệ Thống", fg_color="#C42B1C")
            threading.Thread(target=self.bot_core_logic, daemon=True).start()
        else:
            self.is_running = False
            self.btn_run.configure(text="Bắt đầu Tương tác", fg_color="#107C41")
            self.log("Đang chờ dừng an toàn...")

    # ==========================================
    # 4. ENGINE TỰ ĐỘNG HÓA PLAYWRIGHT
    # ==========================================
    def bot_core_logic(self):
        profile = self.entry_profile.get().strip() or "default"
        api_key = self.entry_ai_key.get().strip()
        max_likes = int(self.slider_likes.get())
        auto_comment = self.switch_comment.get() == 1
        headless_mode = self.switch_headless.get() == 1

        profile_path = os.path.abspath(f"./profiles/{profile}")
        os.makedirs(profile_path, exist_ok=True)

        self.log(f"Nạp Profile: {profile} | Mục tiêu: {max_likes} Likes")
        self.log("Khởi động môi trường trình duyệt...")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    channel="msedge",
                    headless=headless_mode,
                    viewport={"width": 1280, "height": 800},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )

                page = context.new_page()
                self.log("Truy cập Facebook Mobile Interface (Tối ưu tốc độ & DOM)...")
                page.goto("https://m.facebook.com", timeout=60000)
                time.sleep(random.uniform(4.0, 7.0))

                likes_done = 0
                while self.is_running and likes_done < max_likes:
                    # Cuộn giả lập con người
                    self.log("Lướt Newfeed đọc tin...")
                    HumanSimulator.human_scroll(page)

                    # Trích xuất các bài post đang hiển thị trên màn hình
                    posts = page.query_selector_all('div[role="article"], article')
                    if not posts:
                        posts = page.query_selector_all('div[data-tracking-duration-id]')

                    if posts:
                        target_post = random.choice(posts)
                        
                        # 1. Đọc nội dung văn bản bài viết để phân tích
                        post_text = target_post.inner_text()
                        
                        # 2. Xử lý Thả Like có chọn lọc (Xác suất 70%)
                        if random.random() < 0.7:
                            like_btn = target_post.query_selector('div[aria-label*="Thích"], div[aria-label*="Like"]')
                            if like_btn:
                                box = like_btn.bounding_box()
                                if box:
                                    HumanSimulator.move_mouse_naturally(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                                    time.sleep(random.uniform(0.3, 0.8))
                                    like_btn.click()
                                    likes_done += 1
                                    self.log(f"-> Đã Like bài viết thành công ({likes_done}/{max_likes})")
                                    time.sleep(random.uniform(5.0, 10.0))

                        # 3. Phân tích nội dung và Bình luận bằng AI
                        if auto_comment and random.random() < 0.35: # Chỉ comment ~35% số bài để an toàn
                            self.log("Đang phân tích nội dung qua Não bộ AI...")
                            comment_text = AIEngine.generate_reply(post_text, api_key)
                            
                            if comment_text:
                                self.log(f"AI đề xuất CMT: \"{comment_text}\"")
                                comment_btn = target_post.query_selector('div[aria-label*="Bình luận"], div[aria-label*="Comment"]')
                                if comment_btn:
                                    comment_btn.click()
                                    time.sleep(random.uniform(2.0, 4.0))
                                    
                                    # Tìm ô nhập liệu
                                    input_box = page.query_selector('textarea, div[role="textbox"]')
                                    if input_box:
                                        HumanSimulator.human_type(page, 'textarea, div[role="textbox"]', comment_text)
                                        time.sleep(random.uniform(1.0, 2.5))
                                        page.keyboard.press("Enter")
                                        self.log("-> Đã gửi bình luận thông minh thành công!")
                                        time.sleep(random.uniform(8.0, 16.0)) # Giãn cách an toàn sau khi comment

                    # Thời gian nghỉ ngơi sinh học giữa các đợt xem
                    idle_time = random.uniform(6.0, 14.0)
                    self.log(f"Tạm nghỉ {int(idle_time)}s trước khi lướt tiếp...")
                    time.sleep(idle_time)

                self.log("Đã hoàn tất chỉ tiêu hoặc phiên làm việc kết thúc.")
                context.close()

        except Exception as e:
            self.log(f"Sự cố vận hành: {e}")
        finally:
            self.is_running = False
            self.btn_run.configure(text="Bắt đầu Tương tác", fg_color="#107C41")

if __name__ == "__main__":
    app = AdvancedBotApp()
    app.mainloop()
