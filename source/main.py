import os
import json
import re
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from adatbazis_kezel import Database
from adatfeldolgozas import *
import uuid
import random
import pprint
import bcrypt
from adatfeldolgozas_class import Szo_class, SzoContainer, Szo_Elofordulas_Sor, Szamlalo


# PrettyPrinter példány létrehozása
pp = pprint.PrettyPrinter(width=80, compact=True, sort_dicts=False)

# ===== FLASK APP LÉTREHOZÁSA =====
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
ADMIN_PASSWORD_HASH = bcrypt.hashpw(os.environ["ADMIN_PASSWORD"].encode("utf-8"), bcrypt.gensalt())

#setup_sqlite_logging(app, os.path.join(os.path.dirname(__file__), "logs"))
print(">>> Flask index route loaded <<<")


# ===== REGISTRATION KÓD VALIDÁLÁS =====
# reg_kód:	EOmf7txuFkuxuPABYrE6hCVBd1MzTk
# Adatbázis példányosítása
db_url = os.getenv("DATABASE_URL")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

db = Database(db_url)

# Adatbázis inicializálása (táblák létrehozása)



# ===== Segédfüggvény: admin jogosultság ellenőrzése =====
def is_admin_session() -> bool:
    """Igazat ad vissza, ha az aktuális session admin: vagy admin jelszóval hitelesített,
    vagy a bejelentkezett felhasználó admin regisztrációs kódra (regID == 1) regisztrált.
    """
    try:
        if session.get('admin_authenticated'):
            return True
        if 'user_id' in session:
            diak = db.get_diak(session['user_id'])
            return bool(diak and len(diak) > 6 and diak[6] == 1)
        return False
    except Exception:
        return False

def Read_template_content(name):
    with open(f"templates/{name}", "r", encoding="UTF-8") as f:
        adatok = f.read()
    return render_template(adatok)

def generate_neptun_kod():
    """Generál egy egyedi 5 számjegyű Neptun kódot"""
    
    for _ in range(500):
        # 5 számjegyű kód generálása
        neptun_kod = f"{random.randint(10000, 99999)}"
        
        # Ellenőrizzük, hogy már létezik-e az adatbázisban
        existing_diak = db.get_diak_by_neptun(neptun_kod)
        if not existing_diak:
            return neptun_kod
    
    # Ha nem sikerült egyedi kódot generálni, hiba
    raise Exception("Nem sikerült egyedi Neptun kódot generálni.")

@app.route("/admin/clear_task_history")
def admin_clear_task_history():
    """Admin funkció a feladatelőzmények törléséhez"""
    try:
        # Csak admin jogosultsággal
        if not is_admin_session():
            if 'user_id' not in session:
                flash('Kérlek, jelentkezz be admin jelszóval!', 'error')
                return redirect(url_for("admin_login"))
            flash('Nincs jogosultságod a feladatelőzmények törléséhez!', 'error')
            return redirect(url_for("admin"))
        # Törlendő táblák
        tablák = [
            "AlfeladatBeirasos",
            "BeirasosFeladat",
            "AlfeladatKivalasztasos",
            "KivalasztasosFeladat",
            "AlfeladatParositasos",
            "Parok",
            "ParositasosFeladat"
        ]
        for tabla in tablák:
            db.execute(f"DELETE FROM {tabla}")
        flash('Feladatelőzmények sikeresen törölve!', 'success')
    except Exception as e:
        flash(f'Hiba a feladatelőzmények törlésekor: {str(e)}', 'error')
    return redirect(url_for("admin"))

@app.route("/validate_regcode", methods=["POST"])
def validate_regcode():
    data = request.get_json()
    regkod = data.get('regkod', '').strip()
    if not regkod:
        return {"valid": False, "message": "A kód megadása kötelező!"}
    kod_adat = db.fetch_one("SELECT hasznalhatosag FROM regisztracios_kod WHERE kulcs = %s", (regkod,))
    if not kod_adat:
        return {"valid": False, "message": "Érvénytelen regisztrációs kód!"}
    if kod_adat[0] < 1:
        return {"valid": False, "message": "A kód már nem használható!"}
    return {"valid": True, "message": "A kód érvényes és használható."}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "login":
            return redirect(url_for("login"))
        elif action == "register":
            return redirect(url_for("register"))
    # Bejelentkezési állapot ellenőrzése
    is_logged_in = 'user_id' in session
    user_regid = None
    if is_logged_in:
        diak = db.get_diak(session['user_id'])
        if diak and len(diak) > 6:
            user_regid = diak[6]
    return render_template("index.html", is_logged_in=is_logged_in, 
                         user_name=session.get('user_name', ''),
                         user_email=session.get('user_email', ''),
                         user_regid=user_regid)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            email = request.form.get('email', '').strip().lower()
            jelszo = request.form.get('jelszo', '')
            emlekezz_ram = request.form.get('emlekezz_ram') == '1'
            
            # Validáció
            if not email or not jelszo:
                flash('Email és jelszó megadása kötelező!', 'error')
                return render_template("login.html")
            
            # Felhasználó keresése email alapján
            diak = db.get_diak_by_email(email)
            if not diak:
                flash('Hibás email cím vagy jelszó!', 'error')
                return render_template("login.html")
            
            # Jelszó ellenőrzése
            if not check_password_hash(diak[2], jelszo):  # diak[2] = JelszoHash
                flash('Hibás email cím vagy jelszó!', 'error')
                return render_template("login.html")
            
            # Bejelentkezés sikeres - session létrehozása
            session['user_id'] = diak[0]  # NeptunKod
            session['user_email'] = diak[1]  # Email
            session['user_name'] = f"Felhasználó ({diak[0]})"  # Megjelenítendő név
            
            # Session időtartam beállítása
            if emlekezz_ram:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False
            
            flash(f'Sikeres bejelentkezés! Üdvözöljük, {session["user_name"]}!', 'success')
            return redirect(url_for("dashboard"))
            
        except Exception as e:
            flash(f'Váratlan hiba történt: {str(e)}', 'error')
    
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    """Dashboard oldal bejelentkezett felhasználók számára"""
    # Session ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    
    diak = db.get_diak(session['user_id'])
    user_regid = diak[6] if diak and len(diak) > 6 else None
    
    # Regisztrációs dátum formázása
    user_reg_date = "N/A"
    if diak and len(diak) > 7 and diak[7]:
        try:
            # SQLite DATE formátumból magyar formátumra konvertálás
            reg_date = datetime.strptime(diak[7], '%Y-%m-%d')
            user_reg_date = reg_date.strftime('%Y.%m.%d')
        except:
            user_reg_date = diak[7]  # Ha nem sikerül konvertálni, eredeti formátum
    
    # Jogosultsági szint meghatározása
    user_role = "Felhasználó"
    if user_regid and user_regid == 1:
        user_role = "Admin"
    
    return render_template("dashboard.html", 
                         user_id=session['user_id'],
                         user_email=session['user_email'],
                         user_name=session['user_name'],
                         user_regid=user_regid,
                         user_reg_date=user_reg_date,
                         user_role=user_role)

@app.route("/logout")
def logout():
    """Kijelentkezés"""
    # Session törlése
    session.clear()
    flash('Sikeresen kijelentkezett!', 'success')
    return redirect(url_for("index"))

@app.before_request
def clear_vocabulary_session():
    # Ha NEM a /vocabulary végpontot hívja, töröljük a mentett szekeztős szókészletet
    if request.endpoint != "vocabulary":
        session.pop("temp_data", None)

@app.route("/vocabulary", methods=["GET", "POST"])
def vocabulary():
    """
    Szókészlet létrehozás és szerkesztés oldal
    - GET: oldal betöltése, saját szókészletek listázása
    - POST: különböző műveletek (új szókészlet, szerkesztés, törlés)
    """
    sajat_szokeszletekbol_kizart = json.loads(os.getenv("sajat_szokeszletekbol_kizart", "[]"))
    # 1. Bejelentkezés ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))

    # 2. Felhasználói adatok lekérése
    user_id = session['user_id']
    user_email = session['user_email']
    user_name = session['user_name']
    diak = db.get_diak(user_id)
    is_admin = bool(diak and len(diak) > 6 and diak[6] == 1)

    # 3. Szókészletek csoportosítása
    osszes = db.get_all_szokeszletek()
    sajat_szokeszletek = [sz for sz in osszes if sz[2] == user_id]
    public_szokeszletek = [sz for sz in osszes if not sz[2]]
    megosztott_szokeszletek = [sz for sz in osszes if isinstance(sz[2], str) and (',' in sz[2] or sz[2].startswith('/'))]

    if is_admin:
        osszes_szerkesztheto_szokeszlet = sajat_szokeszletek + public_szokeszletek + megosztott_szokeszletek
    else:
        osszes_szerkesztheto_szokeszlet = sajat_szokeszletek

    szokeszlet_szavak = {}
    for szokeszlet in osszes_szerkesztheto_szokeszlet:
        szokeszlet_id = szokeszlet[0]
        szavak = db.get_szavak_by_szokeszlet(szokeszlet_id)
        szokeszlet_szavak[szokeszlet_id] = szavak

    # 4. POST kérések kezelése (űrlapok feldolgozása)
    if request.method == "POST":
        action = request.form.get('action')
        # 4.1. Új szókészlet létrehozó űrlap megjelenítése
        if action == 'create':
            # Csak az új szókészlet űrlapot jelenítjük meg
            return render_template("vocabulary.html",
                                 user_id=user_id,
                                 user_email=user_email,
                                 user_name=user_name,
                                 is_admin=is_admin,
                                 sajat_szokeszletek=sajat_szokeszletek,
                                 public_szokeszletek=public_szokeszletek,
                                 megosztott_szokeszletek=megosztott_szokeszletek,
                                 osszes_szerkesztheto_szokeszlet=osszes_szerkesztheto_szokeszlet,
                                 szokeszlet_szavak=szokeszlet_szavak)
        # 4.2. Meglévő szókészlet szerkesztő űrlapjának megjelenítése
        elif action == 'edit':
            szokeszlet_id_str = request.form.get('szokeszlet_id')
            save = request.form.get('save')
            # 4.2.1. Szerkesztő űrlap megjelenítése (még nincs mentés)
            if szokeszlet_id_str and not save:
                szerkesztendo_id = int(szokeszlet_id_str)
                # Jogosultság ellenőrzése: admin vagy saját tulajdon
                target = db.get_szokeszlet(szerkesztendo_id)
                if not target:
                    flash('A kért szókészlet nem található!', 'error')
                    return redirect(url_for('vocabulary'))
                tulaj = target[2]
                if not is_admin and tulaj != user_id:
                    flash('Nincs jogosultságod ennek a szókészletnek a szerkesztéséhez!', 'error')
                    return redirect(url_for('vocabulary'))
                return render_template("vocabulary.html",
                                     user_id=user_id,
                                     user_email=user_email,
                                     user_name=user_name,
                                     is_admin=is_admin,
                                     sajat_szokeszletek=sajat_szokeszletek,
                                     public_szokeszletek=public_szokeszletek,
                                     megosztott_szokeszletek=megosztott_szokeszletek,
                                     osszes_szerkesztheto_szokeszlet=osszes_szerkesztheto_szokeszlet,
                                     szokeszlet_szavak=szokeszlet_szavak,
                                     szerkesztendo_id=szerkesztendo_id,
                                     edit_mode=True)
            # 4.2.2. Meglévő szókészlet mentése (név és szavak frissítése)
            elif szokeszlet_id_str and save:
                if diak[6] in sajat_szokeszletekbol_kizart:
                    flash('A regisztrált felhasználói csoportodnak nincs joga saját szókészlethez.', 'error')
                    return redirect(url_for('vocabulary'))
                szokeszlet_id = int(szokeszlet_id_str)
                uj_nev = request.form.get('szokeszlet_nev', '').strip()
                if not uj_nev:
                    flash('A szókészlet neve kötelező!', 'error')
                else:
                    # Jogosultság ellenőrzése: admin vagy saját tulajdon
                    target = db.get_szokeszlet(szokeszlet_id)
                    if not target:
                        flash('A kért szókészlet nem található!', 'error')
                        return redirect(url_for('vocabulary'))
                    tulaj = target[2]
                    if not is_admin and tulaj != user_id:
                        flash('Nincs jogosultságod ennek a szókészletnek a mentéséhez!', 'error')
                        return redirect(url_for('vocabulary'))
                    # Szókészlet nevének frissítése
                    db.execute("UPDATE Szokeszletek SET Nev = %s WHERE SzokeszletID = %s", (uj_nev, szokeszlet_id))
                    szo_index = 0
                    eredeti_idk = [i[0] for i in szokeszlet_szavak[szokeszlet_id]]
                    index_max = int(request.form.get("index"))+10
                    while True:
                        if szo_index > index_max: break
                        prefix = f'szo_{szo_index}_'
                        ID = request.form.get(prefix+"ID", None)
                        idegen_szo = request.form.get(prefix + 'idegen_szo', None)
                        if idegen_szo is None: szo_index += 1; continue
                        jelentes1 = request.form.get(prefix + 'jelentes1')
                        jelentes2 = request.form.get(prefix + 'jelentes2')
                        jelentes3 = request.form.get(prefix + 'jelentes3')
                        jelentes4 = request.form.get(prefix + 'jelentes4')
                        jelentes5 = request.form.get(prefix + 'jelentes5')
                        fonetika = request.form.get(prefix + 'fonetika')
                        leiras = request.form.get(prefix + 'leiras')
                        szoveg_kontextus = request.form.get(prefix + 'szoveg_kontextus')
                        uj_szo = (szokeszlet_id, idegen_szo, jelentes1, jelentes2, jelentes3, jelentes4, jelentes5, fonetika, leiras, szoveg_kontextus)
                        if ID is None: # új szó került hozzáadásra
                            db.add_szo(*uj_szo)
                        elif (ID := int(ID)) in eredeti_idk: # régi szó ami vagy szerkeztődött vagy eredeti maradt
                            eredeti_szo = szokeszlet_szavak[szokeszlet_id][szo_index]
                            eredeti_idk.remove(ID)
                            if eredeti_szo[2] != idegen_szo or eredeti_szo[3] != jelentes1 or eredeti_szo[4] != jelentes2 or eredeti_szo[5] != jelentes3 or eredeti_szo[6] != jelentes4 or eredeti_szo[7] != jelentes5 or eredeti_szo[8] != fonetika:
                                # a szó változott -> pont módosul
                                db.update_szo(ID, *uj_szo[1:])

                                pont = db.get_pont(user_id, ID)
                                if pont < 250: db.update_pont(user_id, ID, 250)
                                elif pont > 250: db.update_pont(user_id, ID, pont+100)
                            elif eredeti_szo[9] != leiras or eredeti_szo[10] != szoveg_kontextus: #a szónak csak a leírása változott -> pont marad
                                db.update_szo(ID, *uj_szo[1:])
                            # else: a szó nem változott
                        # else: ilyen legálisan nem lehet szóval eldobjuk az adatokat
                        szo_index += 1
                    # ha maradt bármi a eredeti_idk listában akkor azokat töröljük mindenhonnan
                    if eredeti_idk:
                        for ID in eredeti_idk:
                            db.delete_szo(ID)
                    flash('Szókészlet sikeresen frissítve!', 'success')
                    return redirect(url_for('vocabulary'))
            # 4.2.3. Új szókészlet mentése (név + szavak)
            elif not szokeszlet_id_str:
                if diak[6] in sajat_szokeszletekbol_kizart:
                    flash('A regisztrált felhasználói csoportodnak nincs joga saját szókészlethez.', 'error')
                    return redirect(url_for('vocabulary'))
                nev = request.form.get('szokeszlet_nev', '').strip()
                if not nev:
                    flash('A szókészlet neve kötelező!', 'error')
                    return render_template("vocabulary.html",
                                         user_id=user_id,
                                         user_email=user_email,
                                         user_name=user_name,
                                         is_admin=is_admin,
                                         sajat_szokeszletek=sajat_szokeszletek,
                                         public_szokeszletek=public_szokeszletek,
                                         megosztott_szokeszletek=megosztott_szokeszletek,
                                         osszes_szerkesztheto_szokeszlet=osszes_szerkesztheto_szokeszlet,
                                         szokeszlet_szavak=szokeszlet_szavak)
                
                # JSON fájl feltöltés kezelése
                json_file = request.files.get('json_file')
                if json_file and json_file.filename:
                    try:
                        json_data = json.loads(json_file.read().decode('utf-8'))
                        
                        # JSON adatok validálása
                        if 'szokeszlet_nev' in json_data and 'szavak' in json_data and isinstance(json_data['szavak'], list):
                            # Ha van JSON név, felülírjuk a form névét
                            if json_data['szokeszlet_nev']:
                                nev = json_data['szokeszlet_nev']
                            
                            # Új szókészlet ID generálása
                            max_id = max([sz[0] for sz in db.get_all_szokeszletek()] or [0])
                            new_id = max_id + 1
                            db.add_szokeszlet(new_id, nev, user_id)
                            
                            # Szavak hozzáadása a JSON-ból
                            for szo_data in json_data['szavak']:
                                if 'idegen_szo' in szo_data and 'jelentes1' in szo_data:
                                    idegen_szo = szo_data.get('idegen_szo', '')
                                    jelentes1 = szo_data.get('jelentes1', '')
                                    jelentes2 = szo_data.get('jelentes2', '')
                                    jelentes3 = szo_data.get('jelentes3', '')
                                    jelentes4 = szo_data.get('jelentes4', '')
                                    jelentes5 = szo_data.get('jelentes5', '')
                                    fonetika = szo_data.get('fonetika', '')
                                    leiras = szo_data.get('leiras', '')
                                    szoveg_kontextus = szo_data.get('szoveg_kontextus', '')
                                    
                                    if idegen_szo and jelentes1:
                                        db.add_szo(new_id, idegen_szo, jelentes1, jelentes2, jelentes3, jelentes4, jelentes5, fonetika, leiras, szoveg_kontextus)
                            
                            flash(f'Új szókészlet sikeresen létrehozva JSON fájlból! ({len(json_data["szavak"])} szó)', 'success')
                            return redirect(url_for('vocabulary'))
                        else:
                            flash('Érvénytelen JSON formátum!', 'error')
                    except json.JSONDecodeError:
                        flash('Hibás JSON fájl!', 'error')
                    except Exception as e:
                        flash(f'Hiba a JSON fájl feldolgozásakor: {str(e)}', 'error')
                
                # Ha nincs JSON fájl vagy hiba történt, normál form feldolgozás
                # Új szókészlet ID generálása
                max_id = max([sz[0] for sz in db.get_all_szokeszletek()] or [0])
                new_id = max_id + 1
                db.add_szokeszlet(new_id, nev, user_id)
                # Szavak hozzáadása az új szókészlethez
                szo_index = 0
                while True:
                    prefix = f'szo_{szo_index}_'
                    idegen_szo = request.form.get(prefix + 'idegen_szo')
                    jelentes1 = request.form.get(prefix + 'jelentes1')
                    if not idegen_szo or not jelentes1:
                        break
                    jelentes2 = request.form.get(prefix + 'jelentes2')
                    jelentes3 = request.form.get(prefix + 'jelentes3')
                    jelentes4 = request.form.get(prefix + 'jelentes4')
                    jelentes5 = request.form.get(prefix + 'jelentes5')
                    fonetika = request.form.get(prefix + 'fonetika')
                    leiras = request.form.get(prefix + 'leiras')
                    szoveg_kontextus = request.form.get(prefix + 'szoveg_kontextus')
                    db.add_szo(new_id, idegen_szo, jelentes1, jelentes2, jelentes3, jelentes4, jelentes5, fonetika, leiras, szoveg_kontextus)
                    szo_index += 1
                flash('Új szókészlet sikeresen létrehozva!', 'success')
                return redirect(url_for('vocabulary'))
        # 4.3. Szókészlet törlése
        elif action == 'delete':
            szokeszlet_id_str = request.form.get('szokeszlet_id')
            if szokeszlet_id_str:
                szokeszlet_id = int(szokeszlet_id_str)
                target = db.get_szokeszlet(szokeszlet_id)
                if not target:
                    flash('A kért szókészlet nem található!', 'error')
                    return redirect(url_for('vocabulary'))
                tulaj = target[2]
                if not is_admin and tulaj != user_id:
                    flash('Nincs jogosultságod ennek a szókészletnek a törléséhez!', 'error')
                    return redirect(url_for('vocabulary'))
                db.delete_szokeszlet(szokeszlet_id)  # Szókészlet és szavak törlése (ON DELETE CASCADE)
                flash('Szókészlet és a hozzá tartozó szavak törölve!', 'success')
            return redirect(url_for('vocabulary'))

    # 5. Oldal megjelenítése (GET vagy POST utáni visszatérés)
    return render_template("vocabulary.html",
                         user_id=user_id,
                         user_email=user_email,
                         user_name=user_name,
                         is_admin=is_admin,
                         sajat_szokeszletek=sajat_szokeszletek,
                         public_szokeszletek=public_szokeszletek,
                         megosztott_szokeszletek=megosztott_szokeszletek,
                         osszes_szerkesztheto_szokeszlet=osszes_szerkesztheto_szokeszlet,
                         szokeszlet_szavak=szokeszlet_szavak)

@app.route("/vocabulary/export/<int:szokeszlet_id>")
def vocabulary_export(szokeszlet_id):
    """Szókészlet exportálása JSON formátumban"""
    # Bejelentkezés ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    diak = db.get_diak(user_id)
    is_admin = bool(diak and len(diak) > 6 and diak[6] == 1)
    
    # Szókészlet lekérése és tulajdonjog ellenőrzése
    szokeszlet = db.get_szokeszlet(szokeszlet_id)
    if not szokeszlet or szokeszlet[2] != user_id:
        if not is_admin:
            flash('Nincs jogosultsága ehhez a szókészlethez!', 'error')
            return redirect(url_for('vocabulary'))
    
    # Szavak lekérése
    szavak = db.get_szavak_by_szokeszlet(szokeszlet_id)
    
    # JSON adatstruktúra létrehozása
    export_data = {
        "szokeszlet_nev": szokeszlet[1],
        "szavak": []
    }
    
    for szo in szavak:
        export_data["szavak"].append({
            "idegen_szo": szo[2],
            "jelentes1": szo[3],
            "jelentes2": szo[4],
            "jelentes3": szo[5],
            "jelentes4": szo[6],
            "jelentes5": szo[7],
            "fonetika": szo[8],
            "leiras": szo[9],
            "szoveg_kontextus": szo[10]
        })
    
    # JSON válasz visszaadása letöltésként
    from flask import Response
    
    response = Response(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{szokeszlet[1]}.json"'}
    )
    return response

@app.route("/learning")
def learning():
    """Idegenszavak tanulása oldal"""
    # Session ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    user_id = session['user_id']
    user_email = session['user_email']
    user_name = session['user_name']
    # Saját és publikus szókészletek
    szokeszletek = [sz for sz in db.get_all_szokeszletek() if sz[2] == user_id or sz[2] is None or user_id in sz[2].split(',') or (db.run_szokeszlet_sql_query(sz[2][1:], session) if sz[2].startswith("/") else False)]
    return render_template("learning.html",
                         user_id=user_id,
                         user_email=user_email,
                         user_name=user_name,
                         szokeszletek=szokeszletek)

@app.route("/tasks")
def tasks():
    """Feladat megoldás oldal"""
    # Session ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    user_id = session['user_id']
    user_email = session['user_email']
    user_name = session['user_name']
    # Saját és publikus szókészletek
    szokeszletek = [sz for sz in db.get_all_szokeszletek() if sz[2] == user_id or sz[2] is None or user_id in sz[2].split(',') or (db.run_szokeszlet_sql_query(sz[2][1:], session) if sz[2].startswith("/") else False)]
    return render_template("tasks.html", 
                         user_id=user_id,
                         user_email=user_email,
                         user_name=user_name,
                         szokeszletek=szokeszletek)

@app.route("/statistics")
def statistics():
    """Statisztikák megtekintése oldal"""
    # Session ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    
    db.delete_nemhasznalt_feladatok()
    
    return render_template("statistics.html", 
                         user_id=session['user_id'],
                         user_email=session['user_email'],
                         user_name=session['user_name'])

@app.route("/velemeny", methods=["GET", "POST"])
def velemeny():
    """Vélemény/feedback oldal"""
    # Session ellenőrzése
    if 'user_id' not in session:
        flash('Kérjük, jelentkezzen be!', 'error')
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    user_email = session['user_email']
    user_name = session['user_name']
    
    if request.method == "POST":
        action = request.form.get('action')
        if action == 'save_velemeny':
            velemeny_text = request.form.get('velemeny', '').strip()
            
            # Validáció: maximum 20,000 karakter
            if len(velemeny_text) > 20000:
                flash('A vélemény maximum 20,000 karakter hosszú lehet!', 'error')
            else:
                # Vélemény mentése az adatbázisba
                if db.update_velemeny(user_id, velemeny_text):
                    flash('Vélemény sikeresen mentve!', 'success')
                else:
                    flash('Hiba történt a vélemény mentésekor!', 'error')
    
    # Jelenlegi vélemény lekérése
    current_velemeny = db.get_velemeny(user_id) or ""
    
    return render_template("velemeny.html",
                         user_id=user_id,
                         user_email=user_email,
                         user_name=user_name,
                         current_velemeny=current_velemeny)

@app.route("/api/statistics/sections")
def api_statistics_sections():
    """Visszaadja, hogy az aktuális felhasználó mely statisztikai szekciókat láthat."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    # Itt lehetne jogosultság, csoport, stb. alapján szűrni
    # Egyelőre mindenki ugyanazt látja
    sections = [
        {
            "id": "top_words",
            "title": "Legjobban ismert szavak",
            "description": "A legjobban ismert szavak listája."
        },
        {
            "id": "activity",
            "title": "<br>Aktivitási statisztikák",
            "description": ""
        },
        {
            "id": "progress",
            "title": "<br>Eredmények időbeli alakulása",
            "description": ""
        },
        {
            "id": "error_analysis",
            "title": "<br>Hibaelemzés",
            "description": ""
        },
        {
            "id": "confidence_analysis",
            "title": "<br>Önbizalmi elemzés",
            "description": ""
        },
        {
            "id": "ai_prediction",
            "title": "<br>🤖 AI Predikció",
            "description": "Jövőbeli pontszám trendek és javaslatok"
        }
    ]
    return jsonify({"sections": sections})

@app.route("/api/statistics/top-words")
def api_statistics_top_words():
    """Visszaadja a felhasználó top 5 legtöbb és legkevesebb pontú szavát."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    # Lekérjük az összes pontot és szóadatot
    pontok = db.fetch_all("""
        SELECT Szavak.ID, Szavak.IdegenSzo, Szavak.Jelentes1, Szavak.Jelentes2, Szavak.Jelentes3, Szavak.Jelentes4, Szavak.Jelentes5, Pontok.Pontszam
        FROM Pontok
        JOIN Szavak ON Pontok.SzoID = Szavak.ID
        WHERE Pontok.NeptunKod = %s
    """, (neptun_kod,))
    if not pontok:
        return jsonify({"top_best": [], "top_worst": []})
    # Top 5 legtöbb pontú szó
    top_best = sorted(pontok, key=lambda x: x[-1], reverse=True)[:5]
    # Top 5 legkevesebb pontú szó
    top_worst = sorted(pontok, key=lambda x: x[-1])[:5]
    def szo_dict(szo):
        return {
            "id": szo[0],
            "idegen_szo": szo[1],
            "jelentesek": [j for j in szo[2:7] if j],
            "pontszam": szo[7]
        }
    return jsonify({
        "top_best": [szo_dict(szo) for szo in top_best],
        "top_worst": [szo_dict(szo) for szo in top_worst]
    })

@app.route("/api/statistics/progress")
def api_statistics_progress():
    """Visszaadja az átlagos pontszámot és helyes mezők arányát napi/heti/havi csúszó ablakos bontásban."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    interval = request.args.get('interval', 'weekly')  # daily, weekly, monthly
    now = datetime.now().date()
    if interval == 'daily':
        num = 30
        delta = timedelta(days=1)
        label_fmt = '%Y-%m-%d'
        def get_label(d): return d.strftime(label_fmt)
    elif interval == 'monthly':
        num = 12
        delta = None  # handled below
        label_fmt = '%Y-%m'
        def get_label(d): return d.strftime(label_fmt)
    else:  # weekly (default)
        num = 12
        delta = timedelta(weeks=1)
        label_fmt = '%Y-W%W'
        def get_label(d): return f"{d.year}-W{d.isocalendar()[1]:02d}"

    # Lekérjük az összes alfeladat rekordot (összes típusból)
    # Beirasos
    beirasos = db.fetch_all(
        "SELECT ab.Pontszam, ab.PozicioHelyesseg, bf.Datum FROM AlfeladatBeirasos ab JOIN BeirasosFeladat bf ON ab.AlfeladatID = bf.AlfeladatID WHERE bf.NeptunKod = %s",
        (neptun_kod,)
    )
    # Kivalasztasos
    kivalasztasos = db.fetch_all(
        "SELECT ak.Pontszam, ak.PozicioHelyesseg, kf.Datum FROM AlfeladatKivalasztasos ak JOIN KivalasztasosFeladat kf ON ak.AlfeladatID = kf.AlfeladatID WHERE kf.NeptunKod = %s",
        (neptun_kod,)
    )
    # Parositasos (itt a Parok táblából szedjük a pontokat és helyességet)
    parositasos = db.fetch_all(
        "SELECT p.Pontszam, p.PozicioHelyesseg, pf.Datum FROM Parok p JOIN ParositasosFeladat pf ON p.ParID = pf.AlfeladatID WHERE pf.NeptunKod = %s",
        (neptun_kod,)
    )
    # Összefűzzük az összes rekordot
    all_data = list(beirasos) + list(kivalasztasos) + list(parositasos)
    # Minden rekord: (Pontszam, PozicioHelyesseg, Datum)
    # Csoportosítás időablakokra
    buckets = {}
    for i in range(num):
        if interval == 'daily':
            d = now - timedelta(days=num-1-i)
            label = get_label(d)
            buckets[label] = []
        elif interval == 'weekly':
            d = now - timedelta(weeks=num-1-i)
            label = get_label(d)
            buckets[label] = []
        else:  # monthly
            year = (now.year if now.month - (num-1-i) > 0 else now.year-1)
            month = (now.month - (num-1-i) - 1) % 12 + 1
            d = datetime(year, month, 1).date()
            label = get_label(d)
            buckets[label] = []
    # Szétosztjuk a rekordokat a megfelelő időablakba
    for pontszam, helyesseg, datum in all_data:
        if not datum:
            continue
        if interval == 'daily':
            label = get_label(datetime.strptime(str(datum)[:10], '%Y-%m-%d').date())
        elif interval == 'weekly':
            d = datetime.strptime(str(datum)[:10], '%Y-%m-%d').date()
            iso = d.isocalendar()
            label = f"{d.year}-W{iso[1]:02d}"
        else:  # monthly
            d = datetime.strptime(str(datum)[:10], '%Y-%m-%d').date()
            label = d.strftime('%Y-%m')
        if label in buckets:
            buckets[label].append((pontszam, helyesseg))
    # Átlagolás
    labels = []
    avg_points = []
    correct_percent = []
    for label in buckets:
        records = buckets[label]
        if not records:
            labels.append(label)
            avg_points.append(None)
            correct_percent.append(None)
            continue
        # Átlagos pontszám
        points = [r[0] for r in records if r[0] is not None]
        avg = sum(points)/len(points) if points else None
        # Helyes mezők aránya
        helyes = 0
        osszes = 0
        for _, helyesseg in records:
            if helyesseg:
                parts = str(helyesseg).split(':')
                helyes += sum(1 for x in parts if x == '1')
                osszes += len(parts)
        percent = (helyes/osszes*100) if osszes else None
        labels.append(label)
        avg_points.append(round(avg, 2) if avg is not None else None)
        correct_percent.append(round(percent, 2) if percent is not None else None)
    return jsonify({
        "labels": labels,
        "avg_points": avg_points,
        "correct_percent": correct_percent
    })

@app.route("/api/statistics/activity")
def api_statistics_activity():
    """Visszaadja a felhasználó napi, heti, havi aktivitását szókészletenként."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    now = datetime.now()
    today = now.date()
    week_ago = today - timedelta(days=6)
    month_ago = today - timedelta(days=29)

    # szókészlet nevek lekérése
    szokeszlet_nevek = {row[0]: row[1] for row in db.fetch_all("SELECT SzokeszletID, Nev FROM Szokeszletek")}

    def get_activities_by_type(start_date, end_date):
        activity = {}
        is_single_day = start_date == end_date
        
        # BeirasosFeladat
        if is_single_day:
            beirasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM BeirasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
                (neptun_kod, start_date)
            )
        else:
            beirasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM BeirasosFeladat WHERE NeptunKod = %s AND Datum BETWEEN %s AND %s",
                (neptun_kod, start_date, end_date)
            )
        for alfeladat_id, szokeszlet_id, datum in beirasos:
            count = db.fetch_one("SELECT COUNT(*) FROM AlfeladatBeirasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            if count > 0:
                nev = szokeszlet_nevek.get(szokeszlet_id, str(szokeszlet_id))
                if nev not in activity:
                    activity[nev] = {'beirasos': 0, 'kivalasztasos': 0, 'parositasos': 0}
                activity[nev]['beirasos'] += count
        
        # KivalasztasosFeladat
        if is_single_day:
            kivalasztasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM KivalasztasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
                (neptun_kod, start_date)
            )
        else:
            kivalasztasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM KivalasztasosFeladat WHERE NeptunKod = %s AND Datum BETWEEN %s AND %s",
                (neptun_kod, start_date, end_date)
            )
        for alfeladat_id, szokeszlet_id, datum in kivalasztasos:
            count = db.fetch_one("SELECT COUNT(*) FROM AlfeladatKivalasztasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            if count > 0:
                nev = szokeszlet_nevek.get(szokeszlet_id, str(szokeszlet_id))
                if nev not in activity:
                    activity[nev] = {'beirasos': 0, 'kivalasztasos': 0, 'parositasos': 0}
                activity[nev]['kivalasztasos'] += count
        
        # ParositasosFeladat
        if is_single_day:
            parositasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM ParositasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
                (neptun_kod, start_date)
            )
        else:
            parositasos = db.fetch_all(
                "SELECT AlfeladatID, HasznaltSzokeszlet, Datum FROM ParositasosFeladat WHERE NeptunKod = %s AND Datum BETWEEN %s AND %s",
                (neptun_kod, start_date, end_date)
            )
        for alfeladat_id, szokeszlet_id, datum in parositasos:
            count = db.fetch_one("SELECT COUNT(*) FROM AlfeladatParositasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            if count > 0:
                nev = szokeszlet_nevek.get(szokeszlet_id, str(szokeszlet_id))
                if nev not in activity:
                    activity[nev] = {'beirasos': 0, 'kivalasztasos': 0, 'parositasos': 0}
                activity[nev]['parositasos'] += count * 5  # minden alfeladat 5 pont
        
        return activity

    # Napi aktivitás (ma)
    daily = get_activities_by_type(str(today), str(today))
    # Heti aktivitás (elmúlt 7 nap)
    weekly = get_activities_by_type(str(week_ago), str(today))
    # Havi aktivitás (elmúlt 30 nap)
    monthly = get_activities_by_type(str(month_ago), str(today))

    def max_topic(activity):
        if not activity:
            return None
        # Összesített aktivitás számítása feladatípusok szerint
        total_activity = {}
        for topic, types in activity.items():
            total_activity[topic] = sum(types.values())
        return max(total_activity.items(), key=lambda x: x[1])[0]

    # 30 napos történeti aktivitás (összes szókészletből, naponta)
    history = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_str = str(day)
        count = 0
        # BeirasosFeladat
        beirasos = db.fetch_all(
            "SELECT AlfeladatID FROM BeirasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
            (neptun_kod, day_str)
        )
        for (alfeladat_id,) in beirasos:
            c = db.fetch_one("SELECT COUNT(*) FROM AlfeladatBeirasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            count += c
        # KivalasztasosFeladat
        kivalasztasos = db.fetch_all(
            "SELECT AlfeladatID FROM KivalasztasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
            (neptun_kod, day_str)
        )
        for (alfeladat_id,) in kivalasztasos:
            c = db.fetch_one("SELECT COUNT(*) FROM AlfeladatKivalasztasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            count += c
        # ParositasosFeladat
        parositasos = db.fetch_all(
            "SELECT AlfeladatID FROM ParositasosFeladat WHERE NeptunKod = %s AND Datum::date = %s",
            (neptun_kod, day_str)
        )
        for (alfeladat_id,) in parositasos:
            c = db.fetch_one("SELECT COUNT(*) FROM AlfeladatParositasos WHERE AlfeladatID = %s", (alfeladat_id,))[0]
            count += c * 5
        history.append({"date": day_str, "count": count})

    return jsonify({
        "daily": {"activity": daily, "top_topic": max_topic(daily)},
        "weekly": {"activity": weekly, "top_topic": max_topic(weekly)},
        "monthly": {"activity": monthly, "top_topic": max_topic(monthly)},
        "history": history
    })

@app.route("/api/statistics/error-analysis")
def api_statistics_error_analysis():
    """Visszaadja a hibaelemzés adatait: top hibás szavak, hibák típus szerint, időbeli trend."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    interval = request.args.get('interval', 'weekly')  # weekly, monthly
    
    now = datetime.now()
    if interval == 'weekly':
        start_date = now - timedelta(days=6)
    else:  # monthly
        start_date = now - timedelta(days=29)
    
    start_date_str = str(start_date.date())
    end_date_str = str(now.date())
    
    # 1. feladatok_előkészítése_lista létrehozása
    feladatok_lista = []
    
    # Beirasos feladatok
    beirasos_feladatok = db.fetch_all("""
        SELECT ab.PozicioHelyesseg, ab.MegadottSzo, bf.Datum, ab.SzoID, s.IdegenSzo, s.Jelentes1
        FROM AlfeladatBeirasos ab
        JOIN BeirasosFeladat bf ON ab.AlfeladatID = bf.AlfeladatID
        JOIN Szavak s ON ab.SzoID = s.ID
        WHERE bf.NeptunKod = %s AND bf.Datum::date BETWEEN %s AND %s
    """, (neptun_kod, start_date_str, end_date_str))

    for row in beirasos_feladatok:
        pozicio_helyesseg, megadott_szo, datum, szo_id, idegen_szo, jelentes1 = row
        feladatok_lista.append({
            'szo_id': szo_id,
            'pozicio_helyesseg': pozicio_helyesseg,
            'megadott_szo': megadott_szo,
            'idegen_szo': idegen_szo,
            'jelentes1': jelentes1,
            'datum': datum,
            'task_type': 'beirasos'
        })
    
    # Kivalasztasos feladatok
    pattern = '%0%'
    kivalasztasos_feladatok = db.fetch_all("""
        SELECT ak.PozicioHelyesseg, ak.MegadottSzo, kf.Datum, ak.SzoID, s.IdegenSzo, s.Jelentes1
        FROM AlfeladatKivalasztasos ak
        JOIN KivalasztasosFeladat kf ON ak.AlfeladatID = kf.AlfeladatID
        JOIN Szavak s ON ak.SzoID = s.ID
        WHERE kf.NeptunKod = %s
          AND kf.Datum::date BETWEEN %s AND %s
          AND ak.PozicioHelyesseg::text LIKE %s
    """, (neptun_kod, start_date_str, end_date_str, pattern))

    for row in kivalasztasos_feladatok:
        pozicio_helyesseg, megadott_szo, datum, szo_id, idegen_szo, jelentes1 = row
        feladatok_lista.append({
            'szo_id': szo_id,
            'pozicio_helyesseg': pozicio_helyesseg,
            'megadott_szo': megadott_szo,
            'idegen_szo': idegen_szo,
            'jelentes1': jelentes1,
            'datum': datum,
            'task_type': 'kivalasztasos'
        })
    
    # Parositasos feladatok (párok)
    parositasos_feladatok = db.fetch_all("""
        SELECT p.PozicioHelyesseg, pf.Datum, p.SzoID, s.IdegenSzo, s.Jelentes1
        FROM Parok p
        JOIN AlfeladatParositasos ap ON p.ParID = ap.ParID
        JOIN ParositasosFeladat pf ON ap.AlfeladatID = pf.AlfeladatID
        JOIN Szavak s ON p.SzoID = s.ID
        WHERE pf.NeptunKod = %s AND pf.Datum::date BETWEEN %s AND %s
    """, (neptun_kod, start_date_str, end_date_str))
    
    for row in parositasos_feladatok:
        pozicio_helyesseg, datum, szo_id, idegen_szo, jelentes1 = row
        feladatok_lista.append({
            'szo_id': szo_id,
            'pozicio_helyesseg': pozicio_helyesseg,
            'megadott_szo': None,  # Parositasosnál nincs megadott_szo
            'idegen_szo': idegen_szo,
            'jelentes1': jelentes1,
            'datum': datum,
            'task_type': 'parositasos'
        })
    # 1. Top 5 legtöbbször elrontott szó
    szo_hibak = {}
    for feladat in feladatok_lista:
        szo_id = feladat['szo_id']
        hiba_szam = feladat['pozicio_helyesseg'].count('0')
        if szo_id not in szo_hibak:
            szo_hibak[szo_id] = {
                'szo_id': szo_id,
                'hiba_szam': hiba_szam,
                'idegen_szo': feladat['idegen_szo'],
                'jelentes1': feladat['jelentes1']
            }
        else: szo_hibak[szo_id]['hiba_szam'] += hiba_szam
    
    top_5_errors = sorted(szo_hibak.values(), key=lambda x: x['hiba_szam'], reverse=True)[:5]

    # 2. Hibák típus szerint
    idegen_szo_count = Szamlalo()
    jelentes_count = Szamlalo()
    fonetika_count = Szamlalo()
    def konvert_hatarindex(lista_hossz:int, hatarindex:int) -> int:
        return lista_hossz + hatarindex if hatarindex < 0 else hatarindex

    for feladat in feladatok_lista:
        pozicio_helyesseg = feladat['pozicio_helyesseg']
        megadott_szo = feladat['megadott_szo']
        task_type = feladat['task_type']
        szo_id = feladat['szo_id']
        
        parts = str(pozicio_helyesseg).split(':')
        if task_type == 'parositasos':
            mezonevek = [idegen_szo_count, jelentes_count, fonetika_count]
            # Parositasos: idegen_szo:jelentés:fonetika (3 mező)
            if len(parts) == 3 or len(parts) == 2:
                for i, part in enumerate(parts):
                    if part == '0':
                        mezonevek[i] += 1
                        
        else:
            # Beirasos/Kivalasztasos
            szabalyok = {
                2: ([jelentes_count, fonetika_count], [0, -2, -1, -1]),
                8: ([idegen_szo_count, jelentes_count], [0, 0, 1, -1]),
                3: ([idegen_szo_count, fonetika_count], [0, 0, 1, 1])
            }
            # csak akkor folytatjuk, ha van szabály ehhez a megadott_szo értékhez
            if megadott_szo not in szabalyok: continue 
            mezonevek, ettol_Eddig = szabalyok[megadott_szo]

            for i, part in enumerate(parts):
                    if part == '0':
                        if not db.get_szo(szo_id)[8]: mod = 1
                        else: mod = 0
                        if konvert_hatarindex(len(parts), ettol_Eddig[0]) <= i <= konvert_hatarindex(len(parts), ettol_Eddig[1]+mod):
                            mezonevek[0] += 1
                        elif konvert_hatarindex(len(parts), ettol_Eddig[2]) <= i <= konvert_hatarindex(len(parts), ettol_Eddig[3]):
                            mezonevek[1] += 1

    error_types = {
        'idegen_szo': idegen_szo_count.Szam,
        'jelentes': jelentes_count.Szam,
        'fonetika': fonetika_count.Szam
    }
    
    # 3. Hibák időbeli trendje
    history = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_str = str(day.date())  # Csak a dátum részt vesszük
        
        # Napi hibás mezők száma
        daily_errors = 0
        
        for feladat in feladatok_lista:
            if str(feladat['datum'])[:10] == day_str:
                pozicio_helyesseg = feladat['pozicio_helyesseg']
                parts = str(pozicio_helyesseg).split(':')
                daily_errors += sum(1 for p in parts if p == '0')
        
        history.append({"date": day_str, "errors": daily_errors})
    

    return jsonify({
        "top_errors": top_5_errors,
        "error_types": error_types,
        "history": history
    })

@app.route("/api/statistics/confidence-analysis")
def api_statistics_confidence_analysis():
    """Visszaadja az önbizalmi elemzés adatait: biztosság vs teljesítmény összehasonlítása."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    interval = request.args.get('interval', 'weekly')  # weekly, monthly
    
    now = datetime.now()
    if interval == 'weekly':
        start_date = now - timedelta(days=6)
    else:  # monthly
        start_date = now - timedelta(days=29)
    
    start_date_str = str(start_date.date())
    end_date_str = str(now.date())
    
    # 1. Beirasos feladatok adatainak lekérdezése
    beirasos_data = db.fetch_all("""
        SELECT ab.SzoID,ab.Pontszam, bf.Datum, ab.SzuksegesIdo
        FROM AlfeladatBeirasos ab
        JOIN BeirasosFeladat bf ON ab.AlfeladatID = bf.AlfeladatID
        WHERE bf.NeptunKod = %s AND bf.Datum::date BETWEEN %s AND %s
    """, (neptun_kod, start_date_str, end_date_str))
    
    # 2. Kivalasztasos feladatok adatainak lekérdezése
    kivalasztasos_data = db.fetch_all("""
        SELECT ak.SzoID, ak.Pontszam, ak.VarialasSzama, kf.Datum, ak.SzuksegesIdo
        FROM AlfeladatKivalasztasos ak
        JOIN KivalasztasosFeladat kf ON ak.AlfeladatID = kf.AlfeladatID
        WHERE kf.NeptunKod = %s AND kf.Datum::date BETWEEN %s AND %s
    """, (neptun_kod, start_date_str, end_date_str))
    
    # 3. Parositasos feladatok adatainak lekérdezése
    parositasos_data = db.fetch_all("""
        SELECT p.SzoID, p.Pontszam, pf.Datum, ap.SzuksegesIdo, ap.VarialasSzama
        FROM Parok p
        JOIN AlfeladatParositasos ap ON p.ParID = ap.ParID
        JOIN ParositasosFeladat pf ON ap.AlfeladatID = pf.AlfeladatID
        WHERE pf.NeptunKod = %s AND pf.Datum::date BETWEEN %s AND %s
    """, (neptun_kod, start_date_str, end_date_str))
    
    # 4. Adatok feldolgozása és normalizálása
    def calculate_confidence(varacio_szam, ido, task_type, optimalis_ido:int, probak_szama:int):
        """Biztosság számítása 0-100 skálán"""
        import math
        
        # Hányszor lett ugyanaz a szó beküldve próbákozással
        probalkozasok_score = 100 * (1 / (probak_szama+1))
        
        # Válaszidő (exponenciális csökkenés optimalis_ido mp után)
        ido_mp = max(1, ido)  # minimum 1 mp
        if ido_mp <= optimalis_ido:
            ido_score = 100
        else:
            ido_score = 100 * math.exp(-(ido_mp - optimalis_ido) / 20)
        
        # Variációk (csak kivalasztasos és parositasos esetén)
        if task_type in ['kivalasztasos', 'parositasos']:
            variaciok_score = 100 * (1 / max(1, varacio_szam))
            confidence = (probalkozasok_score + ido_score + variaciok_score) / 3
        else:
            confidence = (probalkozasok_score + ido_score) / 2
        
        return round(confidence, 2)
    
    def normalize_performance(pontszam):
        """Teljesítmény normalizálása 0-100 skálán"""
        # Pontszám: -65 (legjobb) -> 75 (legrosszabb)
        # Normalizálás: 100 * (75 - pontszam) / (75 - (-65))
        normalized = 100 * (75 - pontszam) / (75 - (-65))
        return round(max(0, min(100, normalized)), 2)
    

    def probak_szama_szamitas(szo_id, elozo_szo_id, probak_szama):
        if elozo_szo_id == szo_id: probak_szama += 1
        else:
            probak_szama = 0
            elozo_szo_id = szo_id
        return probak_szama, elozo_szo_id

    # 5. Adatok csoportosítása napokra
    daily_data = {}
    
    # Beirasos adatok
    elozo_szo_id = -1
    probak_szama = 0
    for szo_id, pontszam, datum, ido in beirasos_data:
        day = str(datum)[:10]
        if day not in daily_data: daily_data[day] = {'confidence': [], 'performance': []}
        probak_szama, elozo_szo_id = probak_szama_szamitas(szo_id, elozo_szo_id, probak_szama)

        confidence = calculate_confidence(1, ido, 'beirasos', 90, probak_szama)
        performance = normalize_performance(pontszam)
        
        daily_data[day]['confidence'].append(confidence)
        daily_data[day]['performance'].append(performance)
    
    # Kivalasztasos adatok
    for szo_id, pontszam, varacio_szam, datum, ido in kivalasztasos_data:
        day = str(datum)[:10]
        if day not in daily_data: daily_data[day] = {'confidence': [], 'performance': []}
        probak_szama, elozo_szo_id = probak_szama_szamitas(szo_id, elozo_szo_id, probak_szama)
        
        confidence = calculate_confidence(varacio_szam, ido, 'kivalasztasos', 35, probak_szama)
        performance = normalize_performance(pontszam)
        
        daily_data[day]['confidence'].append(confidence)
        daily_data[day]['performance'].append(performance)
    
    # Parositasos adatok
    for szo_id, pontszam, datum, ido, varacio_szam in parositasos_data:
        day = str(datum)[:10]
        if day not in daily_data:
            daily_data[day] = {'confidence': [], 'performance': []}
        
        confidence = calculate_confidence(varacio_szam, ido, 'parositasos', 90, probak_szama)
        performance = normalize_performance(pontszam)
        
        daily_data[day]['confidence'].append(confidence)
        daily_data[day]['performance'].append(performance)
    
    # 6. Napi átlagok számítása
    history = []
    for day in sorted(daily_data.keys()):
        avg_confidence = sum(daily_data[day]['confidence']) / len(daily_data[day]['confidence'])
        avg_performance = sum(daily_data[day]['performance']) / len(daily_data[day]['performance'])
        
        history.append({
            "date": day,
            "confidence": round(avg_confidence, 2),
            "performance": round(avg_performance, 2)
        })
    
    return jsonify({
        "history": history
    })

@app.route("/api/statistics/ai-prediction")
def api_statistics_ai_prediction():
    """Visszaadja az AI predikciós elemzés adatait: jövőbeli pontszám trendek és javaslatok."""
    if 'user_id' not in session:
        return jsonify({"error": "not_authenticated"}), 401
    neptun_kod = session['user_id']
    
    # 1. Lekérjük a felhasználó jelenlegi pontszámait
    current_scores = db.fetch_all("""
        SELECT p.SzoID, p.Pontszam, s.IdegenSzo, s.Jelentes1, s.Jelentes2, s.Jelentes3, s.Jelentes4, s.Jelentes5
        FROM Pontok p
        JOIN Szavak s ON p.SzoID = s.ID
        WHERE p.NeptunKod = %s
    """, (neptun_kod,))
    
    if not current_scores:
        return jsonify({
            "predictions": [],
            "recommendations": [],
            "overall_trend": "Nincs elég adat a predikcióhoz"
        })
    
    # 2. Minden szóhoz lekérjük a pontmódosítások történetét
    szo_trendek = {}
    
    for szo_id, current_pontszam, idegen_szo, jelentes1, jelentes2, jelentes3, jelentes4, jelentes5 in current_scores:
        # Szó adatainak inicializálása
        szo_trendek[szo_id] = {
            'idegen_szo': idegen_szo,
            'jelentesek': [j for j in [jelentes1, jelentes2, jelentes3, jelentes4, jelentes5] if j],
            'current_score': current_pontszam,
            'history': []  # [(datum, pontszam), ...]
        }
        
        # 2.1 Beirasos feladatok pontmódosításai
        beirasos_modifications = db.fetch_all("""
            SELECT ab.Pontszam, bf.Datum
            FROM AlfeladatBeirasos ab
            JOIN BeirasosFeladat bf ON ab.AlfeladatID = bf.AlfeladatID
            WHERE bf.NeptunKod = %s AND ab.SzoID = %s
            ORDER BY bf.Datum DESC
        """, (neptun_kod, szo_id))
        
        # 2.2 Kivalasztasos feladatok pontmódosításai
        kivalasztasos_modifications = db.fetch_all("""
            SELECT ak.Pontszam, kf.Datum
            FROM AlfeladatKivalasztasos ak
            JOIN KivalasztasosFeladat kf ON ak.AlfeladatID = kf.AlfeladatID
            WHERE kf.NeptunKod = %s AND ak.SzoID = %s
            ORDER BY kf.Datum DESC
        """, (neptun_kod, szo_id))
        
        # 2.3 Parositasos feladatok pontmódosításai (Parok táblából)
        parositasos_modifications = db.fetch_all("""
            SELECT p.Pontszam, pf.Datum
            FROM Parok p
            JOIN AlfeladatParositasos ap ON p.ParID = ap.ParID
            JOIN ParositasosFeladat pf ON ap.AlfeladatID = pf.AlfeladatID
            WHERE pf.NeptunKod = %s AND p.SzoID = %s
            ORDER BY pf.Datum DESC
        """, (neptun_kod, szo_id))
        
        # 2.4 Összes módosítás összefűzése és dátum szerint rendezése
        all_modifications = []
        for pontszam, datum in beirasos_modifications + kivalasztasos_modifications + parositasos_modifications:
            all_modifications.append((datum, pontszam))
        
        # Dátum szerint rendezés (legújabbtól legrégebbiig)
        all_modifications.sort(key=lambda x: x[0], reverse=True)
        
        # 2.5 Történelmi pontszámok rekonstruálása
        # Kezdjük a jelenlegi pontszámmal és vonjuk le a módosításokat időrendben
        reconstructed_scores = []
        current_reconstructed_score = current_pontszam
        
        for datum, pontszam_modification in all_modifications:
            # A módosítás előtti pontszám = jelenlegi - módosítás
            previous_score = current_reconstructed_score - pontszam_modification
            reconstructed_scores.append((datum, previous_score))
            current_reconstructed_score = previous_score
        
        # Ha nincs módosítás, akkor csak a jelenlegi pontszám
        if not reconstructed_scores:
            reconstructed_scores = [(datetime.now().date(), current_pontszam)]
        
        # Dátum szerint rendezés (legrégebbitől legújabbig)
        reconstructed_scores.sort(key=lambda x: x[0])
        szo_trendek[szo_id]['history'] = reconstructed_scores
    
    # 3. Lineáris regresszió minden szóhoz
    def linear_regression(x_values, y_values):
        """Egyszerű lineáris regresszió"""
        n = len(x_values)
        if n < 2:
            return None, None
        
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Slope és intercept számítása
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    predictions = []
    recommendations = []
    
    for szo_id, szo_data in szo_trendek.items():
        history = szo_data['history']
        if len(history) < 2:
            continue
        
        # Időpontok és pontszámok kinyerése
        dates = [entry[0] for entry in history]
        scores = [entry[1] for entry in history]
        
        # Időpontok normalizálása (0, 1, 2, ...)
        x_values = list(range(len(scores)))
        y_values = scores
        
        # Regresszió számítása
        slope, intercept = linear_regression(x_values, y_values)
        if slope is None:
            continue
        
        # Jelenlegi pontszám (utolsó érték)
        current_score = scores[-1]
        elozo_score = scores[-2]
        
        # Predikció 30 napra előre (feltételezve napi 1 feladat)
        future_x = len(scores) + 30
        predicted_score = slope * future_x + intercept
        
        # Predikció korlátozása a 30-800 tartományra
        predicted_score = max(30, min(800, predicted_score))
        
        # Trend iránya
        trend_direction = f"Összességében: Javul" if slope < 0 else f"Összességében: Rontódik"
        trend_strength = abs(slope)
        
        # Javulási potenciál (mennyire közel van a 30-hoz)
        improvement_potential = (current_score - elozo_score) / ((current_score + elozo_score) / 2) * 100
        
        prediction = {
            'szo_id': szo_id,
            'idegen_szo': szo_data['idegen_szo'],
            'jelentesek': szo_data['jelentesek'],
            'current_score': current_score,
            'predicted_score': round(predicted_score, 1),
            'trend_direction': trend_direction,
            'trend_strength': round(trend_strength, 3),
            'improvement_potential': round(improvement_potential, 1),
            'data_points': len(scores)
        }
        
        predictions.append(prediction)
        
        # Javaslatok generálása - prioritás alapján
        if current_score > 800:  # Magas pontszám
            priority = "magas"
            reason = "Nagyon magas pontszám, komoly gyakorlás szükséges"
        elif current_score > 550:  # Magas pontszám
            priority = "magas"
            reason = "Magas pontszám, sürgős javítás szükséges"
        elif current_score > 300:  # Közepes pontszám
            priority = "közepes"
            reason = "Közepesen magas pontszám, javítás szükséges"
        elif current_score > 200:  
            priority = "közepes"
            reason = "Közepesen alacsony pontszám, gyakorlás javasolt"
        elif current_score > 100:
            priority = "alacsony"
            reason = "Alacsony pontszám, gyakorlás javasolt"
        elif current_score > 50:
            priority = "alacsony"
            reason = "Nagyon alacsony pontszám, majdnem tökénletes"
        else:
            continue  # Kiváló pontszám, nincs javítási igény
        
        recommendations.append({
            'szo_id': szo_id,
            'idegen_szo': szo_data['idegen_szo'],
            'jelentesek': szo_data['jelentesek'],
            'current_score': current_score,
            'reason': reason,
            'priority': priority
        })
    
    # Javaslatok rendezése prioritás szerint
    priority_order = {"magas": 3, "közepes": 2, "alacsony": 1}
    recommendations.sort(key=lambda x: (priority_order.get(x['priority'], 0), x['current_score']), reverse=True)
    recommendations = recommendations[:10]  # Top 10 javaslat
    
    # Általános trend elemzése
    if predictions:
        avg_current = sum(p['current_score'] for p in predictions) / len(predictions)
        avg_predicted = sum(p['predicted_score'] for p in predictions) / len(predictions)
        
        if avg_predicted < avg_current:
            overall_trend = "javuló"
        elif avg_predicted > avg_current:
            overall_trend = "rontódó"
        else:
            overall_trend = "stabil"
    else:
        overall_trend = "Nincs elég adat"
    
    return jsonify({
        "predictions": predictions,
        "recommendations": recommendations,
        "overall_trend": overall_trend,
        "total_words": len(predictions)
    })

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            # Adatok beolvasása a form-ból
            neptun_kod = request.form.get('neptun_kod', '').strip().upper()
            email = request.form.get('email', '').strip().lower()
            jelszo = request.form.get('jelszo', '')
            jelszo_megerosites = request.form.get('jelszo_megerosites', '')
            eletkor_str = request.form.get('eletkor')
            tanult_szak_str = request.form.get('tanult_szak')
            angol_szint = request.form.get('angol_szint')
            regisztracios_kod = request.form.get('regisztracios_kod', '').strip()
            
            gepeszet = 1 if request.form.get('gepeszet') else 0
            urkutatas = 1 if request.form.get('urkutatas') else 0
            kvantumszamitas = 1 if request.form.get('kvantumszamitas') else 0
            biotechnologia = 1 if request.form.get('biotechnologia') else 0
            geologia = 1 if request.form.get('geologia') else 0
            nanotechnologia = 1 if request.form.get('nanotechnologia') else 0
            gazdasagi_elemzes = 1 if request.form.get('gazdasagi_elemzes') else 0
            kriminologia = 1 if request.form.get('kriminologia') else 0
            genetika = 1 if request.form.get('genetika') else 0
            meteorologia = 1 if request.form.get('meteorologia') else 0
            adatbanyaszat = 1 if request.form.get('adatbanyaszat') else 0

            if gepeszet + urkutatas + kvantumszamitas + biotechnologia + geologia + nanotechnologia + gazdasagi_elemzes + kriminologia + genetika + meteorologia + adatbanyaszat < 2:
                flash('Legalább két érdeklődési témát ki kell választanod!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Validáció, hogy minden szükséges mező meg van-e adva
            if not email or not jelszo or not jelszo_megerosites or not eletkor_str or not tanult_szak_str or not angol_szint or not regisztracios_kod:
                flash('Minden mező kitöltése kötelező!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Email validáció
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('Érvénytelen email cím formátum!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Email egyediség ellenőrzése
            if db.get_diak_by_email(email):
                flash('Ez az email cím már regisztrálva van!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Jelszó validáció
            if len(jelszo) < 8:
                flash('A jelszónak minimum 8 karakter hosszúnak kell lennie!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            if not re.search(r'[0-9]', jelszo) or not re.search(r'[a-zA-Z]', jelszo):
                flash('A jelszónak tartalmaznia kell számokat és betűket is!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Jelszó megerősítés ellenőrzése
            if jelszo != jelszo_megerosites:
                flash('A jelszavak nem egyeznek!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Jelszó hash generálása
            jelszo_hash = generate_password_hash(jelszo)
            
            # Konvertálás int-re
            eletkor = int(eletkor_str)
            tanult_szak = int(tanult_szak_str)
            
            # Neptun kód generálása, ha üres
            if not neptun_kod:
                neptun_kod = generate_neptun_kod()
            
            # Validáció
            if len(neptun_kod) != 6 and len(neptun_kod) != 5:
                flash('A Neptun kódnak 5-6 karakter hosszúnak kell lennie!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            if not neptun_kod.isalnum():
                flash('A Neptun kódnak csak betűket és számokat tartalmazhat!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            if eletkor < 16 or eletkor > 100:
                flash('Az életkornak 16-100 között kell lennie!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Regisztrációs kód validáció
            if not regisztracios_kod:
                flash('A regisztrációs kód megadása kötelező!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            kod_adat = db.fetch_one("SELECT regID, hasznalhatosag FROM regisztracios_kod WHERE kulcs = %s", (regisztracios_kod,))
            if not kod_adat:
                flash('Érvénytelen regisztrációs kód!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            reg_id, hasznalhatosag = kod_adat
            if hasznalhatosag < 1:
                flash('A megadott regisztrációs kód már nem használható!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                return render_template("register.html", szakok=szakok, formdata=request.form)
            
            # Adatok mentése az adatbázisba
            reg_datum = datetime.now().strftime('%Y-%m-%d')
            success = db.add_diak(neptun_kod, email, jelszo_hash, tanult_szak, angol_szint, eletkor, reg_id, reg_datum)
            
            if success:
                db.execute("UPDATE regisztracios_kod SET hasznalhatosag = hasznalhatosag - 1 WHERE regID = %s", (reg_id,))
                if gepeszet or urkutatas or kvantumszamitas or biotechnologia or geologia or nanotechnologia or gazdasagi_elemzes or kriminologia or genetika or meteorologia or adatbanyaszat:
                    db.add_egyedi_szaktudas(neptun_kod, gepeszet, urkutatas, kvantumszamitas, biotechnologia, geologia, nanotechnologia, gazdasagi_elemzes, kriminologia, genetika, meteorologia, adatbanyaszat)
                flash(f'Sikeres regisztráció! Neptun kód: {neptun_kod}, Email: {email}', 'success')
                return redirect(url_for("index"))
            else:
                if db.get_diak_by_neptun(neptun_kod):
                    flash('Ez a Neptun kód már foglalt, kérlek válassz másikat vagy hagyd üresen az automatikus generáláshoz!', 'error')
                else:
                    flash('Hiba történt a regisztráció során!', 'error')
                szakok = db.get_all_valaszthato_szakok()
                # Átadjuk a korábbi adatokat is
                return render_template("register.html", szakok=szakok, formdata=request.form)
                
        except ValueError as e:
            flash('Hibás adatok! Kérlek ellenőrizd a megadott értékeket.', 'error')
            szakok = db.get_all_valaszthato_szakok()
            return render_template("register.html", szakok=szakok, formdata=request.form)
        except Exception as e:
            flash(f'Váratlan hiba történt: {str(e)}', 'error')
            szakok = db.get_all_valaszthato_szakok()
            return render_template("register.html", szakok=szakok, formdata=request.form)
    
    # GET kérés esetén szakok betöltése
    szakok = db.get_all_valaszthato_szakok()
    return render_template("register.html", szakok=szakok)

@app.route("/load_initial_data")
def load_initial_data():
    """Kezdeti adatok betöltése a JSON fájlból"""
    try:
        # Adatok betöltése a JSON fájlból
        json_path = os.path.join(os.path.dirname(__file__), "initial_data.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Választható szakok betöltése
        for szak in data.get('valaszthato_szakok', []):
            db.add_valaszthato_szak(szak['szak_id'], szak['szak_nev'])
        
        # Szókeszletek betöltése (ha vannak)
        for szokeszlet in data.get('szokeszletek', []):
            db.add_szokeszlet(szokeszlet['szokeszlet_id'], szokeszlet['nev'], szokeszlet.get('tulajdonos'))
        
        # Szavak betöltése (ha vannak)
        for szo in data.get('szavak', []):
            db.add_szo(
                szo['szokeszlet_id'],
                szo['idegen_szo'],
                szo.get('jelentes', "") or szo.get('jelentes1', ""),
                szo.get('jelentes2', ""),
                szo.get('jelentes3', ""),
                szo.get('jelentes4', ""),
                szo.get('jelentes5', ""),
                szo.get('fonetika', ""),
                szo.get('leiras', ""),
                szo.get('szoveg_kontextus', "")
            )
        
        flash('Kezdeti adatok sikeresen betöltve!', 'success')
        
    except FileNotFoundError:
        flash('Az initial_data.json fájl nem található!', 'error')
    except json.JSONDecodeError:
        flash('Hiba a JSON fájl feldolgozásakor!', 'error')
    except Exception as e:
        flash(f'Hiba az adatok betöltésekor: {str(e)}', 'error')
    
    return redirect(url_for("admin"))

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        jelszo = request.form.get("admin_jelszo", "")
        if bcrypt.checkpw(jelszo.encode("utf-8"), ADMIN_PASSWORD_HASH):
            session['admin_authenticated'] = True
            flash("Sikeres admin belépés!", "success")
            return redirect(url_for("admin"))
        else:
            flash("Hibás admin jelszó!", "error")
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    # Admin jogosultság: vagy admin_login, vagy bejelentkezett admin felhasználó
    if not is_admin_session():
        # Ha nincs még admin_login, tereljük oda; különben vissza indexre
        if 'user_id' not in session:
            flash('Kérlek, jelentkezz be admin jelszóval!', 'error')
            return redirect(url_for("admin_login"))
        flash('Nincs jogosultságod az admin felülethez!', 'error')
        return redirect(url_for("index"))
    try:
        # Adatok lekérdezése
        diakok = db.get_all_diakok()
        szakok = db.get_all_valaszthato_szakok()
        egyedi_szaktudasok = db.get_all_egyedi_szaktudas()
        szokeszletek = db.get_all_szokeszletek()
        szavak = db.get_all_szavak()
        regkodok = db.fetch_all("SELECT regID, kulcs, hasznalhatosag, leiras FROM regisztracios_kod")
        # Szókészletekhez szavak száma (tuple/dict)
        szokeszlet_adatok = []
        for szokeszlet in szokeszletek:
            szokeszlet_id = szokeszlet[0]
            szavak_count = len([szo for szo in szavak if szo[1] == szokeszlet_id])
            szokeszlet_adatok.append({
                "id": szokeszlet[0],
                "nev": szokeszlet[1],
                "tulajdonos": szokeszlet[2],
                "szavak_szama": szavak_count
            })
        sql_result_history = session.get('sql_result_history', [])
        return render_template("admin.html", 
                             diakok=diakok, 
                             szakok=szakok, 
                             egyedi_szaktudasok=egyedi_szaktudasok,
                             szokeszlet_adatok=szokeszlet_adatok,
                             szavak=szavak,
                             regkodok=regkodok,
                             sql_result_history=sql_result_history)
    except Exception as e:
        flash(f'Hiba az admin felület betöltésekor: {str(e)}', 'error')
        return redirect(url_for("index"))

@app.route("/admin/regkod_uj", methods=["POST"])
def admin_regkod_uj():
    kulcs = request.form.get("regkod_kulcs", "").strip()
    hasznalhatosag = request.form.get("regkod_hasznalhatosag", "1").strip()
    leiras = request.form.get("leiras", "").strip()
    if not kulcs or not hasznalhatosag.isdigit() or not leiras:
        flash("Hibás kód vagy használhatóság!", "error")
        return redirect(url_for("admin"))
    db.execute("INSERT INTO regisztracios_kod (kulcs, hasznalhatosag, leiras) VALUES (%s, %s, %s)", (kulcs, int(hasznalhatosag), leiras))
    flash("Új regisztrációs kód hozzáadva!", "success")
    return redirect(url_for("admin"))

@app.route("/admin/regkod_szerk/<int:regid>", methods=["POST"])
def admin_regkod_szerk(regid):
    hasznalhatosag = request.form.get("regkod_hasznalhatosag", "1").strip()
    leiras = request.form.get("leiras", "").strip()
    if not hasznalhatosag.isdigit():
        flash("Hibás használhatóság!", "error")
        return redirect(url_for("admin"))
    db.execute("UPDATE regisztracios_kod SET hasznalhatosag = %s WHERE regID = %s", (int(hasznalhatosag), regid))
    db.execute("UPDATE regisztracios_kod SET leiras = %s WHERE regID = %s", (leiras, regid))
    flash("Regisztrációs kód használhatósága frissítve!", "success")
    return redirect(url_for("admin"))

@app.route("/admin/regkod_torol/<int:regid>", methods=["POST"])
def admin_regkod_torol(regid):
    db.execute("DELETE FROM regisztracios_kod WHERE regID = %s", (regid,))
    flash("Regisztrációs kód törölve!", "success")
    return redirect(url_for("admin"))

@app.route("/admin/clear_all")
def admin_clear_all():
    """Admin funkció az összes adat törléséhez"""
    try:
        success = db.clear_all_data()
        if success:
            flash('Minden adat sikeresen törölve!', 'success')
        else:
            flash('Hiba történt az adatok törlésekor!', 'error')
    except Exception as e:
        flash(f'Hiba: {str(e)}', 'error')
    
    return redirect(url_for("admin"))

@app.route("/admin/rebuild_db")
def admin_rebuild_db():
    """Admin funkció az adatbázis séma frissítéséhez"""
    try:
        # Adatbázis séma frissítése (migrációval)
        db.rebuild_database()
        flash('Adatbázis séma sikeresen frissítve! A meglévő adatok megmaradtak.', 'success')
    except Exception as e:
        flash(f'Hiba az adatbázis séma frissítésekor: {str(e)}', 'error')
    
    return redirect(url_for("admin"))

@app.route("/admin/sql_execute", methods=["POST"])
def admin_sql_execute():
    """Admin funkció SQL parancs futtatásához"""
    # Admin jogosultság ellenőrzése
    if not is_admin_session():
        if 'user_id' not in session:
            flash('Kérlek, jelentkezz be admin jelszóval!', 'error')
            return redirect(url_for("admin_login"))
        flash('Nincs jogosultságod az SQL parancs futtatásához!', 'error')
        return redirect(url_for("admin"))
    
    sql_command = request.form.get('sql_command', '').strip()
    if not sql_command:
        flash('SQL parancs megadása kötelező!', 'error')
        return redirect(url_for("admin"))
    
    try:
        if sql_command.startswith("su "):
            user_id = sql_command.removeprefix("su ")
            if db.execute("select count(*) from diakok WHERE neptunkod = %s", (user_id,)) == 1:
                session['user_id'] = user_id
                return redirect(url_for("dashboard"))
            else:
                raise Exception("Nem létezik a megadott felhasználó!")
        # SQL parancs futtatása
        if sql_command.upper().startswith('SELECT'):
            # SELECT parancs - adatok lekérdezése
            result = db.fetch_all(sql_command)
            if result:
                # Oszlopnevek lekérdezése (ha van)
                columns = []
                try:
                    with db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute(sql_command)
                        columns = [description[0] for description in cursor.description]
                except:
                    # Ha nem sikerül az oszlopneveket lekérdezni, számozott oszlopok
                    columns = [f"Oszlop_{i+1}" for i in range(len(result[0]))]
                eredmeny = {
                    'data': result,
                    'columns': columns,
                    'affected_rows': len(result),
                    'sql': sql_command
                }
            else:
                eredmeny = {
                    'data': [],
                    'columns': [],
                    'affected_rows': 0,
                    'sql': sql_command
                }
        else:
            # INSERT, UPDATE, DELETE parancs - módosítás
            with db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_command)
                affected_rows = cursor.rowcount
                conn.commit()
            eredmeny = {
                'affected_rows': affected_rows,
                'sql': sql_command
            }
        flash('SQL parancs sikeresen végrehajtva!', 'success')
        # Eredmény hozzáfűzése a history-hoz
        history = session.get('sql_result_history', [])
        history.insert(0, eredmeny)
        session['sql_result_history'] = history
        session.modified = True
    except Exception as e:
        history = session.get('sql_result_history', [])
        history.insert(0, {'error': str(e), 'sql': sql_command})
        session['sql_result_history'] = history
        session.modified = True
        flash(f'SQL hiba: {str(e)}', 'error')
    return redirect(url_for("admin"))

@app.route("/admin/clear_sql_history", methods=["POST"])
def admin_clear_sql_history():
    session['sql_result_history'] = []
    session.modified = True
    flash('SQL eredménytörténet törölve!', 'success')
    return redirect(url_for("admin"))

@app.route("/start_learning", methods=["POST"])
def start_learning():
    if 'user_id' not in session:
        return jsonify({'error': 'Nincs bejelentkezve!'}), 401
    data = request.get_json()
    method = data.get('method')
    vocab_ids = data.get('vocabs', [])
    min_points = data.get("minPoints")
    max_points = data.get("maxPoints")

    if not method or not vocab_ids:
        return jsonify({'error': 'Hiányzó adatok!'}), 400
    # Session-azonosító generálása
    session_id = str(uuid.uuid4())
    # Tanulási állapot mentése session-be (csak metaadatok)
    session['learning'] = {
        'session_id': session_id,
        'method': method,
        'vocab_ids': vocab_ids,
        'min_points': min_points,
        'max_points': max_points,
        'pos': 0
    }
    # Szavak lekérdezése pontsorrendben
    szavak = db.get_szavak_ponttal_by_szokeszlet_ids(session['user_id'], vocab_ids, min_points, max_points)
    # Munkafelület generálása
    if method == 'simple_list':
        html = render_learning_simple_list(szavak, 0)
    elif method == 'spaced_repetition':
        html = '<div class="soon">A Spaced Repetition módszer hamarosan elkészül.</div>'
    else:
        html = '<div class="error">Ismeretlen tanulási módszer!</div>'
    return jsonify({'html': html, 'session_id': session_id})

def render_learning_simple_list(szavak, pos):
    # 5-asával jelenítjük meg a szavakat
    total = len(szavak)
    end = min(pos + 5, total)
    szavak_chunk = szavak[pos:end]
    html = '<div class="simple-list-block">'
    for szo in szavak_chunk:
        idegen_szo = szo[2] or ''
        fonetika = szo[8] or ''
        jelentések = ', '.join([j for j in [szo[3], szo[4], szo[5], szo[6], szo[7]] if j])
        szoveg_kontextus = szo[10] or ''
        leiras = szo[9] or ''
        pontszam = szo[-1] if len(szo) > 11 else None
        html += '<div class="simple-word">'
        html += f'<b>{idegen_szo}</b>'
        if fonetika:
            html += f' : <i>{fonetika}</i>'
        if jelentések:
            html += f' – <span class="jelentesek">{jelentések}</span>'
        html += '<br>'
        if szoveg_kontextus:
            html += f'<span class="hasznalatban">Használatban: {szoveg_kontextus}</span>'
        if leiras:
            html += f'<span class="leiras">Leírás: {leiras}</span>'
        if pontszam is not None:
            html += f'<div class="pontszam">Pontszám: <b>{pontszam}</b></div>'
        html += '</div>'
    html += f'<div class="progress">{end} / {total} szó</div>'
    if end < total:
        html += '<button id="next-btn">Tovább</button>'
    else:
        html += '<div class="done">Vége a tanulásnak!</div>'
    html += '</div>'
    return html

@app.route("/learning_next", methods=["POST"])
def learning_next():
    if 'user_id' not in session or 'learning' not in session:
        return jsonify({'error': 'Nincs aktív tanulási folyamat!'}), 400
    data = request.get_json()
    session_id = data.get('session_id')
    learning = session.get('learning')
    if not learning or learning.get('session_id') != session_id:
        return jsonify({'error': 'Érvénytelen session!'}), 400
    method = learning['method']
    vocab_ids = learning['vocab_ids']
    min_points = learning['min_points']
    max_points = learning['max_points']

    pos = learning['pos'] + 5
    session['learning']['pos'] = pos
    session.modified = True
    # Szavak lekérdezése pontsorrendben
    szavak = db.get_szavak_ponttal_by_szokeszlet_ids(session['user_id'], vocab_ids, min_points, max_points)
    if method == 'simple_list':
        html = render_learning_simple_list(szavak, pos)
    elif method == 'spaced_repetition':
        html = '<div class="soon">A Spaced Repetition módszer hamarosan elkészül.</div>'
    else:
        html = '<div class="error">Ismeretlen tanulási módszer!</div>'
    return jsonify({'html': html, 'session_id': session_id})

@app.route("/start_task", methods=["POST"])
def start_task():
    # a get_weighted_random_words()[0] álltal visszaadott eredményből sorolja ki a megadandó és a megadott részeket.

    """Feladat indítása - feladat állapotának mentése session-be"""
    if 'user_id' not in session:
        return jsonify({'error': 'Nincs bejelentkezve!'}), 401
    
    data = request.get_json() # vocab_id
    old_current_task = session.get('current_task', {})
    jelenlegi_beallitasok = get_task_settings_hash(data)
    

    # Kapott JSON adatok kiírása a konzolra
    # {'task_type': 'kivalasztasos', 'vocab_id': '3', 'difficulty': 'nehez',
    # 'options': {'fonetika_only': False, 'num_options': 4}
    # }
    alfeladat_frissit = None

    elozo_szavak = Szo_Elofordulas_Sor.from_dict(old_current_task.get("elozo_szavak") or None)

    if not db.van_e_legalabb_n_szo(data['vocab_id'], 15):
        return jsonify({'error': 'A használni kívánt szókészletben nincs elég szó! (legalább 15 szó kell)'}), 400

    if data['task_type'] == "beirasos": # get_weighted_random_words[0] -> (145, 3, 'apple', 'alma', '', '', '', '', 'aŁ$mm', '', '')
        feladat_szo = db.get_weighted_random_words(session['user_id'], [data['vocab_id']], n=1, kizart_szoid_lista=elozo_szavak.Lekerdez)[0]  # egy szót választunk
        if not feladat_szo:
            return jsonify({'error': 'Nincs megfelelő szó!'}), 400
        feladat = generate_feladat_szo_json(db, data, feladat_szo)
        alfeladat_frissit = db.add_beirasos_feladat
    elif data['task_type'] == 'kivalasztasos':
        feladat_szo = db.get_weighted_random_words(session['user_id'], [data['vocab_id']], n=1, kizart_szoid_lista=elozo_szavak.Lekerdez)[0]  # egy szót választunk
        if not feladat_szo:
            return jsonify({'error': 'Nincs megfelelő szó!'}), 400
        feladat = generate_feladat_szo_json(db, data, feladat_szo)
        alfeladat_frissit = db.add_kivalasztasos_feladat
    elif data['task_type'] == 'parositasos':
        feladat_szo = db.get_weighted_random_words(session['user_id'], [data['vocab_id']], n=5, kizart_szoid_lista=elozo_szavak.Lekerdez)
        if not feladat_szo:
            return jsonify({'error': 'Nincs megfelelő szó!'}), 400
        feladat = generate_feladat_szo_json(db, data, feladat_szo)
        alfeladat_frissit = db.add_parositasos_feladat
    else:
        return jsonify({'error': 'Hibás feladatípus: '+ data['task_type']}), 401
    
    jelenlegi_id = feladat['szo_id']
    elozo_szavak.hozzaad(*jelenlegi_id if isinstance(jelenlegi_id, list) else [jelenlegi_id])

    # Egyedi task_id generálása
    task_id = str(uuid.uuid4())

    # Feladat állapot JSON összeállítása
    current_task = {
        'task_id': task_id,
        'settings': data,
        'feladat': feladat,
        'allapot': {
            'probalkozasok_szama': 0,
            'max_probalkozas': 5,
            'allapot_szoveg': 'nincs válasz'
        },
        'előző vocab_id': data['vocab_id'],  # mindig naprakészen frissítjük
        'elozo_szavak': elozo_szavak.to_dict(),
        'jelenlegi_beallitasok': jelenlegi_beallitasok,
        'AlfeladatID': old_current_task.get('AlfeladatID', None),
        'kezdes': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    if old_current_task.get("jelenlegi_beallitasok", None) != jelenlegi_beallitasok:
        print("!=")
        if alfeladat_frissit is None: return jsonify({'error': 'Az alfeladat_frissit() fügvény nem lett betölve!'}), 400
        feladat_datum = current_task['kezdes']
        nehezseg = data.get('difficulty', None)
        felkinaltLehet = intervallumhoz_igazit(data['options'].get('num_options', None), 15, 4)
        current_task['AlfeladatID'] = alfeladat_frissit(session['user_id'], data['vocab_id'], feladat_datum, {"MegadottKezdobetu": 1 if data['options'].get('show_first_letter') == True else 0, "nehezseg":nehezseg, "felkinaltLehet":felkinaltLehet})

    session['current_task'] = current_task
    session.modified = True # ha nem frissítjük a felhasználó felé a season cookie akkor a szerver álltal végrejatott változások elvesznek.

    # Visszaadjuk a task_id-t és a feladat adatait

    print("Válasz json:\n","-" * 50, "\n")
    pp.pprint(current_task)
    print("-" * 50)
    return jsonify(current_task)


@app.route("/submit_task", methods=["POST"])
def submit_task():
    kapott_data = request.get_json() 
    current_task = session.get('current_task')
    print("\nBeküldött válasz a /submit_task végponton:")
    print("-" * 50)
    pp.pprint(kapott_data)
    print("-" * 50)
    # TODO: ellenőtizni hogy a begépelt válaszok maximum 100 karakteres lehet 
    if current_task is None:
        return jsonify({'status': 'error', 'message': 'Nincs aktív feladat!'}), 400

    # Ellenőrzés: task_id egyezés
    if 'task_id' not in kapott_data or kapott_data['task_id'] != current_task.get('task_id'):
        return jsonify({'status': 'error', 'message': 'Érvénytelen vagy nem egyező task_id!'}), 400

    # válasz kiértékelése     
    szavak_lista = SzoContainer()
    egy_szo = None

    fonetika_mezo_index = current_task['feladat']['hasznalt_fonetika_index']
    if current_task['settings']['task_type'] == 'beirasos':
        for task_type in kapott_data['answers']:
            if egy_szo is None:
                helyes_szo_adatok = db.get_szo(current_task['feladat']['szo_id'])
                egy_szo = Szo_class(helyes_szo_adatok, fonetika_mezo_index)
                egy_szo.megadott_feladat = current_task['feladat']['feladat']
            valasz = kapott_data['answers'][task_type]
            if len(valasz) == 1 and task_type != "jelentes":
                egy_szo.add_valasz(task_type, valasz[0])
            else: egy_szo.add_valasz(task_type, valasz)
            # ami None mező a válaszban az már meg van adva.
        szavak_lista.append(egy_szo)

    elif current_task['settings']['task_type'] == 'kivalasztasos':
        if egy_szo is None:
            helyes_szo_adatok = db.get_szo(current_task['feladat']['szo_id'])
            egy_szo = Szo_class(helyes_szo_adatok, fonetika_mezo_index)
            egy_szo.megadott_feladat = current_task['feladat']['feladat']

            lehetosgek = {}
            for kulcs, ertek in current_task['feladat'].items():
                if kulcs.endswith('_lehetőség'):
                    lehetosgek[kulcs] = ertek
            egy_szo.lehetosegek = lehetosgek
        egy_szo.add_valasz_dict(kapott_data['answers'])
        szavak_lista.append(egy_szo)
        # ami None mező a válaszban az már meg van adva.
            

    elif current_task['settings']['task_type'] == 'parositasos':
        for i in range(5):
            egy_szo = Szo_class(current_task['feladat']['megadandó'][i], fonetika_mezo_index)
            
            lehetosgek = {}
            for kulcs, ertek in current_task['feladat'].items():
                if kulcs.endswith('_lehetőség'):
                    lehetosgek[kulcs] = ertek
            egy_szo.lehetosegek = lehetosgek
            szavak_lista.append(egy_szo)
        
        szavak_lista.valasz_hozzaad(kapott_data['answers'])
            
    else:
        return jsonify({'status': 'error', 'message': 'Hibás feladattípus!'}), 400
    
    if egy_szo is None:
            return jsonify({'status': 'error', 'message': 'Nincs beállítva a szó!'}), 400
    

    # ha próbálkozással lett beküldve akkor növelni kell a számát
    if kapott_data['probalkozas']:
        current_task['allapot']['probalkozasok_szama'] += 1

    # válasz generálás
    valasz_json = {"pozicio_helyesseg": egy_szo.Pozicio_helyesseg if len(szavak_lista) != 5 else [(i.eredeti_sor_index, i.Pozicio_helyesseg) for i in szavak_lista],
    "probalkozasok_szama": current_task['allapot']['probalkozasok_szama']}
    
    if len(szavak_lista) == 5: allapot = all(all(sor) for sor in valasz_json['pozicio_helyesseg'])
    else: allapot = all(valasz_json['pozicio_helyesseg'])

    valasz_json["status"] = "beküldve" if not kapott_data['probalkozas'] or current_task['allapot']['probalkozasok_szama'] == 5 or allapot else 'próbálkozás'

    if valasz_json['status'] == "beküldve":
        valasz_json["helyes_lett_volna"] = egy_szo.Helyes_adatok if len(szavak_lista) != 5 else [(i.eredeti_sor_index, i.Helyes_adatok) for i in szavak_lista]
    
    # current_task státusz módosítás
    current_task['allapot']['allapot_szoveg'] = f"{'helyes' if allapot else 'hibás'} {valasz_json['status']}"
    session['current_task'] = current_task
    session.modified = True

    # pontozás és mentés
    tmp = current_task["feladat"]["szo_id"] if isinstance(current_task["feladat"]["szo_id"], list) else [current_task["feladat"]["szo_id"]]
    jelenlegi_pontok = [db.get_pont(session['user_id'], ID) for ID in tmp]

    for regi_pont, szo_class in zip(jelenlegi_pontok, szavak_lista.values()):
        szazalek = szo_class.Hasonlosag
        if kapott_data['probalkozas']: 
            enyhites = 0.2 # 80%-kal enyhébb
        else: enyhites = 1 # nincs enyhítés

        # megadott karakter vagy nehézség megalapítása: 1 ha könnyebb, PONTOK["modosito"] ha nehezebb
        if not current_task['settings']['options'].get('show_first_letter', True) or current_task['settings'].get('difficulty', False) == "nehez":
            nehezseg_modosito = PONTOK[current_task['settings']['task_type']]['modosito']
        else: nehezseg_modosito = 1
        
        pont_modositas = lehetosegek_szama_modosito(pont=pontszamitas(szazalek, *PONTOK[current_task['settings']['task_type']]['parameterek'], nehezseg_modosito), valasztek=current_task['settings']['options'].get('num_options', 1))
        pont_modositas *= enyhites
        regi_pont += pont_modositas
        regi_pont = max(30, regi_pont)
        szo_class.Pontszam = int(pont_modositas)
        db.update_pont(session['user_id'], szo_class.szo_id, int(regi_pont))
    
    if current_task['settings']['task_type'] == "parositasos":
        for i in szavak_lista: 
            print(f"({i.Hasonlosag}% {i.Pontszam}) {i.Pozicio_helyesseg} {i.eredeti_sor_index}")
            print(i)
    else:
        print(f"({egy_szo.Hasonlosag}% {egy_szo.Pontszam}) {egy_szo.Pozicio_helyesseg}")
        print(egy_szo)

    # menéshez szükséges adatok intézése
    kezdes = datetime.strptime(current_task['kezdes'], '%Y-%m-%d %H:%M:%S')
    jelenlegi_ido = datetime.now()
    kulonbseg_ido = (jelenlegi_ido-kezdes).total_seconds()

    isProba = 1 if kapott_data['probalkozas'] else 0
    if (b:=current_task['settings']['task_type'] == 'beirasos') or current_task['settings']['task_type'] == 'kivalasztasos':
        PozicioHelyesSeg = ':'.join("1" if i else "0" for i in egy_szo.Pozicio_helyesseg)
        if current_task['feladat'].get('megadott_betűk', None) is not None:
            megadott_betu_index = ':'.join(str(szam) for szam, _ in current_task['feladat']['megadott_betűk'])
        else: megadott_betu_index = "-1"
        if b: db.add_alfeladat_beirasos(current_task['AlfeladatID'], current_task['feladat']['szo_id'], egy_szo.Megadott_feladat_index, egy_szo.Begepelt_szavak, kulonbseg_ido, PozicioHelyesSeg, egy_szo.Pontszam, isProba, megadott_betu_index)
        else: db.add_alfeladat_kivalasztasos(current_task['AlfeladatID'], current_task['feladat']['szo_id'], egy_szo.Megadott_feladat_index, egy_szo.Begepelt_szavak, PozicioHelyesSeg, egy_szo.Pontszam, kapott_data['variacioSzam'], kulonbseg_ido, isProba)
    elif current_task['settings']['task_type'] == 'parositasos':
        par_id = db.add_alfeladat_parositasos(current_task['AlfeladatID'], kapott_data['variacioSzam'], kulonbseg_ido, isProba)
        # parok mentése:
        for i in szavak_lista:
            PozicioHelyesSeg = ':'.join("1" if i else "0" for i in i.Pozicio_helyesseg)
            par_helyes = 1 if all(i.Pozicio_helyesseg) else 0
            db.add_parok(par_id, i.szo_id, i.Begepelt_szavak_parositasos, PozicioHelyesSeg, i.Pontszam, par_helyes)

    return jsonify(valasz_json)
'''
select * from AlfeladatBeirasos
select * from BeirasosFeladat

select * from AlfeladatKivalasztasos
select * from KivalasztasosFeladat
    
select * from Parok
select * from AlfeladatParositasos
select * from ParositasosFeladat

'''

if __name__ == "__main__":
        # Flask app indítása
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)