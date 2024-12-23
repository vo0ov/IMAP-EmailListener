### !!! Для личного использования в проекте vo0ov, но вы можете использовать библиотеку в своих проектах. !!!
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

```bash
pip install IMAP-EmailListener
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
- **download_folder**: Папка для скачивания вложений. Если не указано, создаётся `downloads` в текущей директории.
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
import sys
from EmailListener import EmailListener, EmailMessage, EmailListenerException


def my_email_handler(email: EmailMessage):
    print('Новое письмо получено!')
    print(f'Отправитель: {email.sender}')
    print(f'Тема: {email.title}')
    print(f'Содержимое:\n{email.body}')

    if email.file_paths:
        print('Вложения сохранены по следующим путям:')
        for path in email.file_paths:
            print(f' - {path}')
    print('-' * 50)


def main():
    email_address = 'ПОЧТА'
    email_password = 'ПАРОЛЬ'  # Чаще пароль приложения
    imap_server = 'imap.mail.ru'  # Замените на нужный IMAP сервер
    imap_port = 993  # Порт обычно 993

    mail_listener = EmailListener(
        email=email_address,
        password=email_password,
        server=imap_server,
        port=imap_port,
        download_folder='attachments',
        accepted_extensions=['.pdf', '.jpg'],
        mailbox='INBOX',
        search_criteria='UNSEEN'
    )

    @mail_listener.on_new_email()
    def handle_new_email(email: EmailMessage):
        my_email_handler(email)

    try:
        print('Запуск прослушивания почты...')
        mail_listener.start(check_interval=10)
    except EmailListenerException as e:
        print(f'Произошла ошибка: {e}', file=sys.stderr)
    except KeyboardInterrupt:
        print('\nОстановка прослушивания почты пользователем.')
        mail_listener.stop()


if __name__ == '__main__':
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
