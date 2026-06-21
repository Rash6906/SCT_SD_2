# GuessMaster Pro — Fully updated single-file script
# Requires: customtkinter
# Save this file as guessmaster_pro.py and run with Python 3.8+

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, filedialog
import random, json, os, time, platform, math
from datetime import datetime

# Optional winsound for Windows
try:
    if platform.system() == "Windows":
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None

# ------------------------
# Config
# ------------------------
APP_W, APP_H = 1280, 800
SAVE_FILE = "gmpro_save.json"
PAD = 12
INNER_PAD = 10
MOBILE_BREAKPOINT = 900  # px: collapse sidebar when window width < this

NEON = {"BG": "#0B0B15", "PANEL": "#141423", "ACCENT1": "#FF4DFF", "ACCENT2": "#00D4FF", "TEXT": "#E6F0FF", "WARN": "#FFB86B", "ERROR": "#FF6B6B", "SUCCESS": "#00FF88"}
GLASS_ROSE = {"BG": "#0F0B10", "PANEL": "#1A0F14", "ACCENT1": "#FF6FA3", "ACCENT2": "#FFD36F", "TEXT": "#FFF7F9", "WARN": "#FFB86B", "ERROR": "#FF6B6B", "SUCCESS": "#00FF88"}
BLACK_GOLD = {"BG": "#070607", "PANEL": "#0F0F0F", "ACCENT1": "#D4AF37", "ACCENT2": "#B8860B", "TEXT": "#FFF9E6", "WARN": "#FFB86B", "ERROR": "#FF6B6B", "SUCCESS": "#00FF88"}
THEMES = {"Neon": NEON, "GlassRose": GLASS_ROSE, "BlackGold": BLACK_GOLD}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ------------------------
# Helpers
# ------------------------
def now_ts(): return int(time.time())
def today_str(): return datetime.utcnow().strftime("%Y-%m-%d")
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default
def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Save error:", e)
def hex_to_rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgb_to_hex(rgb): return "#{:02x}{:02x}{:02x}".format(*[max(0,min(255,int(v))) for v in rgb])
def brighten(hex_color, factor=1.25):
    try:
        r,g,b = hex_to_rgb(hex_color); r=min(255,int(r*factor)); g=min(255,int(g*factor)); b=min(255,int(b*factor)); return rgb_to_hex((r,g,b))
    except:
        return hex_color

# ------------------------
# Profile model
# ------------------------
class Profile:
    def __init__(self, pid, name="Player", avatar="🙂"):
        self.id = pid
        self.name = name
        self.avatar = avatar
        self.xp = 0
        self.level = 1
        self.coins = 200
        self.streak = 0
        self.best_streak = 0
        self.history = []
        self.badges = []
        self.progression = {"skill_points":0, "unlocked":[]}
        self.last_daily = None
        self.pity = 0
    def to_dict(self):
        return {"id":self.id,"name":self.name,"avatar":self.avatar,"xp":self.xp,"level":self.level,"coins":self.coins,
                "streak":self.streak,"best_streak":self.best_streak,"history":self.history[-500:],"badges":self.badges,
                "progression":self.progression,"last_daily":self.last_daily,"pity":self.pity}
    @staticmethod
    def from_dict(d):
        p = Profile(d.get("id",f"profile_{random.randint(1000,9999)}"), d.get("name","Player"), d.get("avatar","🙂"))
        p.xp = d.get("xp",0); p.level = d.get("level",1); p.coins = d.get("coins",200)
        p.streak = d.get("streak",0); p.best_streak = d.get("best_streak",0); p.history = d.get("history",[])
        p.badges = d.get("badges",[]); p.progression = d.get("progression",{"skill_points":0,"unlocked":[]})
        p.last_daily = d.get("last_daily"); p.pity = d.get("pity",0)
        return p

# ------------------------
# Main App
# ------------------------
class GuessMasterPro:
    def __init__(self, root):
        self.root = root
        self.root.title("GuessMaster Pro - Ultimate Edition")
        self.root.geometry(f"{APP_W}x{APP_H}")
        self.root.minsize(900,650)

        # runtime toggles
        self.particles_enabled = True
        self.sound_enabled = True if winsound else False

        # load save
        default_save = {"profiles":{}, "active_profile":None, "missions":None, "achievements":{}, "leaderboard":[], "matches":[], "settings":{"theme":"Neon","default_difficulty":"Normal","particles":True,"sound":True}}
        self.save_data = load_json(SAVE_FILE, default_save)
        self.theme_name = self.save_data.get("settings",{}).get("theme","Neon")
        self.theme = THEMES.get(self.theme_name, NEON)
        self.particles_enabled = self.save_data.get("settings",{}).get("particles", True)
        self.sound_enabled = self.save_data.get("settings",{}).get("sound", True)

        # profiles
        self.profiles = {}
        for pid,pd in self.save_data.get("profiles",{}).items():
            self.profiles[pid] = Profile.from_dict(pd)
        if not self.profiles:
            p = Profile("profile_1001","Player1"); self.profiles[p.id]=p
        self.active_profile_id = self.save_data.get("active_profile") or next(iter(self.profiles.keys()))
        self.active_profile = self.profiles[self.active_profile_id]

        # gameplay
        self.mode = "Single"
        self.difficulty = self.save_data.get("settings",{}).get("default_difficulty","Normal")
        self.reset_state(new_secret=True, preserve_streak=True)

        # missions & achievements
        self.missions = self.save_data.get("missions") or self._generate_daily_missions()
        self.achievements = self.save_data.get("achievements",{})

        # UI state
        self.sidebar_visible = True
        self.is_mobile = False

        # Build UI
        self._build_layout()

        # title glow
        self._title_glow_animating = True
        self._title_glow_phase = 0
        self._title_glow_step()

        # bind resize for responsive behavior
        self.root.bind("<Configure>", self._on_root_resize)

        # refresh
        self._refresh_all()

    # ------------------------
    # Persistence
    # ------------------------
    def _save(self):
        data = {"profiles":{pid:p.to_dict() for pid,p in self.profiles.items()},
                "active_profile":self.active_profile_id,
                "missions":self.missions,
                "achievements":self.achievements,
                "leaderboard":self.save_data.get("leaderboard",[]),
                "matches":self.save_data.get("matches",[]),
                "settings":{"theme":self.theme_name,"default_difficulty":self.difficulty,"particles":self.particles_enabled,"sound":self.sound_enabled}}
        save_json(SAVE_FILE,data)

    # ------------------------
    # State
    # ------------------------
    def reset_state(self,new_secret=True,preserve_streak=False):
        if self.difficulty=="Easy":
            self.lives=7; self.max_value=50
        elif self.difficulty=="Hard":
            self.lives=3; self.max_value=200
        else:
            self.lives=5; self.max_value=100
        if new_secret:
            self.secret = random.randint(1,self.max_value)
        if not preserve_streak:
            self.active_profile.streak = 0
        self.ai_low = 1; self.ai_high = self.max_value

    # ------------------------
    # Layout
    # ------------------------
    def _build_layout(self):
        # root grid: left sidebar fixed, right main expands
        for i in range(2):
            self.root.grid_rowconfigure(i, weight=1)
        self.root.grid_columnconfigure(0, weight=0, minsize=320)
        self.root.grid_columnconfigure(1, weight=1)

        # Sidebar frame
        self.sidebar = ctk.CTkFrame(self.root, fg_color=self.theme["PANEL"], corner_radius=12)
        self.sidebar.grid(row=0, column=0, sticky="nswe", padx=PAD, pady=PAD)
        self._build_sidebar_content()

        # Main frame (tabs)
        self.main = ctk.CTkFrame(self.root, fg_color=self.theme["PANEL"], corner_radius=12)
        self.main.grid(row=0, column=1, sticky="nsew", padx=PAD, pady=PAD)
        self._build_main_tabs()

        # Top compact menu (hidden by default) for mobile mode
        self.top_menu = ctk.CTkFrame(self.root, fg_color=self.theme["PANEL"], corner_radius=8)

    # ------------------------
    # Sidebar content
    # ------------------------
    def _build_sidebar_content(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        inner = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=INNER_PAD, pady=INNER_PAD)

        ctk.CTkLabel(inner, text="Profiles", font=("Segoe UI",14,"bold"), text_color=self.theme["ACCENT1"]).grid(row=0, column=0, sticky="w", pady=(6,4))
        self.profile_listbox = tk.Listbox(inner, bg=self.theme["PANEL"], fg=self.theme["TEXT"], bd=0, highlightthickness=0, selectbackground=brighten(self.theme["PANEL"],1.1), height=6)
        self.profile_listbox.grid(row=1, column=0, sticky="we", pady=(0,8))
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        prof_btns = ctk.CTkFrame(inner, fg_color="transparent")
        prof_btns.grid(row=2, column=0, sticky="we", pady=(0,8))
        prof_btns.grid_columnconfigure((0,1,2), weight=1)
        self.new_profile_btn = ctk.CTkButton(prof_btns, text="New", command=self._create_profile, fg_color=self.theme["ACCENT2"])
        self.new_profile_btn.grid(row=0, column=0, padx=4, sticky="we")
        self.rename_profile_btn = ctk.CTkButton(prof_btns, text="Rename", command=self._rename_profile, fg_color=self.theme["ACCENT1"])
        self.rename_profile_btn.grid(row=0, column=1, padx=4, sticky="we")
        self.delete_profile_btn = ctk.CTkButton(prof_btns, text="Delete", command=self._delete_profile, fg_color=self.theme["ERROR"])
        self.delete_profile_btn.grid(row=0, column=2, padx=4, sticky="we")

        ctk.CTkLabel(inner, text="Avatar", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT2"]).grid(row=3, column=0, sticky="w", pady=(8,4))
        avatar_frame = ctk.CTkFrame(inner, fg_color="transparent")
        avatar_frame.grid(row=4, column=0, sticky="w", pady=(0,8))
        avatars = ["🙂","😎","🎯","🔥","🏆","👾","🤖","🌟"]
        for i,a in enumerate(avatars):
            b = ctk.CTkButton(avatar_frame, text=a, width=36, command=lambda av=a: self._set_avatar(av), fg_color=self.theme["PANEL"])
            b.grid(row=0, column=i, padx=4)

        ctk.CTkLabel(inner, text="Rewards", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT1"]).grid(row=5, column=0, sticky="w", pady=(12,6))
        self.mystery_btn = ctk.CTkButton(inner, text="Mystery Box 🎁", command=self.open_mystery_box, fg_color=self.theme["ACCENT1"])
        self.mystery_btn.grid(row=6, column=0, sticky="we", pady=6)
        self.missions_btn = ctk.CTkButton(inner, text="Daily Missions ✅", command=self.show_missions, fg_color=self.theme["ACCENT2"])
        self.missions_btn.grid(row=7, column=0, sticky="we", pady=6)
        self.daily_claim_btn = ctk.CTkButton(inner, text="Claim Daily Reward", command=self.claim_daily_reward, fg_color=self.theme["ACCENT2"])
        self.daily_claim_btn.grid(row=8, column=0, sticky="we", pady=6)

        ctk.CTkLabel(inner, text="Play", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT2"]).grid(row=9, column=0, sticky="w", pady=(12,6))
        self.mode_menu = ctk.CTkOptionMenu(inner, values=["Single","LocalMultiplayer","AI"], command=self._set_mode, fg_color=self.theme["ACCENT2"])
        self.mode_menu.set(self.mode); self.mode_menu.grid(row=10, column=0, sticky="we", pady=6)
        self.tournament_btn = ctk.CTkButton(inner, text="Tournaments 🏆", command=self.show_tournaments, fg_color=self.theme["ACCENT1"])
        self.tournament_btn.grid(row=11, column=0, sticky="we", pady=6)

        # Export / Import / Settings
        ctk.CTkLabel(inner, text="Data", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT1"]).grid(row=12, column=0, sticky="w", pady=(12,6))
        data_frame = ctk.CTkFrame(inner, fg_color="transparent")
        data_frame.grid(row=13, column=0, sticky="we")
        data_frame.grid_columnconfigure((0,1), weight=1)
        self.export_btn = ctk.CTkButton(data_frame, text="Export Profiles", command=self.export_profiles, fg_color=self.theme["ACCENT1"])
        self.export_btn.grid(row=0, column=0, padx=4, sticky="we")
        self.import_btn = ctk.CTkButton(data_frame, text="Import Profiles", command=self.import_profiles, fg_color=self.theme["ACCENT2"])
        self.import_btn.grid(row=0, column=1, padx=4, sticky="we")

        self.settings_btn = ctk.CTkButton(inner, text="Settings ⚙", command=self.open_settings, fg_color=self.theme["PANEL"], border_width=1)
        self.settings_btn.grid(row=14, column=0, sticky="we", pady=(12,0))

        inner.grid_columnconfigure(0, weight=1)

    # ------------------------
    # Main tabs
    # ------------------------
    def _build_main_tabs(self):
        for w in self.main.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.pack(fill="x", padx=INNER_PAD, pady=(INNER_PAD, 6))

        # Responsive title canvas (no overlapping decorative shapes)
        self.title_canvas = tk.Canvas(header, height=72, bg=self.theme["PANEL"], highlightthickness=0)
        self.title_canvas.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=(4, 0))
        # redraw when canvas size changes
        self.title_canvas.bind("<Configure>", lambda e: self._draw_irregular_header())

        # Theme menu placed to the right
        right_controls = ctk.CTkFrame(header, fg_color="transparent")
        right_controls.pack(side="right", padx=16, pady=(4,0))
        self.header_theme_menu = ctk.CTkOptionMenu(
            right_controls,
            values=list(THEMES.keys()),
            command=self._on_theme_change,
            fg_color=self.theme["ACCENT1"],
            width=140
        )
        self.header_theme_menu.set(self.theme_name); self.header_theme_menu.pack(side="right")

        # Tabview
        self.tabs = ctk.CTkTabview(self.main, width=900)
        self.tabs.pack(fill="both", expand=True, padx=INNER_PAD, pady=(0,INNER_PAD))
        self.tabs.add("Play")
        self.tabs.add("Dashboard")
        self.tabs.set("Play")

        # Play tab
        play_frame = self.tabs.tab("Play")
        play_frame.grid_rowconfigure(0, weight=1)
        play_frame.grid_columnconfigure(0, weight=1)

        # Background canvas for play area
        self.play_canvas = tk.Canvas(play_frame, bg=self.theme["BG"], highlightthickness=0)
        self.play_canvas.grid(row=0, column=0, sticky="nsew")
        self.orbs=[]; self.confetti=[]
        self._create_orbs(10, canvas=self.play_canvas); self._animate_bg(canvas=self.play_canvas)

        # Controls container centered
        controls = ctk.CTkFrame(play_frame, fg_color="transparent")
        controls.place(relx=0.5, rely=0.12, anchor="n", relwidth=0.72)

        info_row = ctk.CTkFrame(controls, fg_color="transparent")
        info_row.pack(fill="x", pady=(6,8))
        self.lives_lbl = ctk.CTkLabel(info_row, text=f"❤️ Lives: {self.lives}", text_color=brighten(self.theme["ACCENT1"],1.05)); self.lives_lbl.pack(side="left", padx=6)
        self.range_lbl = ctk.CTkLabel(info_row, text=f"Range: 1 - {self.max_value}", text_color=brighten(self.theme["ACCENT2"],1.05)); self.range_lbl.pack(side="left", padx=6)
        self.mode_lbl = ctk.CTkLabel(info_row, text=f"Mode: {self.mode}", text_color=brighten(self.theme["ACCENT1"],1.05)); self.mode_lbl.pack(side="right", padx=6)

        self.guess_entry = ctk.CTkEntry(controls, placeholder_text="Enter your guess...", width=480, fg_color=self.theme["PANEL"], text_color=self.theme["TEXT"])
        self.guess_entry.pack(pady=(6,12))
        self.guess_entry.bind("<Return>", lambda e: self._on_guess_click())

        btn_row = ctk.CTkFrame(controls, fg_color="transparent")
        btn_row.pack(pady=8)

        # Guess button
        self.guess_btn = ctk.CTkButton(btn_row, text="GUESS", command=self._wrap_click(None, self._on_guess_click), fg_color=self.theme["ACCENT2"], width=120)
        self.guess_btn.pack(side="left", padx=8)

        # Hint selector + button
        hint_options = [
            "Shrink Range (10)",
            "Parity (5)",
            "Hot/Cold (0)",
            "Reveal Digit (20)",
            "Nearest Multiple (15)"
        ]
        self.hint_menu = ctk.CTkOptionMenu(btn_row, values=hint_options, fg_color=self.theme["PANEL"], width=220)
        self.hint_menu.set(hint_options[0])
        self.hint_menu.pack(side="left", padx=8)
        self.hint_btn = ctk.CTkButton(btn_row, text="HINT", command=self._wrap_click(None, self._on_hint_click), fg_color=self.theme["ACCENT1"], width=100)
        self.hint_btn.pack(side="left", padx=8)

        # New game
        self.new_btn = ctk.CTkButton(btn_row, text="NEW GAME", command=self._wrap_click(None, self.reset_game), fg_color=self.theme["ACCENT1"], width=120)
        self.new_btn.pack(side="left", padx=8)

        self.result_lbl = ctk.CTkLabel(controls, text="", font=("Segoe UI",13,"bold"), text_color=brighten(self.theme["TEXT"],1.15))
        self.result_lbl.pack(pady=10)
        self.progress_bar = ctk.CTkProgressBar(controls, width=480, progress_color=brighten(self.theme["ACCENT1"],1.05)); self.progress_bar.set(0); self.progress_bar.pack(pady=8)
        self.tips_box = ctk.CTkLabel(controls, text="Tips: Use hints to narrow the secret. Costs vary.", wraplength=480, text_color=brighten(self.theme["ACCENT2"],1.05))
        self.tips_box.pack(pady=8)

        # Floating mini-dashboard overlay (hidden by default)
        self.mini_dash = ctk.CTkFrame(play_frame, fg_color=self.theme["PANEL"], corner_radius=12, border_width=1)
        self.mini_dash.place(relx=0.98, rely=0.02, anchor="ne")
        self.mini_dash_visible = True
        self._build_mini_dashboard()

        # Dashboard tab
        dash = self.tabs.tab("Dashboard")
        dash.grid_rowconfigure(0, weight=1)
        dash.grid_columnconfigure(0, weight=1)

        dash_inner = ctk.CTkFrame(dash, fg_color="transparent")
        dash_inner.pack(fill="both", expand=True, padx=INNER_PAD, pady=INNER_PAD)

        # Profile summary
        ctk.CTkLabel(dash_inner, text="Profile", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT1"]).grid(row=0, column=0, sticky="w", pady=(6,4))
        self.profile_name_lbl = ctk.CTkLabel(dash_inner, text=self.active_profile.name, text_color=brighten(self.theme["ACCENT2"],1.05)); self.profile_name_lbl.grid(row=1, column=0, sticky="w")
        self.avatar_lbl = ctk.CTkLabel(dash_inner, text=self.active_profile.avatar, font=("Segoe UI",20), text_color=brighten(self.theme["ACCENT1"],1.05)); self.avatar_lbl.grid(row=2, column=0, sticky="w", pady=(6,8))
        self.coins_lbl = ctk.CTkLabel(dash_inner, text=f"Coins: {self.active_profile.coins} 💰", text_color=brighten(self.theme["ACCENT1"],1.05)); self.coins_lbl.grid(row=3, column=0, sticky="w")
        self.xp_lbl = ctk.CTkLabel(dash_inner, text=f"XP: {self.active_profile.xp} | Lv {self.active_profile.level}", text_color=brighten(self.theme["ACCENT2"],1.05)); self.xp_lbl.grid(row=4, column=0, sticky="w", pady=(4,8))

        # Leaderboard
        ctk.CTkLabel(dash_inner, text="Leaderboard", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT1"]).grid(row=5, column=0, sticky="w", pady=(8,4))
        self.lb_box = scrolledtext.ScrolledText(dash_inner, height=8, bg=self.theme["PANEL"], fg=self.theme["ACCENT1"], bd=0, relief="flat")
        self.lb_box.grid(row=6, column=0, sticky="nsew", pady=(0,8)); self.lb_box.configure(state="disabled")
        self.clear_lb_btn = ctk.CTkButton(dash_inner, text="Clear Leaderboard", command=self.clear_leaderboard, fg_color=self.theme["ERROR"])
        self.clear_lb_btn.grid(row=7, column=0, sticky="we", pady=(0,8))

        # Achievements
        ctk.CTkLabel(dash_inner, text="Achievements", font=("Segoe UI",12,"bold"), text_color=self.theme["ACCENT2"]).grid(row=8, column=0, sticky="w", pady=(6,4))
        self.ach_box = scrolledtext.ScrolledText(dash_inner, height=6, bg=self.theme["PANEL"], fg=self.theme["ACCENT2"], bd=0, relief="flat")
        self.ach_box.grid(row=9, column=0, sticky="nsew", pady=(0,12)); self.ach_box.configure(state="disabled")

        dash_inner.grid_rowconfigure(6, weight=1)
        dash_inner.grid_rowconfigure(9, weight=1)
        dash_inner.grid_columnconfigure(0, weight=1)

    # ------------------------
    # Irregular header drawing (simplified, safe area for text)
    # ------------------------
    def _draw_irregular_header(self):
        c = self.title_canvas
        c.delete("all")
        # get canvas size
        try:
            w = max(420, int(c.winfo_width()))
        except:
            w = 420
        h = int(c.winfo_height() or 72)

        # Draw a subtle rounded rectangle background for the title area
        pad = 8
        # leave at least 220px on the right for controls (theme menu etc.)
        rect_x1 = max(300, w - 220)
        rect_x0 = pad
        rect_y0 = pad
        rect_y1 = h - pad
        radius = 12

        # helper to draw rounded rectangle (approx)
        def _rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
            points = [
                x1+r, y1,
                x2-r, y1,
                x2, y1,
                x2, y1+r,
                x2, y2-r,
                x2, y2,
                x2-r, y2,
                x1+r, y2,
                x1, y2,
                x1, y2-r,
                x1, y1+r,
                x1, y1
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)

        bg_color = brighten(self.theme["ACCENT1"], 0.95)
        _rounded_rect(c, rect_x0, rect_y0, rect_x1, rect_y1, radius, fill=bg_color, outline="")

        # Title text: place inside the rounded rect with safe margins
        title_main_left = rect_x0 + 18
        title_main_top = rect_y0 + 8
        base_font_size = 20 if rect_x1 >= 520 else 16
        small_font_size = 10 if rect_x1 >= 520 else 9

        bright_text = brighten(self.theme["TEXT"], 1.25)
        # place main title left-aligned inside the rounded rect
        c.create_text(title_main_left, title_main_top, anchor="nw", text="GUESS", font=("Segoe UI", base_font_size, "bold"), fill=bright_text)
        c.create_text(title_main_left + int(base_font_size*4.8), title_main_top, anchor="nw", text="NUMBER GAME", font=("Segoe UI", base_font_size, "bold"), fill=bright_text)

        # PRO badge inside the safe rect (to the right of MASTER but inside rect_x1)
        pro_w = 56
        pro_h = base_font_size + 6
        pro_x = min(rect_x1 - pro_w - 12, title_main_left + int(base_font_size*9.2))
        pro_y = title_main_top
        #c.create_rectangle(pro_x, pro_y, pro_x + pro_w, pro_y + pro_h, fill=self.theme["ACCENT2"], outline="")
        #c.create_text(pro_x + 8, pro_y + 2, anchor="nw", text="PRO", font=("Segoe UI", base_font_size, "bold"), fill=self.theme["PANEL"])

        # subtitle below
        subtitle = "Ultimate Edition • Play, Progress, Compete"
        c.create_text(title_main_left, title_main_top + base_font_size + 8, anchor="nw", text=subtitle, font=("Segoe UI", small_font_size), fill=bright_text)

    # ------------------------
    # Mini dashboard
    # ------------------------
    def _build_mini_dashboard(self):
        for w in self.mini_dash.winfo_children():
            w.destroy()
        self.mini_name = ctk.CTkLabel(self.mini_dash, text=self.active_profile.avatar + " " + self.active_profile.name, text_color=brighten(self.theme["ACCENT2"],1.05))
        self.mini_name.grid(row=0, column=0, sticky="w", padx=8, pady=(6,2))
        self.mini_coins = ctk.CTkLabel(self.mini_dash, text=f"💰 {self.active_profile.coins}", text_color=brighten(self.theme["ACCENT1"],1.05))
        self.mini_coins.grid(row=1, column=0, sticky="w", padx=8)
        self.mini_xp = ctk.CTkLabel(self.mini_dash, text=f"XP {self.active_profile.xp} | Lv {self.active_profile.level}", text_color=brighten(self.theme["ACCENT2"],1.05))
        self.mini_xp.grid(row=2, column=0, sticky="w", padx=8, pady=(0,6))
        # small controls
        btns = ctk.CTkFrame(self.mini_dash, fg_color="transparent")
        btns.grid(row=0, column=1, rowspan=3, padx=6, pady=6)
        self.mini_toggle_btn = ctk.CTkButton(btns, text="Hide", width=60, command=self._toggle_mini_dash, fg_color=self.theme["ACCENT1"])
        self.mini_toggle_btn.grid(row=0, column=0, padx=4, pady=2)
        self.mini_settings_btn = ctk.CTkButton(btns, text="⚙", width=36, command=self.open_settings, fg_color=self.theme["ACCENT2"])
        self.mini_settings_btn.grid(row=1, column=0, padx=4, pady=2)

    def _toggle_mini_dash(self):
        self.mini_dash_visible = not self.mini_dash_visible
        if self.mini_dash_visible:
            self.mini_dash.place(relx=0.98, rely=0.02, anchor="ne")
            self.mini_toggle_btn.configure(text="Hide")
        else:
            self.mini_dash.place_forget()
            self.mini_toggle_btn.configure(text="Show")

    # ------------------------
    # Animations & visuals
    # ------------------------
    def _ripple_scale(self, btn, duration=140):
        try:
            orig = btn.cget("fg_color") if btn else self.theme["ACCENT1"]
            bright = brighten(orig, 1.35)
            if btn:
                btn.configure(fg_color=bright)
                bx = btn.winfo_rootx() - self.root.winfo_rootx(); by = btn.winfo_rooty() - self.root.winfo_rooty()
                bw = btn.winfo_width(); bh = btn.winfo_height(); cx = bx + bw//2; cy = by + bh//2
                self._spawn_confetti(x_center=cx, y_center=cy, count=8, canvas=self.play_canvas)
            if self.sound_enabled and winsound:
                try: winsound.Beep(750,60)
                except: pass
            if btn:
                self.root.after(duration, lambda: btn.configure(fg_color=orig))
        except:
            pass

    def _wrap_click(self, btn, func):
        def wrapped():
            self._ripple_scale(btn or self.guess_btn)
            self.root.after(140, func)
        return wrapped

    def _spawn_confetti(self, x_center=None, y_center=None, count=20, canvas=None):
        canvas = canvas or self.play_canvas
        if not self.particles_enabled: return
        width = max(200, self.root.winfo_width()); height = max(200, self.root.winfo_height())
        x_center = x_center or width//2; y_center = y_center or height//2
        for _ in range(count):
            s = random.randint(6,14)
            x = x_center + random.randint(-40,40); y = y_center + random.randint(-20,20)
            color = random.choice([self.theme["ACCENT1"], self.theme["ACCENT2"], "#FFD700", "#FF6FA3", "#66FFCC"])
            rect = canvas.create_rectangle(x,y,x+s,y+s,fill=color,outline="")
            self.confetti.append({'id':rect,'x':x,'y':y,'dx':random.uniform(-3,3),'dy':random.uniform(-6,-2),'s':s,'canvas':canvas})

    def _create_orbs(self,count=10, canvas=None):
        canvas = canvas or self.play_canvas
        for _ in range(count):
            x=random.randint(0,APP_W-150); y=random.randint(0,APP_H-150); size=random.randint(40,120)
            color=random.choice([self.theme["ACCENT1"], self.theme["ACCENT2"], "#FFD700"])
            orb_id = canvas.create_oval(x,y,x+size,y+size,outline=color,width=2)
            self.orbs.append({'id':orb_id,'dx':random.choice([-1,1])*0.6,'dy':random.choice([-1,1])*0.6,'canvas':canvas})

    def _animate_bg(self, canvas=None):
        canvas = canvas or self.play_canvas
        width = max(200, self.root.winfo_width()); height = max(200, self.root.winfo_height())
        for orb in list(self.orbs):
            if orb.get('canvas') != canvas: continue
            coords = orb['canvas'].coords(orb['id'])
            if not coords: continue
            x1,y1,x2,y2 = coords
            if x1<=0 or x2>=width: orb['dx']*=-1
            if y1<=0 or y2>=height: orb['dy']*=-1
            orb['canvas'].move(orb['id'], orb['dx'], orb['dy'])
        for p in list(self.confetti):
            c = p.get('canvas', canvas)
            p['y'] += p['dy']; p['x'] += p['dx']; p['dy'] += 0.2
            try: c.coords(p['id'], p['x'], p['y'], p['x']+p['s'], p['y']+p['s'])
            except: pass
            if p['y'] > height+50:
                try: c.delete(p['id'])
                except: pass
                self.confetti.remove(p)
        self.root.after(30, lambda: self._animate_bg(canvas=canvas))

    def _title_glow_step(self):
        try:
            self._draw_irregular_header()
            self._title_glow_phase += 0.06
        except: pass
        if getattr(self,'_title_glow_animating',True):
            self.root.after(120, self._title_glow_step)

    # ------------------------
    # Profile management
    # ------------------------
    def _refresh_profiles_list(self):
        self.profile_listbox.delete(0,"end")
        for pid,p in self.profiles.items():
            display = f"{p.avatar} {p.name} (Lv{p.level})"
            self.profile_listbox.insert("end", display)
        keys=list(self.profiles.keys())
        if self.active_profile_id in keys:
            idx = keys.index(self.active_profile_id); self.profile_listbox.select_set(idx); self.profile_listbox.see(idx)

    def _on_profile_select(self,event):
        sel = self.profile_listbox.curselection()
        if not sel: return
        idx = sel[0]; pid = list(self.profiles.keys())[idx]
        self.active_profile_id = pid; self.active_profile = self.profiles[pid]; self._refresh_all(); self._save()

    def _create_profile(self):
        name = simpledialog.askstring("New Profile","Enter profile name:",parent=self.root)
        if not name: return
        pid = f"profile_{random.randint(1000,9999)}"; p = Profile(pid,name); self.profiles[pid]=p; self.active_profile_id=pid; self.active_profile=p; self._refresh_all(); self._save()

    def _rename_profile(self):
        sel = self.profile_listbox.curselection()
        if not sel: messagebox.showinfo("Rename","Select a profile first."); return
        idx=sel[0]; pid=list(self.profiles.keys())[idx]; new = simpledialog.askstring("Rename","New name:",initialvalue=self.profiles[pid].name,parent=self.root)
        if new: self.profiles[pid].name=new; self._refresh_all(); self._save()

    def _delete_profile(self):
        sel = self.profile_listbox.curselection()
        if not sel: messagebox.showinfo("Delete","Select a profile first."); return
        idx=sel[0]; pid=list(self.profiles.keys())[idx]
        if messagebox.askyesno("Delete",f"Delete profile {self.profiles[pid].name}?"):
            del self.profiles[pid]
            if not self.profiles:
                p=Profile("profile_1001","Player1"); self.profiles[p.id]=p
            self.active_profile_id = next(iter(self.profiles.keys())); self.active_profile=self.profiles[self.active_profile_id]; self._refresh_all(); self._save()

    def _set_avatar(self, av):
        self.active_profile.avatar = av
        self._refresh_all()
        self._save()

    # ------------------------
    # Gameplay handlers & improved hints
    # ------------------------
    def _set_mode(self, mode):
        # called from option menu
        self.mode = mode
        self.mode_lbl.configure(text=f"Mode: {self.mode}")
        if mode == "AI":
            self.tips_box.configure(text="AI mode: compete against the bot. Hints cost coins.")
        elif mode == "LocalMultiplayer":
            self.tips_box.configure(text="Local Multiplayer: take turns guessing.")
        else:
            self.tips_box.configure(text="Single player: beat your best streak.")
        self._save()

    def _on_hint_click(self):
        choice = self.hint_menu.get()
        # parse cost from label like "Shrink Range (10)"
        if "(" in choice and ")" in choice:
            try:
                cost = int(choice.split("(")[-1].split(")")[0])
            except:
                cost = 0
            hint_type = choice.split("(")[0].strip()
        else:
            cost = 0
            hint_type = choice
        # check coins
        if self.active_profile.coins < cost:
            messagebox.showinfo("Hint", f"Not enough coins. This hint costs {cost} coins.")
            return
        # deduct cost
        self.active_profile.coins -= cost
        # apply hint
        self._apply_hint(hint_type)
        self._refresh_mini_dash()
        self._save()

    def _apply_hint(self, hint_type):
        # Implement hint behaviors
        if hint_type == "Shrink Range":
            # shrink current ai_low/ai_high around secret by half span
            span = max(2, int((self.ai_high - self.ai_low) / 2))
            low = max(1, self.secret - span//2)
            high = min(self.max_value, self.secret + span//2)
            self.ai_low, self.ai_high = low, high
            self.range_lbl.configure(text=f"Range: {low} - {high}")
            self.result_lbl.configure(text=f"Range narrowed to {low} - {high}", text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=12)
        elif hint_type == "Parity":
            parity = "even" if self.secret % 2 == 0 else "odd"
            self.result_lbl.configure(text=f"The secret is {parity}.", text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=8)
        elif hint_type == "Hot/Cold":
            # give a hot/cold indicator relative to last guess if exists, else general hint
            if self.active_profile.history:
                last = self.active_profile.history[-1]["guess"]
                dist = abs(self.secret - last)
                if dist == 0:
                    msg = "You already guessed it!"
                elif dist <= max(1, int(self.max_value*0.05)):
                    msg = "Very hot"
                elif dist <= max(1, int(self.max_value*0.15)):
                    msg = "Hot"
                elif dist <= max(1, int(self.max_value*0.3)):
                    msg = "Warm"
                else:
                    msg = "Cold"
                self.result_lbl.configure(text=f"Hot/Cold: {msg}", text_color=self.theme["ACCENT2"])
            else:
                # no previous guess: give a general proximity hint relative to midpoint
                mid = self.max_value // 2
                if abs(self.secret - mid) < self.max_value * 0.2:
                    msg = "Secret near center"
                else:
                    msg = "Secret away from center"
                self.result_lbl.configure(text=f"Hot/Cold: {msg}", text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=6)
        elif hint_type == "Reveal Digit":
            # reveal one digit of the secret (for numbers >9)
            s = str(self.secret)
            if len(s) == 1:
                self.result_lbl.configure(text=f"Secret is a single digit: {s}", text_color=self.theme["ACCENT2"])
            else:
                idx = random.randrange(len(s))
                revealed = "".join([ch if i==idx else "•" for i,ch in enumerate(s)])
                self.result_lbl.configure(text=f"Digit hint: {revealed}", text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=10)
        elif hint_type == "Nearest Multiple":
            # give nearest multiple of a small base (e.g., 5 or 10)
            base = 5 if self.max_value <= 100 else 10
            lower = (self.secret // base) * base
            higher = lower + base
            # choose the closer one to secret (but not equal)
            if lower == self.secret:
                msg = f"Secret is a multiple of {base}"
            else:
                msg = f"Nearest multiples of {base}: {lower} and {higher}"
            self.result_lbl.configure(text=msg, text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=8)
        else:
            self.result_lbl.configure(text="No hint available.", text_color=self.theme["WARN"])

    def _on_guess_click(self):
        val = self.guess_entry.get().strip()
        if not val:
            return
        try:
            g = int(val)
        except:
            self.result_lbl.configure(text="Enter a valid number.", text_color=self.theme["ERROR"])
            return
        self.guess_entry.delete(0, 'end')
        self._process_guess(g)

    def _process_guess(self, g):
        if g < 1 or g > self.max_value:
            self.result_lbl.configure(text=f"Guess between 1 and {self.max_value}.", text_color=self.theme["WARN"])
            return
        self.active_profile.history.append({"ts": now_ts(), "guess": g})
        self.lives -= 1
        self.lives_lbl.configure(text=f"❤️ Lives: {self.lives}")
        if g == self.secret:
            self._on_win()
        else:
            hint = "higher" if g < self.secret else "lower"
            self.result_lbl.configure(text=f"Try {hint.upper()}!", text_color=self.theme["ACCENT2"])
            self._spawn_confetti(count=6)
            if self.lives <= 0:
                self._on_loss()
        self._save()
        self._refresh_mini_dash()

    def _on_win(self):
        self.result_lbl.configure(text="Correct! You win 🎉", text_color=self.theme["SUCCESS"])
        self.active_profile.xp += 20
        self.active_profile.coins += 50
        self.active_profile.streak += 1
        self.active_profile.best_streak = max(self.active_profile.best_streak, self.active_profile.streak)
        self._spawn_confetti(count=40)
        self.progress_bar.set(min(1.0, (self.active_profile.xp % 100) / 100.0))
        self.reset_state(new_secret=True, preserve_streak=True)
        self._refresh_all()

    def _on_loss(self):
        self.result_lbl.configure(text=f"Out of lives. Secret was {self.secret}.", text_color=self.theme["ERROR"])
        self.active_profile.streak = 0
        self.active_profile.pity += 1
        self.reset_state(new_secret=True, preserve_streak=True)
        self._refresh_all()

    def reset_game(self):
        self.reset_state(new_secret=True, preserve_streak=True)
        self.lives_lbl.configure(text=f"❤️ Lives: {self.lives}")
        self.range_lbl.configure(text=f"Range: 1 - {self.max_value}")
        self.result_lbl.configure(text="")
        self.progress_bar.set(0)
        self._spawn_confetti(count=12)
        self._refresh_all()

    # ------------------------
    # Rewards / Missions / Misc
    # ------------------------
    def _generate_daily_missions(self):
        return {"missions":[{"id":"m1","desc":"Win 1 game","done":False},{"id":"m2","desc":"Use 1 hint","done":False}] , "date": today_str()}

    def open_mystery_box(self):
        # simple random reward
        reward = random.choice(["coins","xp","nothing"])
        if reward == "coins":
            amt = random.randint(20,100); self.active_profile.coins += amt; messagebox.showinfo("Mystery Box", f"You found {amt} coins!")
        elif reward == "xp":
            amt = random.randint(10,40); self.active_profile.xp += amt; messagebox.showinfo("Mystery Box", f"You gained {amt} XP!")
        else:
            messagebox.showinfo("Mystery Box", "The box was empty... better luck next time.")
        self._spawn_confetti(count=20)
        self._refresh_mini_dash()
        self._save()

    def show_missions(self):
        m = self.missions.get("missions",[]) if isinstance(self.missions, dict) else []
        text = "\n".join([f"- {mi['desc']} [{'Done' if mi.get('done') else 'Open'}]" for mi in m])
        messagebox.showinfo("Daily Missions", text or "No missions available.")

    def claim_daily_reward(self):
        today = today_str()
        if self.active_profile.last_daily == today:
            messagebox.showinfo("Daily", "You already claimed today's reward.")
            return
        self.active_profile.last_daily = today
        self.active_profile.coins += 50
        self.active_profile.xp += 10
        messagebox.showinfo("Daily", "Claimed 50 coins and 10 XP!")
        self._refresh_mini_dash()
        self._save()

    def show_tournaments(self):
        messagebox.showinfo("Tournaments", "Tournament mode coming soon!")

    # ------------------------
    # Data import/export & settings
    # ------------------------
    def export_profiles(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")], title="Export Profiles")
        if not path: return
        data = {"profiles":{pid:p.to_dict() for pid,p in self.profiles.items()}, "active_profile": self.active_profile_id}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export", "Profiles exported successfully.")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to export: {e}")

    def import_profiles(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")], title="Import Profiles")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            imported = data.get("profiles",{})
            for pid,pd in imported.items():
                self.profiles[pid] = Profile.from_dict(pd)
            self.active_profile_id = data.get("active_profile") or self.active_profile_id
            self.active_profile = self.profiles[self.active_profile_id]
            self._refresh_all(); self._save()
            messagebox.showinfo("Import", "Profiles imported.")
        except Exception as e:
            messagebox.showerror("Import", f"Failed to import: {e}")

    def open_settings(self):
        # simple settings dialog
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("420x260")
        dlg.transient(self.root)
        dlg.grab_set()
        frame = ctk.CTkFrame(dlg, fg_color=self.theme["PANEL"], corner_radius=8)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(frame, text="Theme", text_color=self.theme["ACCENT1"]).pack(anchor="w", pady=(6,4))
        theme_menu = ctk.CTkOptionMenu(frame, values=list(THEMES.keys()), command=lambda v: self._on_theme_change(v))
        theme_menu.set(self.theme_name); theme_menu.pack(fill="x", pady=6)
        ctk.CTkLabel(frame, text="Particles", text_color=self.theme["ACCENT2"]).pack(anchor="w", pady=(8,4))
        part_var = tk.BooleanVar(value=self.particles_enabled)
        ctk.CTkCheckBox(frame, text="Enable particles", variable=part_var, command=lambda: self._toggle_particles(part_var.get())).pack(anchor="w")
        ctk.CTkLabel(frame, text="Sound", text_color=self.theme["ACCENT2"]).pack(anchor="w", pady=(8,4))
        sound_var = tk.BooleanVar(value=self.sound_enabled)
        ctk.CTkCheckBox(frame, text="Enable sound", variable=sound_var, command=lambda: self._toggle_sound(sound_var.get())).pack(anchor="w")
        ctk.CTkButton(frame, text="Close", command=lambda: (dlg.destroy(), self._save())).pack(pady=(12,0))

    def _toggle_particles(self, val):
        self.particles_enabled = bool(val)
        self._save()

    def _toggle_sound(self, val):
        self.sound_enabled = bool(val)
        self._save()

    # ------------------------
    # Dashboard helpers
    # ------------------------
    def clear_leaderboard(self):
        if messagebox.askyesno("Clear", "Clear leaderboard?"):
            self.save_data["leaderboard"] = []
            self.lb_box.configure(state="normal"); self.lb_box.delete("1.0","end"); self.lb_box.configure(state="disabled")
            self._save()

    # ------------------------
    # UI refresh
    # ------------------------
    def _refresh_all(self):
        # refresh profiles list and UI labels
        self._refresh_profiles_list()
        self._refresh_dashboard()
        self._refresh_mini_dash()
        # update labels in play area
        try:
            self.lives_lbl.configure(text=f"❤️ Lives: {self.lives}")
            self.range_lbl.configure(text=f"Range: 1 - {self.max_value}")
            self.mode_lbl.configure(text=f"Mode: {self.mode}")
            self.profile_name_lbl.configure(text=self.active_profile.name)
            self.avatar_lbl.configure(text=self.active_profile.avatar)
            self.coins_lbl.configure(text=f"Coins: {self.active_profile.coins} 💰")
            self.xp_lbl.configure(text=f"XP: {self.active_profile.xp} | Lv {self.active_profile.level}")
        except:
            pass

    def _refresh_dashboard(self):
        # leaderboard
        lb = self.save_data.get("leaderboard",[])
        self.lb_box.configure(state="normal"); self.lb_box.delete("1.0","end")
        for i,entry in enumerate(lb[:50], start=1):
            self.lb_box.insert("end", f"{i}. {entry.get('name','Anon')} - {entry.get('score',0)}\n")
        self.lb_box.configure(state="disabled")
        # achievements
        ach = self.achievements or {}
        self.ach_box.configure(state="normal"); self.ach_box.delete("1.0","end")
        for k,v in ach.items():
            self.ach_box.insert("end", f"{k}: {v}\n")
        self.ach_box.configure(state="disabled")

    def _refresh_mini_dash(self):
        try:
            self.mini_name.configure(text=self.active_profile.avatar + " " + self.active_profile.name)
            self.mini_coins.configure(text=f"💰 {self.active_profile.coins}")
            self.mini_xp.configure(text=f"XP {self.active_profile.xp} | Lv {self.active_profile.level}")
        except:
            pass

    # ------------------------
    # Responsive behavior
    # ------------------------
    def _on_root_resize(self, event):
        # collapse sidebar for narrow widths
        w = self.root.winfo_width()
        if w < MOBILE_BREAKPOINT and not self.is_mobile:
            self.is_mobile = True
            # hide sidebar and show top menu
            self.sidebar.grid_remove()
            self.top_menu.place(relx=0, rely=0, relwidth=1, height=56)
            # build compact top menu
            for w in self.top_menu.winfo_children(): w.destroy()
            left = ctk.CTkFrame(self.top_menu, fg_color="transparent"); left.pack(side="left", padx=8)
            ctk.CTkButton(left, text="☰", width=36, command=self._toggle_sidebar_mobile, fg_color=self.theme["ACCENT1"]).pack(side="left", padx=(4,8))
            ctk.CTkLabel(left, text="GuessMaster", text_color=self.theme["ACCENT1"], font=("Segoe UI",12,"bold")).pack(side="left")
            right = ctk.CTkFrame(self.top_menu, fg_color="transparent"); right.pack(side="right", padx=8)
            self.header_theme_menu = ctk.CTkOptionMenu(right, values=list(THEMES.keys()), command=self._on_theme_change, fg_color=self.theme["ACCENT1"], width=140)
            self.header_theme_menu.set(self.theme_name); self.header_theme_menu.pack(side="right")
        elif w >= MOBILE_BREAKPOINT and self.is_mobile:
            self.is_mobile = False
            self.top_menu.place_forget()
            self.sidebar.grid()
        # redraw header canvas to avoid overlap
        try:
            self._draw_irregular_header()
        except:
            pass

    def _toggle_sidebar_mobile(self):
        if self.sidebar.winfo_ismapped():
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()

    # ------------------------
    # Theme change
    # ------------------------
    def _on_theme_change(self, theme_name):
        if not theme_name: return
        self.theme_name = theme_name
        self.theme = THEMES.get(theme_name, NEON)
        # update colors across UI by rebuilding main frames
        self._build_sidebar_content()
        self._build_main_tabs()
        self._refresh_all()
        self._save()

# ------------------------
# Run
# ------------------------
if __name__ == "__main__":
    root = ctk.CTk()
    app = GuessMasterPro(root)
    root.mainloop()
