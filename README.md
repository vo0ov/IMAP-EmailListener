# Документация к библиотеке **EmailListener**

**Содержание**  
1. [Введение](#введение)  
2. [Установка](#установка)  
3. [Использование](#использование)  
4. [Описание классов и методов](#описание-классов-и-методов)  
   - [Исключение EmailListenerException](#исключение-emaillistenerexception)  
   - [Класс EmailMessage](#класс-emailmessage)  
   - [Класс EmailListener](#класс-emaillistener)  
     - [Конструктор](#конструктор)  
     - [on_new_email](#on_new_email)  
     - [_decode_str](#_decode_str)  
     - [_get_email_body](#_get_email_body)  
     - [_save_attachment](#_save_attachment)  
     - [start](#start)  
     - [stop](#stop)  
5. [Пример кода](#пример-кода)  
6. [Дополнительно о настройке IMAP](#дополнительно-о-настройке-imap)

---

## Введение
Библиотека **EmailListener** предназначена для отслеживания новых писем в почтовом ящике через протокол IMAP. Она предоставляет удобный интерфейс для:
- Авторизации на почтовом сервере.
- Выбора почтового ящика (по умолчанию **INBOX**).
- Использования любого произвольного критерия поиска писем (например, **UNSEEN**, **ALL**, **FROM "someone"** и т.д.).
- Скачивания вложений с ограничением по типу файлов.
- Регистрации и вызова обработчиков (колбэков) при появлении новых писем.

Главная особенность — библиотека не содержит прямых вызовов `print` и `exit`, что позволяет гибко использовать её в любых проектах и контролировать поток вывода и логику завершения самостоятельно. Все ошибки, с которыми библиотека сталкивается, обрабатываются путём генерации исключений класса `EmailListenerException`.

---

## Установка
Если у вас есть файл **email_listener.py**, его можно просто включить в проект. При желании оформить как отдельный Python-пакет и установить через `pip`, необходимо:
1. Создать структуру пакета (добавить `setup.py`, `__init__.py` и т.д.).
2. Выполнить команду:
   ```bash
   pip install .
   ```
   в корне проекта (где лежит `setup.py`).

Для установки дополнительных зависимостей (например, `beautifulsoup4`) используйте:
   ```bash
   pip install beautifulsoup4
   ```

---

## Использование
1. Импортируйте `EmailListener` и нужные классы из файла **email_listener.py**.
2. Создайте объект `EmailListener`, передав необходимые настройки (логин, пароль, сервер, порт и т.д.).
3. Используйте декоратор `@mail_listener.on_new_email(...)` для регистрации функций-обработчиков писем.
4. Вызовите метод `mail_listener.start(...)` для запуска прослушивания.
5. Чтобы остановить прослушивание, примените `mail_listener.stop()` из любого места кода (или ждите `KeyboardInterrupt`, если вы запускаете прослушивание в основном потоке).

---

## Описание классов и методов

### Исключение **EmailListenerException**
- **Наследуется от** `Exception`.
- **Предназначение**: использоваться для всех ошибок, возникающих в процессе работы библиотеки (ошибки подключения, авторизации, чтения писем, декодирования, сохранения вложений и т.д.).
- **Поведение**: любая нештатная ситуация внутри `EmailListener` вызывает `raise EmailListenerException(...)` с описанием проблемы.

---

### Класс **EmailMessage**
- **Атрибуты**:
  - `title: str` — тема письма.
  - `body: str` — текстовое содержимое письма (извлекается в приоритете: `text/plain`, если нет, то `text/html`).
  - `sender: str` — адрес (и возможное имя) отправителя.
  - `file_paths: List[str]` — список путей к сохранённым вложениям на диске.

Данный класс является простым контейнером (Dataclass), хранящим информацию о конкретном письме, которое передаётся в каждый обработчик.

---

### Класс **EmailListener**
Основной класс, обеспечивающий:
1. Подключение и авторизацию на почтовом сервере (через IMAP).
2. Периодический (с помощью цикла) опрос новых писем.
3. Скачивание вложений (при необходимости).
4. Вызов всех зарегистрированных обработчиков.

#### Конструктор
   ```Python
   def __init__(
       self,
       email: str,
       password: str,
       server: str = 'imap.mail.ru',
       port: int = 993,
       download_folder: Optional[str] = None,
       accepted_extensions: Optional[List[str]] = None,
       mailbox: str = 'INBOX',
       search_criteria: str = 'UNSEEN'
   ):
       ...
   ```

- **email**: Ваш адрес почты (логин для IMAP).
- **password**: Пароль от почты (зачастую требуются специальные пароли приложений).
- **server**: Адрес IMAP-сервера (по умолчанию `imap.mail.ru`).
- **port**: Порт IMAP-сервера (по умолчанию `993`).
- **download_folder**: Папка для скачивания вложений. Если не указано, создаётся `downloads` в директории рядом с файлом **email_listener.py**.
- **accepted_extensions**: Список разрешённых расширений файлов (например, `['.pdf', '.zip', '.jpg']`). Если не указано, по умолчанию `('.pdf', '.zip')`.
- **mailbox**: Почтовый ящик для прослушивания (по умолчанию `INBOX`).
- **search_criteria**: Критерий поиска писем в формате IMAP (по умолчанию `UNSEEN` — не прочитанные письма). Примеры:
  - `'ALL'` — все письма.
  - `'FROM "someone@example.com"'` — письма от конкретного адреса.
  - `'SUBJECT "hello"'` — письма с темой, содержащей "hello".

При инициализации создаются:
- Список обработчиков (handlers).
- Внутренняя переменная `_stop_flag` для плавной остановки.

#### on_new_email
   ```Python
   def on_new_email(self, interval: int = 5) -> Callable[[Callable[[EmailMessage], Any]], Callable[[EmailMessage], Any]]:
       ...
   ```

- **Описание**: Декоратор, регистрирующий обработчики новых писем.  
- **Параметр** `interval: int = 5` служит лишь для наглядности — описывает, что обработчик будет вызываться в цикле, который проверяется каждые `5` секунд (по умолчанию). Технически этот параметр не используется внутри `start()`, но он позволяет иметь несколько декораторов с разным интервалом, если вы захотите модифицировать логику.
- **Возвращает**: функцию-декоратор, которая добавляет саму обёрнутую функцию в список `handlers`.
- **Пример**:
  ```Python
  @mail_listener.on_new_email(interval=10)
  def my_handler(msg: EmailMessage):
      print("У меня есть письмо!", msg)
  ```

#### _decode_str
   ```Python
   def _decode_str(self, value: Optional[str]) -> str:
       ...
   ```
- **Описание**: Метод, декодирующий заголовки (например, тему и отправителя) из MIME-формата (base64, квотированный-printable и т.д.).  
- **На вход**: строка `value`, которая может быть в любом виде или `None`.
- **На выход**: обычная Python-строка в UTF-8 с заменой непредвиденных символов (`errors='replace'`).
- **Генерирует** `EmailListenerException`, если что-то пошло не так в процессе декодирования.

#### _get_email_body
   ```Python
   def _get_email_body(self, msg: Message) -> str:
       ...
   ```
- **Описание**: Извлекает тело письма (body) с приоритетом `text/plain`. Если нет, берёт `text/html` и чистит его от HTML-тэгов через `BeautifulSoup`.
- **На вход**: объект `Message` из модуля `email`.
- **На выход**: декодированная строка.

#### _save_attachment
   ```Python
   def _save_attachment(self, part: Message) -> Optional[str]:
       ...
   ```
- **Описание**: Проверяет, является ли часть письма вложением (нужен `Content-Disposition`) и не `multipart`. Если расширение вложения подходит под `accepted_extensions`, оно сохраняется на диск.
- **Возвращает**: Путь к сохранённому файлу или `None`, если нет файла или расширение не подходит.
- **Генерирует** `EmailListenerException` при ошибках записи на диск.

#### start
   ```Python
   def start(self, check_interval: int = 5) -> None:
       ...
   ```
- **Описание**: Запускает основной цикл прослушивания.
- **Параметр** `check_interval` (по умолчанию 5 сек): частота опроса IMAP-сервера. Внутри цикла:
  1. Выбирается папка `mailbox`.
  2. Поисковые критерии: `search_criteria`.
  3. Для каждого найденного письма вызывается `email.message_from_bytes(...)` и формируется `EmailMessage`.
  4. Запускаются все обработчики из `handlers`.
  5. Пауза `time.sleep(check_interval)`.

- **Остановка**:  
  - Если пользователь нажмёт `Ctrl+C`, сгенерируется `KeyboardInterrupt`, обёрнутый в `EmailListenerException('Прослушивание почты остановлено пользователем')`.
  - Вызов `stop()` (см. ниже) установит `_stop_flag = True`, и цикл завершится без генерирования исключения.

#### stop
   ```Python
   def stop(self) -> None:
       ...
   ```
- **Описание**: Устанавливает флаг `_stop_flag = True`, благодаря чему основной цикл в `start()` завершится в ближайшем цикле `while`.
- **Где использовать**: Можно вызывать из любого места, если у вас, например, есть внешний управляющий поток или логика, при которой нужно завершить прослушивание писем без прерывания клавиатурой.

---

## Пример кода

Ниже приведён полный код файла **email_listener.py** со встроенным примером использования в блоке `if __name__ == '__main__':`.

```Python
import os
import time
import email
import imaplib
from typing import Callable, Any, List, Optional
from functools import wraps
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from bs4 import BeautifulSoup

class EmailListenerException(Exception):
    """Базовое исключение для EmailListener."""
    pass

@dataclass
class EmailMessage:
    title: str
    body: str
    sender: str
    file_paths: List[str]

class EmailListener:
    def __init__(
        self,
        email: str,
        password: str,
        server: str = 'imap.mail.ru',
        port: int = 993,
        download_folder: Optional[str] = None,
        accepted_extensions: Optional[List[str]] = None,
        mailbox: str = 'INBOX',
        search_criteria: str = 'UNSEEN'
    ):
        self.email = email
        self.password = password
        self.server = server
        self.port = port
        self.handlers: List[Callable[[EmailMessage], Any]] = []

        self.download_folder = (
            download_folder
            if download_folder
            else os.path.join(os.path.dirname(__file__), 'downloads')
        )
        if not os.path.exists(self.download_folder):
            try:
                os.makedirs(self.download_folder, exist_ok=True)
            except OSError as e:
                raise EmailListenerException(
                    f'Не удалось создать папку для загрузки: {e}'
                ) from e

        self.accepted_extensions = (
            tuple(ext.lower() for ext in accepted_extensions)
            if accepted_extensions
            else ('.pdf', '.zip')
        )
        self.mailbox = mailbox
        self.search_criteria = search_criteria
        self._stop_flag = False

    def on_new_email(
        self, interval: int = 5
    ) -> Callable[[Callable[[EmailMessage], Any]], Callable[[EmailMessage], Any]]:
        def decorator(func: Callable[[EmailMessage], Any]) -> Callable[[EmailMessage], Any]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            self.handlers.append(wrapper)
            return wrapper
        return decorator

    def _decode_str(self, value: Optional[str]) -> str:
        if not value:
            return ''
        parts = []
        for decoded, charset in decode_header(value):
            if isinstance(decoded, bytes):
                try:
                    parts.append(decoded.decode(charset or 'utf-8', errors='replace'))
                except LookupError as e:
                    raise EmailListenerException(f'Ошибка декодирования заголовка: {e}') from e
            else:
                parts.append(decoded)
        return ''.join(parts)

    def _get_email_body(self, msg: Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    return part.get_payload(decode=True).decode(errors='replace')
                elif ctype == 'text/html':
                    html = part.get_payload(decode=True).decode(errors='replace')
                    return BeautifulSoup(html, 'html.parser').get_text('\n', strip=True)
        return msg.get_payload(decode=True).decode(errors='replace')

    def _save_attachment(self, part: Message) -> Optional[str]:
        filename = part.get_filename()
        if filename:
            decoded_filename = self._decode_str(filename)
            if any(decoded_filename.lower().endswith(ext) for ext in self.accepted_extensions):
                path = os.path.join(self.download_folder, decoded_filename)
                try:
                    with open(path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                except OSError as e:
                    raise EmailListenerException(
                        f'Не удалось сохранить вложение {decoded_filename}: {e}'
                    ) from e
                return path
        return None

    def start(self, check_interval: int = 5) -> None:
        self._stop_flag = False
        try:
            mail = imaplib.IMAP4_SSL(self.server, self.port)
        except Exception as e:
            raise EmailListenerException(f'Ошибка подключения к серверу: {e}') from e

        try:
            mail.login(self.email, self.password)
        except Exception as e:
            raise EmailListenerException(f'Ошибка авторизации: {e}') from e

        try:
            while not self._stop_flag:
                try:
                    mail.select(self.mailbox)
                except Exception as e:
                    raise EmailListenerException(f'Ошибка выбора почтового ящика: {e}') from e

                try:
                    _, email_ids = mail.search(None, self.search_criteria)
                except Exception as e:
                    raise EmailListenerException(f'Ошибка поиска писем: {e}') from e

                for eid in email_ids[0].split():
                    try:
                        _, email_data = mail.fetch(eid, '(RFC822)')
                    except Exception as e:
                        raise EmailListenerException(f'Ошибка чтения письма: {e}') from e

                    try:
                        msg = email.message_from_bytes(email_data[0][1])
                    except Exception as e:
                        raise EmailListenerException(f'Ошибка формирования сообщения: {e}') from e

                    file_paths = []
                    for part in msg.walk():
                        if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition'):
                            saved_path = self._save_attachment(part)
                            if saved_path:
                                file_paths.append(saved_path)

                    email_message = EmailMessage(
                        title=self._decode_str(msg.get('Subject')),
                        sender=self._decode_str(msg.get('From')),
                        body=self._get_email_body(msg),
                        file_paths=file_paths
                    )

                    for handler in self.handlers:
                        handler(email_message)

                time.sleep(check_interval)

        except KeyboardInterrupt:
            raise EmailListenerException('Прослушивание почты остановлено пользователем')
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop_flag = True

if __name__ == '__main__':
    def main():
        mail_listener = EmailListener(
            email='EMAIL',
            password='PASSWORD',
            server='imap.mail.ru',
            port=993,
            download_folder='/path/to/custom/folder',
            accepted_extensions=['.jpg', '.pdf', '.zip'],
            mailbox='INBOX',
            search_criteria='UNSEEN'
        )

        @mail_listener.on_new_email(interval=5)
        def print_all_emails(message: EmailMessage):
            print('\n' + '=' * 50)
            print(f'Тема: {message.title}')
            print(f'От: {message.sender}')
            print('\nТекст письма:')
            print('-' * 20)
            print(message.body)
            if message.file_paths:
                print('\nВложения:')
                for path in message.file_paths:
                    print(f'- {path}')
            print('=' * 50)

        @mail_listener.on_new_email()
        def handle_important_emails(message: EmailMessage):
            if 'important@example.com' in message.sender.lower():
                print(f'\nПолучено важное письмо: {message.title}')

        attachments_count = 0

        @mail_listener.on_new_email()
        def count_attachments(message: EmailMessage):
            nonlocal attachments_count
            if message.file_paths:
                attachments_count += len(message.file_paths)
                print(f'\nВсего получено вложений: {attachments_count}')

        print('Запуск прослушивания почты... Нажмите Ctrl+C или вызовите mail_listener.stop() для остановки.')
        try:
            mail_listener.start()
        except EmailListenerException as exc:
            print(f'\nОшибка в работе EmailListener: {exc}')
        finally:
            mail_listener.stop()

    main()
```

---

## Дополнительно о настройке IMAP
- На большинстве почтовых сервисов для IMAP может потребоваться **включить IMAP-доступ** в настройках аккаунта.
- Часто требуется **пароль приложений** (application password), а не основной пароль, особенно для сервисов, поддерживающих двухфакторную аутентификацию.
- Если вы используете **Gmail**, IMAP-сервер обычно `imap.gmail.com`, порт `993`, и обязательно включенный IMAP в настройках Gmail.

---

**Спасибо за использование **EmailListener**!** 
Если возникнут вопросы или проблемы, вы можете:
- Создать issue (если используете репозиторий на GitHub).
- Написать автору напрямую.
- Сделать pull request с улучшениями.
