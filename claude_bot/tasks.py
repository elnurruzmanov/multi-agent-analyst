"""Jadval bo'yicha bajariladigan vazifalar.

«Har kuni ertalab 8 da yangiliklarni xulosa qilib yubor» — shunday
so'rovlarni saqlaydi va vaqti kelganda bajaradi.

Ikkita qism bor va ular ataylab ajratilgan:

* **saqlash** — SQLite, chunki bot qayta ishga tushganda vazifalar yo'qolmasligi
  kerak;
* **vaqti keldimi** degan hisob (`is_due`) — sof funksiya, testlash oson.

Vaqt foydalanuvchining mahalliy vaqti bo'yicha yuritiladi (`CLAUDE_TZ_OFFSET`),
chunki «ertalab 8» degani server uchun emas, odam uchun aytiladi.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WEEKDAYS = {
    "dushanba": 0, "seshanba": 1, "chorshanba": 2, "payshanba": 3,
    "juma": 4, "shanba": 5, "yakshanba": 6,
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}
WEEKDAY_NAMES = ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba")

DAILY = "daily"
WORKDAYS = "workdays"

MAX_TASKS_PER_CHAT = 10


@dataclass
class Task:
    id: int
    chat_id: int
    prompt: str
    hour: int
    minute: int
    days: str
    last_run: str | None = None

    @property
    def when(self) -> str:
        """«har kuni 08:00» ko'rinishidagi izoh."""
        clock = f"{self.hour:02d}:{self.minute:02d}"
        if self.days == DAILY:
            return f"har kuni {clock}"
        if self.days == WORKDAYS:
            return f"ish kunlari {clock}"
        names = [WEEKDAY_NAMES[int(part)] for part in self.days.split(",") if part != ""]
        return f"{', '.join(names)} {clock}"

    def runs_on(self, weekday: int) -> bool:
        if self.days == DAILY:
            return True
        if self.days == WORKDAYS:
            return weekday < 5
        return str(weekday) in self.days.split(",")


def local_now(tz_offset: float, now: datetime | None = None) -> datetime:
    """Serverning UTC vaqtini foydalanuvchining vaqtiga o'giradi."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone(timedelta(hours=tz_offset)))


def is_due(task: Task, now: datetime, grace_hours: float = 6.0) -> bool:
    """Vazifa hozir bajarilishi kerakmi.

    Uxlab qolgan servis kech uyg'onishi mumkin, shuning uchun vaqti o'tib
    ketgan vazifa ham bajariladi — lekin cheksiz emas. Ertalabki xulosa
    kechqurun kelib qolmasin uchun `grace_hours` chegarasi bor.
    """
    if not task.runs_on(now.weekday()):
        return False
    if task.last_run == now.date().isoformat():
        return False

    scheduled = now.replace(hour=task.hour, minute=task.minute, second=0, microsecond=0)
    if now < scheduled:
        return False
    return (now - scheduled) <= timedelta(hours=grace_hours)


def parse_days(raw: str | None) -> str:
    """Modeldan kelgan kunlarni bir xil ko'rinishga keltiradi."""
    text = (raw or DAILY).strip().lower()
    if text in ("", DAILY, "har kuni", "everyday", "every day"):
        return DAILY
    if text in (WORKDAYS, "ish kunlari", "weekdays", "dushanba-juma"):
        return WORKDAYS

    numbers: list[int] = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit() and 0 <= int(part) <= 6:
            numbers.append(int(part))
        elif part in WEEKDAYS:
            numbers.append(WEEKDAYS[part])
    if not numbers:
        return DAILY
    return ",".join(str(number) for number in sorted(set(numbers)))


def parse_time(raw: str | None) -> tuple[int, int]:
    """«08:00», «8:5», «8» — hammasidan soat va daqiqa chiqaradi."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Vaqt ko'rsatilmagan. Masalan: 08:00")
    parts = text.replace(".", ":").split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        raise ValueError(f"«{text}» — vaqtga o'xshamaydi. Masalan: 08:00") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"«{text}» — bunday vaqt yo'q. 00:00 dan 23:59 gacha.")
    return hour, minute


class TaskStore:
    """Vazifalar SQLite'da: bot qayta ishga tushsa ham joyida qoladi."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                days TEXT NOT NULL,
                last_run TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._connection.commit()

    def add(self, chat_id: int, prompt: str, hour: int, minute: int, days: str) -> Task:
        if len(self.for_chat(chat_id)) >= MAX_TASKS_PER_CHAT:
            raise ValueError(
                f"Bitta chatda ko'pi bilan {MAX_TASKS_PER_CHAT} ta vazifa bo'ladi. "
                "Avval keraksizini o'chiring."
            )
        cursor = self._connection.execute(
            "INSERT INTO tasks (chat_id, prompt, hour, minute, days, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, prompt.strip(), hour, minute, days, datetime.now(timezone.utc).isoformat()),
        )
        self._connection.commit()
        return Task(cursor.lastrowid, chat_id, prompt.strip(), hour, minute, days)

    def remove(self, chat_id: int, task_id: int) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM tasks WHERE id = ? AND chat_id = ?", (task_id, chat_id)
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def for_chat(self, chat_id: int) -> list[Task]:
        rows = self._connection.execute(
            "SELECT * FROM tasks WHERE chat_id = ? ORDER BY hour, minute", (chat_id,)
        ).fetchall()
        return [_row_to_task(row) for row in rows]

    def all(self) -> list[Task]:
        rows = self._connection.execute("SELECT * FROM tasks").fetchall()
        return [_row_to_task(row) for row in rows]

    def due(self, now: datetime, grace_hours: float = 6.0) -> list[Task]:
        return [task for task in self.all() if is_due(task, now, grace_hours)]

    def mark_run(self, task_id: int, day: date) -> None:
        self._connection.execute(
            "UPDATE tasks SET last_run = ? WHERE id = ?", (day.isoformat(), task_id)
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"], chat_id=row["chat_id"], prompt=row["prompt"],
        hour=row["hour"], minute=row["minute"], days=row["days"],
        last_run=row["last_run"],
    )


# --- Claude uchun qurollar --------------------------------------------------

SCHEDULE_TOOL = {
    "name": "schedule_task",
    "description": (
        "Takrorlanadigan vazifa qo'shish. Foydalanuvchi «har kuni ertalab 8 da "
        "yangiliklarni yubor» kabi so'rasa shuni chaqir. Vaqt foydalanuvchining "
        "mahalliy vaqti. `prompt` — o'sha paytda menga beriladigan topshiriq, "
        "to'liq va mustaqil yozilsin, chunki u yangi suhbatda bajariladi."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "time": {"type": "string", "description": "Soat, masalan «08:00»."},
            "days": {
                "type": "string",
                "description": (
                    "«daily», «workdays» yoki kunlar: «dushanba,chorshanba». "
                    "Ko'rsatilmasa har kuni."
                ),
            },
            "prompt": {"type": "string", "description": "Bajariladigan topshiriq."},
        },
        "required": ["time", "prompt"],
    },
}

LIST_TOOL = {
    "name": "list_tasks",
    "description": "Shu chatdagi rejalashtirilgan vazifalar ro'yxatini olish.",
    "input_schema": {"type": "object", "properties": {}},
}

CANCEL_TOOL = {
    "name": "cancel_task",
    "description": "Rejalashtirilgan vazifani o'chirish. `id` ni list_tasks beradi.",
    "input_schema": {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "required": ["id"],
    },
}

TOOLS = (SCHEDULE_TOOL, LIST_TOOL, CANCEL_TOOL)
