import os
import re
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
# 1. BỘ MÔ PHỎNG HÀNH VI SINH HỌC
# ==========================================
class HumanSimulator:
    @staticmethod
    def bezier_curve(p0, p1, p2, p3, num_points=20):
        t = np.linspace(0, 1, num_points)
        return (
            (1 - t) ** 3 * p0
            + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2
            + t ** 3 * p3
        )

    @classmethod
    def move_mouse_naturally(cls, page, target_x, target_y):
        try:
            start_x = random.randint(100, 300)
            start_y = random.randint(150, 400)

            ctrl_x1 = start_x + (target_x - start_x) * random.uniform(0.2, 0.4)
            ctrl_y1 = start_y + (target_y - start_y) * random.uniform(0.1, 0.3)
            ctrl_x2 = start_x + (target_x - start_x) * random.uniform(0.6, 0.8)
            ctrl_y2 = start_y + (target_y - start_y) * random.uniform(0.7, 0.9)

            curve_x = cls.bezier_curve(start_x, ctrl_x1, ctrl_x2, target_x)
            curve_y = cls.bezier_curve(start_y, ctrl_y1, ctrl_y2, target_y)

            for x, y in zip(curve_x, curve_y):
                page.mouse.move(float(x), float(y))
                time.sleep(0.008)
        except Exception:
            page.mouse.move(target_x, target_y)

    @classmethod
    def simulate_reading(cls, page, container_elem, text: str, log_callback):
        """Giả vờ đọc bài viết: tính thời gian theo độ dài và di chuyển chuột nhẹ rà soát nội dung"""
        words = len(text.split())
        # Thời gian đọc trung bình từ 3.5 đến 8.0 giây
        read_time = min(max(words / 4.0, 3.5), 8.0)
        log_callback(f"Đang dừng lại đọc bài viết ({int(read_time)}s)...")

        # Thử bấm 'Xem thêm' nếu bài dài có nút rút gọn
        try:
            see_more = container_elem.locator(
                'div[role="button"]:has-text("Xem thêm"), div[role="button"]:has-text("See more"), '
                'span:has-text("Xem thêm"), span:has-text("See more")'
            ).first
            if see_more.is_visible(timeout=500):
                see_more.click()
                time.sleep(random.uniform(0.8, 1.5))
        except Exception:
            pass

        # Chia nhỏ thời gian đọc để rà chuột nhẹ
        box = container_elem.bounding_box()
        start_time = time.time()
        while time.time() - start_time < read_time:
            if box:
                # Di chuột quanh vùng thân bài viết
                rand_x = box["x"] + random.uniform(box["width"] * 0.2, box["width"] * 0.8)
                rand_y = box["y"] + random.uniform(box["height"] * 0.2, box["height"] * 0.6)
                cls.move_mouse_naturally(page, rand_x, rand_y)
            time.sleep(random.uniform(1.2, 2.0))

    @staticmethod
    def human_type(page, target_locator, text: str):
        target_locator.focus()
        time.sleep(0.3)
        for char in text:
            target_locator.press_sequentially(char, delay=random.randint(60, 140))
            if char in [",", ".", " ", "!"]:
                time.sleep(random.uniform(0.15, 0.35))

    @staticmethod
    def human_scroll(page):
        scroll_distance = random.randint(380, 680)
        page.mouse.wheel(0, scroll_distance)
        time.sleep(random.uniform(2.0, 3.2))

# ==========================================
# 2. XỬ LÝ TRÍ TUỆ NHÂN TẠO (GEMINI)
# ==========================================
class AIEngine:
    @staticmethod
    def analyze_and_react(post_content: str, api_key: str = None) -> tuple:
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
                "1. Chọn 1 cảm xúc phù hợp: LIKE, LOVE, CARE, HAHA, WOW, SAD.\n"
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

        self.title("Facebook AI Smart Assistant - Mobile Engine")
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
        ctk.CTkLabel(self.left_panel, text="CẤU HÌNH TƯƠNG TÁC (MOBILE)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10, 15))

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

        self.sw_smart_react = ctk.CTkSwitch(self.left_panel, text="Thả cảm xúc thông minh (Love, Care, Haha...)")
        self.sw_smart_react.select()
        self.sw_smart_react.pack(anchor="w", padx=10, pady=5)

        self.sw_comment = ctk.CTkSwitch(self.left_panel, text="Tự động Bình luận bằng AI")
        self.sw_comment.select()
        self.sw_comment.pack(anchor="w", padx=10, pady=5)

        self.sw_filter = ctk.CTkSwitch(self.left_panel, text="Chặn bài Quảng cáo & bài spam")
        self.sw_filter.select()
        self.sw_filter.pack(anchor="w", padx=10, pady=5)

        self.sw_history = ctk.CTkSwitch(self.left_panel, text="Lưu lịch sử bài đã tương tác (Chống trùng)")
        self.sw_history.select()
        self.sw_history.pack(anchor="w", padx=10, pady=5)

        self.btn_run = ctk.CTkButton(self.left_panel, text="Bắt đầu Tương tác", height=42, command=self.toggle_task, fg_color="#107C41")
        self.btn_run.pack(fill="x", padx=10, pady=(20, 15))

    def setup_right_panel(self):
        ctk.CTkLabel(self.right_panel, text="NHẬT KÝ THAO TÁC THỜI GIAN THỰC", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 8))
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
            self.log("Đang dừng tác vụ...")

    # ==========================================
    # 4. ENGINE TỰ ĐỘNG HÓA VẬN HÀNH
    # ==========================================
    def bot_core(self):
        profile = self.entry_profile.get().strip() or "my_main_account"
        api_key = self.entry_key.get().strip()
        max_targets = int(self.slider_likes.get())

        cfg_smart_react = self.sw_smart_react.get() == 1
        cfg_comment = self.sw_comment.get() == 1
        cfg_filter = self.sw_filter.get() == 1
        cfg_history = self.sw_history.get() == 1

        profile_dir = os.path.abspath(f"./profiles/{profile}")
        os.makedirs(profile_dir, exist_ok=True)

        self.log(f"Khởi động profile: {profile} trên m.facebook.com")
        self.log(f"Mục tiêu: {max_targets} bài viết.")

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=profile_dir,
                    channel="msedge",
                    headless=False,
                    viewport={"width": 450, "height": 850},
                    user_agent="Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
                    args=["--disable-blink-features=AutomationControlled"]
                )

                page = context.new_page()
                self.log("Đang mở m.facebook.com...")
                page.goto("https://m.facebook.com/", timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)

                completed = 0

                while self.is_running and completed < max_targets:
                    # Đóng pop-up thông báo nếu có
                    try:
                        close_btn = page.locator('div[aria-label*="Đóng"], div[aria-label*="Close"], div[data-sigil="m-overlay-close"]').first
                        if close_btn.is_visible(timeout=300):
                            close_btn.click()
                    except Exception:
                        pass

                    HumanSimulator.human_scroll(page)

                    # Quét tìm các nút Like khả dụng
                    like_locators = page.locator(
                        'div[role="button"][aria-label*="Thích"], div[role="button"][aria-label*="Like"], '
                        'a[role="button"][aria-label*="Thích"], a[role="button"][aria-label*="Like"], '
                        'div[data-sigil="touchable reactions-like-button"], '
                        'div[role="button"]:has-text("Thích"), div[role="button"]:has-text("Like")'
                    ).all()

                    if not like_locators:
                        self.log("Đang cuộn tìm nội dung trên bảng tin...")
                        time.sleep(2)
                        continue

                    chosen_like_btn = None
                    container_elem = None
                    post_text = ""
                    post_sig = ""

                    for btn in like_locators:
                        try:
                            if not btn.is_visible():
                                continue

                            # Bỏ qua nếu đã Like rồi
                            is_pressed = btn.get_attribute("aria-pressed")
                            aria_label = btn.get_attribute("aria-label") or ""
                            if is_pressed == "true" or any(w in aria_label.lower() for w in ["gỡ", "unlike", "bỏ thích", "đã thích"]):
                                continue

                            # Tìm ngược lên khối chứa bài viết
                            parent = btn.locator('xpath=ancestor::div[string-length(normalize-space(.)) > 50][position() <= 4]').first
                            if not parent.is_visible(timeout=400):
                                parent = btn.locator('xpath=../..')

                            raw_text = parent.inner_text().strip()
                            if len(raw_text) < 15:
                                continue

                            clean_text = "".join(raw_text.split())[:70]
                            sig = f"sig_{abs(hash(clean_text))}"

                            if cfg_history and sig in self.history:
                                continue

                            if cfg_filter:
                                if any(kw in raw_text for kw in ["Được tài trợ", "Sponsored", "Gợi ý cho bạn", "Suggested for you"]):
                                    continue

                            chosen_like_btn = btn
                            container_elem = parent
                            post_text = raw_text
                            post_sig = sig
                            break
                        except Exception:
                            continue

                    if not chosen_like_btn or not container_elem:
                        self.log("Đang cuộn tìm bài viết chưa tương tác...")
                        continue

                    # Cuộn bài viết vào giữa màn hình
                    try:
                        chosen_like_btn.scroll_into_view_if_needed(timeout=3000)
                    except Exception:
                        pass
                    time.sleep(1.0)

                    # 1. KỊCH BẢN GIẢ VỜ ĐỌC BÀI VIẾT
                    HumanSimulator.simulate_reading(page, container_elem, post_text, self.log)

                    # 2. PHÂN TÍCH NỘI DUNG QUA AI
                    reaction_type = "LOVE"
                    comment_text = ""
                    if cfg_smart_react or cfg_comment:
                        self.log("AI đang phân tích cảm xúc và nội dung...")
                        reaction_type, comment_text = AIEngine.analyze_and_react(post_text, api_key)

                    # 3. THAO TÁC THẢ CẢM XÚC / LIKE
                    reacted = False
                    box = chosen_like_btn.bounding_box()
                    if box:
                        btn_x = box["x"] + box["width"] / 2
                        btn_y = box["y"] + box["height"] / 2
                        HumanSimulator.move_mouse_naturally(page, btn_x, btn_y)

                        if cfg_smart_react and reaction_type != "LIKE":
                            try:
                                # Nhấn giữ chuột để kích hoạt dock cảm xúc
                                page.mouse.move(btn_x, btn_y)
                                page.mouse.down()
                                time.sleep(1.2)
                                page.mouse.up()
                                time.sleep(0.8)

                                react_map = {
                                    "LOVE": ['div[aria-label*="Yêu thích"]', 'div[aria-label*="Love"]', 'span[aria-label*="Love"]'],
                                    "CARE": ['div[aria-label*="Thương thương"]', 'div[aria-label*="Care"]', 'span[aria-label*="Care"]'],
                                    "HAHA": ['div[aria-label*="Haha"]', 'span[aria-label*="Haha"]'],
                                    "WOW":  ['div[aria-label*="Wow"]', 'span[aria-label*="Wow"]'],
                                    "SAD":  ['div[aria-label*="Buồn"]', 'div[aria-label*="Sad"]', 'span[aria-label*="Sad"]']
                                }
                                for sel in react_map.get(reaction_type, react_map["LOVE"]):
                                    icon = page.locator(sel).first
                                    if icon.is_visible(timeout=800):
                                        icon.click(timeout=1000)
                                        reacted = True
                                        self.log(f"-> Đã thả biểu cảm [{reaction_type}] cho bài viết!")
                                        break
                            except Exception:
                                pass

                        if not reacted:
                            chosen_like_btn.click()
                            reacted = True
                            self.log("-> Đã Thích bài viết thành công!")

                    # 4. THAO TÁC BÌNH LUẬN
                    if cfg_comment and comment_text and reacted:
                        self.log(f"Chuẩn bị bình luận: \"{comment_text}\"")

                        cmt_btn = chosen_like_btn.locator('xpath=following-sibling::*[1]//div[@role="button"], xpath=following-sibling::div[@role="button"]').first
                        if not cmt_btn.is_visible(timeout=500):
                            cmt_btn = page.locator('div[role="button"][aria-label*="Bình luận"], div[role="button"][aria-label*="Comment"]').first

                        if cmt_btn.is_visible(timeout=1000):
                            cmt_btn.click()
                            time.sleep(1.5)

                        input_box = page.locator('textarea, div[role="textbox"][contenteditable="true"]').first
                        if input_box.is_visible(timeout=2000):
                            try:
                                input_box.scroll_into_view_if_needed()
                                input_box.click()
                                time.sleep(0.5)

                                HumanSimulator.human_type(page, input_box, comment_text)
                                time.sleep(1.0)

                                submit_btn = page.locator('div[aria-label*="Đăng"], div[aria-label*="Post"], button:has-text("Đăng"), button:has-text("Post")').first
                                if submit_btn.is_visible(timeout=1000):
                                    submit_btn.click()
                                else:
                                    page.keyboard.press("Enter")

                                self.log(f"-> Đã gửi bình luận: \"{comment_text}\"")
                                time.sleep(random.uniform(5.0, 8.0))
                            except Exception as ex:
                                self.log(f"Lỗi khi gửi bình luận: {ex}")
                        else:
                            self.log("Không thấy ô nhập bình luận, bỏ qua phần comment.")

                    if reacted:
                        completed += 1
                        if cfg_history:
                            self.save_history(post_sig, reaction_type, comment_text)

                        sleep_gap = random.uniform(15.0, 30.0)
                        self.log(f"Tiến độ ({completed}/{max_targets}). Nghỉ an toàn {int(sleep_gap)}s...")
                        time.sleep(sleep_gap)

                self.log("Đã hoàn tất phiên tương tác thành công!")
                context.close()

        except Exception as e:
            self.log(f"Lỗi vận hành: {e}")
        finally:
            self.is_running = False
            self.btn_run.configure(text="Bắt đầu Tương tác", fg_color="#107C41")

if __name__ == "__main__":
    app = ProBotApp()
    app.mainloop()
