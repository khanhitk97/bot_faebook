import os
import sys
import json
import time
import math
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
        t = np.linspace(0, 1, num_points)
        return (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2
            + t ** 3 * p3
        )

    @classmethod
    def move_mouse_naturally(cls, page, target_x, target_y):
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
    def human_type(page, selector, text):
        elem = page.locator(selector).first
        elem.click()
        time.sleep(random.uniform(0.3, 0.6))

        for char in text:
            if random.random() < 0.03 and char.isalpha():
                typo_char = chr(ord(char) + 1)
                elem.press_sequentially(typo_char, delay=random.randint(80, 150))
                time.sleep(random.uniform(0.2, 0.4))
                elem.press("Backspace")
                time.sleep(random.uniform(0.15, 0.3))

            elem.press_sequentially(char, delay=random.randint(60, 180))
            if char in [",", ".", " ", "!"]:
                time.sleep(random.uniform(0.2, 0.45))

    @staticmethod
    def human_scroll(page):
        scroll_steps = random.randint(4, 7)
        direction = 1 if random.random() > 0.15 else -1
        distance = random.randint(350, 650) * direction

        for _ in range(scroll_steps):
            step = distance / scroll_steps
            page.mouse.wheel(0, step)
            time.sleep(random.uniform(0.05, 0.12))
        time.sleep(random.uniform(1.5, 3.5))

# ==========================================
# 2. XỬ LÝ TRÍ TUỆ NHÂN TẠO (GEMINI)
# ==========================================
class AIEngine:
    @staticmethod
    def analyze_and_react(post_content: str, api_key: str = None) -> tuple:
        """Phân tích nội dung và trả về (loại cảm xúc, nội dung bình luận)"""
        if not post_content or len(post_content.strip()) < 10:
            return ("LIKE", "")

        if not api_key:
            return (random.choice(["LIKE", "LOVE", "CARE"]), "Bài viết hay quá bạn ơi 👍")

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                "Bạn là chính chủ Facebook cá nhân tại Việt Nam. Đọc bài viết sau đây:\n"
                f"\"{post_content[:350]}\"\n\n"
                "Nhiệm vụ:\n"
                "1. Chọn 1 cảm xúc phù hợp nhất: LIKE, LOVE, CARE, HAHA, WOW, SAD.\n"
                "2. Viết 1 bình luận ngắn gọn (dưới 10 từ) tự nhiên, lịch sự như bạn bè thân quen.\n"
                "3. NẾU bài viết tiêu cực, tai nạn, tang lễ, bán hàng spam thì bình luận trả về: [SKIP]\n"
                "Trả về định dạng duy nhất gồm 2 dòng:\n"
                "REACTION: <tên_cảm_xúc>\n"
                "COMMENT: <nội_dung_bình_luận>"
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
            return ("LIKE", "Bài viết rất hay và ý nghĩa!")

# ==========================================
# 3. GIAO DIỆN CHÍNH & QUẢN LÝ TÙY CHỌN
# ==========================================
class ProBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Facebook Smart Assistant - Personal Account Edition")
        self.geometry("900x700")
        self.resizable(False, False)

        self.is_running = False
        self.history = self.load_history()

        # Layout chính: 2 cột
        self.left_panel = ctk.CTkScrollableFrame(self, width=400, corner_radius=12)
        self.left_panel.pack(side="left", fill="both", padx=12, pady=12)

        self.right_panel = ctk.CTkFrame(self, corner_radius=12)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)

        self.setup_left_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        title = ctk.CTkLabel(self.left_panel, text="CẤU HÌNH TƯƠNG TÁC", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(anchor="w", padx=10, pady=(10, 15))

        # Tên Profile
        ctk.CTkLabel(self.left_panel, text="Profile cá nhân:").pack(anchor="w", padx=10)
        self.entry_profile = ctk.CTkEntry(self.left_panel, placeholder_text="my_main_account")
        self.entry_profile.insert(0, "my_main_account")
        self.entry_profile.pack(fill="x", padx=10, pady=(2, 10))

        # API Key
        ctk.CTkLabel(self.left_panel, text="Gemini API Key:").pack(anchor="w", padx=10)
        self.entry_key = ctk.CTkEntry(self.left_panel, placeholder_text="AIzaSy...", show="*")
        self.entry_key.pack(fill="x", padx=10, pady=(2, 12))

        # Giới hạn Like
        self.lbl_likes = ctk.CTkLabel(self.left_panel, text="Giới hạn tương tác: 5 bài / phiên")
        self.lbl_likes.pack(anchor="w", padx=10)
        self.slider_likes = ctk.CTkSlider(self.left_panel, from_=1, to=15, number_of_steps=14, command=self.update_slider_label)
        self.slider_likes.set(5)
        self.slider_likes.pack(fill="x", padx=10, pady=(2, 15))

        # --- CÁC CÔNG TẮC BẬT TẮT CHẾ ĐỘ ---
        modes_title = ctk.CTkLabel(self.left_panel, text="CHẾ ĐỘ HOẠT ĐỘNG", font=ctk.CTkFont(size=14, weight="bold"))
