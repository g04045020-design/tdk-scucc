import sqlite3
import logging
from logging import Handler
import threading
import re
import sys
import os
from datetime import datetime

ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
def remove_ansi_codes(text):
    return ANSI_ESCAPE.sub('', text)


class SQLiteHandler(Handler):
    def __init__(self, db_file="logs.sqlite"):
        super().__init__()
        self.db_file = db_file
        self._lock = threading.Lock()
        self._create_table()

    def _get_conn(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _create_table(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TEXT,
            level TEXT,
            logger TEXT,
            message TEXT
        )
        """)
        conn.commit()
        conn.close()

    def emit(self, record):
        conn = self._get_conn()
        with self._lock:
            c = conn.cursor()
            created = self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S")
            message = remove_ansi_codes(record.getMessage())
            c.execute(
                "INSERT INTO logs (created, level, logger, message) VALUES (?, ?, ?, ?)",
                (created, record.levelname, record.name, message)
            )
            conn.commit()
        conn.close()


class LoggerWriter:
    """print és stderr átirányítása a loggerbe"""
    def __init__(self, level):
        self.level = level
    def write(self, message):
        message = message.strip()
        if message:
            self.level(message)
    def flush(self):
        pass


def setup_sqlite_logging(app, logs_mappa, level=logging.INFO, redirect_prints=True):
    with open(os.path.join(logs_mappa, "filename.info"), "w+") as f:
        adat = f.read()
        nap = datetime.now().strftime("%Y.%m.%d")
        if adat or nap != adat: # új file kell
            f.write(nap)
            db_file = os.path.join(logs_mappa, nap+".db")
        else: db_file = os.path.join(logs_mappa, adat+".db")


    sqlite_handler = SQLiteHandler(db_file=db_file)
    formatter = logging.Formatter("%(asctime)s")
    sqlite_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Flask app logger
    app.logger.handlers = []
    app.logger.setLevel(level)
    app.logger.addHandler(sqlite_handler)
    app.logger.addHandler(console_handler)

    # Werkzeug logger
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers = []
    werkzeug_logger.setLevel(level)
    werkzeug_logger.addHandler(sqlite_handler)
    werkzeug_logger.addHandler(console_handler)

    # Redirect print() és hibák a loggerbe
    if redirect_prints and os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        sys.stdout = LoggerWriter(logging.getLogger("stdout").info)
        sys.stderr = LoggerWriter(logging.getLogger("stderr").error)

    return sqlite_handler
