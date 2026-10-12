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
""",
    "version": "20.0.1.2.0",
    "category": "Accounting/Localizations",
    "author": "Matouš Čmelík",
    "website": "https://github.com/cmeldas/cz_qr_payment",
    "license": "LGPL-3",
    # base_iban je v Odoo 20 součástí base/account (typ účtu IBAN dodává account)
    "depends": ["account"],
    "data": [
        "views/res_partner_bank_views.xml",
        "views/report_invoice.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
