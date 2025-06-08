import os
import json
import threading
import socket
import queue
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import re
from datetime import datetime
from pathlib import Path
import logging
import uuid

# ------------------------------
# Логирование
# ------------------------------
LOG_GUI_FILE = "gui_client.log"
logging.basicConfig(
    filename=LOG_GUI_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(module)s:%(lineno)d %(funcName)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    filemode='w'
)
logging.info("=== GUI Клиент запускается ===")

# ------------------------------
# Настройки
# ------------------------------
SETTINGS_FILE = "user_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек: {e}")
    return {
        "last_username": "", "theme": "Современная тёмная", "auto_scroll": True,
        "font_size": 11, "window_geometry": "1200x800",
        "default_download_path": str(Path.home() / "Downloads")
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Ошибка сохранения настроек: {e}")

USER_SETTINGS = load_settings()

# ------------------------------
# Темы
# ------------------------------
THEMES = {
    "Современная тёмная": {"BG_COLOR": "#0d1117", "TEXT_COLOR": "#f0f6fc", "TEXT_SECONDARY": "#8b949e","ENTRY_BG": "#21262d", "ENTRY_FG": "#f0f6fc", "ENTRY_BORDER": "#30363d", "ENTRY_FOCUS": "#58a6ff","BTN_BG": "#21262d", "BTN_HOVER": "#30363d", "BTN_ACTIVE": "#58a6ff", "BTN_TEXT": "#f0f6fc","ACCENT": "#58a6ff", "SUCCESS": "#3fb950", "WARNING": "#d29922", "ERROR": "#f85149","SYSTEM": "#7c3aed", "PM": "#ec4899", "HEADER_BG": "#21262d", "SIDEBAR_BG": "#0d1117","HIGHLIGHT_BG": "#30363d", "HIGHLIGHT_FG": "#ffffff", "INFO_MSG": "#7c3aed"},
    "Современная светлая": {"BG_COLOR": "#ffffff", "TEXT_COLOR": "#24292f", "TEXT_SECONDARY": "#656d76","ENTRY_BG": "#f6f8fa", "ENTRY_FG": "#24292f", "ENTRY_BORDER": "#d0d7de", "ENTRY_FOCUS": "#0969da","BTN_BG": "#f6f8fa", "BTN_HOVER": "#f3f4f6", "BTN_ACTIVE": "#0969da", "BTN_TEXT": "#24292f","ACCENT": "#0969da", "SUCCESS": "#1a7f37", "WARNING": "#9a6700", "ERROR": "#cf222e","SYSTEM": "#8250df", "PM": "#bf8700", "HEADER_BG": "#f6f8fa", "SIDEBAR_BG": "#ffffff","HIGHLIGHT_BG": "#d0d7de", "HIGHLIGHT_FG": "#000000", "INFO_MSG": "#8250df"}
}
CURRENT_THEME = THEMES.get(USER_SETTINGS.get("theme", "Современная тёмная"), THEMES["Современная тёмная"]).copy()

# ------------------------------
# Вспомогательные классы
# ------------------------------
class NotificationHelper:
    @staticmethod
    def show_toast(parent, message, msg_type="info", duration=3000):
        try:
            if not parent.winfo_exists(): return
            toast = tk.Toplevel(parent)
            toast.withdraw(); toast.overrideredirect(True)
            colors = {"info": CURRENT_THEME["ACCENT"], "success": CURRENT_THEME["SUCCESS"], "warning": CURRENT_THEME["WARNING"], "error": CURRENT_THEME["ERROR"]}
            bg_color = colors.get(msg_type, CURRENT_THEME["ACCENT"])
            frame = tk.Frame(toast, bg=bg_color, padx=15, pady=10); frame.pack()
            label = tk.Label(frame, text=message, bg=bg_color, fg="white", font=("Arial", 10, "bold")); label.pack()
            toast.update_idletasks()
            x = parent.winfo_rootx() + parent.winfo_width() - toast.winfo_width() - 20
            y = parent.winfo_rooty() + 50
            toast.geometry(f"+{x}+{y}")
            toast.deiconify(); toast.lift(); toast.attributes("-topmost", True)
            toast.after(duration, toast.destroy)
        except Exception as e: logging.error(f"Ошибка Toast: {e}")

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, client_app):
        super().__init__(master)
        self.client_app = client_app
        self.title("Настройки")
        self.geometry("450x300")
        self.resizable(False, False)
        self.configure(bg=CURRENT_THEME["BG_COLOR"], padx=20, pady=20)
        self.transient(master)
        self.grab_set()

        self.theme_var = tk.StringVar(value=USER_SETTINGS.get("theme"))
        self.autoscroll_var = tk.BooleanVar(value=USER_SETTINGS.get("auto_scroll"))
        self.fontsize_var = tk.IntVar(value=USER_SETTINGS.get("font_size"))
        
        style = ttk.Style(self)
        style.configure("TCheckbutton", background=CURRENT_THEME["BG_COLOR"], foreground=CURRENT_THEME["TEXT_COLOR"])
        style.map("TCheckbutton", background=[("active", CURRENT_THEME["BG_COLOR"])])

        tk.Label(self, text="Тема оформления:", bg=CURRENT_THEME["BG_COLOR"], fg=CURRENT_THEME["TEXT_COLOR"]).grid(row=0, column=0, sticky="w", pady=5)
        theme_combo = ttk.Combobox(self, textvariable=self.theme_var, values=list(THEMES.keys()), state="readonly")
        theme_combo.grid(row=0, column=1, sticky="ew", padx=10)

        tk.Label(self, text="Размер шрифта:", bg=CURRENT_THEME["BG_COLOR"], fg=CURRENT_THEME["TEXT_COLOR"]).grid(row=1, column=0, sticky="w", pady=5)
        font_spinbox = ttk.Spinbox(self, from_=8, to=20, textvariable=self.fontsize_var, width=5)
        font_spinbox.grid(row=1, column=1, sticky="w", padx=10)

        autoscroll_check = ttk.Checkbutton(self, text="Автопрокрутка чата", variable=self.autoscroll_var, style="TCheckbutton")
        autoscroll_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=10)

        btn_frame = tk.Frame(self, bg=CURRENT_THEME["BG_COLOR"])
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))

        save_btn = tk.Button(btn_frame, text="Сохранить", command=self.save_and_close, bg=CURRENT_THEME["SUCCESS"], fg="white", relief=tk.FLAT, padx=10)
        save_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(btn_frame, text="Отмена", command=self.destroy, bg=CURRENT_THEME["BTN_BG"], fg=CURRENT_THEME["BTN_TEXT"], relief=tk.FLAT, padx=10)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        self.grid_columnconfigure(1, weight=1)

    def save_and_close(self):
        USER_SETTINGS["theme"] = self.theme_var.get()
        USER_SETTINGS["auto_scroll"] = self.autoscroll_var.get()
        USER_SETTINGS["font_size"] = self.fontsize_var.get()
        
        self.client_app.auto_scroll_enabled = self.autoscroll_var.get()
        
        save_settings(USER_SETTINGS)
        
        messagebox.showinfo("Сохранено", "Настройки сохранены.\nТема и размер шрифта вступят в силу после перезапуска приложения.", parent=self)
        self.destroy()

# ------------------------------
# ОКНО ЛИЧНЫХ СООБЩЕНИЙ
# ------------------------------
class PrivateMessageWindow(tk.Toplevel):
    def __init__(self, master, client_app):
        super().__init__(master)
        self.client_app = client_app
        self.active_partner = None
        self.chat_history = {}

        self.title("Личные сообщения")
        self.geometry("800x600")
        self.minsize(600, 400)
        self.configure(bg=CURRENT_THEME["BG_COLOR"])
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, bg=CURRENT_THEME["BG_COLOR"], relief=tk.FLAT)
        main_pane.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_pane, bg=CURRENT_THEME["SIDEBAR_BG"], width=200)
        tk.Label(left_frame, text="Диалоги", bg=CURRENT_THEME["HEADER_BG"], fg=CURRENT_THEME["TEXT_COLOR"], font=("Arial", 12, "bold"), anchor="w").pack(fill=tk.X, padx=5, pady=5)
        self.partners_listbox = tk.Listbox(left_frame, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["ENTRY_FG"], selectbackground=CURRENT_THEME["ACCENT"], selectforeground="white", font=("Arial", self.client_app.font_size), relief=tk.FLAT, bd=0, highlightthickness=0, exportselection=False)
        self.partners_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.partners_listbox.bind("<<ListboxSelect>>", self.on_partner_select)
        main_pane.add(left_frame, minsize=150)

        right_frame = tk.Frame(main_pane, bg=CURRENT_THEME["BG_COLOR"])
        self.chat_area = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, state=tk.DISABLED, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["TEXT_COLOR"], font=("Arial", self.client_app.font_size), relief=tk.FLAT, bd=0)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        input_container = tk.Frame(right_frame, bg=CURRENT_THEME["ENTRY_BG"])
        input_container.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.msg_var = tk.StringVar()
        self.msg_entry = tk.Entry(input_container, textvariable=self.msg_var, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["ENTRY_FG"], insertbackground=CURRENT_THEME["ENTRY_FG"], relief=tk.FLAT, font=("Arial", self.client_app.font_size))
        self.msg_entry.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=10, pady=10)
        self.msg_entry.bind("<Return>", self.send_pm)
        
        self.attach_btn = tk.Button(input_container, text="📎", font=("Arial", 16), bg=CURRENT_THEME["BTN_BG"], fg=CURRENT_THEME["BTN_TEXT"], relief=tk.FLAT, cursor="hand2", command=self.send_file_to_active_partner)
        self.attach_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        send_btn = tk.Button(input_container, text="▶", font=("Arial", 16), bg=CURRENT_THEME["ACCENT"], fg="white", relief=tk.FLAT, cursor="hand2", command=self.send_pm)
        send_btn.pack(side=tk.RIGHT, padx=10, pady=5)
        main_pane.add(right_frame, minsize=300)

        self.setup_tags()
        self.withdraw()

    def send_file_to_active_partner(self):
        if not self.active_partner:
            NotificationHelper.show_toast(self.client_app, "Сначала выберите диалог", "warning")
            return

        filepath = filedialog.askopenfilename(title=f"Файл для {self.active_partner}", parent=self)
        if not filepath: return
        
        self.client_app.initiate_file_send(target_user=self.active_partner, filepath=filepath)

    def setup_tags(self):
        fnt_bold = ("Arial", self.client_app.font_size, "bold")
        self.chat_area.tag_config("me", foreground=CURRENT_THEME["ACCENT"], font=fnt_bold, justify=tk.RIGHT)
        self.chat_area.tag_config("partner", foreground=CURRENT_THEME["SUCCESS"], font=fnt_bold, justify=tk.LEFT)
        self.chat_area.tag_config("me_msg", justify=tk.RIGHT)
        self.chat_area.tag_config("partner_msg", justify=tk.LEFT)

    def hide_window(self):
        self.withdraw()

    def show_window(self, partner=None):
        self.deiconify(); self.lift(); self.focus_set()
        if partner: self.start_chat_with(partner)

    def start_chat_with(self, partner):
        if partner not in self.chat_history:
            self.chat_history[partner] = []
            self.partners_listbox.insert(tk.END, partner)
        
        all_items = list(self.partners_listbox.get(0, tk.END))
        if partner in all_items:
            idx = all_items.index(partner)
            self.partners_listbox.selection_clear(0, tk.END)
            self.partners_listbox.selection_set(idx)
            self.partners_listbox.activate(idx)
            self.on_partner_select()

    def on_partner_select(self, event=None):
        if not self.partners_listbox.curselection(): return
        idx = self.partners_listbox.curselection()[0]
        self.active_partner = self.partners_listbox.get(idx)
        self.load_chat_history()
        self.msg_entry.focus()
        self.partners_listbox.itemconfig(idx, {'bg': CURRENT_THEME["ENTRY_BG"]})

    def load_chat_history(self):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete(1.0, tk.END)
        history = self.chat_history.get(self.active_partner, [])
        for entry in history:
            self.append_message_to_display(entry['sender'], entry['text'])
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.yview(tk.END)

    def send_pm(self, event=None):
        text = self.msg_var.get().strip()
        if not text or not self.active_partner: return
        
        command = f"/pm {self.active_partner} {text}"
        if self.client_app.send_message_to_server(command):
            # self.handle_incoming_pm(self.active_partner, text, from_me=True) # Убрано локальное эхо
            self.msg_var.set("")
    
    def handle_incoming_pm(self, partner, text, from_me=False):
        sender = self.client_app.username if from_me else partner
        if partner not in self.chat_history:
            self.chat_history[partner] = []
            self.partners_listbox.insert(0, partner)
        self.chat_history[partner].append({"sender": sender, "text": text})
        
        if partner == self.active_partner:
            self.append_message_to_display(sender, text)
        else:
            all_items = list(self.partners_listbox.get(0, tk.END))
            if partner in all_items:
                idx = all_items.index(partner)
                self.partners_listbox.itemconfig(idx, {'bg': CURRENT_THEME["WARNING"]})
        
        if not from_me:
             NotificationHelper.show_toast(self.client_app, f"Новое ЛС от {partner}", "info")

    def append_message_to_display(self, sender, text):
        self.chat_area.config(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        if sender == self.client_app.username:
            self.chat_area.insert(tk.END, f"Вы [{ts}]\n", ("me",))
            self.chat_area.insert(tk.END, f"{text}\n\n", ("me_msg",))
        else:
            self.chat_area.insert(tk.END, f"{sender} [{ts}]\n", ("partner",))
            self.chat_area.insert(tk.END, f"{text}\n\n", ("partner_msg",))
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.yview(tk.END)

# ------------------------------
# Основной класс GUI-клиента
# ------------------------------
class ChatClientGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wi-Fi Chat Pro")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_window_properties()
        self.withdraw()
        self.init_variables()
        self.create_login_window()
        if USER_SETTINGS.get("last_username"):
            self.name_var.set(USER_SETTINGS["last_username"])
        self.process_gui_queue()

    def setup_window_properties(self):
        self.minsize(1000, 700)
        try:
            self.geometry(USER_SETTINGS.get("window_geometry", "1200x800"))
        except tk.TclError:
            self.geometry("1200x800")
        self.configure(bg=CURRENT_THEME["BG_COLOR"])

    def init_variables(self):
        self.username = ""
        self.server_host = ""
        self.server_port = 0
        self.command_socket = None
        self.gui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.network_thread = None
        self.online_users = set()
        self.connection_status = "disconnected"
        self.auto_scroll_enabled = USER_SETTINGS.get("auto_scroll", True)
        self.font_size = USER_SETTINGS.get("font_size", 11)
        self.pm_window = None
        # --- ИЗМЕНЕНО ---
        self.pending_downloads = {} # Словарь для хранения информации о скачиваемых файлах
        self.pending_upload_queue = []

    def create_login_window(self):
        self.login_window = tk.Toplevel(self)
        self.login_window.title("Вход в чат")
        self.login_window.protocol("WM_DELETE_WINDOW", self.quit_app_on_login_close)
        self.login_window.configure(bg=CURRENT_THEME["BG_COLOR"], padx=20, pady=20)
        self.login_window.grab_set()
        self.center_window(self.login_window, 400, 250)
        
        tk.Label(self.login_window, text="Никнейм:", bg=CURRENT_THEME["BG_COLOR"], fg=CURRENT_THEME["TEXT_COLOR"], font=("Arial", 12)).pack(pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(self.login_window, textvariable=self.name_var, font=("Arial", 14), width=30, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["ENTRY_FG"], insertbackground=CURRENT_THEME["ENTRY_FG"])
        self.name_entry.pack(pady=5, ipady=5)
        self.name_entry.focus()
        self.name_entry.bind("<Return>", lambda e: self.on_connect())

        self.connect_btn = tk.Button(self.login_window, text="Подключиться", command=self.on_connect, bg=CURRENT_THEME["ACCENT"], fg="white", font=("Arial", 12, "bold"))
        self.connect_btn.pack(pady=20, ipady=5)
        
        self.status_label_login = tk.Label(self.login_window, text="Ожидание подключения...", bg=CURRENT_THEME["BG_COLOR"], fg=CURRENT_THEME["TEXT_SECONDARY"])
        self.status_label_login.pack(pady=5)
        
        threading.Thread(target=self.find_server_udp, daemon=True).start()

    def find_server_udp(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            udp_socket.bind(("", 9999))
            logging.info("Слушаю UDP порт 9999 для автообнаружения...")
            while self.connection_status == "disconnected":
                data, addr = udp_socket.recvfrom(1024)
                try:
                    server_info = json.loads(data.decode())
                    if server_info.get("app_name") == "python_chat":
                        self.server_host = server_info["host"]
                        self.server_port = server_info["port"]
                        logging.info(f"Сервер найден: {self.server_host}:{self.server_port}")
                        if self.login_window.winfo_exists():
                            self.status_label_login.config(text=f"Сервер найден: {self.server_host}", fg=CURRENT_THEME["SUCCESS"])
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
        except Exception as e:
            logging.error(f"Ошибка UDP сокета: {e}")
            if self.login_window.winfo_exists():
                 self.status_label_login.config(text=f"Ошибка поиска сервера", fg=CURRENT_THEME["ERROR"])
        finally:
            udp_socket.close()
            
    def on_connect(self):
        if not self.server_host:
            self.status_label_login.config(text="Сервер не найден, подождите...", fg=CURRENT_THEME["WARNING"])
            return
        
        nickname = self.name_var.get().strip()
        if not re.match("^[a-zA-Z0-9_.-]{3,16}$", nickname):
            self.status_label_login.config(text="Неверный формат имени", fg=CURRENT_THEME["ERROR"])
            return
        
        self.username = nickname
        USER_SETTINGS["last_username"] = nickname
        save_settings(USER_SETTINGS)
        self.connect_btn.config(state=tk.DISABLED)
        self.status_label_login.config(text="Подключение...", fg=CURRENT_THEME["WARNING"])
        
        threading.Thread(target=self.start_network_connection, daemon=True).start()
    
    def center_window(self, window, width, height):
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
        
    def quit_app_on_login_close(self):
        self.on_closing(from_login=True)

    def start_network_connection(self):
        try:
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.connect((self.server_host, self.server_port))
            self.command_socket.sendall(b"CMD\n")
            response = self.command_socket.recv(1024).decode().strip()
            if response == "AUTH_REQUEST":
                self.command_socket.sendall((self.username + "\n").encode())
                auth_response_raw = self.command_socket.recv(1024).decode().strip()
                if auth_response_raw.startswith("AUTH_SUCCESS"):
                    self.connection_status = "connected"
                    self.gui_queue.put({"type": "connection_success", "message": auth_response_raw.split(" ", 1)[1]})
                else:
                    error_msg = auth_response_raw.split(" ", 1)[1]
                    self.gui_queue.put({"type": "connection_failed", "message": error_msg})
                    self.command_socket.close()
            else:
                 self.gui_queue.put({"type": "connection_failed", "message": "Неверный ответ от сервера."})
                 self.command_socket.close()
        except Exception as e:
            logging.error(f"Ошибка подключения: {e}")
            self.gui_queue.put({"type": "connection_failed", "message": str(e)})

    # --- ИЗМЕНЕНО: Удалена старая логика обработки потока файла ---
    def receive_messages(self):
        buffer = b""
        logging.info("Поток receive_messages запущен.")
        while not self.stop_event.is_set():
            try:
                data_chunk = self.command_socket.recv(4096)
                if not data_chunk:
                    self.gui_queue.put({"type": "connection_error", "message": "Сервер разорвал соединение."})
                    break
                buffer += data_chunk
                while b'\n' in buffer:
                    line_bytes, buffer = buffer.split(b'\n', 1)
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                    if line:
                        parsed = self.parse_server_line(line)
                        if parsed: self.gui_queue.put(parsed)
            except (socket.error, ConnectionResetError, BrokenPipeError):
                if not self.stop_event.is_set():
                    self.gui_queue.put({"type": "connection_error", "message": "Потеряно соединение с сервером."})
                break
            except Exception as e:
                if not self.stop_event.is_set():
                     logging.critical(f"Критическая ошибка в receive_messages: {e}", exc_info=True)
                break
        logging.info("Поток receive_messages завершен.")

    # --- УДАЛЕНО: Метод handle_file_download_stream больше не нужен ---

    # --- ИЗМЕНЕНО: Добавлена обработка DOWNLOAD_PROCEED ---
    def parse_server_line(self, line: str):
        parts = line.split(" ", 4)
        command = parts[0]
        handlers = {
            "USER_LIST": lambda p: {"type": "user_list_update", "users": p[1].split(',') if len(p) > 1 else []},
            "FILE_INCOMING": lambda p: {"type": "file_incoming", "from_user": p[1], "filename": p[2], "filesize": int(p[3]), "transfer_id": p[4]},
            "UPLOAD_PROCEED": lambda p: {"type": "upload_proceed", "transfer_id": p[1], "port": int(p[2])},
            "UPLOAD_REJECTED": lambda p: {"type": "upload_rejected", "reason": " ".join(p[1:])},
            "DOWNLOAD_READY": lambda p: {"type": "download_ready", "from_user": p[1], "filename": p[2], "filesize": int(p[3]), "transfer_id": p[4]},
            "DOWNLOAD_PROCEED": lambda p: {"type": "download_proceed", "transfer_id": p[1], "port": int(p[2])}, # НОВАЯ КОМАНДА
            "SERVER_MSG": lambda p: {"type": "system_message", "text": " ".join(p[1:]), "class_key": "info_msg"}
        }
        if command in handlers: return handlers[command](parts)
        match_msg = re.match(r"^\[(.*?)\]\s(\(PM от (.*?)\):|\(PM для (.*?)\):|(.*?):)\s(.*)$", line)
        if match_msg:
            ts, _, from_user_pm, to_user_pm, from_user_public, text = match_msg.groups()
            partner = from_user_pm if from_user_pm else to_user_pm
            if partner:
                return {"type": "pm_message", "partner": partner, "text": text, "from_me": bool(to_user_pm)}
            else:
                 return {"type": "new_message", "username": from_user_public, "text": text, "timestamp": ts}
        match_sys = re.match(r"^\[(.*?)\]\s\*\*\*\s(.*)\s\*\*\*$", line)
        if match_sys: return {"type": "system_message", "text": match_sys.group(2), "class_key": "system_msg", "timestamp": match_sys.group(1)}
        return {"type": "system_message", "text": line, "class_key": "info_msg"}

    def _thread_keepalive(self):
        while not self.stop_event.is_set():
            if self.stop_event.wait(60): break
            if self.send_message_to_server("/ping"):
                logging.info("Keep-alive ping sent.")
            else:
                logging.warning("Keep-alive ping failed, connection seems lost.")
                break
    
    # --- ИЗМЕНЕНО: Обновлен цикл обработки очереди ---
    def process_gui_queue(self):
        try:
            while not self.gui_queue.empty():
                data = self.gui_queue.get_nowait()
                msg_type = data.get("type")
                if msg_type == "connection_success":
                    self.login_window.destroy()
                    self.deiconify()
                    self.build_chat_interface()
                    self.display_system_message(data['message'], "success_msg")
                    self.stop_event.clear()
                    self.network_thread = threading.Thread(target=self.receive_messages, daemon=True)
                    self.network_thread.start()
                    keepalive_thread = threading.Thread(target=self._thread_keepalive, daemon=True)
                    keepalive_thread.start()
                elif msg_type == "connection_failed":
                    self.status_label_login.config(text=f"Ошибка: {data['message']}", fg=CURRENT_THEME["ERROR"])
                    self.connect_btn.config(state=tk.NORMAL)
                    self.server_host = ""
                    threading.Thread(target=self.find_server_udp, daemon=True).start()
                elif msg_type == "connection_error": self.handle_disconnection(data.get("message"))
                elif msg_type == "new_message": self.append_formatted_message(data['timestamp'], data['username'], data['text'])
                elif msg_type == "system_message": self.display_system_message(data['text'], data.get('class_key', 'system_msg'), timestamp=data.get('timestamp'))
                elif msg_type == "pm_message":
                    if not self.pm_window: self.pm_window = PrivateMessageWindow(self, self)
                    self.pm_window.handle_incoming_pm(data['partner'], data['text'], from_me=data['from_me'])
                elif msg_type == "user_list_update":
                    self.online_users = set(u for u in data.get("users", []) if u != self.username)
                    self.update_user_listbox()
                elif msg_type == "file_incoming": self.handle_file_incoming(data)
                elif msg_type == "upload_proceed": self.handle_upload_proceed(data)
                elif msg_type == "upload_rejected": NotificationHelper.show_toast(self, data['reason'], "warning")
                elif msg_type == "download_ready": self.handle_download_ready(data)
                elif msg_type == "download_proceed": self.handle_download_proceed(data) # НОВЫЙ ОБРАБОТЧИК
                elif msg_type == "file_download_complete": NotificationHelper.show_toast(self, f"Файл '{data['filename']}' скачан!", "success")
                elif msg_type == "file_download_error": NotificationHelper.show_toast(self, f"Ошибка скачивания: {data['error']}", "error")
        except queue.Empty:
            pass
        finally:
            if not self.stop_event.is_set():
                self.after(100, self.process_gui_queue)

    def send_message_to_server(self, message: str):
        if self.command_socket and self.connection_status == "connected":
            try:
                self.command_socket.sendall((message + "\n").encode("utf-8"))
                return True
            except socket.error as e:
                self.handle_disconnection(f"Ошибка сети: {e}")
                return False
        return False

    def handle_file_incoming(self, data):
        response = messagebox.askyesno("Входящий файл", f"Пользователь {data['from_user']} хочет отправить вам файл:\n{data['filename']} ({self._format_filesize(data['filesize'])})\n\nПринять?", parent=self)
        self.send_message_to_server(f"/{'file_accept' if response else 'file_reject'} {data['transfer_id']}")

    def handle_upload_proceed(self, data):
        transfer_id = data['transfer_id']
        port = data['port']
        if self.pending_upload_queue:
            info = self.pending_upload_queue.pop(0)
            threading.Thread(target=self._thread_upload_file, 
                             args=(transfer_id, info['filepath'], self.server_host, port), 
                             daemon=True).start()
        else:
            logging.warning("Получено UPLOAD_PROCEED, но очередь отправки пуста. Нечего отправлять.")

    def _thread_upload_file(self, transfer_id, filepath, host, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upload_socket:
                upload_socket.connect((host, port))
                upload_socket.sendall(f"UPLOAD {transfer_id}\n".encode())
                with open(filepath, "rb") as f:
                    while chunk := f.read(4096):
                        upload_socket.sendall(chunk)
            self.gui_queue.put({"type": "system_message", "text": f"Файл {os.path.basename(filepath)} успешно загружен на сервер.", "class_key": "success_msg"})
        except Exception as e:
            self.gui_queue.put({"type": "system_message", "text": f"Ошибка загрузки файла: {e}", "class_key": "error_msg"})

    # --- ИЗМЕНЕНО: Логика стала проще ---
    def handle_download_ready(self, data):
        if messagebox.askyesno("Файл готов", f"Файл '{data['filename']}' от {data['from_user']} готов к скачиванию.\nНачать?", parent=self):
            save_path = filedialog.asksaveasfilename(initialdir=USER_SETTINGS.get("default_download_path"), initialfile=data['filename'], parent=self)
            if save_path:
                # Сохраняем информацию о скачивании, чтобы использовать ее в новом потоке
                self.pending_downloads[data['transfer_id']] = {
                    'filename': data['filename'], 
                    'filesize': data['filesize'],
                    'local_filepath': save_path
                }
                self.send_message_to_server(f"/download {data['transfer_id']}")

    # --- НОВЫЙ МЕТОД: Обработчик разрешения на скачивание ---
    def handle_download_proceed(self, data):
        transfer_id = data['transfer_id']
        port = data['port']
        if transfer_id in self.pending_downloads:
            info = self.pending_downloads[transfer_id]
            threading.Thread(target=self._thread_download_file, 
                             args=(transfer_id, info, self.server_host, port), 
                             daemon=True).start()
        else:
            logging.warning(f"Получено DOWNLOAD_PROCEED для неизвестного transfer_id: {transfer_id}")

    # --- НОВЫЙ МЕТОД: Поток для скачивания файла ---
    def _thread_download_file(self, transfer_id, info, host, port):
        local_filepath = info['local_filepath']
        filesize = info['filesize']
        filename = info['filename']
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as download_socket:
                download_socket.connect((host, port))
                download_socket.sendall(f"DOWNLOAD {transfer_id}\n".encode())
                
                bytes_received = 0
                with open(local_filepath, "wb") as f:
                    while bytes_received < filesize:
                        bytes_to_read = min(4096, filesize - bytes_received)
                        chunk = download_socket.recv(bytes_to_read)
                        if not chunk:
                            raise ConnectionError("Соединение потеряно во время скачивания.")
                        f.write(chunk)
                        bytes_received += len(chunk)

            if bytes_received == filesize:
                self.gui_queue.put({"type": "file_download_complete", "filename": filename})
            else:
                raise IOError("Скачанный файл имеет неверный размер.")

        except Exception as e:
            self.gui_queue.put({"type": "file_download_error", "filename": filename, "error": str(e)})
            if os.path.exists(local_filepath): os.remove(local_filepath)
        finally:
            self.pending_downloads.pop(transfer_id, None)

    def initiate_file_send(self, target_user=None, filepath=None):
        if not target_user:
            if not self.users_listbox.curselection():
                messagebox.showwarning("Нет получателя", "Выберите пользователя из списка онлайн, которому хотите отправить файл.", parent=self)
                return
            idx = self.users_listbox.curselection()[0]
            target_user = self.users_listbox.get(idx).replace(" (Вы)", "").strip()
        
        if target_user == self.username:
            messagebox.showerror("Ошибка", "Нельзя отправить файл самому себе.", parent=self)
            return

        if not filepath:
            filepath = filedialog.askopenfilename(title=f"Выберите файл для {target_user}", parent=self)
        if not filepath: return

        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        
        self.pending_upload_queue.append({'filepath': filepath})
        
        self.send_message_to_server(f"/upload {target_user} {filename} {filesize}")
        self.display_system_message(f"Запрос на отправку файла '{filename}' пользователю {target_user} отправлен.", "info_msg")

    def build_chat_interface(self):
        self.configure(bg=CURRENT_THEME["BG_COLOR"])
        self.create_header()
        self.create_main_area()
        self.create_input_area()
        self.create_sidebar()
        self.create_status_bar()
        self.status_label.config(text=f"Подключено: {self.server_host}:{self.server_port} | Вы: {self.username}", fg=CURRENT_THEME["SUCCESS"])
        self.connection_indicator.config(fg=CURRENT_THEME["SUCCESS"])
        self.pm_window = PrivateMessageWindow(self, self)

    def create_header_buttons(self, parent):
        bf = tk.Frame(parent, bg=CURRENT_THEME["HEADER_BG"])
        bf.pack(side=tk.RIGHT, padx=15)
        tk.Button(bf, text="✉️", font=("Arial", 16), bg=CURRENT_THEME["BTN_BG"], fg=CURRENT_THEME["BTN_TEXT"], relief=tk.FLAT, width=2, cursor="hand2", command=self.toggle_pm_window).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="⚙", font=("Arial", 16), bg=CURRENT_THEME["BTN_BG"], fg=CURRENT_THEME["BTN_TEXT"], relief=tk.FLAT, width=2, cursor="hand2", command=self.open_settings).pack(side=tk.LEFT, padx=5)

    def toggle_pm_window(self):
        if not self.pm_window.winfo_viewable():
            self.pm_window.show_window()
        else:
            self.pm_window.hide_window()

    def create_sidebar(self):
        self.sidebar = tk.Frame(self.main_container, bg=CURRENT_THEME["SIDEBAR_BG"], width=200)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(2,0))
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="Онлайн:", bg=CURRENT_THEME["SIDEBAR_BG"],fg=CURRENT_THEME["TEXT_COLOR"], font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(10,5))
        self.users_listbox = tk.Listbox(self.sidebar, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["ENTRY_FG"],selectbackground=CURRENT_THEME["ACCENT"], selectforeground="white",font=("Arial", self.font_size), relief=tk.FLAT, bd=0, highlightthickness=0,activestyle=tk.NONE, exportselection=False )
        self.users_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.users_listbox.bind("<Double-1>", self.on_user_double_click)

    def on_user_double_click(self, event=None):
        if not self.users_listbox.curselection(): return
        username = self.users_listbox.get(self.users_listbox.curselection()[0]).replace(" (Вы)", "").strip()
        if username != self.username:
            self.pm_window.show_window(partner=username)

    def send_message(self, event=None):
        msg_text = self.msg_var.get().strip()
        if not msg_text: return
        if self.send_message_to_server(msg_text):
            self.msg_var.set("")

    def handle_disconnection(self, reason):
        if self.connection_status == "disconnected": return
        self.connection_status = "disconnected"
        self.display_system_message(reason, "error_msg")
        self.connection_indicator.config(fg=CURRENT_THEME["ERROR"])
        self.status_label.config(text="Соединение потеряно", fg=CURRENT_THEME["ERROR"])
        self.online_users.clear()
        self.update_user_listbox()
        self.stop_event.set()
        NotificationHelper.show_toast(self, "Соединение разорвано", "error")

    def on_closing(self, from_login=False):
        if hasattr(self, 'main_container') and self.main_container.winfo_exists():
            USER_SETTINGS["window_geometry"] = self.geometry()
        save_settings(USER_SETTINGS)
        self.stop_event.set()
        if self.command_socket:
            try: self.command_socket.close()
            except: pass
        self.destroy()

    def update_user_listbox(self):
        if not hasattr(self, 'users_listbox') or not self.users_listbox.winfo_exists(): return
        selected_user = None
        if self.users_listbox.curselection():
            selected_user = self.users_listbox.get(self.users_listbox.curselection()[0])
        
        self.users_listbox.delete(0, tk.END)
        self.users_listbox.insert(tk.END, f"{self.username} (Вы)")
        self.users_listbox.itemconfig(0, {'fg': CURRENT_THEME["ACCENT"]})
        
        sorted_users = sorted(list(self.online_users))
        for user in sorted_users:
            self.users_listbox.insert(tk.END, user)
        
        if selected_user and selected_user in self.users_listbox.get(0, tk.END):
            idx = list(self.users_listbox.get(0, tk.END)).index(selected_user)
            self.users_listbox.selection_set(idx)

    def append_formatted_message(self, timestamp_str, user_str, message_str):
        if not hasattr(self, 'text_area') or not self.text_area.winfo_exists(): return
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"[{timestamp_str}] ", ("timestamp",))
        self.text_area.insert(tk.END, f"{user_str}: ", ("username",))
        self.text_area.insert(tk.END, message_str + "\n")
        if self.auto_scroll_enabled: self.text_area.yview(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def display_system_message(self, message, class_key="system_msg", timestamp=None):
        if not hasattr(self, 'text_area') or not self.text_area.winfo_exists(): return
        self.text_area.config(state=tk.NORMAL)
        ts = timestamp if timestamp else datetime.now().strftime("%H:%M:%S")
        self.text_area.tag_config(class_key, foreground=CURRENT_THEME.get(class_key.upper().replace("_MSG", ""), CURRENT_THEME["SYSTEM"]), font=("Arial", self.font_size, "italic"))
        self.text_area.insert(tk.END, f"[{ts}] {message}\n", (class_key,))
        if self.auto_scroll_enabled: self.text_area.yview(tk.END)
        self.text_area.config(state=tk.DISABLED)
    
    def _format_filesize(self, num_bytes):
        if num_bytes is None: return "N/A"
        for unit in ['байт', 'КБ', 'МБ', 'ГБ']:
            if abs(num_bytes) < 1024.0: return f"{num_bytes:3.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} ТБ"
    
    def create_main_area(self):
        self.main_container = tk.Frame(self, bg=CURRENT_THEME["BG_COLOR"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.create_text_area()
    
    def create_text_area(self):
        self.text_area = scrolledtext.ScrolledText(self.main_container, bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["TEXT_COLOR"], state=tk.DISABLED, wrap=tk.WORD, font=("Arial", self.font_size))
        self.text_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.text_area.tag_config("timestamp", foreground=CURRENT_THEME["TEXT_SECONDARY"])
        self.text_area.tag_config("username", foreground=CURRENT_THEME["ACCENT"], font=("Arial", self.font_size, "bold"))

    def create_input_area(self):
        self.input_frame = tk.Frame(self, bg=CURRENT_THEME["BG_COLOR"])
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        tk.Button(self.input_frame, text="📎", font=("Arial", 16), relief=tk.FLAT, cursor="hand2", bg=CURRENT_THEME["BTN_BG"], fg=CURRENT_THEME["BTN_TEXT"], command=self.initiate_file_send).pack(side=tk.LEFT, padx=(0, 5))
        
        self.msg_var = tk.StringVar()
        self.entry_msg = tk.Entry(self.input_frame, textvariable=self.msg_var, font=("Arial", self.font_size), bg=CURRENT_THEME["ENTRY_BG"], fg=CURRENT_THEME["ENTRY_FG"], insertbackground=CURRENT_THEME["ENTRY_FG"], relief=tk.FLAT, bd=5)
        self.entry_msg.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.entry_msg.bind("<Return>", self.send_message)
        
        tk.Button(self.input_frame, text="▶", font=("Arial", 16), command=self.send_message, bg=CURRENT_THEME["ACCENT"], fg="white", relief=tk.FLAT, cursor="hand2").pack(side=tk.RIGHT, padx=(5, 0))
    
    def create_header(self):
        self.header = tk.Frame(self, bg=CURRENT_THEME["HEADER_BG"], height=60)
        self.header.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(self.header, text="Wi-Fi Chat Pro", bg=CURRENT_THEME["HEADER_BG"], fg=CURRENT_THEME["TEXT_COLOR"], font=("Arial", 16, "bold")).pack(side=tk.LEFT, padx=15)
        
        self.connection_indicator = tk.Label(self.header, text="●", bg=CURRENT_THEME["HEADER_BG"], font=("Arial", 20))
        self.connection_indicator.pack(side=tk.RIGHT, padx=15)
        self.create_header_buttons(self.header)

    def create_status_bar(self):
        self.status_bar = tk.Frame(self, bg=CURRENT_THEME["HEADER_BG"], height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="Нет подключения", bg=CURRENT_THEME["HEADER_BG"], fg=CURRENT_THEME["TEXT_SECONDARY"])
        self.status_label.pack(side=tk.LEFT, padx=10)

    def open_settings(self):
        SettingsWindow(self, self)
        
if __name__ == "__main__":
    try:
        app = ChatClientGUI()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Критическая ошибка приложения: {e}", exc_info=True)
        try:
            messagebox.showerror("Критическая ошибка", f"Произошла непредвиденная ошибка: {e}")
        except tk.TclError:
            print(f"Критическая ошибка Tkinter: {e}")