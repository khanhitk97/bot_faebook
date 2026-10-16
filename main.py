import os
import sys
import json
import time
import random
import threading
import numpy as np
import customtkinter as ctk
from playwright.sync_api import sync_playwright

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "history.json"

# ==========================================
# 1. HỆ THỐNG MÔ PHỎNG HÀNH VI SINH HỌC
# ==========================================
class HumanSimulator:
    @staticmethod
    def bezier_curve(p0, p1, p2, p3, num_points=25):
        """Tạo đường cong Bezier bậc 3 mô phỏng quỹ đạo tự nhiên của tay người"""
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
        """Di chuyển trỏ chuột theo đường cong có gia tốc mềm mại"""
        start_x = random.randint(150, 450)
        start_y = random.randint(150, 450)

        ctrl_x1 = start_x + (target_x - start_x) * random.uniform(0.1, 0.4) + random.randint(-40, 40)
        ctrl_y1 = start_y + (target_y - start_y) * random.uniform(0.1, 0.4) + random.randint(-40, 40)
        ctrl_x2 = start_x + (target_x - start_x) * random.uniform(0.6, 0.9) + random.randint(-40, 40)
        ctrl_y2 = start_y + (target_y - start_y) * random.uniform(0.6, 0.9) + random.randint(-40, 40)

        curve_x = cls.bezier_curve(start_x, ctrl_x1, ctrl_x2, target_x)
        curve_y = cls.bezier_curve(start_y, ctrl_y1, ctrl_y2, target_y)

        for x, y in zip(curve_x, curve_y):
            page.mouse.move(float(x), float(y))
            time.sleep(random.uniform(0.005, 0.012))

    @staticmethod
    def human_type(page, text: str):
        """Gõ chữ mô phỏng nhịp người thật: có độ trễ phím và thỉnh thoảng gõ nhầm"""
        for char in text:
            if random.random() < 0.03 and char.isalpha():
                typo = chr(ord(char) + 1)
                page.keyboard.type(typo, delay=random.randint(70, 140))
                time.sleep(random.uniform(0.2, 0.35))
                page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.1, 0.25))

            page.keyboard.type(char, delay=random.randint(60, 160))
            if char in [",", ".", " ", "!"]:
                time.sleep(random.uniform(0.2, 0.45))

    @staticmethod
    def human_scroll(page):
        """Cuộn trang vi phân có quán tính, ngẫu nhiên cuộn ngược lên lại"""
        scroll_steps = random.randint(4, 7)
        direction = 1 if random.random() > 0.15 else -1
        distance = random.randint(350, 650) * direction

        for _ in range(scroll_steps):
            step = distance / scroll_steps
            page.mouse.wheel(0, step)
            time.sleep(random.uniform(0.05, 0.12))
        time.sleep(random.uniform(1.5, 3.2))

# ==========================================
# 2. XỬ LÝ TRÍ TUỆ NHÂN TẠO (GEMINI)
# ==========================================
class AIEngine:
    @staticmethod
    def analyze_and_react(post_content: str, api_key: str = None) -> tuple:
        """Đọc nội dung bài viết và phân loại cảm xúc + sinh nội dung bình luận ngắn"""
        if not post_content or len(post_content.strip()) < 10:
            return ("LIKE", "")

        if not api_key:
            return (random.choice(["LIKE", "LOVE", "CARE"]), "Bài viết rất hay và ý nghĩa ạ 👍")

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                "Bạn là chính chủ Facebook cá nhân tại Việt Nam. Đọc bài viết sau:\n"
                f"\"{post_content[:400]}\"\n\n"
                "Nhiệm vụ:\n"
                "1. Chọn 1 cảm xúc phù hợp nhất: LIKE, LOVE, CARE, HAHA, WOW, SAD.\n"
                "2. Viết 1 bình luận ngắn (dưới 10 từ) tự nhiên, lịch sự như bạn bè thân quen.\n"
                "3. NẾU bài viết tiêu cực, tang lễ, tai nạn, chửi bới, bán hàng spam thì bình luận trả về: [SKIP]\n"
                "Định dạng trả về đúng 2 dòng:\n"
                "REACTION: <tên_cảm_xúc>\n"
                "COMMENT: <nội_dung>"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            lines = [l.strip() for l in response.text.split("\n") if l.strip()]
            reaction = "LIKE"
            comment = ""
            for l in lines:
                if l.startswith("REACTION:"):
                    reaction = l.replace("REACTION:", "").strip().upper()
                elif l.startswith("COMMENT:"):
                    comment = l.replace("COMMENT:", "").strip()

            if "[SKIP]" in comment:
                comment = ""
            return (reaction, comment)
        except Exception:
            return ("LIKE", "Bài viết rất ý nghĩa ạ!")

# ==========================================
# 3. GIAO DIỆN PHẦN MỀM (CUSTOMTKINTER)
# ==========================================
class ProBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Facebook AI Smart Assistant - Personal Edition")
        self.geometry("900x720")
        self.resizable(False, False)

        self.is_running = False
        self.history = self.load_history()

        self.left_panel = ctk.CTkScrollableFrame(self, width=400, corner_radius=12)
        self.left_panel.pack(side="left", fill="both", padx=12, pady=12)

        self.right_panel = ctk.CTkFrame(self, corner_radius=12)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)

        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        ctk.CTkLabel(
            self.left_panel, text="CẤU HÌNH TƯƠNG TÁC", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 15))

        ctk.CTkLabel(self.left_panel, text="Tên Profile (Lưu cookie/session):").pack(anchor="w", padx=10)
        self.entry_profile = ctk.CTkEntry(self.left_panel, placeholder_text="my_main_account")
        self.entry_profile.insert(0, "my_main_account")
        self.entry_profile.pack(fill="x", padx=10, pady=(2, 10))

        ctk.CTkLabel(self.left_panel, text="Gemini API Key (Tạo bình luận AI):").pack(anchor="w", padx=10)
        self.entry_key = ctk.CTkEntry(self.left_panel, placeholder_text="AIzaSy...", show="*")
        self.entry_key.pack(fill="x", padx=10, pady=(2, 12))

        self.lbl_likes = ctk.CTkLabel(self.left_panel, text="Giới hạn tương tác: 5 bài / phiên")
        self.lbl_likes.pack(anchor="w", padx=10)
        self.slider_likes = ctk.CTkSlider(self.left_panel, from_=1, to=15, number_of_steps=14, command=self.update_slider_label)
        self.slider_likes.set(5)
        self.slider_likes.pack(fill="x", padx=10, pady=(2, 15))

        ctk.CTkLabel(self.left_panel, text="CHẾ ĐỘ TÙY CHỌN", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(5, 5))

        self.sw_friends = ctk.CTkSwitch(self.left_panel, text="Ưu tiên bảng tin Bạn bè (Friends Feed)")
        self.sw_friends.select()
        self.sw_friends.pack(anchor="w", padx=10, pady=5)

        self.sw_smart_react = ctk.CTkSwitch(self.left_panel, text="Thả cảm xúc thông minh (Love, Care, Haha...)")
        self.sw_smart_react.select()
        self.sw_smart_react.pack(anchor="w", padx=10, pady=5)

        self.sw_comment = ctk.CTkSwitch(self.left_panel, text="Tự động Bình luận bằng AI")
        self.sw_comment.select()
        self.sw_comment.pack(anchor="w", padx=10, pady=5)

        self.sw_dwell = ctk.CTkSwitch(self.left_panel, text="Đọc bài theo độ dài chữ (Dwell Time)")
        self.sw_dwell.select()
        self.sw_dwell.pack(anchor="w", padx=10, pady=5)

        self.sw_filter = ctk.CTkSwitch(self.left_panel, text="Chặn bài Quảng cáo & bài spam")
        self.sw_filter.select()
        self.sw_filter.pack(anchor="w", padx=10, pady=5)

        self.sw_history = ctk.CTkSwitch(self.left_panel, text="Lưu lịch sử bài đã tương tác")
        self.sw_history.select()
        self.sw_history.pack(anchor="w", padx=10, pady=5)

        self.btn_run = ctk.CTkButton(
            self.left_panel, text="Bắt đầu Tương tác", height=42, command=self.toggle_task, fg_color="#107C41"
        )
        self.btn_run.pack(fill="x", padx=10, pady=(20, 15))

    def setup_right_panel(self):
        ctk.CTkLabel(
            self.right_panel, text="NHẬT KÝ THAO TÁC THỜI GIAN THỰC", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 8))
        self.console = ctk.CTkTextbox(self.right_panel, font=("Consolas", 12))
        self.console.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def update_slider_label(self, val):
        self.lbl_likes.configure(text=f"Giới hạn tương tác: {int(val)} bài / phiên")

    def log(self, text: str):
        now = time.strftime("%H:%M:%S")
        self.console.insert("end", f"[{now}] {text}\n")
        self.console.see("end")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_history(self, post_sig, reaction, comment):
        self.history[post_sig] = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "reaction": reaction,
            "comment": comment
        }
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def toggle_task(self):
        if not self.is_running:
            self.is_running = True
            self.btn_run.configure(text="Dừng Hệ Thống", fg_color="#C42B1C")
            threading.Thread(target=self.bot_core, daemon=True).start()
        else:
            self.is_running = False
            self.btn_run.configure(text="Bắt đầu Tương tác", fg_color="#107C41")
            self.log("Đang gửi yêu cầu dừng an toàn...")

    # ==========================================
    # 4. ENGINE TỰ ĐỘNG HÓA VẬN HÀNH
    # ==========================================
    def bot_core(self):
        profile = self.entry_profile.get().strip() or "my_main_account"
        api_key = self.entry_key.get().strip()
        max_targets = int(self.slider_likes.get())

        cfg_friends = self.sw_friends.get() == 1
        cfg_smart_react = self.sw_smart_react.get() == 1
        cfg_comment = self.sw_comment.get() == 1
        cfg_dwell = self.sw_dwell.get() == 1
        cfg_filter = self.sw_filter.get() == 1
        cfg_history = self.sw_history.get() == 1

        profile_dir = os.path.abspath(f"./profiles/{profile}")
        os.makedirs(profile_dir, exist_ok=True)

        self.log(f"Khởi động profile: {profile} | Mục tiêu: {max_targets} bài")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="msedge",
                    headless=False,
                    viewport={"width": 1280, "height": 850},
                    args=["--disable-blink-features=AutomationControlled"]
                )

                page = context.new_page()

                target_url = "https://www.facebook.com/?filter=friends&sk=h_chr" if cfg_friends else "https://www.facebook.com/"
                self.log(f"Đang điều hướng đến: {target_url}")
                page.goto(target_url, timeout=60000)
                time.sleep(random.uniform(4.0, 6.0))

                completed = 0

                while self.is_running and completed < max_targets:
                    HumanSimulator.human_scroll(page)

                    articles = page.query_selector_all('div[role="feed"] div[role="article"], div[role="article"]')
                    if not articles:
                        time.sleep(2.5)
                        continue

                    target_post = None
                    post_text = ""
                    post_sig = ""

                    for art in articles:
                        raw_text = art.inner_text().strip()
                        if len(raw_text) < 25:
                            continue

                        sig = raw_text[:60].replace("\n", " ")
                        if cfg_history and sig in self.history:
                            continue

                        if cfg_filter:
                            if "Được tài trợ" in raw_text or "Sponsored" in raw_text:
                                continue
                            if "Gợi ý cho bạn" in raw_text or "Suggested for you" in raw_text:
                                continue

                        target_post = art
                        post_text = raw_text
                        post_sig = sig
                        break

                    if not target_post:
                        self.log("Đang cuộn tìm bài viết chưa tương tác...")
                        continue

                    target_post.scroll_into_view_if_needed()
                    time.sleep(random.uniform(1.0, 2.0))

                    # 1. Đọc bài viết (Dwell Time)
                    if cfg_dwell:
                        words = len(post_text.split())
                        read_time = min(max(words / 4.0, 3.5), 10.0)
                        self.log(f"Đang dừng đọc nội dung bài viết ({int(read_time)}s)...")
                        time.sleep(read_time)

                    # 2. Ph
