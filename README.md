# QR Platba CZ (`cz_qr_payment`)

Odoo modul, který přidává české QR kódy pro platbu převodem ve formátu
**SPD** (Short Payment Descriptor, standard [QR Platba](https://qr-platba.cz)).

## Co dělá

- Registruje metodu QR kódu `qr_czk` na bankovním účtu (`res.partner.bank`).
  Odoo ji pak použije všude, kde QR kód pro platbu nabízí:
  - na PDF **faktury** (Fakturace → Nastavení → QR kódy),
  - v **pokladně** u platební metody typu „Bankovní aplikace (QR kód)“.
- Na bankovním účtu doplňuje **tuzemský tvar čísla účtu** a **kód banky**,
  odvozené z českého IBAN (např. `CZ65 0800 0000 1920 0014 5399` →
  `19-2000145399/0800`). Tuzemský tvar se tiskne na fakturu vedle IBAN.

Obsah QR kódu má záměrně **pevný tvar** (pořadí, bez `RN`, bez mezer, částka jako `123.5`):

- pokladna: `SPD*1.0*ACC:<IBAN>*AM:<částka>*CC:<měna>*PT:IP*MSG:<Order pos_reference tracking>`
  (`PT:IP` = okamžitá platba, ve zprávě číslo objednávky a pořadové číslo lístku, bez mezer),
- faktura: `SPD*1.0*ACC:<IBAN>*AM:<částka>*CC:<měna>*X-VS:<číslice platební reference>`.

`PT:IP` stojí před `MSG`, protože některé bankovní aplikace berou vše za `MSG:` jako zprávu
a příznak okamžité platby by jinak přehlédly.

## Kde se nastavuje číslo účtu pro QR

Modul žádné vlastní nastavení nemá. Číslo účtu v QR kódu je vždy **IBAN z pole „Číslo účtu"
bankovního účtu firmy** (`res.partner.bank`, pole `acc_number`); tuzemský tvar
(`Číslo účtu (CZ)`, `Kód banky (CZ)`) se z IBAN dopočítá sám (počítané uložené pole, bez instalačního
hooku) a slouží jen k zobrazení a tisku.
Který účet Odoo použije, určuje standardní nastavení Odoo:

**Bankovní účet firmy**
Kontakty → firma (Anežka Čmelíková) → záložka Fakturace / Účetnictví → Bankovní účty.
Do „Číslo účtu" patří český IBAN (např. `CZ38 2010 0000 0024 0183 5999`); banku (Fio) je dobré
vyplnit kvůli názvu. Bez českého IBAN metoda QR Platba není k dispozici.

**Bankovní deník** (Účetnictví/Fakturace → Konfigurace → Deníky → deník „Banka")
Pole „Číslo bankovního účtu" ukazuje na účet výše. Tento deník je zdrojem účtu pro pokladnu
a pro faktury, které mají nastavený způsob platby vedoucí na tento deník.

**Pokladna** (Pokladna → Konfigurace → Platební metody → metoda „QR")
Integrace = „Bankovní aplikace (QR kód)", Deník = bankovní deník „Banka", Formát QR kódu = „QR Platba (CZ)".
QR na účtence se generuje na účet z tohoto deníku. Jiný účet = jiný deník nebo jiný účet v deníku.

**Faktura**
Pole „Bankovní účet příjemce" (`partner_bank_id`) v hlavičce faktury. Odoo ho předvyplní účtem
z deníku preferovaného způsobu platby (faktury nebo zákazníka), jinak prvním aktivním bankovním účtem
firmy (přednost má účet ve stejné měně). Na konkrétní faktuře jde účet přepsat ručně.
Formát QR („QR Code Format" v záložce Další informace) se vybere automaticky: pro faktury v EUR SEPA,
pro CZK QR Platba (CZ). QR se tiskne, jen když je zapnuté Fakturace → Nastavení → Platby zákazníků → „QR kódy".

Aktuální stav na ranči: deník „Banka" → účet `CZ38 2010 0000 0024 0183 5999` = `2401835999/2010` (Fio),
používá ho pokladna i faktury.

## Testy

```
odoo -d <db> -i cz_qr_payment --test-enable --test-tags /cz_qr_payment --stop-after-init
```

## Licence

LGPL-3, autor Matouš Čmelík.
