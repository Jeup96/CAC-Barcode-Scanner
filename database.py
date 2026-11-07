import sqlite3
from datetime import datetime


class Database:

    def __init__(self, db_path="personnel.db"):

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.create_tables()

    def create_tables(self):

        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                rank TEXT,
                status TEXT,
                location TEXT,
                last_scan TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                rank TEXT,
                action TEXT,
                location TEXT,
                timestamp TEXT
            )
        """)

        self.conn.commit()

    def check_in(self, name, rank):

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cur = self.conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO personnel
            (
                name,
                rank,
                status,
                location,
                last_scan
            )
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            rank,
            "IN",
            "",
            now
        ))

        cur.execute("""
            INSERT INTO activity
            (
                name,
                rank,
                action,
                location,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            rank,
            "CHECK_IN",
            "",
            now
        ))

        self.conn.commit()

    def check_out(
        self,
        name,
        rank,
        location
    ):

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cur = self.conn.cursor()

        cur.execute("""
            UPDATE personnel
            SET
                status=?,
                location=?,
                last_scan=?
            WHERE name=?
        """,
        (
            "OUT",
            location,
            now,
            name
        ))

        cur.execute("""
            INSERT INTO activity
            (
                name,
                rank,
                action,
                location,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            rank,
            "CHECK_OUT",
            location,
            now
        ))

        self.conn.commit()

    def get_person(self, name):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM personnel
            WHERE name=?
        """,
        (name,))

        return cur.fetchone()

    def get_all_personnel(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                name,
                rank,
                status,
                location,
                last_scan
            FROM personnel
            ORDER BY name
        """)

        return cur.fetchall()

    def count_in(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM personnel
            WHERE status='IN'
        """)

        return cur.fetchone()[0]

    def count_out(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM personnel
            WHERE status='OUT'
        """)

        return cur.fetchone()[0]

    def total_count(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM personnel
        """)

        return cur.fetchone()[0]

    def scan_count(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM activity
        """)

        return cur.fetchone()[0]

    def last_scan(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                name,
                timestamp
            FROM activity
            ORDER BY id DESC
            LIMIT 1
        """)

        return cur.fetchone()

    def search_personnel(self, search):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                name,
                rank,
                status,
                location,
                last_scan
            FROM personnel
            WHERE name LIKE ?
            ORDER BY name
        """,
        (f"%{search}%",))

        return cur.fetchall()

    def get_activity(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                timestamp,
                name,
                action,
                location
            FROM activity
            ORDER BY id DESC
            LIMIT 100
        """)

        return cur.fetchall()

    def clear_all(self):

        cur = self.conn.cursor()

        cur.execute(
            "DELETE FROM personnel"
        )

        cur.execute(
            "DELETE FROM activity"
        )

        self.conn.commit()

    def export_roster_csv(
        self,
        filename="roster_export.csv"
    ):

        import csv

        rows = self.get_all_personnel()

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "Name",
                    "Rank",
                    "Status",
                    "Location",
                    "Last Scan"
                ]
            )

            writer.writerows(rows)

    def export_activity_csv(
        self,
        filename="activity_export.csv"
    ):

        import csv

        rows = self.get_activity()

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    "Timestamp",
                    "Name",
                    "Action",
                    "Location"
                ]
            )

            writer.writerows(rows)