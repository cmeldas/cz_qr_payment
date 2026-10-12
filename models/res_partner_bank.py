# -*- coding: utf-8 -*-
"""QR Platba (SPD) jako metoda generování QR kódu na res.partner.bank.

Specifikace formátu: https://qr-platba.cz/pro-vyvojare/specifikace-formatu/
"""
import re
import unicodedata

from odoo import _, api, fields, models


# Klíč metody je uložený v account.move.qr_code_method a pos.payment.method.qr_code_method,
# proto se nesmí měnit.
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
    """Očistí text pro hodnotu SPD: bez diakritiky, bez hvězdiček, konců řádků a mezer.

    Mezery se odstraňují úplně: některé
    bankovní aplikace berou zbytek řetězce za `MSG:` jako zprávu, a mezery
    v hodnotách jim vadí.
    """
    ascii_text = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return SPD_FORBIDDEN_RE.sub("", ascii_text).replace(" ", "")[:max_len]


def spd_amount(amount):
    """Částka jako ``str(round(amount, 2))``, tedy 123.5 nebo 1500.0."""
    return str(round(amount, 2))


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
        return cz_parts_from_iban(self.sanitized_account_number or self.account_number)

    @api.model
    def _cz_fill_vals_from_iban(self, vals):
        parts = cz_parts_from_iban(vals.get("account_number"))
        if not parts:
            return
        bank_code, account_number = parts
        if not vals.get("cz_bank_code"):
            vals["cz_bank_code"] = bank_code
        if not vals.get("cz_account_number"):
            vals["cz_account_number"] = account_number

    @api.onchange("account_number")
    def _onchange_account_number_cz(self):
        parts = cz_parts_from_iban(self.account_number)
        if parts:
            self.cz_bank_code, self.cz_account_number = parts

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._cz_fill_vals_from_iban(vals)
        return super().create(vals_list)

    def write(self, vals):
        if "account_number" in vals:
            self._cz_fill_vals_from_iban(vals)
        return super().write(vals)

    # ------------------------------------------------------------------
    # Metoda QR kódu ``qr_czk``
    # ------------------------------------------------------------------
    @api.model
    def _get_available_qr_methods(self):
        # Sekvence 25: před metodou „CZK QR“ z l10n_cz (50), která má jiný obsah
        # (RN, DT, X-VS z čísla faktury), a za SEPA QR (20), která se na CZK nehodí.
        methods = super()._get_available_qr_methods()
        methods.append((QR_METHOD, _("QR Platba (CZ)"), 25))
        return methods

    def _cz_qr_eligible(self):
        if not self:
            # faktura bez bankovního účtu příjemce: QR Platba není možná, ale nesmí spadnout
            return False
        self.ensure_one()
        return self.account_type == "iban" and (self.sanitized_account_number or "").startswith("CZ")

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == QR_METHOD:
            if not self._cz_qr_eligible():
                return _("QR Platba requires a Czech IBAN on the receiving bank account.")
            return None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """Řetězec SPD v pevném tvaru a pořadí.

        Pokladna (kontext ``is_online_qr``):  ``SPD*1.0*ACC*AM*CC*PT:IP*MSG``
        Faktura / platba:                     ``SPD*1.0*ACC*AM*CC*X-VS``
        Bez ``RN`` a bez mezer; ``PT:IP`` před ``MSG``, protože některé bankovní
        aplikace berou vše za ``MSG:`` jako zprávu a příznak okamžité platby by přehlédly.
        """
        if qr_method == QR_METHOD:
            vals = ["SPD*1.0", f"ACC:{self.sanitized_account_number}"]
            if amount:
                vals.append("AM:" + spd_amount(amount))
            vals.append(f"CC:{currency.name}")
            if self.env.context.get("is_online_qr"):
                # Pokladna: zákazník platí na místě, okamžitá platba a číslo objednávky ve zprávě.
                vals.append("PT:IP")
                message = spd_text(free_communication, 60)
                if message:
                    vals.append(f"MSG:{message}")
            else:
                variable_symbol = re.sub(r"\D", "", structured_communication or "")[:10]
                if variable_symbol:
                    vals.append(f"X-VS:{variable_symbol}")
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
