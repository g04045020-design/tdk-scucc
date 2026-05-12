from pathlib import Path
import json

a = []
folder = Path(r"C:\Users\User\Documents\GitHub\TDK-source\source\megosztott tematikus szókészlet mentés")

ID = 9
db = []
# Összes JSON beolvasása és összevonása
for file in folder.glob("*.json"):
    ID += 1
    db.append(str(file).split("\\")[-1])
    with open(file, "r", encoding="utf-8") as f:
        data = []
        for i in json.load(f)["szavak"]:
            print(i)
            i = {'szokeszlet_id': ID, **i}
            data.append(i)
        a += data

# Kiírás, minden elem külön sorba
with open(r"C:\Users\User\Documents\GitHub\TDK-source\source\megosztott tematikus szókészlet mentés\aa.j", "w", encoding="utf-8") as f:
    for item in a:
        f.write(json.dumps(item, ensure_ascii=False) + ",\n")

print()
print("db", db)