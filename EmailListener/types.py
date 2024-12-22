from dataclasses import dataclass
from typing import List


@dataclass
class EmailMessage:
    """
    Dataclass для хранения информации о полученном письме.
    """
    title: str
    body: str
    sender: str
    file_paths: List[str]
