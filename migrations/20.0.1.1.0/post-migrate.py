# -*- coding: utf-8 -*-
"""Migrace 19 → 20: bankovní účty po zrušení ``res.bank`` a přejmenování polí účtu.

V Odoo 20 je banka text na účtu (``bank_name``, ``bank_bic``) a pole účtu jsou přejmenovaná
(``acc_number`` → ``account_number``, ``sanitized_acc_number`` → ``sanitized_account_number``,
``acc_holder_name`` → ``holder_name``). Převod má udělat migrační skript jádra (OpenUpgrade
``base``); tady se jen **doplní, co zůstalo prázdné**, protože bez ``sanitized_account_number``
nevznikne QR Platba (``ACC:``) a bez ``bank_name`` chybí na účtu název banky (Fio).

Staré sloupce a tabulku ``res_bank`` rámec OpenUpgrade nemaže, takže jdou přečíst. Nakonec se
z IBAN doplní tuzemský tvar (``cz_account_number``, ``cz_bank_code``), kde chybí. Skript je
idempotentní a nic vyplněného nepřepisuje.
"""
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.sql import column_exists, table_exists

_logger = logging.getLogger(__name__)

# (nový sloupec, starý sloupec) na res_partner_bank
RENAMED_COLUMNS = [
    ("account_number", "acc_number"),
    ("sanitized_account_number", "sanitized_acc_number"),
    ("holder_name", "acc_holder_name"),
]


def _fill_renamed_columns(cr):
    for new, old in RENAMED_COLUMNS:
        if not (column_exists(cr, "res_partner_bank", new) and column_exists(cr, "res_partner_bank", old)):
            continue
        cr.execute(
            f"""
            UPDATE res_partner_bank
               SET {new} = {old}
             WHERE ({new} IS NULL OR {new} = '')
               AND {old} IS NOT NULL AND {old} <> ''
            """
        )
        if cr.rowcount:
            _logger.info("cz_qr_payment: %s doplněno z %s u %s účtů", new, old, cr.rowcount)


def _fill_bank_from_res_bank(cr):
    """Název a BIC banky ze zrušeného ``res.bank`` (přes starý sloupec ``bank_id``)."""
    if not (
        table_exists(cr, "res_bank")
        and column_exists(cr, "res_partner_bank", "bank_id")
        and column_exists(cr, "res_partner_bank", "bank_name")
    ):
        return
    cr.execute(
        """
        UPDATE res_partner_bank pb
           SET bank_name = b.name
          FROM res_bank b
         WHERE pb.bank_id = b.id
           AND (pb.bank_name IS NULL OR pb.bank_name = '')
           AND b.name IS NOT NULL AND b.name <> ''
        """
    )
    if cr.rowcount:
        _logger.info("cz_qr_payment: název banky převzat z res_bank u %s účtů", cr.rowcount)
    if column_exists(cr, "res_partner_bank", "bank_bic") and column_exists(cr, "res_bank", "bic"):
        cr.execute(
            """
            UPDATE res_partner_bank pb
               SET bank_bic = upper(b.bic)
              FROM res_bank b
             WHERE pb.bank_id = b.id
               AND (pb.bank_bic IS NULL OR pb.bank_bic = '')
               AND b.bic IS NOT NULL AND b.bic <> ''
            """
        )
        if cr.rowcount:
            _logger.info("cz_qr_payment: BIC převzat z res_bank u %s účtů", cr.rowcount)


def migrate(cr, version):
    if not version:
        return
    _fill_renamed_columns(cr)
    _fill_bank_from_res_bank(cr)

    from odoo.addons.cz_qr_payment.hooks import fill_cz_account_numbers

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.partner.bank"].invalidate_model()
    fill_cz_account_numbers(env)
