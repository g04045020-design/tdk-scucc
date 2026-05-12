import random
import hashlib
import json as _json
from adatfeldolgozas_class import Iranyitott_indexeles
from math import sqrt

hasznalt_fonetika_index = 8 # ha ténylg a jelentés van használva, 9 ha a Leírás

PONTOK = {
    "beirasos": {
        "parameterek": [0.8, 15, 60, -50],  # van megadott betű --> *= 1, nincs megadott betű --> *= "modosito"
        "modosito": 0.70 # 30% os enyhítés
    },
    "kivalasztasos": {
        "parameterek": [0.8, 17, 75, -18], # könnyű --> *= 1, nehéz --> *= "modosito"
        "modosito": 0.80 # 20% os enyhítés
    },
    "parositasos": {
        "parameterek": [0.8, 10, 70, -12], # könnyű --> *= 1, nehéz --> *= "modosito"
        "modosito": 0.60 # 40% os enyhítés
    }
}

def intervallumhoz_igazit(value, max_, min_):
    if value is None: return value
    return max_ if value >= max_ else min_ if value <= min_ else value

def lehetosegek_szama_modosito(pont:int, valasztek:int) -> float:
    if valasztek == 1: return pont
    scale = sqrt((valasztek - 4) / 11)
    if pont < 0: return pont + pont * scale * 0.5
    else: return pont - pont * scale * 0.2

def pontszamitas(szazalek, gorbe, min_pont, max_pont, hibatlan, szorzo) ->float:
    if szazalek == 100: return hibatlan*(2-szorzo)
    else: return (min_pont + (((99 - szazalek) / 99) ** gorbe) * (max_pont - min_pont)) * szorzo

def get_task_settings_hash(data) -> str:
    relevant = {
        'task_type': data.get('task_type'),
        'vocab_id': data.get('vocab_id'),
        'difficulty': data.get('difficulty', None),
        'options': data.get('options', {})
    }
    # A hash mindig ugyanaz ugyanarra a beállításra: kulcs szerint rendezett JSON
    s = _json.dumps(relevant, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def get_random_szo_mezo(szavak:list, mezo_index:int, n:int) -> list:
    tmp = []
    nem_lett_egyedi = 0
    if mezo_index == hasznalt_fonetika_index: # fonetika
        osszes_fonetika = [szo for szo in szavak if szo[8] not in (None, '', 'None')]
    while len(tmp) < n and nem_lett_egyedi < 1000:
        if mezo_index == hasznalt_fonetika_index:
            szo = random.choice(osszes_fonetika)
        else:
            szo = random.choice(szavak)

        if mezo_index == -1: # ekkor jelenés kell ami range(3, 8)
            jelentések = [szo[i] for i in range(3, 8) if isinstance(szo[i], str) and szo[i].strip()] # Csak a nem üres stringeket vesszük figyelembe (jelentések: index 3–7)
            if jelentések:
                t = random.choice(jelentések)
                if t not in tmp: tmp.append(t)
                else: nem_lett_egyedi += 1
        else:
            if szo[mezo_index] not in tmp:
                tmp.append(szo[mezo_index])
            else:
                nem_lett_egyedi += 1
    return tmp

def generate_feladat_szo_json(db, data, kapott_szo) -> dict: # kapott_szo -> (145, 3, 'apple', 'alma', '', '', '', '', 'aŁ$mm', '', '')

    def remove_words_from_list(szavak_lista, words_to_remove):
        words_to_remove_ids = {word[0] for word in words_to_remove}
        
        return [szo for szo in szavak_lista if szo[0] not in words_to_remove_ids]

    feladat = {}
    if data['task_type'] == 'kivalasztasos' or data['task_type'] == 'beirasos': # beirásos vagy kiválasztós
        idegen_szo = (kapott_szo[2],)
        jelentes = tuple(x for x in kapott_szo[3:8] if x) #csak azok a mezők kerünek bele ami nem üres
        hasznalt_fonetika_index = 9 if kapott_szo[8] == "" else 8
        fonetika = (kapott_szo[hasznalt_fonetika_index],) 
        # Elérhető típusok listája, arányokkal
        tipusok = []
        if fonetika[0] in (None, '', 'None'): # nincs fonetika
            tipusok += [1] # 50% idegen szó
            tipusok += [2] # 50% jelentés szó
        else:
            tipusok += [1]*4 # 40% idegen szó
            tipusok += [2]*4 # 40% jelentés
            tipusok += [3]*2 # 20% fonetika
        valasztott = random.choice(tipusok)

        if valasztott == 1: # idegenszó van megadva
            feladat = {
                "hasznalt_fonetika_index": hasznalt_fonetika_index,
                "feladat": "idegen_szo",
                "megadandó": ["jelentes"],
                "idegen_szo": idegen_szo,
                "jelentes": jelentes,
                "fonetika": fonetika,
                "szo_id": kapott_szo[0]
            }
            if db.van_e_legalabb_10_fonetikas_szo(data['vocab_id']): feladat['megadandó'].append("fonetika")
        elif valasztott == 2: # jelentés van megadva
            feladat = {
                "hasznalt_fonetika_index": hasznalt_fonetika_index,
                "feladat": "jelentes",
                "megadandó": ["idegen_szo"],
                "idegen_szo": idegen_szo,
                "jelentes": jelentes,
                "fonetika": fonetika,
                "szo_id": kapott_szo[0]
            }
            if db.van_e_legalabb_10_fonetikas_szo(data['vocab_id']): feladat['megadandó'].append("fonetika")
        elif valasztott == 3: # fonetika van megadva
            feladat = {
                "hasznalt_fonetika_index": hasznalt_fonetika_index,
                "feladat": "fonetika",
                "megadandó": ["idegen_szo", "jelentes"],
                "idegen_szo": idegen_szo,
                "jelentes": jelentes,
                "fonetika": fonetika,
                "szo_id": kapott_szo[0]
            }
        
        if data['task_type'] == 'beirasos' and data['options']["show_first_letter"]: # csak beírásos esetben lehet megadott betű
                betuk = [] # betű = (index, betű):int, char
                for kulcs in feladat['megadandó']:
                    for szo in feladat[kulcs]:
                        if szo == '': continue
                        index = random.randint(0, len(szo)-1)
                        betuk.append((index, szo[index]))
                feladat['megadott_betűk'] = betuk
        if data['task_type'] == 'kivalasztasos': # kiválasztásos feladat. nehézség és lehetőségek kötelező ekkor
                toltelek_szavak = remove_words_from_list(db.get_szavak_by_szokeszlet(data['vocab_id']), [kapott_szo]) # ebben biztos nincs benne a helyes szó.
                random.shuffle(toltelek_szavak)
                for kulcs in feladat['megadandó']:
                    mezo_index = -1
                    match kulcs:
                        case "idegen_szo": mezo_index = 2
                        case "jelentes": mezo_index = 3
                        case "fonetika": mezo_index = hasznalt_fonetika_index
                    
                    csokkentes = 1
                    van_helyes = True

                    # ['megkönnyít', 'zéró kibocsátás', 'ökoszisztéma szolgáltatás', 'átalakít', 'alkot'] -> ez egy darab
                    van_tobb_jelentes = not all(x in ('', None) for x in kapott_szo[4:7])
                    if kulcs == "jelentes" and van_tobb_jelentes:
                        feladat[kulcs+"_lehetőség"] = [] # ebben lesz benne a max 5 jelentéshez tartozó lehetőségek 
                        for i in range(3, 8): # kapott_szo[4:7]
                            if data['difficulty'] == "nehez":
                                esely = random.uniform(50, 85)  # Véletlen esély: 30%–55%
                                van_helyes = random.random() * 100 < esely
                                if not van_helyes: csokkentes = 0 # ha nehéz feladatnál nincs helyes nem kell csökkenteni
                                else: csokkentes = 1
                            
                            if kapott_szo[i] == "" or kapott_szo[i] == None: break
                            tmp = get_random_szo_mezo(toltelek_szavak, -1, data['options']['num_options']-csokkentes)
                            if van_helyes: tmp.append(kapott_szo[i]) # Csak nehéznél lehet bekerül a helyes válasz de lehet nem
                            random.shuffle(tmp)
                            feladat[kulcs+"_lehetőség"].append(tmp)
                            
                    else: # mivel itt nem lehet több jelentés így jó lesz ez.
                        if data['difficulty'] == "nehez":
                            esely = random.uniform(50, 85)  # Véletlen esély: 30%–55%
                            van_helyes = random.random() * 100 < esely
                            if not van_helyes: csokkentes = 0 # ha nehéz feladatnál nincs helyes nem kell csökkenteni
                        feladat[kulcs+"_lehetőség"] = get_random_szo_mezo(toltelek_szavak, mezo_index, data['options']['num_options']-csokkentes)
                        if van_helyes: feladat[kulcs+"_lehetőség"].append(kapott_szo[mezo_index]) # kapott_szo[mezo_index]  # Csak nehéznél lehet bekerül a helyes válasz de lehet nem
                        random.shuffle(feladat[kulcs+"_lehetőség"]) # megkeverjük a kilistázott lehetőségeket 
                        if kulcs == "jelentes":
                            tmp = feladat[kulcs+"_lehetőség"]
                            feladat[kulcs+"_lehetőség"] = [tmp]

    elif data['task_type'] == 'parositasos': # parositasos
        van_fonetika = True
        for i in kapott_szo: # itt a kapott_szo egy 5 elemű lista
            if i[8] == "": 
                van_fonetika = False
                break
        hasznalt_fonetika_index = 8 if van_fonetika else 9

        if data['difficulty'] == "konnyu":
            feladat = {
                "hasznalt_fonetika_index": hasznalt_fonetika_index,
                "megadandó": kapott_szo, # ekkor a kapott szó egy lista mely 5 szót tartalmaz
                "szo_id": [i[0] for i in kapott_szo],
                "idegen_szo_lehetőség": random.sample([i[2] for i in kapott_szo], k=len(kapott_szo)), # -> [str, str, ...]
                "jelentes_lehetőség": random.sample([i[3] for i in kapott_szo], k=len(kapott_szo)),
                "fonetika_lehetőség": random.sample([i[hasznalt_fonetika_index] for i in kapott_szo], k=len(kapott_szo))
            }
        else: # nehéz
            szavak = remove_words_from_list(db.get_szavak_by_szokeszlet(data['vocab_id']), kapott_szo) # a szókészlet azon szavai melyek nem szereplenek a megoldásban
            hibas_mezok = random.randint(1,5)
            toltelek_szavak = random.sample(szavak, k=hibas_mezok) # az ebben lévő szavak biztos nincsennek a megoldásban, és egymástól különbözőek

            elso = random.randint(0, hibas_mezok)
            masodik = random.randint(0, hibas_mezok - elso)
            harmadik = hibas_mezok - elso - masodik

            feladat = {
                "hasznalt_fonetika_index": hasznalt_fonetika_index,
                "megadandó": kapott_szo, # ekkor a kapott szó egy lista mely 5 szót tartalmaz
                "szo_id": [i[0] for i in kapott_szo],
                "idegen_szo_lehetőség": random.sample([i[2] for i in kapott_szo], k=len(kapott_szo) - elso), # -> [str, str, ...]
                "jelentes_lehetőség": random.sample([i[3] for i in kapott_szo], k=len(kapott_szo) - masodik),
                "fonetika_lehetőség": random.sample([i[hasznalt_fonetika_index] for i in kapott_szo], k=len(kapott_szo) - harmadik)
            }
            index = 0
            for _ in range(elso):
                feladat["idegen_szo_lehetőség"].append(toltelek_szavak[index][2]) # idegenszó
                index += 1
            for _ in range(masodik):
                feladat["jelentes_lehetőség"].append(toltelek_szavak[index][3]) # jelentés
                index += 1
            for _ in range(harmadik):
                feladat["fonetika_lehetőség"].append(toltelek_szavak[index][hasznalt_fonetika_index]) # fonetika itt lehet hogy a töltelék üres string
                index += 1
            # ismét megkeverjük a lehetőségeket.
            random.shuffle(feladat["idegen_szo_lehetőség"])
            random.shuffle(feladat["jelentes_lehetőség"])
            random.shuffle(feladat["fonetika_lehetőség"])
    return feladat