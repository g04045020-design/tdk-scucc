import os
import psycopg2
import psycopg2.extras
import random
from datetime import datetime
import re

def nonefix(val):
    return None if val == 'None' else val

class Database:
    def __init__(self, db_url=None):
        # Railway environment változó
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise RuntimeError("DATABASE_URL nincs beállítva")
        # Railway néha "postgres://" prefixet ad — psycopg2 elfogadja ugyan, de egységesítünk
        if self.db_url.startswith("postgres://"):
            self.db_url = self.db_url.replace("postgres://", "postgresql://", 1)

    def connect(self):
        # egyszerű csatlakozás; ha szükséges, hozzáadhatsz sslmode='require'
        return psycopg2.connect(self.db_url)

    def execute(self, query, params=()):
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                conn.commit()
            return True
        except psycopg2.Error as e:
            print(f"Hiba az adatbázis művelet során: {e.pgcode} {e.pgerror}\nQuery: {query}\nParams: {params}")
            return False

    def fetch_all(self, query, params=()):
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Hiba a lekérdezés során: {e.pgcode} {e.pgerror}\nQuery: {query}\nParams: {params}")
            return []

    def fetch_one(self, query, params=()):
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Hiba a lekérdezés során: {e.pgcode} {e.pgerror}\nQuery: {query}\nParams: {params}")
            return None

    # segédfüggvény: táblalétezés ellenőrzése
    def table_exists(self, table_name):
        q = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """
        r = self.fetch_one(q, (table_name,))
        return bool(r[0]) if r is not None else False

    # segédfüggvény: oszlop létezik-e
    def column_exists(self, table_name, column_name):
        q = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        )
        """
        r = self.fetch_one(q, (table_name, column_name))
        return bool(r[0]) if r is not None else False

    def rebuild_database(self):
        # PostgreSQL-kompatibilis sémák (CREATE TABLE IF NOT EXISTS)
        tables = [
            ("ValaszthatoSzakok",
             '''CREATE TABLE IF NOT EXISTS ValaszthatoSzakok (
                SzakID INTEGER PRIMARY KEY,
                SzakNev VARCHAR(70) NOT NULL
            )''',
             ["SzakID", "SzakNev"]),

            ("Szokeszletek",
             '''CREATE TABLE IF NOT EXISTS Szokeszletek (
                SzokeszletID INTEGER PRIMARY KEY,
                Nev VARCHAR(500) NOT NULL,
                Tulajdonos VARCHAR(300)
            )''',
             ["SzokeszletID", "Nev", "Tulajdonos"]),

            ("Szavak",
             '''CREATE TABLE IF NOT EXISTS Szavak (
                ID SERIAL PRIMARY KEY,
                SzokeszletID INTEGER NOT NULL,
                IdegenSzo VARCHAR(100) NOT NULL,
                Jelentes1 VARCHAR(100) NOT NULL,
                Jelentes2 VARCHAR(100),
                Jelentes3 VARCHAR(100),
                Jelentes4 VARCHAR(100),
                Jelentes5 VARCHAR(100),
                Fonetika VARCHAR(100),
                Leiras VARCHAR(500),
                Szoveg_Kontextus VARCHAR(500),
                FOREIGN KEY (SzokeszletID) REFERENCES Szokeszletek(SzokeszletID) ON DELETE CASCADE
            )''',
             ["ID", "SzokeszletID", "IdegenSzo", "Jelentes1", "Jelentes2", "Jelentes3", "Jelentes4", "Jelentes5", "Fonetika", "Leiras", "Szoveg_Kontextus"]),

            ("Parok",
             '''CREATE TABLE IF NOT EXISTS Parok (
                ParID INTEGER NOT NULL,
                SzoID INTEGER NOT NULL,
                KivalasztottSzo1 VARCHAR(100) NOT NULL,
                KivalasztottSzo2 VARCHAR(100) NOT NULL,
                KivalasztottSzo3 VARCHAR(500),
                PozicioHelyesseg VARCHAR(100) NOT NULL,
                Pontszam INTEGER NOT NULL,
                ISHelyesPar INTEGER NOT NULL,
                FOREIGN KEY (SzoID) REFERENCES Szavak(ID) ON DELETE CASCADE
            )''',
             ["ParID", "SzoID", "KivalasztottSzo1", "KivalasztottSzo2", "KivalasztottSzo3", "PozicioHelyesseg", "Pontszam", "ISHelyesPar"]),

            ("AlfeladatKivalasztasos",
             '''CREATE TABLE IF NOT EXISTS AlfeladatKivalasztasos (
                AlfeladatID INTEGER NOT NULL,
                SzoID INTEGER NOT NULL,
                MegadottSzo INTEGER NOT NULL,
                KivalasztottSzo1 VARCHAR(100) NOT NULL,
                KivalasztottSzo2 VARCHAR(100),
                KivalasztottSzo3 VARCHAR(100),
                KivalasztottSzo4 VARCHAR(100),
                KivalasztottSzo5 VARCHAR(100),
                KivalasztottSzo6 VARCHAR(100),
                PozicioHelyesseg VARCHAR(100) NOT NULL,
                VarialasSzama INTEGER NOT NULL,
                SzuksegesIdo INTEGER NOT NULL,
                Pontszam INTEGER NOT NULL,
                ISProbalkozas INTEGER NOT NULL,
                FOREIGN KEY (SzoID) REFERENCES Szavak(ID) ON DELETE CASCADE
            )''',
             ["AlfeladatID", "SzoID", "MegadottSzo", "KivalasztottSzo1", "KivalasztottSzo2", "KivalasztottSzo3", "KivalasztottSzo4", "KivalasztottSzo5", "KivalasztottSzo6", "PozicioHelyesseg", "VarialasSzama", "SzuksegesIdo", "Pontszam", "ISProbalkozas"]),

            ("AlfeladatBeirasos",
             '''CREATE TABLE IF NOT EXISTS AlfeladatBeirasos (
                AlfeladatID INTEGER NOT NULL,
                MegadottBetuIndex VARCHAR(100) NOT NULL,
                SzoID INTEGER NOT NULL,
                MegadottSzo INTEGER NOT NULL,
                BegepeltSzo1 VARCHAR(100) NOT NULL,
                BegepeltSzo2 VARCHAR(100),
                BegepeltSzo3 VARCHAR(100),
                BegepeltSzo4 VARCHAR(100),
                BegepeltSzo5 VARCHAR(100),
                BegepeltSzo6 VARCHAR(100),
                PozicioHelyesseg VARCHAR(100) NOT NULL,
                SzuksegesIdo INTEGER NOT NULL,
                Pontszam INTEGER NOT NULL,
                ISProbalkozas INTEGER NOT NULL,
                FOREIGN KEY (SzoID) REFERENCES Szavak(ID) ON DELETE CASCADE
            )''',
             ["AlfeladatID", "MegadottBetuIndex", "SzoID", "MegadottSzo", "BegepeltSzo1", "BegepeltSzo2", "BegepeltSzo3", "BegepeltSzo4", "BegepeltSzo5", "BegepeltSzo6", "PozicioHelyesseg", "SzuksegesIdo", "Pontszam", "ISProbalkozas"]),

            ("AlfeladatParositasos",
             '''CREATE TABLE IF NOT EXISTS AlfeladatParositasos (
                AlfeladatID INTEGER NOT NULL,
                ParID SERIAL PRIMARY KEY,
                VarialasSzama INTEGER NOT NULL,
                SzuksegesIdo INTEGER NOT NULL,
                ISProbalkozas INTEGER NOT NULL
            )''',
             ["AlfeladatID", "ParID", "VarialasSzama", "SzuksegesIdo", "ISProbalkozas"]),

            ("BeirasosFeladat",
             '''CREATE TABLE IF NOT EXISTS BeirasosFeladat (
                NeptunKod VARCHAR(6) NOT NULL,
                AlfeladatID SERIAL PRIMARY KEY,
                MegadottKezdobetu INTEGER NOT NULL,
                HasznaltSzokeszlet INTEGER NOT NULL,
                Datum DATE NOT NULL
            )''',
             ["NeptunKod", "AlfeladatID", "MegadottKezdobetu", "HasznaltSzokeszlet", "Datum"]),

            ("KivalasztasosFeladat",
             '''CREATE TABLE IF NOT EXISTS KivalasztasosFeladat (
                NeptunKod VARCHAR(6) NOT NULL,
                AlfeladatID SERIAL PRIMARY KEY,
                HasznaltSzokeszlet INTEGER NOT NULL,
                FelkinaltLehetosegekSzama INTEGER NOT NULL,
                Nehezseg INTEGER NOT NULL,
                Datum DATE NOT NULL
            )''',
             ["NeptunKod", "AlfeladatID", "HasznaltSzokeszlet", "FelkinaltLehetosegekSzama", "Nehezseg", "Datum"]),

            ("ParositasosFeladat",
             '''CREATE TABLE IF NOT EXISTS ParositasosFeladat (
                NeptunKod VARCHAR(6) NOT NULL,
                AlfeladatID SERIAL PRIMARY KEY,
                HasznaltSzokeszlet INTEGER NOT NULL,
                Nehezseg INTEGER NOT NULL,
                Datum DATE NOT NULL
            )''',
             ["NeptunKod", "AlfeladatID", "HasznaltSzokeszlet", "Nehezseg", "Datum"]),

            ("EgyediSzaktudas",
             '''CREATE TABLE IF NOT EXISTS EgyediSzaktudas (
                NeptunKod VARCHAR(6) PRIMARY KEY,
                Gepeszet INTEGER NOT NULL DEFAULT 0,
                Urkutatas INTEGER NOT NULL DEFAULT 0,
                Kvantumszamitas INTEGER NOT NULL DEFAULT 0,
                Biotechnologia INTEGER NOT NULL DEFAULT 0,
                Geologia INTEGER NOT NULL DEFAULT 0,
                Nanotechnologia INTEGER NOT NULL DEFAULT 0,
                GazdasagiElemzes INTEGER NOT NULL DEFAULT 0,
                Kriminologia INTEGER NOT NULL DEFAULT 0,
                Genetika INTEGER NOT NULL DEFAULT 0,
                Meteorologia INTEGER NOT NULL DEFAULT 0,
                Adatbanyaszat INTEGER NOT NULL DEFAULT 0
            )''',
             ["NeptunKod", "Gepeszet", "Urkutatas", "Kvantumszamitas", "Biotechnologia", "Geologia", "Nanotechnologia", "GazdasagiElemzes", "Kriminologia", "Genetika", "Meteorologia", "Adatbanyaszat"]),

            ("Pontok",
             '''CREATE TABLE IF NOT EXISTS Pontok (
                NeptunKod VARCHAR(6) NOT NULL,
                SzoID INTEGER NOT NULL,
                Pontszam INTEGER NOT NULL,
                PRIMARY KEY (NeptunKod, SzoID),
                FOREIGN KEY (SzoID) REFERENCES Szavak(ID) ON DELETE CASCADE
            )''',
             ["NeptunKod", "SzoID", "Pontszam"]),

            ("regisztracios_kod",
             '''CREATE TABLE IF NOT EXISTS regisztracios_kod (
                regID SERIAL PRIMARY KEY,
                kulcs TEXT NOT NULL,
                hasznalhatosag INTEGER NOT NULL,
                leiras VARCHAR(100) NOT NULL
            )''',
             ["regID", "kulcs", "hasznalhatosag", "leiras"]),

            ("Diakok",
             '''CREATE TABLE IF NOT EXISTS Diakok (
                NeptunKod VARCHAR(6) PRIMARY KEY,
                Email VARCHAR(100) UNIQUE NOT NULL,
                JelszoHash VARCHAR(255) NOT NULL,
                TanultSzak INTEGER NOT NULL,
                AngolSzokeszletSzint VARCHAR(2) NOT NULL,
                Eletkor INTEGER NOT NULL,
                regID INTEGER NOT NULL,
                regDatum DATE NOT NULL,
                Velemeny TEXT,
                FOREIGN KEY (TanultSzak) REFERENCES ValaszthatoSzakok(SzakID),
                FOREIGN KEY (regID) REFERENCES regisztracios_kod(regID)
            )''',
             ["NeptunKod", "Email", "JelszoHash", "TanultSzak", "AngolSzokeszletSzint", "Eletkor", "regID", "regDatum", "Velemeny"]),
        ]

        for name, create_sql, cols in tables:
            # létrehozzuk a táblát ha nem létezik
            self.execute(create_sql)
            # ha már létezett régibb verzió (SQLite-ról jött) és hiányoznak oszlopok, próbáljuk pótolni
            # (feltételezi, hogy új oszlopok nem primáris kulcsok)
            for col in cols:
                # itt nem bontjuk szét a típusokat automatikusan, csak szükség esetén pótolhatunk alapértelmezett NULL oszlopokkal
                # ha nem létezik az oszlop, add hozzá TEXT-ként (biztonsági fallback)
                if not self.column_exists(name, col):
                    try:
                        self.execute(f'ALTER TABLE {name} ADD COLUMN {col} TEXT')
                    except Exception as e:
                        # ha nem sikerül, folytatjuk - a részletes migrációt külön szkripttel érdemes elvégezni
                        print(f"Hiba oszlop hozzáadásakor {name}.{col}: {e}")

    # ===== VALASZTHATO SZAKOK =====
    def add_valaszthato_szak(self, szak_id, szak_nev):
        return self.execute(
            "INSERT INTO ValaszthatoSzakok (SzakID, SzakNev) VALUES (%s, %s)",
            (szak_id, szak_nev)
        )

    def get_valaszthato_szak(self, szak_id):
        return self.fetch_one(
            "SELECT * FROM ValaszthatoSzakok WHERE SzakID = %s",
            (szak_id,)
        )

    def get_all_valaszthato_szakok(self):
        return self.fetch_all("SELECT * FROM ValaszthatoSzakok")

    def delete_valaszthato_szak(self, szak_id):
        return self.execute(
            "DELETE FROM ValaszthatoSzakok WHERE SzakID = %s",
            (szak_id,)
        )

    def clear_valaszthato_szakok(self):
        return self.execute("DELETE FROM ValaszthatoSzakok")

    # ===== SZOKESZLETek =====
    def add_szokeszlet(self, szokeszlet_id, nev, tulajdonos=None):
        return self.execute(
            "INSERT INTO Szokeszletek (SzokeszletID, Nev, Tulajdonos) VALUES (%s, %s, %s)",
            (szokeszlet_id, nev, tulajdonos)
        )

    def get_szokeszlet(self, szokeszlet_id):
        return self.fetch_one(
            "SELECT * FROM Szokeszletek WHERE SzokeszletID = %s",
            (szokeszlet_id,)
        )

    def get_all_szokeszletek(self):
        return self.fetch_all("SELECT * FROM Szokeszletek")

    def delete_szokeszlet(self, szokeszlet_id):
        a = self.execute(
            "DELETE FROM Szokeszletek WHERE SzokeszletID = %s",
            (szokeszlet_id,)
        )
        b = self.execute(
            "DELETE FROM Szavak WHERE SzokeszletID = %s",
            (szokeszlet_id,)
        )
        return a and b

    def clear_szokeszletek(self):
        return self.execute("DELETE FROM Szokeszletek")

    # ===== SZAVAK =====
    def add_szo(self, szokeszlet_id, idegen_szo, jelentes1, jelentes2=None, jelentes3=None, jelentes4=None, jelentes5=None, fonetika=None, leiras=None, szoveg_kontextus=None):
        return self.execute(
            "INSERT INTO Szavak (SzokeszletID, IdegenSzo, Jelentes1, Jelentes2, Jelentes3, Jelentes4, Jelentes5, Fonetika, Leiras, Szoveg_Kontextus) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                szokeszlet_id,
                idegen_szo,
                jelentes1,
                nonefix(jelentes2),
                nonefix(jelentes3),
                nonefix(jelentes4),
                nonefix(jelentes5),
                nonefix(fonetika),
                nonefix(leiras),
                nonefix(szoveg_kontextus)
            )
        )

    def get_szo(self, szo_id):
        return self.fetch_one(
            "SELECT * FROM Szavak WHERE ID = %s",
            (szo_id,)
        )

    def get_szavak_by_szokeszlet(self, szokeszlet_id):
        return self.fetch_all(
            "SELECT * FROM Szavak WHERE SzokeszletID = %s",
            (szokeszlet_id,)
        )

    def get_all_szavak(self):
        return self.fetch_all("SELECT * FROM Szavak")

    def delete_szo(self, szo_id):
        return self.execute(
            "DELETE FROM Szavak WHERE ID = %s",
            (szo_id,)
        )

    def clear_szavak(self):
        return self.execute("DELETE FROM Szavak")

    def update_szo(self, szo_id, idegen_szo, jelentes1, jelentes2=None, jelentes3=None, jelentes4=None, jelentes5=None, fonetika=None, leiras=None, szoveg_kontextus=None):
        return self.execute(
            """
            UPDATE Szavak
            SET IdegenSzo = %s, Jelentes1 = %s, Jelentes2 = %s, Jelentes3 = %s, Jelentes4 = %s, Jelentes5 = %s, Fonetika = %s, Leiras = %s, Szoveg_Kontextus = %s
            WHERE ID = %s
            """,
            (
                idegen_szo,
                jelentes1,
                nonefix(jelentes2),
                nonefix(jelentes3),
                nonefix(jelentes4),
                nonefix(jelentes5),
                nonefix(fonetika),
                nonefix(leiras),
                nonefix(szoveg_kontextus),
                szo_id
            )
        )

    # ===== EGYEDI SZAKTUDAS =====
    def add_egyedi_szaktudas(self, neptun_kod, gepeszet, urkutatas, kvantumszamitas, biotechnologia, geologia, nanotechnologia, gazdasagi_elemzes, kriminologia, genetika, meteorologia, adatbanyaszat):
        return self.execute(
            "INSERT INTO EgyediSzaktudas (NeptunKod, Gepeszet, Urkutatas, Kvantumszamitas, Biotechnologia, Geologia, Nanotechnologia, GazdasagiElemzes, Kriminologia, Genetika, Meteorologia, Adatbanyaszat) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (neptun_kod, gepeszet, urkutatas, kvantumszamitas, biotechnologia, geologia, nanotechnologia, gazdasagi_elemzes, kriminologia, genetika, meteorologia, adatbanyaszat)
        )

    def get_egyedi_szaktudas(self, neptun_kod):
        return self.fetch_one(
            "SELECT * FROM EgyediSzaktudas WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def get_all_egyedi_szaktudas(self):
        return self.fetch_all("SELECT * FROM EgyediSzaktudas")

    def delete_egyedi_szaktudas(self, neptun_kod):
        return self.execute(
            "DELETE FROM EgyediSzaktudas WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def clear_egyedi_szaktudas(self):
        return self.execute("DELETE FROM EgyediSzaktudas")

    def migrate_egyedi_szaktudas_table(self):
        """Migrálja az EgyediSzaktudas táblát: hozzáadja a hiányzó oszlopokat DEFAULT 0 értékkel."""
        try:
            existing_columns_q = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'egyediszaktudas' OR table_name = 'egyediszaktudas' OR table_name = 'EgyediSzaktudas'
            """
            cols = [r[0] for r in self.fetch_all(existing_columns_q)]
            desired = [
                ("Kvantumszamitas", "INTEGER DEFAULT 0"),
                ("Biotechnologia", "INTEGER DEFAULT 0"),
                ("Geologia", "INTEGER DEFAULT 0"),
                ("Nanotechnologia", "INTEGER DEFAULT 0"),
                ("GazdasagiElemzes", "INTEGER DEFAULT 0"),
                ("Kriminologia", "INTEGER DEFAULT 0"),
                ("Genetika", "INTEGER DEFAULT 0"),
                ("Meteorologia", "INTEGER DEFAULT 0"),
                ("Adatbanyaszat", "INTEGER DEFAULT 0")
            ]
            for col_name, col_def in desired:
                if not self.column_exists('EgyediSzaktudas', col_name):
                    self.execute(f"ALTER TABLE EgyediSzaktudas ADD COLUMN {col_name} {col_def}")
            return True
        except Exception as e:
            print(f"Hiba az EgyediSzaktudas tábla migrálásakor: {e}")
            return False

    # ===== PONTOK =====
    def add_pont(self, neptun_kod, szo_id, pontszam):
        # Pontok PRIMARY KEY (NeptunKod, SzoID) -> ON CONFLICT DO NOTHING
        return self.execute(
            "INSERT INTO Pontok (NeptunKod, SzoID, Pontszam) VALUES (%s, %s, %s) ON CONFLICT (NeptunKod, SzoID) DO NOTHING",
            (neptun_kod, szo_id, pontszam)
        )

    def get_pont(self, neptun_kod, szo_id):
        end = self.fetch_one(
            "SELECT Pontszam FROM Pontok WHERE NeptunKod = %s AND SzoID = %s",
            (neptun_kod, szo_id)
        )
        return end[0] if end is not None else None

    def get_pontok_by_diak(self, neptun_kod):
        return self.fetch_all(
            "SELECT * FROM Pontok WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def get_all_pontok(self):
        return self.fetch_all("SELECT * FROM Pontok")

    def delete_pont(self, neptun_kod, szo_id):
        return self.execute(
            "DELETE FROM Pontok WHERE NeptunKod = %s AND SzoID = %s",
            (neptun_kod, szo_id)
        )

    def clear_pontok(self):
        return self.execute("DELETE FROM Pontok")

    def update_pont(self, neptun_kod, szo_id, uj_pontszam):
        return self.execute(
            "UPDATE Pontok SET Pontszam = %s WHERE NeptunKod = %s AND SzoID = %s",
            (uj_pontszam, neptun_kod, szo_id)
        )

    # ===== DIAKOK =====
    def add_diak(self, neptun_kod, email, jelszo_hash, tanult_szak, angol_szokeszlet_szint, eletkor, reg_id, reg_datum):
        return self.execute(
            "INSERT INTO Diakok (NeptunKod, Email, JelszoHash, TanultSzak, AngolSzokeszletSzint, Eletkor, regID, regDatum, Velemeny) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)",
            (neptun_kod, email, jelszo_hash, tanult_szak, angol_szokeszlet_szint, eletkor, reg_id, reg_datum)
        )

    def update_velemeny(self, neptun_kod, velemeny):
        return self.execute(
            "UPDATE Diakok SET Velemeny = %s WHERE NeptunKod = %s",
            (velemeny, neptun_kod)
        )

    def get_velemeny(self, neptun_kod):
        result = self.fetch_one(
            "SELECT Velemeny FROM Diakok WHERE NeptunKod = %s",
            (neptun_kod,)
        )
        return result[0] if result else None

    def get_diak(self, neptun_kod):
        return self.fetch_one(
            "SELECT * FROM Diakok WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def get_all_diakok(self):
        return self.fetch_all("SELECT * FROM Diakok")

    def delete_diak(self, neptun_kod):
        self.delete_egyedi_szaktudas(neptun_kod)
        self.clear_pontok_by_diak(neptun_kod)
        self.clear_beirasos_feladatok_by_diak(neptun_kod)
        self.clear_kivalasztasos_feladatok_by_diak(neptun_kod)
        self.clear_parositasos_feladatok_by_diak(neptun_kod)
        return self.execute(
            "DELETE FROM Diakok WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def clear_diakok(self):
        return self.execute("DELETE FROM Diakok")

    # ===== SEGÉDFÜGGVÉNYEK =====
    def clear_pontok_by_diak(self, neptun_kod):
        return self.execute(
            "DELETE FROM Pontok WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def clear_beirasos_feladatok_by_diak(self, neptun_kod):
        return self.execute(
            "DELETE FROM BeirasosFeladat WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def clear_kivalasztasos_feladatok_by_diak(self, neptun_kod):
        return self.execute(
            "DELETE FROM KivalasztasosFeladat WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def clear_parositasos_feladatok_by_diak(self, neptun_kod):
        return self.execute(
            "DELETE FROM ParositasosFeladat WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def delete_nemhasznalt_feladatok(self):
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    DELETE FROM BeirasosFeladat
                    WHERE AlfeladatID NOT IN (
                        SELECT AlfeladatID FROM AlfeladatBeirasos
                    )
                ''')
                cursor.execute('''
                    DELETE FROM KivalasztasosFeladat
                    WHERE AlfeladatID NOT IN (
                        SELECT AlfeladatID FROM AlfeladatKivalasztasos
                    )
                ''')
                cursor.execute('''
                    DELETE FROM ParositasosFeladat
                    WHERE AlfeladatID NOT IN (
                        SELECT AlfeladatID FROM AlfeladatParositasos
                    )
                ''')
            conn.commit()

    # ===== TELJES ADATBÁZIS TÖRLÉSE =====
    def clear_all_data(self):
        tables = [
            "Diakok", "Pontok", "EgyediSzaktudas", "ParositasosFeladat",
            "KivalasztasosFeladat", "BeirasosFeladat",
            "AlfeladatParositasos", "AlfeladatKivalasztasos", "AlfeladatBeirasos",
            "Parok", "Szavak", "Szokeszletek", "ValaszthatoSzakok"
        ]

        success = True
        for table in tables:
            if not self.execute(f"DELETE FROM {table}"):
                success = False
                print(f"Hiba a {table} tábla törlése során")
        return success

    def get_diak_by_email(self, email):
        return self.fetch_one(
            "SELECT * FROM Diakok WHERE Email = %s",
            (email,)
        )

    def get_diak_by_neptun(self, neptun_kod):
        return self.fetch_one(
            "SELECT * FROM Diakok WHERE NeptunKod = %s",
            (neptun_kod,)
        )

    def get_weighted_random_words(self, neptun_kod, szokeszlet_idk, n=1, fonetika_kotelezo=False, kizart_szoid_lista=None):
        from time import perf_counter
        start_time = perf_counter()
        if not szokeszlet_idk:
            return []
        # készítsünk %s helyőrző listát
        placeholders = ','.join(['%s'] * len(szokeszlet_idk))
        query = f"SELECT Szavak.ID FROM Szavak WHERE Szavak.SzokeszletID IN ({placeholders})"
        params = list(szokeszlet_idk)
        if fonetika_kotelezo:
            query += " AND Szavak.Fonetika IS NOT NULL AND Szavak.Fonetika != '' AND Szavak.Fonetika != 'None'"
        if kizart_szoid_lista:
            q2 = ','.join(['%s'] * len(kizart_szoid_lista))
            query += f" AND Szavak.ID NOT IN ({q2})"
            params += list(kizart_szoid_lista)

        szo_rows = self.fetch_all(query, tuple(params))
        szo_idk = [row[0] for row in szo_rows]
        if not szo_idk:
            return []

        # Minden szóhoz próbálunk beszúrni pontot, de csak a hiányzókhoz kerül ténylegesen
        values = [(neptun_kod, szo_id, 250) for szo_id in szo_idk]
        # használjuk executemany + ON CONFLICT DO NOTHING
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    psyq = "INSERT INTO Pontok (NeptunKod, SzoID, Pontszam) VALUES (%s, %s, %s) ON CONFLICT (NeptunKod, SzoID) DO NOTHING"
                    cursor.executemany(psyq, values)
                conn.commit()
        except Exception as e:
            print(f"Hiba pontok beszúrásakor: {e}")

        # lekérdezzük a szavakat pontszámmal
        placeholders2 = ','.join(['%s'] * len(szo_idk))
        query2 = f"""
            SELECT Szavak.*, COALESCE(Pontok.Pontszam, 0) as Pontszam
            FROM Szavak
            LEFT JOIN Pontok ON Szavak.ID = Pontok.SzoID AND Pontok.NeptunKod = %s
            WHERE Szavak.ID IN ({placeholders2})
            ORDER BY Pontszam DESC
        """
        params2 = [neptun_kod] + szo_idk
        szavak = self.fetch_all(query2, tuple(params2))
        if not szavak:
            return []
        # weights: pontszám az utolsó oszlop (Pontszam)
        weights = [row[-1] for row in szavak]
        if all(w == 0 for w in weights):
            return []
        results = []
        szavak_copy = szavak[:]
        weights_copy = weights[:]
        n = min(n, len(szavak_copy))
        for _ in range(n):
            chosen = random.choices(szavak_copy, weights=weights_copy, k=1)[0]
            idx = szavak_copy.index(chosen)
            results.append(chosen)
            szavak_copy.pop(idx)
            weights_copy.pop(idx)
        end_time = perf_counter()
        print(f"Feladatgenerálás_idő: {end_time-start_time:.7f} sec")
        return results

    def van_e_legalabb_10_fonetikas_szo(self, szokeszlet_id):
        result = self.fetch_one(
            "SELECT COUNT(*) FROM Szavak WHERE SzokeszletID = %s AND Fonetika IS NOT NULL AND Fonetika != '' AND Fonetika != 'None'",
            (szokeszlet_id,)
        )
        if result and result[0] >= 10:
            return result
        else:
            result2 = self.fetch_one(
                "SELECT COUNT(*) FROM Szavak WHERE SzokeszletID = %s AND Leiras IS NOT NULL AND Leiras != '' AND Leiras != 'None'",
                (szokeszlet_id,)
            )
            return result2 if result2 and result2[0] >= 10 else False

    def van_e_legalabb_n_szo(self, szokeszlet_id, n):
        result = self.fetch_one(
            "SELECT CASE WHEN COUNT(*) >= %s THEN 1 ELSE 0 END FROM Szavak WHERE SzokeszletID = %s",
            (n, szokeszlet_id)
        )
        return bool(result[0]) if result else False

    def add_beirasos_feladat(self, neptun_kod, hasznalt_szokeszlet, datum, par):
        tmp = par['MegadottKezdobetu']
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO BeirasosFeladat (NeptunKod, MegadottKezdobetu, HasznaltSzokeszlet, Datum)
                        VALUES (%s, %s, %s, %s)
                        RETURNING AlfeladatID
                        """,
                        (neptun_kod, tmp, hasznalt_szokeszlet, datum)
                    )
                    new_id = cursor.fetchone()[0]
                conn.commit()
            return new_id
        except Exception as e:
            print(f"Hiba beirasos feladat beszuraskor: {e}")
            return None

    def add_kivalasztasos_feladat(self, neptun_kod, hasznalt_szokeszlet, datum, par):
        felkinalt = par['felkinaltLehet']
        nehezseg = 0 if par['nehezseg'] == "konnyu" else 1
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO KivalasztasosFeladat (NeptunKod, HasznaltSzokeszlet, FelkinaltLehetosegekSzama, Nehezseg, Datum)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING AlfeladatID
                        """,
                        (neptun_kod, hasznalt_szokeszlet, felkinalt, nehezseg, datum)
                    )
                    new_id = cursor.fetchone()[0]
                conn.commit()
            return new_id
        except Exception as e:
            print(f"Hiba kivalasztasos feladat beszuraskor: {e}")
            return None

    def add_parositasos_feladat(self, neptun_kod, hasznalt_szokeszlet, datum, par):
        nehezseg = 0 if par['nehezseg'] == "konnyu" else 1
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO ParositasosFeladat (NeptunKod, HasznaltSzokeszlet, Nehezseg, Datum)
                        VALUES (%s, %s, %s, %s)
                        RETURNING AlfeladatID
                        """,
                        (neptun_kod, hasznalt_szokeszlet, nehezseg, datum)
                    )
                    new_id = cursor.fetchone()[0]
                conn.commit()
            return new_id
        except Exception as e:
            print(f"Hiba parositasos feladat beszuraskor: {e}")
            return None

    # ===== ALFELADAT BEIRASOS =====
    def add_alfeladat_beirasos(self, alfeladat_id, szo_id, megadott_szo, begepelt_szavak, szukseges_ido, PozicioHelyesseg, Pontszam, is_probalkozas, megadott_betu_index):
        szavak = list(begepelt_szavak) + [None] * (6 - len(begepelt_szavak))
        szavak = szavak[:6]
        return self.execute(
            """
            INSERT INTO AlfeladatBeirasos (AlfeladatID, MegadottBetuIndex, SzoID, MegadottSzo, BegepeltSzo1, BegepeltSzo2, BegepeltSzo3, BegepeltSzo4, BegepeltSzo5, BegepeltSzo6, PozicioHelyesseg, SzuksegesIdo, Pontszam, ISProbalkozas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (alfeladat_id, megadott_betu_index, szo_id, megadott_szo, *szavak, PozicioHelyesseg, szukseges_ido, Pontszam, is_probalkozas)
        )

    # ===== ALFELADAT KIVALASZTASOS =====
    def add_alfeladat_kivalasztasos(self, alfeladat_id, szo_id, megadott_szo, kivalasztott_szavak, PozicioHelyesseg, Pontszam, varialas_szama, szukseges_ido, is_probalkozas):
        szavak = list(kivalasztott_szavak) + [None] * (6 - len(kivalasztott_szavak))
        return self.execute(
            """
            INSERT INTO AlfeladatKivalasztasos (AlfeladatID, SzoID, MegadottSzo, KivalasztottSzo1, KivalasztottSzo2, KivalasztottSzo3, KivalasztottSzo4, KivalasztottSzo5, KivalasztottSzo6, PozicioHelyesseg, VarialasSzama, SzuksegesIdo, Pontszam, ISProbalkozas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (alfeladat_id, szo_id, megadott_szo, *szavak, PozicioHelyesseg, varialas_szama, szukseges_ido, Pontszam, is_probalkozas)
        )

    # ===== PAROK =====
    def add_parok(self, par_id, szo_id, kivalasztott_szavak, PozicioHelyesseg, Pontszam, is_helyes_par):
        szavak = list(kivalasztott_szavak) + [None] * (3 - len(kivalasztott_szavak))
        return self.execute(
            """
            INSERT INTO Parok (ParID, SzoID, KivalasztottSzo1, KivalasztottSzo2, KivalasztottSzo3, PozicioHelyesseg, Pontszam, ISHelyesPar)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (par_id, szo_id, *szavak, PozicioHelyesseg, Pontszam, is_helyes_par)
        )

    # ===== ALFELADAT PAROSITASOS =====
    def add_alfeladat_parositasos(self, alfeladat_id, varialas_szama, szukseges_ido, is_probalkozas):
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO AlfeladatParositasos (AlfeladatID, VarialasSzama, SzuksegesIdo, ISProbalkozas)
                        VALUES (%s, %s, %s, %s)
                        RETURNING ParID
                        """,
                        (alfeladat_id, varialas_szama, szukseges_ido, is_probalkozas)
                    )
                    par_id = cursor.fetchone()[0]
                conn.commit()
            return par_id
        except Exception as e:
            print(f"Hiba AlfeladatParositasos beszúrásakor: {e}")
            return None

    def get_szavak_ponttal_by_szokeszlet_ids(self, neptun_kod, szokeszlet_ids, min_points=None, max_points=None):
        if not szokeszlet_ids:
            return []
        placeholders = ','.join(['%s'] * len(szokeszlet_ids))
        query = f'''
            SELECT Szavak.*, COALESCE(Pontok.Pontszam, 0) as Pontszam
            FROM Szavak
            LEFT JOIN Pontok ON Szavak.ID = Pontok.SzoID AND Pontok.NeptunKod = %s
            WHERE Szavak.SzokeszletID IN ({placeholders})
        '''
        params = [neptun_kod] + list(szokeszlet_ids)
        if min_points is not None:
            query += " AND (Pontok.Pontszam >= %s)"
            params.append(min_points)
        if max_points is not None:
            query += " AND (Pontok.Pontszam <= %s)"
            params.append(max_points)
        query += " ORDER BY Pontszam DESC"
        return self.fetch_all(query, tuple(params))

    def run_szokeszlet_sql_query(self, nyers_sql:str, session) -> bool:
        parts = nyers_sql.split("/")
        if parts[0] == "neptun_kod":
            params = (session['user_id'], )
        else:
            params = ()
        end = self.fetch_one(parts[1], params)
        if end == "None" or end is None:
            return False
        return bool(end[0])
