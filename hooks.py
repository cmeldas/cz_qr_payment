# -*- coding: utf-8 -*-
"""Instalační hook: doplnění tuzemského tvaru čísel účtů z IBAN."""
import logging

_logger = logging.getLogger(__name__)


def fill_cz_account_numbers(env):
    """Doplní tuzemské číslo účtu a kód banky z českého IBAN tam, kde chybí.

    Už vyplněné hodnoty nepřepisuje; když nesedí s IBAN, jen to zapíše do logu.
    Používá ho instalační hook i migrace na Odoo 20.
    """
    bank_accounts = env["res.partner.bank"].with_context(active_test=False).search([])
    for bank_account in bank_accounts:
        parts = bank_account._cz_parts_from_iban()
        if not parts:
            continue
        bank_code, account_number = parts
        vals = {}
        if not bank_account.cz_bank_code:
            vals["cz_bank_code"] = bank_code
        elif bank_account.cz_bank_code != bank_code:
            _logger.warning(
                "cz_qr_payment: účet %s má kód banky %s, IBAN říká %s; ponechávám původní",
                bank_account.account_number, bank_account.cz_bank_code, bank_code,
            )
        if not bank_account.cz_account_number:
            vals["cz_account_number"] = account_number
        elif bank_account.cz_account_number != account_number:
            _logger.warning(
                "cz_qr_payment: účet %s má číslo %s, IBAN říká %s; ponechávám původní",
                bank_account.account_number, bank_account.cz_account_number, account_number,
            )
        if vals:
            bank_account.write(vals)

    for bank_account in bank_accounts:
        _logger.info(
            "cz_qr_payment: účet %s -> %s (%s)",
            bank_account.account_number,
            bank_account.cz_account_display or "bez tuzemského tvaru",
            bank_account.bank_name or "bez banky",
        )


def post_init_hook(env):
    """Po instalaci doplní tuzemský tvar u existujících bankovních účtů."""
    fill_cz_account_numbers(env)
