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

Obsah QR kódu: `SPD*1.0*ACC:<IBAN>*AM:<částka>*CC:<měna>*RN:<příjemce>*X-VS:<variabilní symbol>*MSG:<zpráva>`.
Variabilní symbol se bere z číslic platební reference faktury. V pokladně se
přidává příznak okamžité platby `PT:IP`.

## Nahrazení modulu Origamis Base CZ

Modul je navržený jako náhrada za `origamis_base_cz` + `origamis_cz_qr_code_pos`
v místech, kde jde jen o QR platbu. Klíč metody `qr_czk` je záměrně stejný,
takže hodnoty uložené na fakturách a platebních metodách pokladny zůstávají platné.

Postup výměny:

1. Nainstalovat `cz_qr_payment` **při stále nainstalovaném Origamis**.
   Instalační hook překopíruje kód banky, doplní chybějící údaje z IBAN
   a odpojí záznamy bank od Origamis, aby přežily jeho odinstalaci.
   Průběh je v logu pod prefixem `cz_qr_payment:`.
2. U modulů závislých na `origamis_cz_qr_code_pos` změnit závislost na `cz_qr_payment`
   a aktualizovat je.
3. Odinstalovat `origamis_cz_qr_code_pos` a potom `origamis_base_cz`.

## Testy

```
odoo -d <db> -i cz_qr_payment --test-enable --test-tags /cz_qr_payment --stop-after-init
```

## Licence

LGPL-3, autor Matouš Čmelík.
