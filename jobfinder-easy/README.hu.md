# JobFinder Easy – magyar útmutató

Ingyenes álláskereső segéd egy Google-táblázatban. Minden reggel átnézi az állásportálokat, egy ingyenes mesterséges intelligencia (MI) összeveti a hirdetéseket az önéletrajzoddal és a kívánságaiddal, és e-mailben elküldi a legjobb találatokat egy hozzájuk igazított önéletrajzzal.

- **Ingyenes:** csak egy Google-fiók és egy ingyenes MI-kulcs kell hozzá (ezt is a Google adja).
- **Nem kell semmit telepíteni, és programozni sem kell:** a Google gépein fut, a számítógéped akár ki is lehet kapcsolva.
- **Több állásportál:** LinkedIn, Profession.hu, NoFluffJobs és Jooble. Mindegyik egy-egy pipa, bármikor be- vagy kikapcsolhatod.
- **Magyarul vagy angolul:** a menü, a beállító ablak, a fülek, a beállítások és az e-mailek is magyarul jelennek meg.

*(English guide: [README.md](README.md))*

---

## Beállítás (kb. 10 perc)

1. **Nyisd meg a linket**, amit kaptál, és kattints a **Másolat készítése** gombra.
2. A saját példányodban kattints fent a **🔎 JobFinder** menüre (a „Súgó” mellett), majd a **▶ Beállítás** pontra.
   *Nincs ilyen menü? Töltsd újra az oldalt, és várj néhány másodpercet.*
   *Ha minden angolul jelenik meg, kattints a beállító ablak tetején a **Magyar** gombra.*
3. A Google engedélyt kér:
   - Válaszd ki a Google-fiókodat.
   - Ha azt írja, hogy a Google nem ellenőrizte az alkalmazást, kattints a **Speciális** (Advanced) linkre, majd a **JobFinder megnyitása (nem biztonságos)** linkre, végül az **Engedélyezés** (Allow) gombra.
   - Ez biztonságos: a program a táblázatod saját példányában van, és csak te futtatod.
4. Megnyílik a beállító ablak. Töltsd ki az 5 lépést:
   1. **Ingyenes MI-kulcs:** kattints a kék gombra, jelentkezz be, kattints a **Create API key** gombra, másold ki a kulcsot, és illeszd be.
   2. **Rólad:** név, e-mail cím, telefonszám, város.
   3. **Milyen munkát keresel:** munkakörök vesszővel elválasztva, hol (pl. „Budapest, Hungary”), és hány irodai napot vállalsz.
   4. **Állásportálok:** jelöld be, melyiken keressen.
   5. **Önéletrajzod:** nyisd meg az önéletrajzodat, nyomd meg a Ctrl+A, majd a Ctrl+C billentyűket, kattints a mezőbe, és nyomd meg a Ctrl+V billentyűket.
5. Kattints a **✅ Mentés és indítás**, majd a **🔎 Állások keresése most** gombra, hogy kipróbáld.

Ezután minden reggel 7 óra körül magától keres:
- A jó állásokról e-mailt kapsz.
- Minden átnézett állás megjelenik az **Állások** fülön (a füleket a képernyő alján találod). A **Státuszom** oszlopban követheted, hova jelentkeztél.
- A hozzád igazított önéletrajzok a Google Drive-ban, a **JobFinder önéletrajzok** mappában vannak.

## Ha változtatnál

- **Alapadatok** (név, munkakörök, helyszín, állásportálok, önéletrajz): nyisd meg újra: **🔎 JobFinder → ▶ Beállítás**.
- **Minden más** a **Beállítások** fülön van. Írd át a sárga cellákat; a legtöbbhöz lenyíló lista tartozik. Például:
  - minimális fizetés
  - kihagyandó szavak az állások címében
  - kerülendő cégek vagy iparágak
  - egyéb kívánságok egyszerű szavakkal, pl. „nincs éjszakai műszak”
  - mennyire legyen szigorú a pontozás
  - az önéletrajz nyelve
  - motivációs levél
  - az e-mailek nyelve
- **Szüneteltetés:** **🔎 JobFinder → Napi keresés leállítása**. Újraindítás: **▶ Beállítás**, majd **Mentés és indítás**.
- **Nyelv:** kattints a beállító ablak tetején az **English** vagy a **Magyar** gombra, vagy a Beállítások fül első sorában (**Nyelv / Language**) válassz. Minden válaszod megmarad. Utána töltsd újra az oldalt, hogy a menü is átváltson.

## Az állásportálok

| Portál | Mi kell hozzá | Megjegyzés |
| --- | --- | --- |
| LinkedIn | semmi | Világszerte. A LinkedIn néha egy időre letiltja az automatikus keresést. |
| Profession.hu | semmi | Magyarország. Az egész országban keres, ezért más városok állásai is megjelennek; ezekre az MI kevesebb pontot ad. |
| NoFluffJobs | semmi | Magyarország, Lengyelország, Csehország, Szlovákia. Csak a „Hol” mezőhöz közeli és az otthonról végezhető állásokat tartja meg. |
| Jooble | ingyenes kulcs | Világszerte, sok oldal állásait gyűjti össze. Kulcsot a [jooble.org/api/about](https://jooble.org/api/about) oldalon kérhetsz; e-mailben érkezik. Illeszd be a beállító ablakba. |

Ha egy portál nem válaszol, a JobFinder ezt felírja a *Kezdés* fülre, és a többin tovább keres.

## Jó tudni

- **Naponta kb. 10 állás:** a Google 6 perc után leállít minden futást, ezért naponta kb. 10 új állást néz át. A többi másnap kerül sorra.
- **Ingyenes MI-keret:** az ingyenes MI-kulcsnak napi kerete van. Ha elfogy, a JobFinder jelzi, és másnap folytatja.
- **Adatvédelem:** a kulcsaidat a Google-fiókod tárolja, nem a táblázat. Ne oszd meg a saját példányodat, mert benne van az önéletrajzod.
- **„Reggel” időzóna:** a reggeli időpont a beállító ismerősöd időzónája szerint számít. Ha másik időzónában vagy, kérd meg, hogy segítsen átállítani.
