# -*- coding: utf-8 -*-
{
    "name": "QR Platba CZ",
    "summary": "České QR kódy pro platbu převodem (formát SPD) na fakturách a v POS",
    "description": """
QR Platba CZ
============

Přidává metodu generování QR kódu ``qr_czk`` podle českého standardu
QR Platba (Short Payment Descriptor, https://qr-platba.cz). Metoda se
používá všude, kde Odoo QR kód pro platbu nabízí:

* na PDF faktury (nastavení Fakturace → QR kódy),
* v pokladně u platební metody typu „Bankovní aplikace (QR kód)“.

Na bankovním účtu doplňuje tuzemský tvar čísla účtu a kód banky, které
se automaticky odvozují z českého IBAN a tisknou na fakturu vedle IBAN.

Při instalaci převezme čísla účtů z modulu Origamis Base CZ, pokud je
nainstalovaný, a odpojí od něj záznamy bank, aby přežily jeho odinstalaci.
""",
    "version": "19.0.1.1.0",
    "category": "Accounting/Localizations",
    "author": "Matouš Čmelík",
    "website": "https://github.com/cmeldas/cz_qr_payment",
    "license": "LGPL-3",
    "depends": ["account", "base_iban"],
    "data": [
        "views/res_partner_bank_views.xml",
        "views/report_invoice.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
