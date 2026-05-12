
lehetosegek = ["Alma", "Körte"]
helyes_lehetosegek = ["Narancs", "Birs", "Pálesz", "alma"]
eredmeny = 100 if not any(any([helyes == i.lower() for i in lehetosegek]) for helyes in helyes_lehetosegek) else 0
print(f"nincs benne? {"nincs benne" if eredmeny == 100 else "benne van"}")