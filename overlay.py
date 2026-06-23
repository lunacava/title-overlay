#!/usr/bin/env python3
"""
Exhibition Title Overlay / 展示会タイトルオーバーレイ (Mac/Linux 対応版)

操作:
  ドラッグ         : ウィンドウを移動
  右下角ドラッグ   : リサイズ（フォントが自動連動）
  ダブルクリック   : テキスト編集
  右クリック       : 設定メニュー
  Esc / 終了メニュー: 終了
"""
import tkinter as tk
from tkinter import colorchooser, font as tkfont
import sys
import platform
import json
import os
import io

try:
    import qrcode
    from PIL import Image, ImageTk
    HAS_QR = True
except ImportError:
    HAS_QR = False

PAD_X = 24
PAD_Y = 4
REF_PT = 100


def _config_path():
    base = os.path.expanduser("~/Library/Application Support/overlay_app") \
        if sys.platform == "darwin" else \
        os.path.join(os.path.expanduser("~"), ".config", "overlay_app")
    return os.path.join(base, "config.json")


def _load_config():
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(data):
    path = _config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

# ── カラーパレット ──────────────────────────────────────────────────────
C = {
    "bg":        "#0D0D0D",
    "border":    "#2A2A2A",
    "item_bg":   "#0D0D0D",
    "item_hover":"#1E1E2E",
    "accent":    "#7C6FCD",
    "text":      "#E0E0E0",
    "text_dim":  "#555555",
    "icon":      "#7C6FCD",
}

MENU_W    = 260
ITEM_H    = 30
SEP_H     = 9

IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _make_borderless(win):
    """枠なしウィンドウにする。macOS は Tk 9 の -stylemask、それ以外は overrideredirect。"""
    if IS_MAC:
        try:
            win.attributes('-stylemask', '')
            return
        except tk.TclError:
            pass
    win.overrideredirect(True)


def _pick_font():
    """日本語表示用フォント（タイトルラベル用）。"""
    available = set(tkfont.families())
    candidates = (
        # macOS
        "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Hiragino Maru Gothic ProN",
        "PingFang SC", "Apple SD Gothic Neo",
        # Windows
        "Yu Gothic UI", "Meiryo UI", "Meiryo", "MS UI Gothic",
        # Linux 系（IPA / Noto / Takao など）
        "Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "IPAGothic",
        "TakaoGothic", "VL Gothic", "Source Han Sans JP",
        # 汎用
        "Arial Unicode MS", "DejaVu Sans", "Liberation Sans", "Arial",
    )
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"


def _pick_ui_font():
    """UI（メニュー・ボタン）用フォント。"""
    available = set(tkfont.families())
    candidates = (
        # macOS
        "Menlo", "SF Mono", "Monaco",
        # Windows
        "Consolas", "Segoe UI",
        # Linux
        "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono",
        "Ubuntu Mono", "FreeMono",
    )
    for name in candidates:
        if name in available:
            return name
    return "TkFixedFont"


# UI フォントは起動後に決定する（プレースホルダ）
FONT_UI_FAMILY   = "Consolas"
FONT_ICON_FAMILY = "Consolas"
FONT_TEXT_FAMILY = "Segoe UI"

FONT_UI   = (FONT_UI_FAMILY,   10)
FONT_ICON = (FONT_ICON_FAMILY, 10)


# ── カスタムメニュー ────────────────────────────────────────────────────
class DarkMenu(tk.Toplevel):
    def __init__(self, parent, items):
        super().__init__(parent)
        _make_borderless(self)
        self.attributes('-topmost', True)
        self.configure(bg=C["border"])
        self.resizable(False, False)

        outer = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=C["bg"])
        inner.pack(fill=tk.BOTH, expand=True)

        hdr = tk.Frame(inner, bg=C["bg"], height=4)
        hdr.pack(fill=tk.X)
        tk.Frame(hdr, bg=C["accent"], height=2).place(relx=0, rely=0.5,
                                                       relwidth=1, anchor="w")

        self._rows = []
        for item in items:
            if item is None:
                self._add_sep(inner)
            else:
                self._add_item(inner, *item)

        tk.Frame(inner, bg=C["text_dim"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        self.bind('<Escape>', lambda e: self._close())

    def _add_item(self, parent, icon, label, cmd):
        row = tk.Frame(parent, bg=C["item_bg"], height=ITEM_H, cursor="hand2")
        row.pack(fill=tk.X)
        row.pack_propagate(False)

        bar = tk.Frame(row, bg=C["accent"], width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar.pack_forget()

        ic = tk.Label(row, text=icon, font=FONT_ICON,
                      fg=C["icon"], bg=C["item_bg"],
                      width=3, anchor="center")
        ic.pack(side=tk.LEFT, padx=(8, 4), pady=0)

        lbl = tk.Label(row, text=label, font=FONT_UI,
                       fg=C["text"], bg=C["item_bg"],
                       anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        def enter(_):
            for w in (row, ic, lbl):
                w.config(bg=C["item_hover"])
            bar.pack(side=tk.LEFT, fill=tk.Y, before=ic)

        def leave(_):
            for w in (row, ic, lbl):
                w.config(bg=C["item_bg"])
            bar.pack_forget()

        def click(_):
            # 親 root に対して after を呼ぶ（自分は destroy 後に消えるため）
            parent = self.master
            if cmd:
                parent.after(10, cmd)
            self._close()

        for w in (row, ic, lbl):
            w.bind('<Enter>', enter)
            w.bind('<Leave>', leave)
            w.bind('<Button-1>', click)

        self._rows.append(row)

    def _add_sep(self, parent):
        sep = tk.Frame(parent, bg=C["bg"], height=SEP_H)
        sep.pack(fill=tk.X)
        tk.Frame(sep, bg=C["border"], height=1).place(
            relx=0.04, rely=0.5, relwidth=0.92, anchor="w")

    def _close(self):
        self.destroy()

    def popup(self, x, y):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = MENU_W + 2
        h  = self.winfo_reqheight()
        if x + w > sw:
            x = sw - w - 4
        if y + h > sh:
            y = sh - h - 4
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.lift()
        self.focus_force()


# ── 透明度スライダーダイアログ ──────────────────────────────────────────
class DarkSliderDialog(tk.Toplevel):
    def __init__(self, parent, title, current, lo, hi, unit, on_ok):
        super().__init__(parent)
        _make_borderless(self)
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.configure(bg=C["border"])

        outer = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        outer.pack()
        body = tk.Frame(outer, bg=C["bg"], padx=20, pady=16, width=300)
        body.pack()

        tk.Label(body, text=title, font=(FONT_TEXT_FAMILY, 10, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(anchor="w")
        tk.Frame(body, bg=C["accent"], height=1).pack(fill=tk.X, pady=(4, 12))

        self._var = tk.IntVar(value=current)
        val_lbl = tk.Label(body, textvariable=self._var,
                           font=(FONT_TEXT_FAMILY, 18, "bold"),
                           fg=C["accent"], bg=C["bg"], width=4)
        val_lbl.pack()
        tk.Label(body, text=unit, font=(FONT_TEXT_FAMILY, 8),
                 fg=C["text_dim"], bg=C["bg"]).pack()

        sl = tk.Scale(body, from_=lo, to=hi, orient=tk.HORIZONTAL,
                      variable=self._var, length=260, showvalue=False,
                      bg=C["bg"], fg=C["text"],
                      troughcolor="#1E1E2E", activebackground=C["accent"],
                      highlightthickness=0, bd=0, sliderrelief=tk.FLAT,
                      sliderlength=18)
        sl.pack(pady=(6, 14))

        bf = tk.Frame(body, bg=C["bg"])
        bf.pack()

        def _btn(text, cmd, accent=False):
            bg = C["accent"] if accent else "#1C1C2A"
            b = tk.Label(bf, text=text, font=(FONT_TEXT_FAMILY, 9, "bold"),
                         fg="#FFFFFF", bg=bg, padx=16, pady=6, cursor="hand2")
            b.pack(side=tk.LEFT, padx=5)
            b.bind('<Enter>', lambda e: b.config(bg="#9A8EE0" if accent else "#2A2A3A"))
            b.bind('<Leave>', lambda e: b.config(bg=bg))
            b.bind('<Button-1>', lambda e: cmd())

        _btn("  OK  ", self._ok, accent=True)
        _btn("キャンセル", self.destroy)

        self._on_ok = on_ok
        self.bind('<Return>', lambda e: self._ok())
        self.bind('<Escape>', lambda e: self.destroy())
        self.update_idletasks()
        w  = self.winfo_reqwidth()
        h  = self.winfo_reqheight()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")
        self.grab_set()

    def _ok(self):
        self._on_ok(self._var.get())
        self.destroy()


def _supports_japanese(family):
    """family が日本語（CJK）グリフを持っているかをざっくり判定する。"""
    try:
        f = tkfont.Font(family=family, size=14)
    except tk.TclError:
        return False
    # CJK 非対応フォントは「あ」がフォールバック描画されるが、
    # 多くのフォントでは tofu/通常字幅と異なる。比較として "x" の幅と比べる。
    try:
        ja = f.measure("あ漢")
        en = f.measure("xx") or 1
    except tk.TclError:
        return False
    # 全角文字幅は半角の概ね1.5倍以上になるはず（CJK対応の目安）
    return ja >= en * 1.4


# ── フォント選択ダイアログ ──────────────────────────────────────────────
class FontPickerDialog(tk.Toplevel):
    def __init__(self, parent, current, on_pick, on_preview=None):
        super().__init__(parent)
        _make_borderless(self)
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.configure(bg=C["border"])

        self._committed = False
        self._original = current
        self._on_pick = on_pick
        self._on_preview = on_preview

        outer = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        outer.pack()
        body = tk.Frame(outer, bg=C["bg"], padx=20, pady=16)
        body.pack()

        tk.Label(body, text="フォントを選択 (★は日本語対応)",
                 font=(FONT_TEXT_FAMILY, 10, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(anchor="w")
        tk.Frame(body, bg=C["accent"], height=1).pack(fill=tk.X, pady=(4, 12))

        # スクロール可能リスト
        list_frame = tk.Frame(body, bg=C["bg"])
        list_frame.pack()
        sb = tk.Scrollbar(list_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lb = tk.Listbox(list_frame, width=36, height=14,
                        bg="#1A1A1A", fg=C["text"],
                        selectbackground=C["accent"],
                        selectforeground="#FFFFFF",
                        highlightthickness=0, bd=0,
                        font=(FONT_TEXT_FAMILY, 10),
                        yscrollcommand=sb.set, activestyle="none")
        lb.pack(side=tk.LEFT)
        sb.config(command=lb.yview)

        # 日本語対応を先頭に持ってきてソート
        all_families = sorted(set(tkfont.families()))
        ja_families = [f for f in all_families if _supports_japanese(f)]
        ja_set = set(ja_families)
        non_ja = [f for f in all_families if f not in ja_set]
        families = ja_families + non_ja
        for f in families:
            mark = "★ " if f in ja_set else "   "
            lb.insert(tk.END, mark + f)
        if current in families:
            i = families.index(current)
            lb.select_set(i)
            lb.see(i)

        # プレビュー（固定サイズ Frame に入れる）
        preview_var = tk.StringVar(value=current)
        prev_frame = tk.Frame(body, bg="#1A1A1A", width=320, height=60)
        prev_frame.pack(pady=(10, 4))
        prev_frame.pack_propagate(False)
        prev = tk.Label(prev_frame, textvariable=preview_var,
                        font=(current, 18), fg=C["text"], bg="#1A1A1A",
                        anchor="center")
        prev.pack(fill=tk.BOTH, expand=True)

        def on_select(_=None):
            sel = lb.curselection()
            if sel:
                fam = families[sel[0]]
                preview_var.set(fam)
                prev.config(font=(fam, 18))
                # メインウィンドウへライブプレビュー
                if self._on_preview is not None:
                    self._on_preview(fam)

        lb.bind('<<ListboxSelect>>', on_select)

        bf = tk.Frame(body, bg=C["bg"])
        bf.pack(pady=(10, 0))

        def _btn(text, cmd, accent=False):
            bg = C["accent"] if accent else "#1C1C2A"
            b = tk.Label(bf, text=text, font=(FONT_TEXT_FAMILY, 9, "bold"),
                         fg="#FFFFFF", bg=bg, padx=16, pady=6, cursor="hand2")
            b.pack(side=tk.LEFT, padx=5)
            b.bind('<Enter>', lambda e: b.config(bg="#9A8EE0" if accent else "#2A2A3A"))
            b.bind('<Leave>', lambda e: b.config(bg=bg))
            b.bind('<Button-1>', lambda e: cmd())

        def _ok():
            sel = lb.curselection()
            if sel:
                self._committed = True
                self._on_pick(families[sel[0]])
            self.destroy()

        _btn("  OK  ", _ok, accent=True)
        _btn("キャンセル", self.destroy)

        # 閉じるときに未確定ならプレビューを巻き戻す
        self.bind('<Destroy>', self._on_destroy)

        self.bind('<Return>', lambda e: _ok())
        self.bind('<Escape>', lambda e: self.destroy())
        self.update_idletasks()
        w  = self.winfo_reqwidth()
        h  = self.winfo_reqheight()
        # オーバーレイ本体と重ならない位置に出す（プレビューを見えるように）
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        ox = parent.winfo_rootx()
        oy = parent.winfo_rooty()
        ow = parent.winfo_width()
        oh = parent.winfo_height()
        gap = 8
        # 候補: 右、下、左、上 の順
        candidates = [
            (ox + ow + gap, oy),                    # 右
            (ox, oy + oh + gap),                    # 下
            (ox - w - gap, oy),                     # 左
            (ox, oy - h - gap),                     # 上
        ]
        x, y = candidates[0]
        for cx, cy in candidates:
            if 0 <= cx and cx + w <= sw and 0 <= cy and cy + h <= sh:
                x, y = cx, cy
                break
        else:
            # どこにも収まらなければ画面に押し込む
            x = max(0, min(x, sw - w))
            y = max(0, min(y, sh - h))
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.grab_set()

    def _on_destroy(self, e):
        if e.widget is not self:
            return
        if not self._committed and self._on_preview is not None:
            self._on_preview(self._original)


# ── QR 設定ダイアログ ──────────────────────────────────────────────────
class QRSettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_url, current_side, on_ok):
        super().__init__(parent)
        _make_borderless(self)
        self.attributes('-topmost', True)
        self.resizable(False, False)
        self.configure(bg=C["border"])

        outer = tk.Frame(self, bg=C["border"], padx=1, pady=1)
        outer.pack()
        body = tk.Frame(outer, bg=C["bg"], padx=20, pady=16)
        body.pack()

        tk.Label(body, text="QR コード設定",
                 font=(FONT_TEXT_FAMILY, 10, "bold"),
                 fg=C["text"], bg=C["bg"]).pack(anchor="w")
        tk.Frame(body, bg=C["accent"], height=1).pack(fill=tk.X, pady=(4, 12))

        tk.Label(body, text="URL", font=(FONT_TEXT_FAMILY, 9),
                 fg=C["text_dim"], bg=C["bg"]).pack(anchor="w")
        url_var = tk.StringVar(value=current_url)
        entry = tk.Entry(body, textvariable=url_var, width=40,
                         bg="#1A1A1A", fg=C["text"],
                         insertbackground=C["text"],
                         relief=tk.FLAT, bd=0,
                         highlightthickness=1,
                         highlightcolor=C["accent"],
                         highlightbackground="#444444",
                         font=(FONT_TEXT_FAMILY, 11))
        entry.pack(pady=(4, 12), ipady=6)
        entry.focus_set()

        tk.Label(body, text="表示位置", font=(FONT_TEXT_FAMILY, 9),
                 fg=C["text_dim"], bg=C["bg"]).pack(anchor="w")

        side_var = tk.StringVar(value=current_side)
        sides = tk.Frame(body, bg=C["bg"])
        sides.pack(anchor="w", pady=(4, 12))

        def _radio(text, value):
            r = tk.Radiobutton(
                sides, text=text, variable=side_var, value=value,
                bg=C["bg"], fg=C["text"],
                selectcolor=C["bg"], activebackground=C["bg"],
                activeforeground=C["accent"],
                font=(FONT_TEXT_FAMILY, 10), bd=0, highlightthickness=0,
            )
            r.pack(side=tk.LEFT, padx=(0, 16))

        _radio("左側", "left")
        _radio("右側", "right")

        bf = tk.Frame(body, bg=C["bg"])
        bf.pack()

        def _btn(text, cmd, accent=False):
            bg = C["accent"] if accent else "#1C1C2A"
            b = tk.Label(bf, text=text, font=(FONT_TEXT_FAMILY, 9, "bold"),
                         fg="#FFFFFF", bg=bg, padx=16, pady=6, cursor="hand2")
            b.pack(side=tk.LEFT, padx=5)
            b.bind('<Enter>', lambda e: b.config(bg="#9A8EE0" if accent else "#2A2A3A"))
            b.bind('<Leave>', lambda e: b.config(bg=bg))
            b.bind('<Button-1>', lambda e: cmd())

        def _ok():
            on_ok(url_var.get().strip(), side_var.get())
            self.destroy()

        _btn("  OK  ", _ok, accent=True)
        _btn("キャンセル", self.destroy)

        self.bind('<Return>', lambda e: _ok())
        self.bind('<Escape>', lambda e: self.destroy())
        self.update_idletasks()
        w  = self.winfo_reqwidth()
        h  = self.winfo_reqheight()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{max(0, px - w//2)}+{max(0, py - h//2)}")
        self.grab_set()


# ── メインオーバーレイ ──────────────────────────────────────────────────
class Overlay:
    MIN_W, MIN_H = 80, 40

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        # フォント決定（Tk 起動後でないと families() が取得できない）
        global FONT_UI_FAMILY, FONT_ICON_FAMILY, FONT_TEXT_FAMILY, FONT_UI, FONT_ICON
        FONT_UI_FAMILY   = _pick_ui_font()
        FONT_ICON_FAMILY = FONT_UI_FAMILY
        FONT_TEXT_FAMILY = FONT_UI_FAMILY
        FONT_UI   = (FONT_UI_FAMILY,   10)
        FONT_ICON = (FONT_ICON_FAMILY, 10)

        cfg = _load_config()
        self.text        = cfg.get("text", "展示タイトル")
        self.font_family = cfg.get("font_family") or _pick_font()
        self.font_bold   = bool(cfg.get("font_bold", True))
        self.text_color  = cfg.get("text_color", "#FFFFFF")
        self.bg_color    = cfg.get("bg_color", "#1A1A1A")
        self.alpha       = float(cfg.get("alpha", 0.92))
        self.bg_transparent = bool(cfg.get("bg_transparent", False))
        self.qr_url      = cfg.get("qr_url", "")
        self.qr_side     = cfg.get("qr_side", "right")  # "left" or "right"
        self.qr_visible  = bool(cfg.get("qr_visible", True))
        self._geometry   = cfg.get("geometry", "800x160+60+60")
        self._drag_x = self._drag_y = 0
        self._rsz_x = self._rsz_y = self._rsz_w = self._rsz_h = 0
        self._ref_font   = None
        self._ref_h      = 1
        self._ref_w      = 1

        self._build()
        self._bind()
        self._apply_platform_quirks()
        self._apply_colors()

        self.root.geometry(self._geometry)
        self.root.attributes('-alpha', self.alpha)
        self.root.deiconify()
        self.root.update_idletasks()
        if IS_MAC:
            self.root.lift()
            self.root.attributes('-topmost', True)
            # macOS の枠なしウィンドウは -topmost が抜けがちなので定期的に再前面化
            self._keep_on_top()
        self._rebuild_cache()
        self._refit()
        # 終了時に最終状態を保存
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.mainloop()

    def _on_quit(self):
        try:
            self._save_state()
        finally:
            self.root.quit()

    def _keep_on_top(self):
        if not getattr(self, '_suppress_lift', False):
            try:
                self.root.lift()
                self.root.attributes('-topmost', True)
            except tk.TclError:
                return
        self.root.after(1000, self._keep_on_top)

    # ── build UI ───────────────────────────────────────────────────────
    def _build(self):
        r = self.root
        _make_borderless(r)
        r.attributes('-topmost', True)
        r.configure(bg=self.bg_color, bd=0, highlightthickness=0)
        # macOS の NSWindow ドロップシャドウを消す（細いエッジラインの正体）
        if IS_MAC:
            try:
                r.tk.eval(
                    f"::tk::unsupported::MacWindowStyle style {r._w} plain {{noShadow}}"
                )
            except tk.TclError:
                pass

        self.frame = tk.Frame(r, bg=self.bg_color, bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Canvas で描画（Label のフォント上下マージンを回避し、bbox で正確に中央配置）
        self.canvas = tk.Canvas(
            self.frame, bg=self.bg_color,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._text_id = self.canvas.create_text(
            0, 0, text=self.text, fill=self.text_color,
            font=self._font(REF_PT), anchor="center",
        )
        self.canvas.bind('<Configure>', lambda e: self._redraw_text())
        # 既存コードが self.label を参照しているので Canvas をエイリアス
        self.label = self.canvas

        # macOS の Tk は "size_nw_se" を受け付けない（TclError）
        resize_cursor = "crosshair" if IS_MAC else "size_nw_se"
        # grip は透明（テキスト色を背景と同じにして見えなくする）。
        # 当たり判定だけ残してドラッグでリサイズできるようにする。
        self.grip = tk.Label(
            r, text="◢", font=("Arial", 11),
            fg=self.bg_color, bg=self.bg_color,
            cursor=resize_cursor, padx=3, pady=1,
        )
        self.grip.place(relx=1.0, rely=1.0, anchor="se")

    def _apply_platform_quirks(self):
        """OS 固有の挙動補正。"""
        if IS_MAC:
            # Mac の overrideredirect ウィンドウは Dock に出ることがある。
            # AppKit の LSUIElement 相当を実行時に効かせる試み（失敗しても無視）。
            try:
                from ctypes import cdll
                cdll.LoadLibrary(
                    '/System/Library/Frameworks/AppKit.framework/AppKit'
                )
            except Exception:
                pass
        if IS_LINUX:
            # 一部 WM では -topmost が無視されるので type="dock" 風にしておく
            try:
                self.root.attributes('-type', 'dock')
            except Exception:
                pass

    def _font(self, size):
        return (self.font_family, size, "bold" if self.font_bold else "normal")

    def _apply_colors(self):
        if self.bg_transparent and IS_MAC:
            try:
                self.root.attributes('-transparent', True)
                bg = 'systemTransparent'
            except tk.TclError:
                self.bg_transparent = False
                bg = self.bg_color
        else:
            if IS_MAC:
                try:
                    self.root.attributes('-transparent', False)
                except tk.TclError:
                    pass
            bg = self.bg_color
        self.root.configure(bg=bg)
        self.frame.configure(bg=bg)
        self.canvas.configure(bg=bg)
        self.canvas.itemconfigure(self._text_id, fill=self.text_color)
        # grip は背景に紛れさせる（クリック判定だけ残す）
        self.grip.configure(bg=bg, fg=bg)

    # ── font fitting ───────────────────────────────────────────────────
    def _rebuild_cache(self):
        # 参照サイズで実際に描画して bbox を測る（フォント間で実描画範囲が揃う）
        weight = "bold" if self.font_bold else "normal"
        self._ref_font = tkfont.Font(family=self.font_family,
                                     size=REF_PT, weight=weight)
        # 実描画範囲を測るための隠し Canvas
        if not hasattr(self, '_probe_canvas'):
            self._probe_canvas = tk.Canvas(self.root, width=1, height=1,
                                           highlightthickness=0)
        probe = self._probe_canvas
        probe.delete('all')
        tid = probe.create_text(0, 0, text=self.text, font=self._font(REF_PT),
                                anchor='nw')
        bbox = probe.bbox(tid)
        if bbox:
            x1, y1, x2, y2 = bbox
            self._ref_h = max(1, y2 - y1)
            self._ref_w = max(1, x2 - x1)
        else:
            self._ref_h = 1
            self._ref_w = 1

    def _qr_area(self, win_h):
        """QR 表示領域の幅。win_h と同じ正方形 + パディング。"""
        if not self.qr_url or not HAS_QR or not self.qr_visible:
            return 0
        # QR は高さ - PAD_Y*2 の正方形、左右にも余白
        return max(1, win_h - 2 * PAD_Y) + PAD_X

    def _compute_font_size(self, win_w, win_h):
        avail_w = max(1, win_w - 2 * PAD_X - self._qr_area(win_h))
        avail_h = max(1, win_h - 2 * PAD_Y)
        scale_h = avail_h / self._ref_h
        scale_w = avail_w / self._ref_w
        return max(6, int(REF_PT * min(scale_h, scale_w)))

    def _refit(self, w=None, h=None):
        if w is None: w = self.root.winfo_width()
        if h is None: h = self.root.winfo_height()
        if w <= 1 or h <= 1: return
        size = self._compute_font_size(w, h)
        self.canvas.itemconfigure(self._text_id, font=self._font(size))
        self._redraw_text()
        self._redraw_qr()

    def _redraw_text(self):
        """Canvas 内のテキストをテキスト領域の中心に置く。QR がある側を避ける。"""
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return
        qr_area = self._qr_area(ch)
        text_left = qr_area if (qr_area and self.qr_side == "left") else 0
        text_right = cw - qr_area if (qr_area and self.qr_side == "right") else cw
        text_w = max(1, text_right - text_left)
        # 一旦 (0,0) anchor=nw に置いて bbox を測り、そこから中心オフセットを計算
        self.canvas.coords(self._text_id, 0, 0)
        self.canvas.itemconfigure(self._text_id, anchor='nw')
        bbox = self.canvas.bbox(self._text_id)
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        tw, th = x2 - x1, y2 - y1
        cx = text_left + (text_w - tw) / 2 - x1
        cy = (ch - th) / 2 - y1
        self.canvas.coords(self._text_id, cx, cy)

    def _redraw_qr(self):
        """QR コードを Canvas 上に描画する。"""
        # 既存の QR をクリア
        if hasattr(self, '_qr_id') and self._qr_id is not None:
            self.canvas.delete(self._qr_id)
            self._qr_id = None
        self._qr_image = None  # ImageTk の参照保持用
        if not self.qr_url or not HAS_QR or not self.qr_visible:
            return
        ch = self.canvas.winfo_height()
        cw = self.canvas.winfo_width()
        if cw <= 1 or ch <= 1:
            return
        size = max(1, ch - 2 * PAD_Y)
        try:
            qr = qrcode.QRCode(border=1, box_size=10)
            qr.add_data(self.qr_url)
            qr.make(fit=True)
            # スキャン精度のため黒/白で固定
            img = qr.make_image(fill_color="black",
                                back_color="white").convert("RGB")
            img = img.resize((size, size), Image.NEAREST)
            self._qr_image = ImageTk.PhotoImage(img)
        except Exception:
            return
        if self.qr_side == "left":
            x = PAD_X // 2
        else:
            x = cw - size - PAD_X // 2
        y = (ch - size) // 2
        self._qr_id = self.canvas.create_image(x, y, image=self._qr_image,
                                                anchor='nw')
        # grip を Canvas より下に沈めて QR を見せる
        try:
            self.grip.lower(self.canvas)
        except tk.TclError:
            pass

    # ── bindings ───────────────────────────────────────────────────────
    def _bind(self):
        # 右クリックは Linux/Win では <Button-3>、macOS でも <Button-2>/<Button-3>
        rclick_events = ('<Button-3>', '<Button-2>')
        if IS_MAC:
            rclick_events = ('<Button-2>', '<Button-3>', '<Control-Button-1>')

        for w in (self.frame, self.label):
            w.bind('<Button-1>',        self._drag_start)
            w.bind('<B1-Motion>',       self._drag_move)
            w.bind('<ButtonRelease-1>', lambda e: self._save_state())
            w.bind('<Double-Button-1>', lambda e: self._start_inline_edit())
            w.bind('<Motion>',          self._update_cursor)
            for ev in rclick_events:
                w.bind(ev, self._show_menu)
        # grip のイベントは root に伝播させない（ドラッグと競合するため）
        self.grip.bind('<Button-1>',  self._rsz_start)
        self.grip.bind('<B1-Motion>', self._rsz_move)
        def _grip_up(e):
            self._rsz_active = False
            self._save_state()
            return 'break'
        self.grip.bind('<ButtonRelease-1>', _grip_up)
        # ウィンドウリサイズ時にフォントを連動
        self.root.bind('<Configure>', self._on_configure)

    def _on_configure(self, e):
        # _rsz_move 経由でリサイズ中は重複呼び出しになるので何もしない
        if e.widget is self.root and not getattr(self, '_rsz_active', False):
            self._refit(e.width, e.height)

    def _update_cursor(self, e):
        if getattr(self, '_mode', None) == 'resize':
            return
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        rx = e.x_root - self.root.winfo_x()
        ry = e.y_root - self.root.winfo_y()
        edges = self._hit_edges(rx, ry, rw, rh)
        # macOS Tk は size_* 系を受け付けないので crosshair で代替
        if IS_MAC:
            cursor = "crosshair" if edges else ""
        else:
            cmap = {
                "n": "size_ns", "s": "size_ns",
                "e": "size_we", "w": "size_we",
                "ne": "size_ne_sw", "sw": "size_ne_sw",
                "nw": "size_nw_se", "se": "size_nw_se",
            }
            cursor = cmap.get(edges, "")
        try:
            e.widget.configure(cursor=cursor)
        except tk.TclError:
            pass

    def _hit_edges(self, rx, ry, rw, rh, hot=12):
        """ポインタ位置からどの辺/角に当たっているか返す ('n','s','e','w' の組合せ)。"""
        edges = ""
        if ry < hot:                edges += "n"
        elif ry >= rh - hot:        edges += "s"
        if rx < hot:                edges += "w"
        elif rx >= rw - hot:        edges += "e"
        return edges

    def _drag_start(self, e):
        m = getattr(self, '_active_menu', None)
        if m is not None:
            try:
                m.destroy()
            except tk.TclError:
                pass
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        rx = e.x_root - self.root.winfo_x()
        ry = e.y_root - self.root.winfo_y()
        edges = self._hit_edges(rx, ry, rw, rh)
        if edges:
            self._mode = 'resize'
            self._rsz_edges = edges
            self._rsz_start(e)
            return
        self._mode = 'drag'
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        if getattr(self, '_mode', 'drag') == 'resize':
            self._rsz_move(e)
            return
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _rsz_start(self, e):
        self._rsz_active = True
        self._rsz_x = e.x_root
        self._rsz_y = e.y_root
        self._rsz_w = self.root.winfo_width()
        self._rsz_h = self.root.winfo_height()
        self._rsz_origin_x = self.root.winfo_x()
        self._rsz_origin_y = self.root.winfo_y()
        return 'break'

    def _rsz_move(self, e):
        edges = getattr(self, '_rsz_edges', 'se')
        dx = e.x_root - self._rsz_x
        dy = e.y_root - self._rsz_y
        x = self._rsz_origin_x
        y = self._rsz_origin_y
        w = self._rsz_w
        h = self._rsz_h
        if 'e' in edges:
            w = max(self.MIN_W, self._rsz_w + dx)
        if 'w' in edges:
            new_w = max(self.MIN_W, self._rsz_w - dx)
            x = self._rsz_origin_x + (self._rsz_w - new_w)
            w = new_w
        if 's' in edges:
            h = max(self.MIN_H, self._rsz_h + dy)
        if 'n' in edges:
            new_h = max(self.MIN_H, self._rsz_h - dy)
            y = self._rsz_origin_y + (self._rsz_h - new_h)
            h = new_h
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self._refit(w, h)
        return 'break'

    # ── context menu ───────────────────────────────────────────────────
    def _show_menu(self, e):
        # macOS では OS 標準のメニューを使う（最前面・自動クローズが正しく動く）
        if IS_MAC:
            prev = getattr(self, '_native_menu', None)
            if prev is not None:
                try:
                    prev.unpost()
                    prev.destroy()
                except tk.TclError:
                    pass
            m = tk.Menu(self.root, tearoff=0)
            m.add_command(label="テキストを編集", command=self._start_inline_edit)
            m.add_command(label="フォントを変更", command=self.change_font)
            m.add_command(label="太字 切替",     command=self.toggle_bold)
            m.add_separator()
            m.add_command(label="文字色を変更", command=self.change_text_color)
            m.add_command(label="背景色を変更", command=self.change_bg_color)
            m.add_command(label="透明度を変更", command=self.change_alpha)
            m.add_separator()
            qr_label = "QRを編集..." if self.qr_url else "QRを設定..."
            m.add_command(label=qr_label, command=self.change_qr)
            if self.qr_url:
                vis_label = "QRを非表示" if self.qr_visible else "QRを表示"
                m.add_command(label=vis_label, command=self.toggle_qr_visible)
            m.add_separator()
            m.add_command(label="終了",         command=self._on_quit)
            self._native_menu = m
            m.tk_popup(e.x_root, e.y_root)
            return
        qr_label = "QRを編集..." if self.qr_url else "QRを設定..."
        vis_label = "QRを非表示" if self.qr_visible else "QRを表示"
        items = [
            (" T", "テキストを編集",    self._start_inline_edit),
            (" F", "フォントを変更",    self.change_font),
            (" B", "太字 切替",         self.toggle_bold),
            None,
            (" A", "文字色を変更",      self.change_text_color),
            ("[]", "背景色を変更",      self.change_bg_color),
            (" %", "透明度を変更",      self.change_alpha),
            None,
            (" Q", qr_label,            self.change_qr),
        ] + ([(">|", vis_label, self.toggle_qr_visible)] if self.qr_url else []) + [
            None,
            (" x", "終了",              self._on_quit),
        ]
        self._suppress_lift = True
        m = DarkMenu(self.root, items)
        def _on_close(_=None):
            self._suppress_lift = False
            self._active_menu = None
        m.bind('<Destroy>', _on_close)
        self._active_menu = m
        m.popup(e.x_root, e.y_root)

    # ── inline edit ────────────────────────────────────────────────────
    def _start_inline_edit(self):
        if hasattr(self, '_inline') and self._inline:
            return
        self._inline = True

        cur_font = self.canvas.itemcget(self._text_id, 'font')
        self.canvas.pack_forget()

        self._editor = tk.Text(
            self.frame,
            font=cur_font,
            fg=self.text_color,
            bg=self.bg_color,
            insertbackground=self.text_color,
            selectbackground="#7C6FCD",
            selectforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            padx=PAD_X, pady=PAD_Y,
            wrap=tk.WORD,
            highlightthickness=1,
            highlightcolor="#7C6FCD",
            highlightbackground="#444444",
        )
        self._editor.insert("1.0", self.text)
        self._editor.pack(fill=tk.BOTH, expand=True)
        self._editor.focus_set()
        self._editor.mark_set("insert", tk.END)

        self._editor.bind('<Return>',       self._inline_commit)
        self._editor.bind('<Shift-Return>', lambda e: None)
        self._editor.bind('<Escape>',       self._inline_cancel)
        self._editor.bind('<FocusOut>',     self._inline_commit)

    def _inline_commit(self, e=None):
        if not getattr(self, '_inline', False):
            return 'break'
        t = self._editor.get("1.0", tk.END).rstrip('\n')
        self._inline = False
        self._editor.destroy()
        self._editor = None
        if t:
            self.text = t
        self.canvas.itemconfigure(self._text_id, text=self.text)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._rebuild_cache()
        self._refit()
        self._save_state()
        return 'break'

    def _inline_cancel(self, e=None):
        if not getattr(self, '_inline', False):
            return
        self._inline = False
        self._editor.destroy()
        self._editor = None
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # ── actions ───────────────────────────────────────────────────────
    def edit_text(self):
        self._start_inline_edit()

    def _save_state(self):
        _save_config({
            "text":        self.text,
            "font_family": self.font_family,
            "font_bold":   self.font_bold,
            "text_color":  self.text_color,
            "bg_color":    self.bg_color,
            "alpha":       self.alpha,
            "geometry":    self.root.geometry(),
            "qr_url":      self.qr_url,
            "qr_side":     self.qr_side,
            "qr_visible":  self.qr_visible,
        })

    def toggle_bold(self):
        self.font_bold = not self.font_bold
        self._rebuild_cache()
        self._refit()
        self._save_state()

    def _yield_topmost(self):
        """ダイアログ表示中はメインの最前面化を一時的に切る。"""
        self._suppress_lift = True
        try:
            self.root.attributes('-topmost', False)
        except tk.TclError:
            pass

    def _restore_topmost(self):
        self._suppress_lift = False
        try:
            self.root.attributes('-topmost', True)
        except tk.TclError:
            pass

    def change_font(self):
        self._yield_topmost()
        d = FontPickerDialog(
            self.root, self.font_family,
            on_pick=self._set_font,
            on_preview=self._set_font,
        )
        d.bind('<Destroy>', lambda e: self._restore_topmost())

    def _set_font(self, family):
        self.font_family = family
        self._rebuild_cache()
        self._refit()
        self._save_state()

    def change_text_color(self):
        c = colorchooser.askcolor(color=self.text_color, parent=self.root,
                                   title="文字色を選択")
        if c[1]:
            self.text_color = c[1]
            self.canvas.itemconfigure(self._text_id, fill=self.text_color)
            self._save_state()

    def change_bg_color(self):
        c = colorchooser.askcolor(color=self.bg_color, parent=self.root,
                                   title="背景色を選択")
        if c[1]:
            self.bg_color = c[1]
            self.bg_transparent = False
            self._apply_colors()
            self._save_state()

    def toggle_transparent_bg(self):
        self.bg_transparent = not self.bg_transparent
        self._apply_colors()
        self._save_state()

    def change_alpha(self):
        def on_ok(v):
            self.alpha = v / 100.0
            self.root.attributes('-alpha', self.alpha)
            self._save_state()
        self._yield_topmost()
        d = DarkSliderDialog(self.root, "透明度", int(self.alpha * 100),
                             10, 100, "%", on_ok)
        d.bind('<Destroy>', lambda e: self._restore_topmost())

    def change_qr(self):
        if not HAS_QR:
            return
        def on_ok(url, side):
            self.qr_url = url
            self.qr_side = side
            self._refit()
            self._save_state()
        self._yield_topmost()
        d = QRSettingsDialog(self.root, self.qr_url, self.qr_side, on_ok)
        d.bind('<Destroy>', lambda e: self._restore_topmost())

    def clear_qr(self):
        self.qr_url = ""
        self._refit()
        self._save_state()

    def toggle_qr_visible(self):
        self.qr_visible = not self.qr_visible
        self._refit()
        self._save_state()


if __name__ == "__main__":
    try:
        import tkinter  # noqa: F401
    except ImportError:
        msg = "tkinter が見つかりません。"
        if platform.system() == "Linux":
            msg += "\n  Ubuntu/Debian: sudo apt install python3-tk"
            msg += "\n  Fedora       : sudo dnf install python3-tkinter"
        print(msg)
        sys.exit(1)
    Overlay()
