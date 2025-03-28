import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
import configparser
import os
from datetime import datetime

class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        root.title("スクリーンキャプチャアプリ")

        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"
        self.load_config()

        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.rect_id = None

        self.create_widgets()

    def load_config(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
            if 'JPEG' not in self.config:
                self.config['JPEG'] = {}
            if 'SAVE' not in self.config:
                self.config['SAVE'] = {}
        else:
            self.config['JPEG'] = {'quality': '80'}
            self.config['SAVE'] = {'directory': os.path.expanduser("~/Pictures")}
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def create_widgets(self):
        # JPEG設定フレーム
        jpeg_frame = ttk.LabelFrame(self.root, text="JPEG設定")
        jpeg_frame.pack(padx=10, pady=10, fill=tk.X)

        ttk.Label(jpeg_frame, text="品質:").pack(side=tk.LEFT, padx=5, pady=5)
        self.quality_var = tk.StringVar(value=self.config['JPEG'].get('quality', '80'))
        quality_scale = ttk.Scale(
            jpeg_frame,
            from_=1, to=100,
            orient=tk.HORIZONTAL,
            variable=self.quality_var,
            command=self.update_quality_label
        )
        quality_scale.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        self.quality_label = ttk.Label(jpeg_frame, text=f"{self.quality_var.get()}%")
        self.quality_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.quality_var.trace("w", self.update_config_quality)


        # 保存場所フレーム
        save_frame = ttk.LabelFrame(self.root, text="保存場所設定")
        save_frame.pack(padx=10, pady=10, fill=tk.X)

        ttk.Label(save_frame, text="保存場所:").pack(side=tk.LEFT, padx=5, pady=5)
        self.dir_var = tk.StringVar(value=self.config['SAVE'].get('directory', os.path.expanduser("~/Pictures")))
        dir_entry = ttk.Entry(save_frame, textvariable=self.dir_var, width=50)
        dir_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.dir_var.trace("w", self.update_config_dir)


        # キャプチャボタン
        capture_button = ttk.Button(self.root, text="範囲指定キャプチャ", command=self.start_capture_area)
        capture_button.pack(pady=20)

    def update_quality_label(self, value):
        self.quality_label.config(text=f"{int(float(value))}%")

    def update_config_quality(self, *args):
         self.config['JPEG']['quality'] = self.quality_var.get()
         self.save_config()

    def update_config_dir(self, *args):
        self.config['SAVE']['directory'] = self.dir_var.get()
        self.save_config()

    def start_capture_area(self):
        self.root.withdraw()  # メインウィンドウを非表示
        self.overlay_root = tk.Tk()
        self.overlay_root.attributes('-fullscreen', True)
        self.overlay_root.attributes('-alpha', 0.3) # 半透明
        self.overlay_canvas = tk.Canvas(self.overlay_root, cursor="cross")
        self.overlay_canvas.pack(fill=tk.BOTH, expand=True)

        self.overlay_canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.overlay_canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.overlay_canvas.bind("<B1-Motion>", self.on_mouse_motion)

        self.overlay_root.mainloop()


    def on_mouse_down(self, event):
        self.start_x = self.overlay_canvas.canvasx(event.x)
        self.start_y = self.overlay_canvas.canvasy(event.y)
        if self.rect_id:
            self.overlay_canvas.delete(self.rect_id)
            self.rect_id = None


    def on_mouse_motion(self, event):
        cur_x = self.overlay_canvas.canvasx(event.x)
        cur_y = self.overlay_canvas.canvasy(event.y)

        if not self.rect_id:
            self.rect_id = self.overlay_canvas.create_rectangle(self.start_x, self.start_y, cur_x, cur_y, outline='red')
        else:
            self.overlay_canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)


    def on_mouse_up(self, event):
        self.end_x = self.overlay_canvas.canvasx(event.x)
        self.end_y = self.overlay_canvas.canvasy(event.y)
        self.overlay_root.destroy()
        self.root.deiconify() # メインウィンドウを再表示
        self.capture_screenshot()


    def capture_screenshot(self):
        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)

        bbox = (x0, y0, x1, y1)
        im = ImageGrab.grab(bbox=bbox)

        save_dir = self.dir_var.get()
        os.makedirs(save_dir, exist_ok=True) # ディレクトリが存在しない場合は作成

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.jpg"
        save_path = os.path.join(save_dir, filename)

        quality = int(self.quality_var.get())
        im.save(save_path, 'JPEG', quality=quality)
        tk.messagebox.showinfo("キャプチャ完了", f"画像を保存しました: {save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()
