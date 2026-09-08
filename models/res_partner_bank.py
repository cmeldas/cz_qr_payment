# -*- coding: utf-8 -*-
"""QR Platba (SPD) jako metoda generování QR kódu na res.partner.bank.

Specifikace formátu: https://qr-platba.cz/pro-vyvojare/specifikace-formatu/
"""
import re
import unicodedata

from odoo import _, api, fields, models
from odoo.tools import float_repr

# Stejný klíč jako používal modul Origamis, aby hodnoty uložené
# v account.move.qr_code_method a pos.payment.method.qr_code_method zůstaly platné.
QR_METHOD = "qr_czk"

# CZkk BBBB PPPP PPNN NNNN NNNN  (B = kód banky, P = předčíslí, N = číslo účtu)
CZ_IBAN_RE = re.compile(r"^CZ\d{2}(\d{4})(\d{6})(\d{10})$")
SPD_FORBIDDEN_RE = re.compile(r"[*\r\n\t]")


def cz_parts_from_iban(iban):
    """Rozloží český IBAN na dvojici (kód banky, tuzemské číslo účtu).

    Tuzemské číslo má tvar ``předčíslí-číslo`` bez úvodních nul, předčíslí
    se vynechá, když je nulové. Pro jiný než český IBAN vrací ``None``.
    """
    match = CZ_IBAN_RE.match((iban or "").replace(" ", "").upper())
    if not match:
        return None
    bank_code, prefix, number = match.groups()
    prefix = prefix.lstrip("0")
    number = number.lstrip("0") or "0"
    return bank_code, f"{prefix}-{number}" if prefix else number


def spd_text(value, max_len):
    """Očistí text pro hodnotu SPD: bez diakritiky, bez hvězdiček a konců řádků."""
    ascii_text = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return SPD_FORBIDDEN_RE.sub(" ", ascii_text).strip()[:max_len]


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    cz_account_number = fields.Char(
        string="Account Number (CZ)",
        size=17,
        help="Domestic Czech account number without the bank code, e.g. 19-2000145399. "
        "Filled automatically from a Czech IBAN.",
    )
    cz_bank_code = fields.Char(
        string="Bank Code (CZ)",
        size=4,
        # Origamis definuje stejnojmenné pole jako related na banku (neukládané).
        # Po dobu společné instalace musí vyhrát tato uložená varianta, proto explicitně.
        related=None,
        store=True,
        help="Four-digit Czech bank code, e.g. 2010. Filled automatically from a Czech IBAN.",
    )
    cz_account_display = fields.Char(
        string="Account Number (CZ) with Bank Code",
        compute="_compute_cz_account_display",
    )

    @api.depends("cz_account_number", "cz_bank_code")
    def _compute_cz_account_display(self):
        for bank in self:
            if bank.cz_account_number and bank.cz_bank_code:
                bank.cz_account_display = f"{bank.cz_account_number}/{bank.cz_bank_code}"
            else:
                bank.cz_account_display = False

    # ------------------------------------------------------------------
    # Odvození tuzemského tvaru z IBAN
    # ------------------------------------------------------------------
    def _cz_parts_from_iban(self):
        self.ensure_one()
        return cz_parts_from_iban(self.sanitized_acc_number or self.acc_number)

    @api.model
    def _cz_fill_vals_from_iban(self, vals):
        parts = cz_parts_from_iban(vals.get("acc_number"))
        if not parts:
            return
        bank_code, account_number = parts
        if not vals.get("cz_bank_code"):
            vals["cz_bank_code"] = bank_code
        if not vals.get("cz_account_number"):
            vals["cz_account_number"] = account_number

    @api.onchange("acc_number")
    def _onchange_acc_number_cz(self):
        parts = cz_parts_from_iban(self.acc_number)
        if parts:
            self.cz_bank_code, self.cz_account_number = parts

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._cz_fill_vals_from_iban(vals)
        return super().create(vals_list)

    def write(self, vals):
        if "acc_number" in vals:
            self._cz_fill_vals_from_iban(vals)
        return super().write(vals)

    # ------------------------------------------------------------------
    # Metoda QR kódu ``qr_czk``
    # ------------------------------------------------------------------
    @api.model
    def _get_available_qr_methods(self):
        # Po dobu společné instalace s Origamis nesmí být klíč v seznamu dvakrát.
        methods = [m for m in super()._get_available_qr_methods() if m[0] != QR_METHOD]
        methods.append((QR_METHOD, _("QR Platba (CZ)"), 25))
        return methods

    def _cz_qr_eligible(self):
        self.ensure_one()
        return self.acc_type == "iban" and (self.sanitized_acc_number or "").startswith("CZ")

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == QR_METHOD:
            if not self._cz_qr_eligible():
                return _("QR Platba requires a Czech IBAN on the receiving bank account.")
            return None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == QR_METHOD:
            vals = ["SPD*1.0", f"ACC:{self.sanitized_acc_number}"]
            if amount:
                vals.append("AM:" + float_repr(currency.round(amount), currency.decimal_places))
            vals.append(f"CC:{currency.name}")
            recipient = spd_text(self.acc_holder_name or self.partner_id.name, 35)
            if recipient:
                vals.append(f"RN:{recipient}")
            variable_symbol = re.sub(r"\D", "", structured_communication or "")[:10]
            if variable_symbol:
                vals.append(f"X-VS:{variable_symbol}")
            message = spd_text(free_communication, 60)
            if message:
                vals.append(f"MSG:{message}")
            if self.env.context.get("is_online_qr"):
                # Pokladna: zákazník platí na místě, požádat o okamžitou platbu.
                vals.append("PT:IP")
            return vals
        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == QR_METHOD:
            return {
                "barcode_type": "QR",
                "width": 128,
                "height": 128,
                "humanreadable": 1,
                "value": "*".join(self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
