# -*- coding: utf-8 -*-
"""Instalační hook: převzetí čísel účtů z modulu Origamis Base CZ."""
import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

ORIGAMIS_MODULE = "origamis_base_cz"


def post_init_hook(env):
    """Doplní tuzemská čísla účtů a odpojí banky od Origamis, je-li nainstalovaný.

    Pole ``cz_account_number`` má stejné jméno jako v Origamis, takže jeho
    hodnoty Odoo zachová samo. Kód banky měl Origamis na záznamu banky
    (``res.bank.cz_bank_code``), ten se překopíruje na bankovní účet.
    Chybějící údaje se odvodí z českého IBAN.
    """
    cr = env.cr
    bank_accounts = env["res.partner.bank"].with_context(active_test=False).search([])

    if column_exists(cr, "res_bank", "cz_bank_code"):
        cr.execute(
            """
            UPDATE res_partner_bank pb
               SET cz_bank_code = b.cz_bank_code
              FROM res_bank b
             WHERE pb.bank_id = b.id
               AND b.cz_bank_code IS NOT NULL AND b.cz_bank_code <> ''
               AND (pb.cz_bank_code IS NULL OR pb.cz_bank_code = '')
            """
        )
        _logger.info("cz_qr_payment: kód banky převzat z Origamis u %s účtů", cr.rowcount)
        bank_accounts.invalidate_recordset(["cz_bank_code"])

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
                bank_account.acc_number, bank_account.cz_bank_code, bank_code,
            )
        if not bank_account.cz_account_number:
            vals["cz_account_number"] = account_number
        elif bank_account.cz_account_number != account_number:
            _logger.warning(
                "cz_qr_payment: účet %s má číslo %s, IBAN říká %s; ponechávám původní",
                bank_account.acc_number, bank_account.cz_account_number, account_number,
            )
        if vals:
            bank_account.write(vals)

    origamis_installed = env["ir.module.module"].search_count(
        [("name", "=", ORIGAMIS_MODULE), ("state", "=", "installed")]
    )
    if origamis_installed:
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = %s AND model = 'res.bank'",
            (ORIGAMIS_MODULE,),
        )
        _logger.info(
            "cz_qr_payment: %s záznamů bank odpojeno od %s, aby přežily jeho odinstalaci",
            cr.rowcount, ORIGAMIS_MODULE,
        )

    for bank_account in bank_accounts:
        _logger.info(
            "cz_qr_payment: účet %s -> %s (%s)",
            bank_account.acc_number,
            bank_account.cz_account_display or "bez tuzemského tvaru",
            bank_account.bank_id.name or "bez banky",
        )
