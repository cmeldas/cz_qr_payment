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
bankovního účtu firmy** (`res.partner.bank`, pole `account_number`); tuzemský tvar
(`Číslo účtu (CZ)`, `Kód banky (CZ)`) se z IBAN doplní sám a slouží jen k zobrazení a tisku.
Který účet Odoo použije, určuje standardní nastavení Odoo:

**Bankovní účet firmy**
Kontakty → firma (Anežka Čmelíková) → záložka Fakturace / Účetnictví → Bankovní účty.
Do „Číslo účtu" patří český IBAN (např. `CZ38 2010 0000 0024 0183 5999`); název banky (Fio)
je dobré vyplnit kvůli zobrazení (v Odoo 20 textové pole název banky v záložce s údaji o bance,
číselník bank už není). Bez českého IBAN metoda QR Platba není k dispozici.

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

## Odoo 20

Port z větve `19.0`, verze `20.0.1.1.0`. Obsah QR kódu (řetězec SPD) je **beze změny**,
kontrolují to testy (`test_spd_values_*`, `test_qr_value_pos`).

Co se změnilo v Odoo 20 a v modulu:

- `res.bank` je zrušený, banka je text na účtu (`bank_name`, `bank_bic`); pole účtu jsou
  přejmenovaná: `acc_number` → `account_number`, `sanitized_acc_number` → `sanitized_account_number`,
  `acc_type` → `account_type`, `acc_holder_name` → `holder_name`. Modul i pohledy používají nové názvy.
- `base_iban` je sloučený do jádra (typ účtu `iban` a kontrola IBAN jsou v `account`
  a `odoo.tools.bank_account_number`), závislost je jen `account`.
- Bez instalačního hooku: `cz_account_number` a `cz_bank_code` jsou počítaná uložená pole z IBAN
  (Odoo je spočítá při instalaci i při změně čísla účtu, ruční hodnota zůstane u jiného než českého IBAN).
- `l10n_cz` má v Odoo 20 vlastní metodu „CZK QR“ (`czk_qr`, sekvence 50, jiný obsah: `RN`, `DT`,
  `X-VS` z čísla faktury, `PT:IP` i na faktuře). `qr_czk` má sekvenci 25, takže se při automatickém
  výběru na faktuře použije dřív; v pokladně zůstává uložená `qr_czk`. Na výběru v nastavení se
  objeví obě, správná je „QR Platba (CZ)“.
- Pokladna Odoo 20 si od serveru bere surovou hodnotu QR (`get_qr_code_value` →
  `build_qr_code_value`) a obrázek kreslí sama; řetězec je tentýž jako dřív.
- Faktura s metodou `qr_czk` bez bankovního účtu příjemce (např. když ho Odoo přepočtem vyprázdní)
  dřív při tisku spadla na `ensure_one`, teď ukáže srozumitelnou chybu „QR Platba requires a Czech IBAN…“.
- Ověřeno i na faktuře v Odoo 20 (s `l10n_cz`): PDF má vedle IBAN tuzemský tvar `(2401835999/2010)`,
  QR obsahuje `SPD*1.0*ACC:CZ3820100000002401835999*AM:1500.0*CC:CZK*X-VS:202600001`.

### Migrace dat 19 → 20

`migrations/20.0.1.1.0/post-migrate.py` (běží při `-u` z `19.0.1.1.0`, idempotentní, nic vyplněného
nepřepisuje):

1. Doplní `account_number`, `sanitized_account_number`, `holder_name` ze starých sloupců
   `acc_number`, `sanitized_acc_number`, `acc_holder_name`, pokud je migrace jádra nechala prázdné
   (bez `sanitized_account_number` by QR neměl `ACC:`).
2. Doplní `bank_name` a `bank_bic` ze zrušené tabulky `res_bank` přes starý sloupec `bank_id`
   (na produkci Fio banka, a.s. / `FIOBCZPP` u obou účtů).
3. Doplní z IBAN chybějící `cz_account_number` a `cz_bank_code` (na produkci jsou vyplněné).

Vlastní sloupce modulu (`cz_account_number`, `cz_bank_code` na `res_partner_bank`) zůstávají beze
změny. Hlavní převod polí a `res.bank` musí udělat migrace jádra (OpenUpgrade `base`); staré sloupce
a tabulku `res_bank` nesmí smazat dřív, než doběhne tento skript. Klíč `qr_czk` na fakturách
(`account_move.qr_code_method`) a na platební metodě pokladny platí dál.

## Testy

```
odoo -d <db> -i cz_qr_payment --test-enable --test-tags /cz_qr_payment --stop-after-init
```

V Docker stacku Odoo 20 (`odoo20/docker-compose.yml`) s vlastní databází a `--db-filter`.

## Licence

LGPL-3, autor Matouš Čmelík.
