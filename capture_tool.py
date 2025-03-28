import tkinter as tk
from PIL import ImageGrab, Image, ImageTk
import mss
import mss.tools
import time
import os

class CaptureWindow:
    def __init__(self, root, save_dir, quality, callback):
        self.root = root
        self.save_dir = save_dir
        self.quality = quality
        self.callback = callback # キャプチャ完了時に呼び出す関数

        self.top = tk.Toplevel(root)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.3) # 少し透明にする
        self.top.overrideredirect(True) # ウィンドウ枠を消す
        self.top.wait_visibility(self.top) # ウィンドウが表示されるのを待つ
        self.top.grab_set() # 他のウィンドウ操作をブロック

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="grey", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.top.bind("<Escape>", self.cancel_capture) # Escキーでキャンセル

        # 全画面のスクリーンショットを背景として保持 (mssの方が高速)
        self.bg_image = None # 初期化
        try:
            with mss.mss() as sct:
                # プライマリモニターを取得しようとする
                # マルチモニター環境など、モニター[0]が存在しない/アクセスできない場合がある
                if not sct.monitors or len(sct.monitors) < 2: # 通常 monitors[1] が全画面
                    print("エラー: mssがモニターを検出できませんでした。monitors:", sct.monitors)
                    self.top.destroy()
                    self.callback(None)
                    return # 初期化失敗

                # monitor = sct.monitors[0] # プライマリモニター全体を試みる - 問題がある場合がある
                monitor = sct.monitors[1] # 全画面を含むモニターを選択 (より安全な場合が多い)
                print(f"mss: 使用するモニター情報: {monitor}") # デバッグ情報追加
                im_bytes = sct.grab(monitor)
                self.bg_image = Image.frombytes("RGB", im_bytes.size, im_bytes.bgra, "raw", "BGRX")
        except Exception as e:
            print(f"エラー: mssでの初期スクリーンショット取得に失敗しました: {e}")
            import traceback
            traceback.print_exc() # スタックトレースを出力
            # エラーが発生した場合、ウィンドウを閉じてコールバックを呼ぶ
            try:
                self.top.destroy()
            except tk.TclError:
                 print("ウィンドウは既に破棄されています。") # destroyが複数回呼ばれる可能性への対処
            self.callback(None)
            return # 初期化失敗


        # ImageTkオブジェクトを作成してCanvasの背景に設定（任意、重くなる可能性あり）
        # self.bg_photo = ImageTk.PhotoImage(self.bg_image)
        # self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_photo)

    def on_button_press(self, event):
        self.start_x = self.canvas.winfo_pointerx()
        self.start_y = self.canvas.winfo_pointery()
        # 古い矩形があれば削除
        if self.rect:
            self.canvas.delete(self.rect)
        # 新しい矩形を作成（最初は見えない）
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                outline='red', width=2)

    def on_mouse_drag(self, event):
        cur_x = self.canvas.winfo_pointerx()
        cur_y = self.canvas.winfo_pointery()
        # 矩形を更新
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x = self.canvas.winfo_pointerx()
        end_y = self.canvas.winfo_pointery()
        self.top.destroy() # キャプチャウィンドウを閉じる

        # 座標を正規化 (左上 < 右下)
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        # 幅や高さが0の場合はキャプチャしない
        if x1 == x2 or y1 == y2:
            print("キャプチャ範囲が無効です。")
            self.callback(None) # キャンセル扱い
            return

        # mss を使って指定範囲をキャプチャ
        try:
            bbox = {'top': y1, 'left': x1, 'width': x2 - x1, 'height': y2 - y1}
            with mss.mss() as sct:
                sct_img = sct.grab(bbox)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # ファイル名を生成
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            ms = int(time.time() * 1000) % 1000
            filename = f"{timestamp}_{ms:03d}.jpg"
            save_path = os.path.join(self.save_dir, filename)

            # JPEGで保存
            img.save(save_path, 'JPEG', quality=self.quality, optimize=True)
            print(f"スクリーンショットを保存しました: {save_path}")
            self.callback(save_path) # 保存成功、パスを通知

        except Exception as e:
            print(f"キャプチャまたは保存中にエラーが発生しました: {e}")
            self.callback(None) # エラー発生


    def cancel_capture(self, event=None):
        print("キャプチャをキャンセルしました。")
        self.top.destroy()
        self.callback(None) # キャンセル


def start_capture(root, save_dir, quality, callback):
    # 既存のCaptureWindowがあれば破棄（念のため）
    for widget in root.winfo_children():
        if isinstance(widget, tk.Toplevel) and hasattr(widget, 'is_capture_window'):
            widget.destroy()

    # キャプチャウィンドウ作成
    cap_win = CaptureWindow(root, save_dir, quality, callback)
    cap_win.top.is_capture_window = True # 目印


if __name__ == '__main__':
    # テスト用
    root = tk.Tk()
    root.withdraw() # メインウィンドウ非表示

    save_directory = "./test_captures" # テスト用保存先
    if not os.path.exists(save_directory):
        os.makedirs(save_directory)
    jpeg_quality = 85

    def capture_finished(saved_path):
        if saved_path:
            print(f"キャプチャ完了: {saved_path}")
        else:
            print("キャプチャ失敗またはキャンセル")
        # テスト終了
        # root.quit()

    print(f"キャプチャを開始します。保存先: {save_directory}, 品質: {jpeg_quality}")
    print("画面をドラッグして範囲を選択してください。Escキーでキャンセル。")
    start_capture(root, save_directory, jpeg_quality, capture_finished)
    root.mainloop()