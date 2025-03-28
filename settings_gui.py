import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import configparser
import os

CONFIG_FILE = 'config.ini'
DEFAULT_SAVE_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
DEFAULT_QUALITY = 90
DEFAULT_HOTKEY = '<ctrl>+<shift>+s'

class SettingsWindow:
    def __init__(self, parent, config, save_callback):
        self.config = config
        self.save_callback = save_callback

        self.top = tk.Toplevel(parent)
        self.top.title("設定")
        self.top.geometry("400x200")
        self.top.transient(parent) # 親ウィンドウの上に表示
        self.top.deiconify() # ウィンドウを明示的に表示
        self.top.grab_set() # モーダルにする
        self.top.focus_force() # フォーカスを強制的に設定
        print("設定ウィンドウを初期化しました。") # デバッグ用ログ

        # 保存先フォルダ
        tk.Label(self.top, text="保存先フォルダ:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.save_dir_var = tk.StringVar(value=self.config.get('CaptureSettings', 'save_directory', fallback=DEFAULT_SAVE_DIR))
        self.save_dir_entry = tk.Entry(self.top, textvariable=self.save_dir_var, width=40)
        self.save_dir_entry.grid(row=0, column=1, padx=5, pady=5)
        self.browse_button = tk.Button(self.top, text="参照...", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        # JPEG品質
        tk.Label(self.top, text="JPEG品質 (1-100):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.quality_var = tk.IntVar(value=self.config.getint('CaptureSettings', 'jpeg_quality', fallback=DEFAULT_QUALITY))
        self.quality_scale = ttk.Scale(self.top, from_=1, to=100, orient=tk.HORIZONTAL, variable=self.quality_var, length=200, command=self._update_quality_label)
        self.quality_scale.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.quality_label = tk.Label(self.top, text=str(self.quality_var.get()))
        self.quality_label.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        # ホットキー設定
        tk.Label(self.top, text="キャプチャホットキー:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.hotkey_var = tk.StringVar(value=self.config.get('CaptureSettings', 'hotkey', fallback=DEFAULT_HOTKEY))
        self.hotkey_entry = tk.Entry(self.top, textvariable=self.hotkey_var, width=20)
        self.hotkey_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        tk.Label(self.top, text="(例: <ctrl>+<alt>+p)").grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)


        # 保存・キャンセルボタン
        button_frame = tk.Frame(self.top)
        button_frame.grid(row=3, column=0, columnspan=3, pady=15)
        self.save_button = tk.Button(button_frame, text="保存して閉じる", command=self.save_and_close)
        self.save_button.pack(side=tk.LEFT, padx=10)
        self.cancel_button = tk.Button(button_frame, text="キャンセル", command=self.top.destroy)
        self.cancel_button.pack(side=tk.LEFT, padx=10)

        self.top.protocol("WM_DELETE_WINDOW", self.top.destroy) # xボタンで閉じる

    def _update_quality_label(self, value):
        # スケールの整数値のみラベルに表示
        self.quality_label.config(text=str(int(float(value))))

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if directory:
            self.save_dir_var.set(directory)

    def save_and_close(self):
        save_dir = self.save_dir_var.get()
        quality = self.quality_var.get()
        hotkey = self.hotkey_var.get().lower() # ホットキーは小文字で統一

        if not os.path.isdir(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except OSError:
                messagebox.showerror("エラー", f"保存先フォルダを作成できませんでした:\n{save_dir}", parent=self.top)
                return

        if not (1 <= quality <= 100):
            messagebox.showerror("エラー", "JPEG品質は1から100の間で指定してください。", parent=self.top)
            return

        # TODO: ホットキーのバリデーションを追加するとより親切

        self.config['CaptureSettings'] = {
            'save_directory': save_dir,
            'jpeg_quality': str(quality),
            'hotkey': hotkey
        }
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                self.config.write(configfile)
            self.save_callback() # メインアプリに設定変更を通知
            self.top.destroy()
        except IOError:
            messagebox.showerror("エラー", f"{CONFIG_FILE}への書き込みに失敗しました。", parent=self.top)

# --- 設定読み込み/デフォルト作成 ---
def load_config():
    config = configparser.ConfigParser()
    # デフォルト値を設定
    config['CaptureSettings'] = {
        'save_directory': DEFAULT_SAVE_DIR,
        'jpeg_quality': str(DEFAULT_QUALITY),
        'hotkey': DEFAULT_HOTKEY
    }
    # ファイルが存在すれば読み込み、なければデフォルトで作成
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        # デフォルト保存先フォルダが存在しない場合は作成試行
        default_dir = config.get('CaptureSettings', 'save_directory')
        if not os.path.exists(default_dir):
            try:
                os.makedirs(default_dir, exist_ok=True)
            except OSError as e:
                print(f"Warning: Default save directory creation failed: {e}")
                # エラーが発生した場合、ユーザーのホームディレクトリなどにフォールバックも検討
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except IOError as e:
             print(f"Warning: Failed to write initial config file: {e}")
    return config

def get_save_directory(config):
    return config.get('CaptureSettings', 'save_directory', fallback=DEFAULT_SAVE_DIR)

def get_jpeg_quality(config):
    return config.getint('CaptureSettings', 'jpeg_quality', fallback=DEFAULT_QUALITY)

def get_hotkey(config):
    return config.get('CaptureSettings', 'hotkey', fallback=DEFAULT_HOTKEY)

if __name__ == '__main__':
    # テスト用
    root = tk.Tk()
    root.withdraw() # メインウィンドウは非表示
    config = load_config()

    def on_save():
        print("設定が保存されました。")
        # 必要ならここで設定を再読み込みするなどの処理
        print("新しいホットキー:", get_hotkey(config))

    app = SettingsWindow(root, config, on_save)
    root.mainloop()