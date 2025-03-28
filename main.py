import pystray
from PIL import Image, ImageDraw
import threading
from pynput import keyboard
import tkinter as tk
import configparser
import os
import traceback # エラー出力用にインポート
import sys # コマンドライン引数用にインポート
import argparse # コマンドライン引数解析用にインポート

# 他の自作モジュールをインポート
from settings_gui import SettingsWindow, load_config, get_save_directory, get_jpeg_quality, get_hotkey
from capture_tool import start_capture

CONFIG_FILE = 'config.ini'

# グローバル変数（スレッド間の共有用）
config = None
hotkey_listener = None
current_hotkey_comb = None
capture_in_progress = False # キャプチャ中のフラグ
root = None # Tkinterのルートウィンドウ
icon = None # pystrayのアイコンオブジェクト
settings_win = None # 設定ウィンドウのインスタンス

# --- タスクトレイアイコン関連 ---
def create_image(width, height, color1, color2):
    # 簡単なアイコンを生成
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 4, height // 4, width * 3 // 4, height * 3 // 4),
        fill=color2)
    return image

def open_settings():
    global config, root, settings_win
    if not root: # Tkinterのルートがなければ作成
        setup_tkinter_root()

    # 設定変更が保存されたときにホットキーを再登録するためのコールバック
    def on_settings_saved():
        print("設定が保存されたため、ホットキーを再読み込み・再登録します。")
        reload_hotkey()

    # 設定ウィンドウを表示（グローバル変数に保存）
    settings_win = SettingsWindow(root, config, on_settings_saved)
    
    # ウィンドウが閉じられるまで待機
    if settings_win and settings_win.top:
        settings_win.top.wait_window()
    
    print("設定ウィンドウが閉じられました。")

def exit_action(icon_obj, item): # 引数名をiconからicon_objに変更
    global hotkey_listener, root, icon
    print("アプリケーションを終了します。")
    if hotkey_listener:
        try:
            hotkey_listener.stop()
        except Exception as e:
            print(f"ホットキーリスナーの停止中にエラー: {e}")
    if root:
        try:
            # root.quit() はメインループを止めるだけなので、ウィンドウも破棄する
            root.destroy()
        except Exception as e:
            print(f"Tkinterウィンドウの破棄中にエラー: {e}")
    if icon: # グローバル変数 icon を使用
        try:
            icon.stop() # pystrayのループを終了
        except Exception as e:
            print(f"タスクトレイアイコンの停止中にエラー: {e}")
    print("終了処理が要求されました。") # mainloop終了後に実際の終了処理が行われる

def setup_tray_icon():
    global root, icon # グローバル変数 icon を使うように宣言
    if not root: # Tkinterのルートがなければ作成
        setup_tkinter_root()

    icon_image = create_image(64, 64, 'grey', 'red') # アイコン画像
    menu = (pystray.MenuItem('設定', open_settings),
            pystray.MenuItem('終了', exit_action))
    icon = pystray.Icon("ScreenCaptureApp", icon_image, "スクリーンキャプチャ", menu) # グローバル変数 icon に代入
    return icon

# タスクトレイスレッドのターゲット関数
def run_icon():
    global icon
    if not icon:
        print("エラー: アイコンオブジェクトがセットアップされていません。")
        return
    try:
        print("タスクトレイスレッドを開始します...")
        icon.run()
        print("タスクトレイスレッドが正常に終了しました。")
    except Exception as e:
        print(f"エラー: タスクトレイスレッドで例外が発生しました: {e}")
        traceback.print_exc() # 詳細なトレースバックを出力
    finally:
        print("タスクトレイスレッドのrunメソッドが終了しました。")


# --- ホットキー関連 ---
def on_activate():
    global capture_in_progress, config, root
    if capture_in_progress:
        print("既にキャプチャ処理が進行中です。")
        return

    print("ホットキーが押されました。キャプチャを開始します。")
    capture_in_progress = True

    if not root: # Tkinterのルートがなければ作成
        setup_tkinter_root()
        # Tkinterルートがない状態でホットキーが押された場合、
        # mainloopがまだ動いていない可能性があるので注意が必要。
        # ここでmainloopを開始するか、あるいはmainloopが開始されるのを待つ必要があるかもしれない。
        # 現状は setup_tkinter_root() でインスタンスを作るだけ。

    save_dir = get_save_directory(config)
    quality = get_jpeg_quality(config)

    # キャプチャ完了時のコールバック
    def capture_finished_callback(saved_path):
        global capture_in_progress
        capture_in_progress = False # フラグをリセット
        if saved_path:
            print(f"キャプチャ完了: {saved_path}")
        else:
            print("キャプチャ失敗またはキャンセル")

    # Tkinterの処理はメインスレッドで行う必要があるため、root.afterを使用
    # rootが確実に存在し、mainloopが実行されている前提
    if root:
        try:
            root.after(10, lambda: start_capture(root, save_dir, quality, capture_finished_callback))
        except tk.TclError as e:
             print(f"Tkinter afterスケジューリングエラー: {e} (mainloopが実行されていない可能性があります)")
             # mainloopが動いていない場合のエラー処理
             capture_in_progress = False # フラグを戻す
    else:
        print("エラー: Tkinterルートウィンドウが存在しないため、キャプチャを開始できません。")
        capture_in_progress = False # フラグを戻す


# ホットキーリスナースレッドのターゲット関数
def run_hotkey_listener():
    global hotkey_listener
    if not hotkey_listener:
        print("エラー: ホットキーリスナーオブジェクトがありません。")
        return
    try:
        print("ホットキーリスナースレッドを開始します...")
        hotkey_listener.run()
        print("ホットキーリスナースレッドが正常に終了しました。")
    except Exception as e:
        print(f"エラー: ホットキーリスナースレッドで例外が発生しました: {e}")
        traceback.print_exc()
    finally:
        print("ホットキーリスナースレッドのrunメソッドが終了しました。")


def start_hotkey_listener():
    global hotkey_listener, current_hotkey_comb, config
    hotkey_str = get_hotkey(config)
    current_hotkey_comb = keyboard.HotKey.parse(hotkey_str)

    def for_canonical(f):
        # pynputのホットキーリスナーに渡すためのラッパー
        # canonical が存在しない古いバージョンも考慮
        return lambda k: f(hotkey_listener.canonical(k) if hasattr(hotkey_listener, 'canonical') else k)

    # ホットキー定義
    hotkeys_map = {
        hotkey_str: on_activate
    }

    # リスナーを開始
    try:
        # pynput 1.7.7+ スタイルの呼び出しを試みる
        hotkey_listener = keyboard.GlobalHotKeys(hotkeys_map)
        print(f"ホットキー '{hotkey_str}' の監視を開始しました (GlobalHotKeys)。")
        # GlobalHotKeysの場合、runメソッドを持つスレッドを別途開始する必要がある
        listener_thread = threading.Thread(target=run_hotkey_listener, daemon=True)
        listener_thread.start()
        return listener_thread
    except TypeError:
        # 古い pynput バージョン (Listenerベース) の可能性
        try:
            def on_press(key):
                if key in current_hotkey_comb:
                    on_activate()

            # Listener を使う場合
            hotkey_listener = keyboard.Listener(on_press=on_press)
            print(f"ホットキー '{hotkey_str}' の監視を開始しました (Listener)。")
            # Listenerの場合、runメソッドを持つスレッドを別途開始する必要がある
            listener_thread = threading.Thread(target=run_hotkey_listener, daemon=True)
            listener_thread.start()
            return listener_thread
        except Exception as e:
            print(f"ホットキーリスナーの開始に失敗しました: {e}")
            traceback.print_exc()
            hotkey_listener = None
            return None


def stop_hotkey_listener():
    global hotkey_listener
    if hotkey_listener:
        print("ホットキーの監視を停止します。")
        try:
            hotkey_listener.stop()
        except Exception as e:
            print(f"ホットキーリスナーの停止中にエラー: {e}")
        traceback.print_exc()
        hotkey_listener = None

def reload_hotkey():
    stop_hotkey_listener()
    # start_hotkey_listener はスレッドを返すので、ここでは再起動のみ
    start_hotkey_listener()

# --- Tkinter関連 ---
def setup_tkinter_root(withdraw_window=True): # 引数を追加
    global root
    if root is None:
        try:
            print("Tkinterルートウィンドウを初期化します。")
            root = tk.Tk()
            if withdraw_window:
                root.withdraw() # 引数に応じて非表示にする
            print("Tkinterルートウィンドウの初期化完了。")
        except Exception as e:
            print(f"Tkinterルートウィンドウの初期化中にエラー: {e}")
            traceback.print_exc()
            root = None # エラー発生時はNoneに戻す

def run_tkinter_mainloop():
    global root
    if root:
        print("Tkinter mainloop を開始します...")
        try:
            root.mainloop()
        # mainloopが正常終了した場合（通常はexit_actionでquit/destroyされた場合）
            print("Tkinter mainloop が終了しました。")
        except Exception as e:
            print(f"Tkinter mainloop でエラーが発生しました: {e}")
            traceback.print_exc() # スタックトレースを詳細に出力
            messagebox.showerror("エラー", f"Tkinter mainloop でエラーが発生しました:\n{e}", parent=root) # エラーメッセージを表示
        finally:
            print("Tkinter mainloop 処理ブロックを抜けました。")
            # mainloopが終了したら、アプリケーション終了処理へ繋げる必要がある場合がある
            # exit_actionが呼ばれていれば、そちらで後続処理が行われる想定
    else:
        print("エラー: Tkinter ルートウィンドウがありません。mainloopを開始できません。")

# --- メイン処理 ---
if __name__ == "__main__":
    icon_thread = None
    hotkey_thread = None

    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="スクリーンキャプチャアプリケーション")
    parser.add_argument('--settings', action='store_true', help='起動時に設定画面を表示します')
    args = parser.parse_args()

    try:
        print("アプリケーションを開始します...")
        # 設定ファイルを読み込む（なければデフォルトで作成）
        config = load_config()

        if args.settings:
            # --- 設定モード ---
            print("設定モードで起動します...")
            # Tkinterのルートウィンドウを表示状態で準備
            setup_tkinter_root(withdraw_window=False)
            if not root:
                print("Tkinterの初期化に失敗したため、設定画面を起動できません。")
                exit()

            # 設定ウィンドウを開く
            open_settings()

            # Tkinterのメインループを開始（設定画面表示のため）
            run_tkinter_mainloop()

        else:
            # --- 通常モード（タスクトレイ） ---
            print("通常モード（タスクトレイ）で起動します...")
            # Tkinterのルートウィンドウを非表示で準備
            setup_tkinter_root(withdraw_window=True)
            if not root:
                 print("Tkinterの初期化に失敗したため、アプリケーションを起動できません。")
                 exit() # Tkinterがないと動作しないため終了

            # タスクトレイアイコンをセットアップ
            tray_icon = setup_tray_icon() # setup_tray_icon内でグローバル変数iconに代入される

            # タスクトレイスレッドを開始
            icon_thread = threading.Thread(target=run_icon, daemon=True) # ターゲットをrun_iconに変更
            icon_thread.start()

            # ホットキーリスナーを開始
            hotkey_thread = start_hotkey_listener() # スレッドオブジェクトを受け取る

        print("-" * 30)
        print("スクリーンキャプチャアプリが起動しました。")
        print(f"タスクトレイアイコンから設定変更、終了が可能です。")
        if hotkey_listener:
             print(f"ホットキー '{get_hotkey(config)}' でキャプチャを開始します。")
        else:
             print("警告: ホットキーリスナーの起動に失敗しました。")
        print("-" * 30)

            # Tkinterのメインループを開始（設定画面やキャプチャ画面の表示に必要）
            # これが終了するとプログラム全体が終了する
        run_tkinter_mainloop()

    except Exception as e:
        print(f"アプリケーションのメイン処理で予期せぬエラーが発生しました: {e}")
        traceback.print_exc()

    finally:
        # --- 終了処理 (共通) ---
        print("アプリケーションの終了処理を開始します...")

        # mainloopが終了した or 例外が発生した場合のクリーンアップ
        stop_hotkey_listener() # ホットキーリスナーを停止 (通常モードでのみ意味があるが、呼んでも問題ない)

        if icon and icon.visible: # iconオブジェクトが存在し、表示されている場合のみ停止
             print("タスクトレイアイコンを停止します...")
             try:
                 icon.stop()
             except Exception as e:
                 print(f"タスクトレイアイコンの停止中にエラー: {e}")

        # スレッドの終了を待機（メインループが終了しないとここには来ない想定）
        if icon_thread and icon_thread.is_alive():
            print("タスクトレイスレッドの終了を待機...")
            icon_thread.join(timeout=2.0)
            if icon_thread.is_alive():
                print("警告: タスクトレイスレッドが時間内に終了しませんでした。")
        if hotkey_thread and hotkey_thread.is_alive():
             # hotkey_listener.stop()が呼ばれていれば、runメソッドは終了するはず
             print("ホットキーリスナースレッドの終了を待機...")
             hotkey_thread.join(timeout=2.0)
             if hotkey_thread.is_alive():
                 print("警告: ホットキーリスナースレッドが時間内に終了しませんでした。")

        print("アプリケーションが完全に終了しました。")