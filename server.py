import asyncio
import json
import os
import logging
import uuid
import re
import socket
from pathlib import Path
from datetime import datetime

HOST = "0.0.0.0"
PORT = 9090
LOG_FILE = "server.log"
TEMP_UPLOAD_DIR = "server_uploads"
BROADCAST_PORT = 9999
BROADCAST_INTERVAL = 5
CLIENT_TIMEOUT = 300.0

class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.local_ip = self._get_local_ip()
        self.connected_clients = {}
        self.active_transfers = {}
        self.lock = asyncio.Lock()

    def _setup_logging(self):
        logging.basicConfig(
            filename=LOG_FILE, level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(funcName)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S", filemode='w'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(console_handler)
        logging.info("=== Сервер запускается ===")

    def _get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    async def start(self):
        self._setup_logging()
        Path(TEMP_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        tcp_server = await asyncio.start_server(self._protocol_dispatcher, self.host, self.port)
        logging.info(f"TCP сервер запущен на {self.host}:{self.port}")
        print(f"[🚀] Сервер запущен. Адрес для клиентов в локальной сети: {self.local_ip}:{self.port}")
        broadcast_task = asyncio.create_task(self._run_broadcast_service())
        try:
            await tcp_server.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Сервер останавливается...")
        finally:
            broadcast_task.cancel()
            tcp_server.close()
            await tcp_server.wait_closed()
            logging.info("=== Сервер остановлен ===")

    async def _protocol_dispatcher(self, reader, writer):
        addr = writer.get_extra_info("peername")
        try:
            initial_message_raw = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if not initial_message_raw:
                return

            initial_message = initial_message_raw.decode().strip()
            logging.info(f"Получено приветствие от {addr}: '{initial_message}'")
            parts = initial_message.split()
            command = parts[0]

            if command == "CMD":
                await self._handle_command_connection(reader, writer)
            elif command == "UPLOAD" and len(parts) > 1:
                transfer_id = parts[1]
                await self._handle_upload_connection(reader, writer, transfer_id)
            elif command == "DOWNLOAD" and len(parts) > 1:
                transfer_id = parts[1]
                await self._handle_download_connection(reader, writer, transfer_id)
            else:
                logging.warning(f"Неизвестный тип подключения от {addr}: '{initial_message}'")

        except (asyncio.TimeoutError, ConnectionResetError, asyncio.IncompleteReadError):
            logging.info(f"Клиент {addr} не представился или отсоединился.")
        except Exception as e:
            logging.error(f"Ошибка в диспетчере для {addr}: {e}", exc_info=True)
        finally:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()

    async def _handle_command_connection(self, reader, writer):
        addr = writer.get_extra_info("peername")
        try:
            await self._send_message(writer, "AUTH_REQUEST")
            username_raw = await asyncio.wait_for(reader.readline(), timeout=15.0)
            username = username_raw.decode().strip()

            async with self.lock:
                if not re.match("^[a-zA-Z0-9_.-]{3,16}$", username):
                    await self._send_message(writer, "AUTH_ERROR Неверный формат имени.")
                    return
                if self._get_writer_by_username(username):
                    await self._send_message(writer, f"AUTH_ERROR Имя '{username}' уже занято.")
                    return
                self.connected_clients[writer] = {"username": username}
            
            logging.info(f"Клиент {addr} авторизован как '{username}'.")
            await self._send_message(writer, f"AUTH_SUCCESS Добро пожаловать, {username}!")
            await self._broadcast_message(f"[{self._now()}] *** Пользователь {username} вошёл в чат ***", exclude_writer=writer)
            await self._broadcast_user_list()
        
        except (asyncio.TimeoutError, ConnectionResetError, asyncio.IncompleteReadError):
            logging.warning(f"Ошибка аутентификации для {addr}.")
            return
        
        try:
            while True:
                line_data = await asyncio.wait_for(reader.readline(), timeout=CLIENT_TIMEOUT)
                if not line_data: break
                
                line = line_data.decode().strip()
                if line:
                    await self._process_line(writer, line)
        except (asyncio.TimeoutError, ConnectionResetError, asyncio.IncompleteReadError) as e:
            logging.info(f"Клиент '{self.connected_clients.get(writer, {}).get('username', addr)}' отсоединен (таймаут или разрыв): {type(e).__name__}")
        except Exception as e:
            logging.error(f"Ошибка в _handle_command_connection: {e}", exc_info=True)
        finally:
            await self._cleanup_client(writer)

    async def _handle_upload_connection(self, reader, writer, transfer_id):
        async with self.lock:
            transfer = self.active_transfers.get(transfer_id)
            if not transfer or transfer["status"] != "pending_upload":
                logging.warning(f"Неверная или устаревшая попытка загрузки для transfer_id={transfer_id}")
                return
            
            transfer["status"] = "uploading"
            temp_filepath = Path(TEMP_UPLOAD_DIR) / f"{transfer_id}.upload"
            transfer["temp_filepath"] = temp_filepath

        logging.info(f"Начало приема файла {transfer_id} в {temp_filepath}")
        bytes_received = 0
        try:
            with open(temp_filepath, "wb") as f_temp:
                while bytes_received < transfer["filesize"]:
                    chunk = await reader.read(4096)
                    if not chunk:
                        logging.error(f"Соединение потеряно при загрузке файла {transfer_id}.")
                        transfer["status"] = "error"
                        break
                    f_temp.write(chunk)
                    bytes_received += len(chunk)
            
            async with self.lock:
                if transfer["status"] == "uploading":
                    if bytes_received == transfer["filesize"]:
                        transfer["status"] = "pending_download"
                        logging.info(f"Файл {transfer_id} успешно загружен на сервер.")
                        await self._send_message(transfer["to_writer"], f"DOWNLOAD_READY {transfer['from_user']} {transfer['filename']} {transfer['filesize']} {transfer_id}")
                    else:
                        transfer["status"] = "error"
                        logging.warning(f"Файл {transfer_id} загружен не полностью.")
        
        except Exception as e:
            logging.error(f"Ошибка в _handle_upload_connection для {transfer_id}: {e}", exc_info=True)
            async with self.lock:
                if transfer_id in self.active_transfers:
                    self.active_transfers[transfer_id]["status"] = "error"

    async def _handle_download_connection(self, reader, writer, transfer_id):
        addr = writer.get_extra_info("peername")
        logging.info(f"Клиент {addr} подключился для скачивания файла {transfer_id}.")
        
        async with self.lock:
            transfer = self.active_transfers.get(transfer_id)
            if not transfer or transfer.get("status") != "downloading":
                logging.warning(f"Неверная или устаревшая попытка скачивания для transfer_id={transfer_id} от {addr}")
                return
            
            filepath = transfer.get("temp_filepath")
            if not filepath or not os.path.exists(filepath):
                 logging.error(f"Файл для скачивания {transfer_id} не найден на диске по пути {filepath}.")
                 await self._send_message(transfer["to_writer"], "SERVER_MSG Ошибка: Файл для скачивания не найден на сервере.")
                 transfer["status"] = "error"
                 return
        
        try:
            logging.info(f"Начало отправки файла {filepath} клиенту {transfer['to_user']}.")
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    writer.write(chunk)
                    await writer.drain()
            logging.info(f"Файл {transfer_id} успешно отправлен клиенту {transfer['to_user']}.")
        except (ConnectionResetError, BrokenPipeError):
             logging.warning(f"Соединение с клиентом {transfer['to_user']} разорвано во время скачивания файла {transfer_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке файла {transfer_id} клиенту: {e}", exc_info=True)
        finally:
            async with self.lock:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logging.info(f"Временный файл {filepath} удален.")
                    except OSError as e:
                        logging.error(f"Не удалось удалить временный файл {filepath}: {e}")
                self.active_transfers.pop(transfer_id, None)
                logging.info(f"Трансфер {transfer_id} завершен и удален.")

    async def _process_line(self, writer, line):
        parts = line.split(" ", 3)
        command_str = parts[0].lower()
        
        handler = self.command_handlers.get(command_str)
        
        if handler:
            await handler(self, writer, parts)
        else:
            username = self.connected_clients[writer]["username"]
            formatted_msg = f"[{self._now()}] {username}: {line}"
            await self._broadcast_message(formatted_msg)
    
    async def _handle_pm(self, writer, parts):
        if len(parts) < 3:
            await self._send_message(writer, "SERVER_MSG Формат: /pm <user> <message>")
            return
        
        target_user, msg = parts[1], " ".join(parts[2:])
        sender_user = self.connected_clients[writer]["username"]
        
        if target_user == sender_user:
            await self._send_message(writer, "SERVER_MSG Нельзя отправить сообщение самому себе.")
            return

        target_writer = self._get_writer_by_username(target_user)
        if target_writer:
            pm = f"[{self._now()}] (PM от {sender_user}): {msg}"
            await self._send_message(target_writer, pm)
            await self._send_message(writer, f"[{self._now()}] (PM для {target_user}): {msg}")
        else:
            await self._send_message(writer, f"SERVER_MSG Пользователь '{target_user}' не найден.")
    
    async def _handle_upload(self, writer, parts):
        if len(parts) < 4:
            await self._send_message(writer, "SERVER_MSG Формат: /upload <user> <filename> <size>")
            return
        
        target_user, filename, size_str = parts[1], parts[2], parts[3]
        sender_user = self.connected_clients[writer]["username"]
        try:
            filesize = int(size_str)
        except ValueError:
            await self._send_message(writer, "SERVER_MSG Неверный размер файла."); return

        target_writer = self._get_writer_by_username(target_user)
        if not target_writer:
            await self._send_message(writer, f"SERVER_MSG Пользователь '{target_user}' не в сети."); return

        transfer_id = str(uuid.uuid4())
        async with self.lock:
            self.active_transfers[transfer_id] = {
                "id": transfer_id, "filename": filename, "filesize": filesize,
                "from_user": sender_user, "to_user": target_user,
                "from_writer": writer, "to_writer": target_writer,
                "status": "pending_target_accept"
            }
        
        await self._send_message(target_writer, f"FILE_INCOMING {sender_user} {filename} {filesize} {transfer_id}")
        await self._send_message(writer, f"SERVER_MSG Запрос на отправку файла '{filename}' пользователю {target_user} отправлен.")

    async def _handle_file_action(self, writer, parts, action):
        if len(parts) < 2: return
        transfer_id = parts[1]
        
        async with self.lock:
            transfer = self.active_transfers.get(transfer_id)
            if not transfer or transfer["to_user"] != self.connected_clients[writer]["username"]:
                return

            if action == "accept":
                if transfer["status"] != "pending_target_accept": return
                transfer["status"] = "pending_upload"
                await self._send_message(transfer["from_writer"], f"UPLOAD_PROCEED {transfer_id} {self.port}")
                await self._send_message(writer, f"SERVER_MSG Вы приняли файл '{transfer['filename']}'. Ожидание загрузки.")
            elif action == "reject":
                await self._send_message(transfer["from_writer"], f"UPLOAD_REJECTED Пользователь {transfer['to_user']} отклонил передачу файла.")
                self.active_transfers.pop(transfer_id, None)

    async def _handle_download(self, writer, parts):
        if len(parts) < 2: return
        transfer_id = parts[1]
        
        async with self.lock:
            transfer = self.active_transfers.get(transfer_id)
            if not transfer or transfer["to_user"] != self.connected_clients[writer]["username"] or transfer["status"] != "pending_download":
                await self._send_message(writer, "SERVER_MSG Ошибка: неверный ID или файл не готов к скачиванию.")
                return
            transfer["status"] = "downloading"
            
        await self._send_message(writer, f"DOWNLOAD_PROCEED {transfer_id} {self.port}")
        logging.info(f"Дано разрешение на скачивание файла {transfer_id} клиенту {transfer['to_user']}.")
    
    async def _handle_ping(self, writer, parts):
        username = self.connected_clients.get(writer, {}).get("username", "N/A")
        logging.info(f"Получен ping от пользователя '{username}'. Соединение активно.")

    command_handlers = {
        "/pm": _handle_pm,
        "/w": _handle_pm,
        "/upload": _handle_upload,
        "/file_accept": lambda self, w, p: self._handle_file_action(w, p, "accept"),
        "/file_reject": lambda self, w, p: self._handle_file_action(w, p, "reject"),
        "/download": _handle_download,
        "/ping": _handle_ping,
    }

    @staticmethod
    def _now(): return datetime.now().strftime("%H:%M:%S")

    async def _send_message(self, writer, message):
        if writer and not writer.is_closing():
            try:
                writer.write((message + "\n").encode("utf-8"))
                await writer.drain()
                return True
            except (ConnectionResetError, BrokenPipeError) as e:
                logging.warning(f"Не удалось отправить сообщение клиенту {writer.get_extra_info('peername')}: {e}")
                return False
        return False
    
    async def _broadcast_message(self, message, exclude_writer=None):
        all_writers = list(self.connected_clients.keys())
        for writer in all_writers:
            if writer != exclude_writer:
                await self._send_message(writer, message)

    async def _broadcast_user_list(self):
        async with self.lock:
            usernames = [cd["username"] for cd in self.connected_clients.values() if cd.get("username")]
        msg = f"USER_LIST {','.join(sorted(usernames))}"
        logging.info(f"Рассылка списка пользователей: {usernames}")
        await self._broadcast_message(msg)

    def _get_writer_by_username(self, username):
        for writer, data in self.connected_clients.items():
            if data.get("username") == username:
                return writer
        return None

    async def _cleanup_client(self, writer):
        username = None
        async with self.lock:
            if writer in self.connected_clients:
                removed_user = self.connected_clients.pop(writer)
                username = removed_user.get("username")
                logging.info(f"Клиент '{username}' удален из списка подключенных.")
                
                related_transfers = []
                for tid, t_info in self.active_transfers.items():
                    if t_info.get("from_writer") == writer or t_info.get("to_writer") == writer:
                        related_transfers.append(tid)
                
                for tid in related_transfers:
                    t_info = self.active_transfers.pop(tid)
                    logging.info(f"Отменен трансфер {tid} из-за отключения пользователя {username}.")
                    
                    other_writer = t_info.get("from_writer") if t_info.get("to_writer") == writer else t_info.get("to_writer")
                    if other_writer:
                        await self._send_message(other_writer, f"SERVER_MSG Передача файла '{t_info['filename']}' отменена, так как пользователь отключился.")
                    
                    if t_info.get("temp_filepath") and os.path.exists(t_info.get("temp_filepath")):
                        try:
                            os.remove(t_info.get("temp_filepath"))
                        except OSError as e:
                            logging.error(f"Не удалось удалить временный файл {t_info.get('temp_filepath')}: {e}")

            if username:
                await self._broadcast_message(f"[{self._now()}] *** Пользователь {username} вышел из чата ***")
                await self._broadcast_user_list()
        
        if not writer.is_closing():
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
    
    async def _run_broadcast_service(self):
        class BroadcastProtocol(asyncio.DatagramProtocol):
            def __init__(self, message):
                self.message = message
                self.transport = None
            def connection_made(self, transport):
                self.transport = transport
                sock = self.transport.get_extra_info('socket')
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            def send(self):
                if self.transport:
                    self.transport.sendto(self.message, ('<broadcast>', BROADCAST_PORT))

        message = json.dumps({
            "app_name": "python_chat",
            "host": self.local_ip,
            "port": self.port
        }).encode('utf-8')
        
        loop = asyncio.get_running_loop()
        try:
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: BroadcastProtocol(message), local_addr=('0.0.0.0', 0))
            logging.info(f"Служба автообнаружения запущена на UDP порту {BROADCAST_PORT}.")
            while True:
                protocol.send()
                await asyncio.sleep(BROADCAST_INTERVAL)
        except asyncio.CancelledError:
            logging.info("Служба автообнаружения остановлена.")
        except Exception as e:
            logging.error(f"Критическая ошибка в службе автообнаружения: {e}", exc_info=True)
        finally:
            if 'transport' in locals() and transport:
                transport.close()

if __name__ == "__main__":
    server = ChatServer(HOST, PORT)
    try:
        asyncio.run(server.start())
    except Exception as e:
        logging.critical(f"Не удалось запустить сервер: {e}", exc_info=True)