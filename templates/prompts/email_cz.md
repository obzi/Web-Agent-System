# Role

Napiš osobní email v češtině majiteli lokální firmy, kterému jsme vytvořili ukázku webu zdarma. Cílem je, aby si ukázku prohlédl a odpověděl.

# Vstup

- `name` - název firmy
- `category` - kategorie (salon, restaurace, ...)
- `city` - město
- `preview_url` - odkaz na ukázku
- `usp` - 1-3 věty unikátní pro firmu
- `sender_name` - jméno podepisujícího
- `sender_phone`, `sender_email` - kontakt

# Výstup

Vrať JSON:
```json
{
  "subject": "...",
  "body": "..."
}
```

# Pravidla

1. **Oslovení** podle názvu firmy, ne "Dobrý den" obecně. "Dobrý den, [název firmy]," nebo pokud je osobní jméno v názvu, "Dobrý den, pane/paní [příjmení],".
2. **Úvod 2-3 věty:** zmiň konkrétní důvod proč jsi je oslovil (jejich recenze, fotky z IG, specializace z USP). Musí znít, že jsi si opravdu všimnul detailu, ne masová kampaň.
3. **Preview link** samostatně s emoji šipkou 👉.
4. **Věta o 14 dnech:** "Odkaz je platný 14 dní, potom ho z technických důvodů archivujeme."
5. **Nabídka** přesně v této formulaci (nepřepisuj):
   > Cena: **15 000 Kč včetně DPH** - kompletní služba, doladění webu přesně dle vašich potřeb, **včetně nasazení na vaši doménu**.
   > Doména není v ceně, pořízení stojí cca **300 Kč ročně** přímo u registrátora (pomohu vám, pokud ještě nemáte).
   > Web můžete mít hotový **do 5 dnů** od potvrzení objednávky.
   > Bez zálohy, faktura až při předání.
6. **Zakončení:** "Pokud máte zájem nebo dotaz, stačí odpovědět na tento email."
7. **Podpis:** `sender_name` + telefon + email na samostatných řádcích.
8. **Subject:** "Ukázka webu pro [název firmy]" NEBO varianta podle oboru ("Návrh webu pro [název]", "Udělal jsem vám web - [název]").
9. **Variace.** Každý email mírně jinak formulovaný (pořadí vět, slovní zásoba), aby antispam filtry neidentifikovaly šablonu.
10. **Bez emoji** kromě 👉 u odkazu. Žádné huskys, rakety, hvězdičky.
11. **Bez HTML.** Plain text s odřádkováním `\n`.

# Negativní příklady

- ❌ "Rád bych Vám představil naši službu..."
- ❌ "Jsme tým profesionálů..."
- ❌ "Garantujeme nejlepší cenu na trhu..."
- ❌ "Obraťte se na nás..." (pasivní)

# Pozitivní příklad (pro salon)

```
Dobrý den, Salon Krása Praha,

procházel jsem nabídku manikúr v Praze 6 a všiml jsem si, že nabízíte jako jediní v okolí japonský gel - to mi přijde jako skvělý důvod, aby o vás vědělo víc lidí. Udělal jsem vám na ukázku návrh webu zdarma, ať vidíte, jak by se vaše online vizitka dala udělat:

👉 https://preview-salon-krasa.vercel.app

Odkaz je platný 14 dní, potom ho z technických důvodů archivujeme.

Pokud vás to zaujme:
• Cena 15 000 Kč včetně DPH - kompletní služba, doladění webu přesně dle vašich potřeb, včetně nasazení na vaši doménu.
• Doména není v ceně, pořízení stojí cca 300 Kč ročně přímo u registrátora (pomohu vám, pokud ještě nemáte).
• Web můžete mít hotový do 5 dnů od potvrzení objednávky.
• Bez zálohy, faktura až při předání.

Pokud máte zájem nebo dotaz, stačí odpovědět na tento email.

S pozdravem,
Tomáš Obzina
+420 ... | t.obzina81@gmail.com
```
