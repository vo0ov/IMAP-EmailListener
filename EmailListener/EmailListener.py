import os
import time
import email
import imaplib

from typing import Callable, Any, List, Optional
from functools import wraps
from email.header import decode_header
from email.message import Message
from bs4 import BeautifulSoup

# Импортируем нужные сущности из соседних файлов:
from .errors import EmailListenerException
from .types import EmailMessage


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
        """
        :param email: Адрес почты (логин).
        :param password: Пароль от почты.
        :param server: IMAP-сервер (по умолчанию 'imap.mail.ru').
        :param port: Порт IMAP (по умолчанию 993).
        :param download_folder: Папка для скачивания вложений.
        :param accepted_extensions: Список разрешённых расширений ('.pdf', '.jpg' и т.д.).
        :param mailbox: Почтовый ящик (INBOX, SENT и т.п.).
        :param search_criteria: Критерий поиска (по умолчанию 'UNSEEN').
        """
        self.email = email
        self.password = password
        self.server = server
        self.port = port

        # Папка для вложений
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

        # Список разрешённых расширений
        self.accepted_extensions = (
            tuple(ext.lower() for ext in accepted_extensions)
            if accepted_extensions
            else ('.pdf', '.zip')
        )

        # Почтовый ящик и критерий поиска
        self.mailbox = mailbox
        self.search_criteria = search_criteria

        # Список обработчиков
        self.handlers: List[Callable[[EmailMessage], Any]] = []

        # Флаг для остановки
        self._stop_flag = False

    def on_new_email(
        self, interval: int = 5
    ) -> Callable[[Callable[[EmailMessage], Any]], Callable[[EmailMessage], Any]]:
        """
        Декоратор для регистрации функций-обработчиков новых писем.
        :param interval: Интервал опроса почты (только для наглядности).
        """
        def decorator(func: Callable[[EmailMessage], Any]) -> Callable[[EmailMessage], Any]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            self.handlers.append(wrapper)
            return wrapper
        return decorator

    def _decode_str(self, value: Optional[str]) -> str:
        """
        Декодирование MIME-заголовка (например, темы или адреса).
        """
        if not value:
            return ''
        parts = []
        for decoded, charset in decode_header(value):
            if isinstance(decoded, bytes):
                try:
                    parts.append(decoded.decode(
                        charset or 'utf-8', errors='replace'))
                except LookupError as e:
                    raise EmailListenerException(
                        f'Ошибка декодирования заголовка: {e}') from e
            else:
                parts.append(decoded)
        return ''.join(parts)

    def _get_email_body(self, msg: Message) -> str:
        """
        Извлекает текст письма (text/plain или text/html).
        """
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == 'text/plain':
                    return part.get_payload(decode=True).decode(errors='replace')
                elif ctype == 'text/html':
                    html = part.get_payload(
                        decode=True).decode(errors='replace')
                    return BeautifulSoup(html, 'html.parser').get_text('\n', strip=True)
        return msg.get_payload(decode=True).decode(errors='replace')

    def _save_attachment(self, part: Message) -> Optional[str]:
        """
        Сохраняет вложение, если расширение соответствует accepted_extensions.
        """
        filename = part.get_filename()
        if filename:
            decoded_filename = self._decode_str(filename)
            # Проверяем расширение
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
        """
        Запуск бесконечного цикла прослушивания почты.
        """
        self._stop_flag = False
        try:
            mail = imaplib.IMAP4_SSL(self.server, self.port)
        except Exception as e:
            raise EmailListenerException(
                f'Ошибка подключения к серверу: {e}') from e

        try:
            mail.login(self.email, self.password)
        except Exception as e:
            raise EmailListenerException(f'Ошибка авторизации: {e}') from e

        try:
            while not self._stop_flag:
                try:
                    mail.select(self.mailbox)
                except Exception as e:
                    raise EmailListenerException(
                        f'Ошибка выбора почтового ящика: {e}') from e

                try:
                    # Ищем письма по заданному критерию
                    _, email_ids = mail.search(None, self.search_criteria)
                except Exception as e:
                    raise EmailListenerException(
                        f'Ошибка поиска писем: {e}') from e

                for eid in email_ids[0].split():
                    try:
                        _, email_data = mail.fetch(eid, '(RFC822)')
                    except Exception as e:
                        raise EmailListenerException(
                            f'Ошибка чтения письма: {e}') from e

                    try:
                        msg = email.message_from_bytes(email_data[0][1])
                    except Exception as e:
                        raise EmailListenerException(
                            f'Ошибка формирования сообщения: {e}') from e

                    # Сбор вложений
                    file_paths = []
                    for part in msg.walk():
                        if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition'):
                            saved_path = self._save_attachment(part)
                            if saved_path:
                                file_paths.append(saved_path)

                    # Создаем объект письма
                    email_message = EmailMessage(
                        title=self._decode_str(msg.get('Subject')),
                        sender=self._decode_str(msg.get('From')),
                        body=self._get_email_body(msg),
                        file_paths=file_paths
                    )

                    # Вызываем все обработчики
                    for handler in self.handlers:
                        handler(email_message)

                time.sleep(check_interval)
        except KeyboardInterrupt:
            # Уведомим вызывающую сторону, что произошла остановка
            raise EmailListenerException(
                'Прослушивание почты остановлено пользователем')
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    def stop(self) -> None:
        """
        Устанавливает флаг остановки, завершая цикл в start().
        """
        self._stop_flag = True
