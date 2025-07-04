Wi-Fi Chat Pro: Локальный чат на Python
Wi-Fi Chat Pro — это полнофункциональное клиент-серверное приложение для обмена текстовыми сообщениями и файлами в рамках локальной беспроводной сети. Проект написан с нуля на чистом Python без использования сторонних зависимостей, что делает его максимально портативным и легким для запуска.

Проект был создан как часть курсовой работы, но представляет собой полноценный рабочий прототип, демонстрирующий ключевые аспекты сетевого программирования.



🚀 Основные возможности
Общий и личные чаты: Общайтесь со всеми пользователями в общем чате или отправляйте приватные сообщения.

Передача файлов: Безопасная передача любых файлов между пользователями через сервер-посредник.

Автообнаружение сервера: Клиентам не нужно вводить IP-адрес вручную. Приложение автоматически находит сервер в локальной сети с помощью UDP-рассылки.

Кросс-платформенность: Сервер и клиент гарантированно работают на Windows, macOS и Linux.

Кастомизация интерфейса: Клиентское приложение поддерживает светлую и тёмную темы, а также настройку размера шрифта.

Отсутствие внешних зависимостей: Для работы нужен только стандартный интерпретатор Python 3. Никаких pip install.

Пользовательские уведомления: Всплывающие toast-уведомления информируют о новых сообщениях и статусе передачи файлов, не прерывая работу.

🛠️ Технологический стек
Весь проект построен исключительно на Стандартной библиотеке Python, что является его ключевой особенностью.

Сервер:

asyncio: Для высокопроизводительной асинхронной обработки сотен одновременных подключений.

socket: Для низкоуровневой работы с TCP-сокетами (основной канал, передача файлов) и UDP-сокетами (автообнаружение).

logging: Для детального логирования работы сервера.

json: Для сериализации данных в службе автообнаружения.

Клиент:

tkinter: Для создания кросс-платформенного графического пользовательского интерфейса (GUI).

threading: Для разделения сетевой логики и логики GUI, что обеспечивает отзывчивость интерфейса.

queue: Для безопасного обмена данными между потоками.

pathlib: Для кросс-платформенной работы с файловыми путями.

⚙️ Как запустить
Для работы приложения не требуется установка каких-либо пакетов. Нужен только Python 3.8+.

1. Запуск сервера

Выберите компьютер в вашей Wi-Fi сети, который будет выполнять роль сервера.

Клонируйте репозиторий:

git clone https://github.com/Padre12Rus/wifi_prodeji/
cd wifi-chat-pro

Запустите серверный скрипт:

python server.py

В консоли вы увидите сообщение о запуске и локальный IP-адрес сервера. Сервер готов к приему подключений.


2. Запуск клиента

На любом другом компьютере (или на том же) в той же Wi-Fi сети запустите клиентский скрипт:

python client.py

Откроется окно входа. Приложение автоматически начнет поиск сервера. Как только сервер будет найден, появится соответствующее уведомление.

Введите желаемый никнейм (3-16 символов, латиница, цифры, _, ., -) и нажмите "Подключиться".


Готово! Вы можете начать общение. Запустите несколько клиентов на разных машинах, чтобы протестировать все возможности.

📂 Структура проекта
server.py: Главный файл сервера. Содержит всю логику по управлению чатом.

client.py: Главный файл клиента. Содержит всю логику GUI и взаимодействия с сервером.

server_uploads/: Папка, которая создается сервером для временного хранения файлов при передаче.

user_settings.json: Файл, который создается клиентом для сохранения ваших настроек (тема, ник, размер окна).

*.log: Файлы логирования для сервера и клиента. Помогают при отладке.

🔮 Будущие улучшения
Проект имеет большой потенциал для развития. Вот некоторые идеи:

🔐 Безопасность: Интеграция SSL/TLS для шифрования всего трафика.

👥 Групповые чаты: Возможность создавать приватные "комнаты" для общения.

📜 История сообщений: Сохранение истории переписки в локальной базе данных (например, sqlite3).

✨ Расширенный контент: Поддержка отправки изображений с предпросмотром прямо в чат, форматирование текста и эмодзи.

🚀 Оптимизация протокола: Переход на бинарный протокол для уменьшения сетевого трафика.

📄 Лицензия
Проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.
