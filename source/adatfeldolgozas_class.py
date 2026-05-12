from difflib import SequenceMatcher

def intervallumhoz_igazit(value, max_, min_):
    if value is None: return value
    return max_ if value >= max_ else min_ if value <= min_ else value

def kicsi_contains(elem: str, kollekcio: list) -> bool:
    return any([elem == i.lower() for i in kollekcio])

class Szamlalo:
    def __init__(self):
        self._szam = 0
    
    @property
    def Szam(self):
        return self._szam
    
    @Szam.setter
    def Szam(self, value:int):
        self._szam = value

    def __iadd__(self, vaule:int):
        self._szam += vaule
        return self

class Szo_Elofordulas_Sor:
    STATIC_METET = 5
    def __init__(self, elemek=None):
        self.elemek = elemek or []

    def hozzaad(self, *elem):
        for i in range(len(elem)):
            self.elemek.append(elem[i])
            if len(self.elemek) > self.STATIC_METET:
                self.elemek.pop(0)

    @property
    def Lekerdez(self):
        return list(self.elemek)

    def to_dict(self):
        return {
            'elemek': self.elemek
        }

    @staticmethod
    def from_dict(data):
        return Szo_Elofordulas_Sor(data.get('elemek', None) if data is not None else None)

class Iranyitott_indexeles:
    def __init__(self, max_index) -> None:
        self.max_index = max_index
        self.index = 0
    def index_leptet(self):
        self.index += 1
        if self.index >= self.max_index:
            self.index = 0
    def reset(self):
        self.index = 0
    @property
    def Index(self) -> int:
        return self.index

class Szo_class: # vagy inkább feladat class
    def __init__(self, szo_adatList, fonetika_mezo_index) -> None:
        self.fonetika_mezo_index = fonetika_mezo_index
        self.megadott_feladat = None
        self.eredeti_sor_index = None

        self.valasz_idegen_szo = None
        self.valasz_jelentes_ek = None
        self.valasz_fonetika = None
        self.hasonlosag = None
        self.lehetosegek = {}

        self.szo_id, self.vocab_id, self.helyes_idegen_szo = szo_adatList[:3]
        self.helyes_jelentes_ek = [x for x in szo_adatList[3:8] if x not in ('', None)] # a '' és None értékek nem kerülnek bele
        self.helyes_fonetika = szo_adatList[self.fonetika_mezo_index]
        
        self.helyes_idegen_szo = self.helyes_idegen_szo.lower()
        if isinstance(self.helyes_jelentes_ek, list):
            for i in range(self.helyes_jelentes_ek.__len__()):
                self.helyes_jelentes_ek[i] = self.helyes_jelentes_ek[i].lower()
        else:
            self.helyes_jelentes_ek = self.helyes_jelentes_ek.lower()
        self.helyes_fonetika = self.helyes_fonetika.lower()

    @property
    def Begepelt_szavak_parositasos(self) -> tuple:
        return (self.valasz_idegen_szo, self.valasz_jelentes_ek, self.valasz_fonetika)

    @property
    def Begepelt_szavak(self) -> tuple:
        end = []
        if self.valasz_idegen_szo is not None: end.append(self.valasz_idegen_szo)
        if self.valasz_jelentes_ek is not None: end+=self.valasz_jelentes_ek
        if self.valasz_fonetika is not None: end.append(self.valasz_fonetika)
        return tuple(end)

    @property
    def Megadott_feladat_index(self) -> int:
        if self.megadott_feladat == 'idegen_szo':
            return 2
        elif self.megadott_feladat == "fonetika":
            return self.fonetika_mezo_index
        elif self.megadott_feladat == "jelentes": 
            return 3
        return -1

    @property
    def Helyes_adatok(self) -> dict:
        return {"idegen_szo": self.helyes_idegen_szo,
                "jelentes_ek": self.helyes_jelentes_ek,
                "fonetika": self.helyes_fonetika}

    @property
    def Hasonlosag(self) -> float:
        if self.megadott_feladat is not None: return self.hasonlosag_kivalaszt_beirasos()
        else: return self.hasonlosag_parositasos()

    @property
    def Pozicio_helyesseg(self) -> list:
        end = []
        if self.valasz_idegen_szo is not None:
            if self.valasz_idegen_szo != -1:
                end.append(self.helyes_idegen_szo == self.valasz_idegen_szo)
            else:
                end.append(not kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']))
        if self.megadott_feladat is not None: # ez lehet kiválasztásos is ahol a jelentések válasz egy lista
            for i, valasz in enumerate(self.valasz_jelentes_ek or []):
                if valasz != -1:
                    end.append(valasz in self.helyes_jelentes_ek)
                else:
                    end.append(not any(kicsi_contains(jel, self.lehetosegek['jelentes_lehetőség'][i]) for jel in self.helyes_jelentes_ek or []))
        else: 
            if self.valasz_jelentes_ek != -1:
                if self.valasz_jelentes_ek is not None and self.helyes_jelentes_ek is not None: end.append(self.valasz_jelentes_ek in self.helyes_jelentes_ek)
            else: 
                if self.helyes_jelentes_ek is not None:
                    end.append(not any(kicsi_contains(jel, self.lehetosegek['jelentes_lehetőség']) for jel in self.helyes_jelentes_ek))
        if self.valasz_fonetika is not None: 
            if self.valasz_fonetika != -1:
                end.append(self.helyes_fonetika == self.valasz_fonetika)
            else:
                 end.append(not kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) )
        return end

    def hasonlosag_kivalaszt_beirasos(self) -> float:
        def count_jelentesek_hasonlosag():
            if self.helyes_jelentes_ek is not None:
                return sum(max(self.szovegosszehasonlitas(helyes, valasz) for helyes in self.helyes_jelentes_ek)
                           if valasz != -1
            else (100 if not any(kicsi_contains(helyes, self.lehetosegek['jelentes_lehetőség'][i]) for helyes in self.helyes_jelentes_ek) else 0) for i, valasz in enumerate(self.valasz_jelentes_ek or []))
            return 0
        def count_valasz_fonetika_hasonlosag():
            if self.valasz_fonetika is not None:
                return self.szovegosszehasonlitas(self.helyes_fonetika, self.valasz_fonetika) if self.valasz_fonetika != -1 else 100 if not kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) else 0
            return 0
        def count_valasz_idegeszo_hasonlosag():
            if self.valasz_idegen_szo is not None:
                return self.szovegosszehasonlitas(self.helyes_idegen_szo, self.valasz_idegen_szo) if self.valasz_idegen_szo != -1 else 100 if not kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']) else 0
            return 0
        db = 0
        ossz = 0
        if self.megadott_feladat == "idegen_szo":
            if self.helyes_jelentes_ek is None or self.valasz_jelentes_ek is None: raise ValueError(f"Nem lehet None: {self.helyes_jelentes_ek, self.valasz_jelentes_ek} nem lehet!")
            
            db = len(self.valasz_jelentes_ek)
            ossz += count_jelentesek_hasonlosag()
            if self.valasz_fonetika is not None:
                db += 1
                ossz += count_valasz_fonetika_hasonlosag()
            
        elif self.megadott_feladat == "fonetika": 
            if self.helyes_jelentes_ek is None or self.valasz_jelentes_ek is None: raise ValueError(f"Nem lehet None: {self.helyes_jelentes_ek, self.valasz_jelentes_ek} nem lehet!")
            db = len(self.valasz_jelentes_ek)+1
            ossz += count_jelentesek_hasonlosag()
            ossz += count_valasz_idegeszo_hasonlosag()
        elif self.megadott_feladat == "jelentes": 
            db = 1
            ossz = count_valasz_idegeszo_hasonlosag()
            if self.valasz_fonetika is not None:
                db += 1
                ossz += count_valasz_fonetika_hasonlosag()
        else:
            raise ValueError(f"a megadott feladat: {self.megadott_feladat} nem lehet!")
        return round(ossz/db, 2)


    def hasonlosag_parositasos(self, valasz_tuple=None) -> float:
        if self.helyes_jelentes_ek is None: raise ValueError("Ilyen sem fog lenni!")

        if valasz_tuple is None:
            if self.valasz_idegen_szo is None or self.helyes_idegen_szo is None: 
                raise ValueError("Ilyen itt úgysem lesz de a fordítót boldoggá teszi a hibakezelés!")
            db = self.IsSetValasz
            ossz = []
            if self.lehetosegek.get('idegen_szo_lehetőség') is not None:
                ossz.append(100 if kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']) and self.valasz_idegen_szo == self.helyes_idegen_szo else 100 if not kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']) and self.valasz_idegen_szo == -1 else self.szovegosszehasonlitas(self.helyes_idegen_szo, self.valasz_idegen_szo))
            if self.lehetosegek.get('jelentes_lehetőség') is not None:  
                ossz.append(100 if any(kicsi_contains(jel, self.lehetosegek['jelentes_lehetőség']) for jel in self.helyes_jelentes_ek) and self.valasz_jelentes_ek in self.helyes_jelentes_ek else 100 if not kicsi_contains(self.helyes_jelentes_ek, self.lehetosegek['jelentes_lehetőség']) and self.valasz_jelentes_ek == -1 else 0)
            if self.lehetosegek.get('fonetika_lehetőség') is not None: 
                ossz.append(100 if kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) and self.valasz_fonetika == self.helyes_fonetika else 100 if not kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) and self.valasz_fonetika == -1 else self.szovegosszehasonlitas(self.helyes_fonetika, self.valasz_fonetika))
            print("hasonlosag_parositasos", ossz, sum(ossz), db)
            return round(sum(ossz)/len(ossz), 2) if db != 0 else 0.0
        else:
            ossz = sum([
                100 if kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']) and valasz_tuple[0] == self.helyes_idegen_szo else 100 if not kicsi_contains(self.helyes_idegen_szo, self.lehetosegek['idegen_szo_lehetőség']) and valasz_tuple[0] == -1 else 0,
                100 if any(kicsi_contains(jel, self.lehetosegek['jelentes_lehetőség']) for jel in self.helyes_jelentes_ek) and valasz_tuple[1] in self.helyes_jelentes_ek else 100 if not kicsi_contains(self.helyes_jelentes_ek, self.lehetosegek['jelentes_lehetőség']) and valasz_tuple[1] == -1 else 0,
                100 if kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) and valasz_tuple[2] == self.helyes_fonetika else 100 if not kicsi_contains(self.helyes_fonetika, self.lehetosegek['fonetika_lehetőség']) and valasz_tuple[2] == -1 else 0
            ])
            return round(ossz/3, 2)

    def convert_nyers_valasz(self, nyers_szo:tuple) -> tuple:
        max_lehetoseg = len(self.lehetosegek['idegen_szo_lehetőség'])-1
        return (
            self.lehetosegek['idegen_szo_lehetőség'][intervallumhoz_igazit(nyers_szo[0], max_lehetoseg, 0)].lower() if nyers_szo[0] != -1 else -1,
            self.lehetosegek['jelentes_lehetőség'][intervallumhoz_igazit(nyers_szo[1], max_lehetoseg, 0)].lower() if nyers_szo[1] != -1 else -1,
            self.lehetosegek['fonetika_lehetőség'][intervallumhoz_igazit(nyers_szo[2], max_lehetoseg, 0)].lower() if nyers_szo[2] != -1 else -1
        )

    @property
    def IsSetValasz(self) -> bool|int:
        db = sum(x is not None for x in [self.valasz_idegen_szo, self.valasz_jelentes_ek, self.valasz_fonetika])
        return db if db != 0 else False

    def add_valasz(self, adattipus, adat):
        match adattipus:
            case 'idegen_szo':
                self.valasz_idegen_szo = adat.lower()
            case 'jelentes':
                if isinstance(adat, list):
                    self.valasz_jelentes_ek = []
                    for i in range(adat.__len__()):
                        self.valasz_jelentes_ek.append(adat[i].lower())
                else:
                    self.valasz_jelentes_ek = adat.lower()
            case 'fonetika':
                self.valasz_fonetika = adat.lower()

    def add_valasz_tuple(self, valasz_tuple):
        self.valasz_idegen_szo, self.valasz_jelentes_ek, self.valasz_fonetika = valasz_tuple

    def add_valasz_dict(self, adat_dict):
        max_index = 0
        if len(self.lehetosegek.get('jelentes_lehetőség', [])) != 0: max_index = len(self.lehetosegek['jelentes_lehetőség'][0])-1
        elif len(self.lehetosegek.get('idegen_szo_lehetőség', [])) != 0: max_index = len(self.lehetosegek['idegen_szo_lehetőség'])-1
        elif len(self.lehetosegek.get('fonetika_lehetőség', [])) != 0: max_index = len(self.lehetosegek['fonetika_lehetőség'])-1

        if adat_dict.get('idegen_szo') is not None:
            self.valasz_idegen_szo = self.lehetosegek['idegen_szo_lehetőség'][intervallumhoz_igazit(adat_dict['idegen_szo'][0], max_index, 0)].lower() if adat_dict['idegen_szo'][0] != -1 else -1
        if adat_dict.get('jelentes') is not None:
            self.valasz_jelentes_ek = []
            for i,szo_jelentes in enumerate(adat_dict['jelentes']):
                tmp = [self.lehetosegek['jelentes_lehetőség'][i][intervallumhoz_igazit(szo_jelentes, max_index, 0)].lower() if szo_jelentes != -1 else -1]
                self.valasz_jelentes_ek.append(tmp if len(tmp) != 1 else tmp[0])
        if adat_dict.get('fonetika') is not None:
            self.valasz_fonetika = self.lehetosegek['fonetika_lehetőség'][intervallumhoz_igazit(adat_dict['fonetika'][0], max_index, 0)].lower() if adat_dict['fonetika'][0] != -1 else -1

    def szovegosszehasonlitas(self, s1, s2) -> float:
        if s1 is None or s2 is None:
            return 0.0
        return round(SequenceMatcher(None, str(s1), str(s2)).ratio() * 100, 2)

    def __str__(self) -> str:
        return f"ID: {self.szo_id}, SzókészletID: {self.vocab_id}: Idegenszó: <{self.helyes_idegen_szo} ? {self.valasz_idegen_szo}>- Jelentések: <{self.helyes_jelentes_ek} ? {self.valasz_jelentes_ek}>- Fonetika: <{self.helyes_fonetika} ? {self.valasz_fonetika}>\n"

    def __repr__(self) -> str:
        return self.__str__()

class SzoContainer:
    def __init__(self, szavak=None):
        self._dict = {}
        if szavak:
            for szo in szavak:
                self.append(szo)

    def append(self, szo: Szo_class):
        if not hasattr(szo, 'szo_id'):
            raise ValueError("A szó példánynak kell legyen szo_id attribútuma!")
        self._dict[szo.szo_id] = szo

    def valasz_hozzaad(self, nyers_valaszok):
        nyers_valaszok_szavankent = list(zip(nyers_valaszok['idegen_szo'], nyers_valaszok['jelentes'], nyers_valaszok['fonetika']))
        valaszok_szavankent = [list(self._dict.values())[0].convert_nyers_valasz(i) for i in nyers_valaszok_szavankent]

        for szo_index in range(5):
            legjobb_illeszkedes = None
            for i in self._dict.values():
                if not i.IsSetValasz:
                    if legjobb_illeszkedes is None:
                        legjobb_illeszkedes = i
                    elif legjobb_illeszkedes.hasonlosag_parositasos(valaszok_szavankent[szo_index]) < i.hasonlosag_parositasos(valaszok_szavankent[szo_index]): 
                        legjobb_illeszkedes = i
            if legjobb_illeszkedes is not None:
                legjobb_illeszkedes.add_valasz_tuple(valaszok_szavankent[szo_index])
                legjobb_illeszkedes.eredeti_sor_index = szo_index
            else:
                for i in self._dict.values(): print(i.Hasonlosag, i)
                raise Exception(f"Hiba a válaszokban: {nyers_valaszok} != 5")

    def __getitem__(self, szo_id):
        return self._dict[szo_id]

    def __setitem__(self, szo_id, szo):
        self._dict[szo_id] = szo

    def __contains__(self, szo_id):
        return szo_id in self._dict

    def __len__(self):
        return len(self._dict)

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def get_by_szoid(self, szo_id, default=None):
        return self._dict.get(szo_id, default)

    def __iter__(self):
        return iter(self._dict.values())
