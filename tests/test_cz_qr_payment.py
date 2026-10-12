# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCzQrPayment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Ranč Na Samotách"})
        # Vzorový IBAN z dokumentace ČNB: 19-2000145399/0800
        cls.bank_account = cls.env["res.partner.bank"].create({
            "account_number": "CZ65 0800 0000 1920 0014 5399",
            "partner_id": cls.partner.id,
        })
        cls.czk = cls.env.ref("base.CZK")
        cls.eur = cls.env.ref("base.EUR")
        cls.no_partner = cls.env["res.partner"]

    def test_fields_from_iban(self):
        self.assertEqual(self.bank_account.cz_bank_code, "0800")
        self.assertEqual(self.bank_account.cz_account_number, "19-2000145399")
        self.assertEqual(self.bank_account.cz_account_display, "19-2000145399/0800")

    def test_iban_without_prefix(self):
        account = self.env["res.partner.bank"].create({
            "account_number": "CZ38 2010 0000 0024 0183 5999",
            "partner_id": self.partner.id,
        })
        self.assertEqual(account.cz_account_display, "2401835999/2010")

    def test_qr_method_available(self):
        methods = dict(self.env["res.partner.bank"].get_available_qr_methods_in_sequence())
        self.assertIn("qr_czk", methods)

    def test_spd_values_invoice(self):
        """Faktura: ACC, AM, CC, X-VS; bez RN a MSG."""
        vals = self.bank_account._get_qr_vals(
            "qr_czk", 1500.0, self.czk, self.no_partner, "FA/2026/00005", "202600005",
        )
        self.assertEqual(
            vals,
            ["SPD*1.0", "ACC:CZ6508000000192000145399", "AM:1500.0", "CC:CZK", "X-VS:202600005"],
        )

    def test_spd_values_pos(self):
        """Pokladna: ACC, AM, CC, PT:IP, MSG v tomto pořadí, bez mezer a diakritiky."""
        vals = self.bank_account.with_context(is_online_qr=True)._get_qr_vals(
            "qr_czk", 123.5, self.czk, self.no_partner, "Order 26A-1-000042 A12", "",
        )
        self.assertEqual(
            vals,
            ["SPD*1.0", "ACC:CZ6508000000192000145399", "AM:123.5", "CC:CZK", "PT:IP", "MSG:Order26A-1-000042A12"],
        )

    def test_spd_values_pos_offline_default(self):
        """Výchozí QR pokladny bez částky a zprávy (offline záloha)."""
        vals = self.bank_account.with_context(is_online_qr=True)._get_qr_vals(
            "qr_czk", 0, self.czk, self.no_partner, "", "",
        )
        self.assertEqual(vals, ["SPD*1.0", "ACC:CZ6508000000192000145399", "CC:CZK", "PT:IP"])

    def test_spd_text_strips_spaces_and_diacritics(self):
        vals = self.bank_account.with_context(is_online_qr=True)._get_qr_vals(
            "qr_czk", 10, self.czk, self.no_partner, "Objednávka č. 42 * test", "",
        )
        self.assertIn("MSG:Objednavkac.42test", vals)

    def test_qr_image(self):
        image = self.bank_account.build_qr_code_base64(
            1500.0, "Test", "202600005", self.czk, self.no_partner, "qr_czk", silent_errors=False,
        )
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_foreign_iban_not_eligible(self):
        account = self.env["res.partner.bank"].create({
            "account_number": "DE89 3704 0044 0532 0130 00",
            "partner_id": self.partner.id,
        })
        self.assertFalse(account.cz_account_display)
        self.assertTrue(account._get_error_messages_for_qr("qr_czk", self.no_partner, self.eur))

    def test_no_bank_account(self):
        """Faktura s metodou qr_czk bez účtu příjemce: chybová zpráva, ne pád na ensure_one."""
        self.assertTrue(
            self.env["res.partner.bank"]._get_error_messages_for_qr("qr_czk", self.no_partner, self.czk)
        )

    def test_write_account_number_updates_cz_fields(self):
        """Změna IBAN přepočítá tuzemský tvar (Odoo 20: pole account_number)."""
        account = self.env["res.partner.bank"].create({
            "account_number": "CZ38 2010 0000 0024 0183 5999",
            "partner_id": self.partner.id,
        })
        account.account_number = "CZ02 2010 0000 0026 0156 9541"
        self.assertEqual(account.cz_account_display, "2601569541/2010")

    def test_account_type_iban(self):
        """Typ IBAN dodává v Odoo 20 modul account (dřív base_iban)."""
        self.assertEqual(self.bank_account.account_type, "iban")
        self.assertEqual(self.bank_account.sanitized_account_number, "CZ6508000000192000145399")

    def test_qr_value_pos(self):
        """Pokladna Odoo 20 bere surovou hodnotu (build_qr_code_value), obsah beze změny proti 19."""
        value = self.bank_account.with_context(is_online_qr=True).build_qr_code_value(
            123.5, "Order 26A-1-000042 A12", "", self.czk, self.no_partner, "qr_czk", silent_errors=False,
        )
        self.assertEqual(
            value,
            "SPD*1.0*ACC:CZ6508000000192000145399*AM:123.5*CC:CZK*PT:IP*MSG:Order26A-1-000042A12",
        )

    def test_fill_cz_account_numbers(self):
        """Funkce hooku a migrace doplní chybějící tuzemský tvar, vyplněný nepřepíše."""
        from odoo.addons.cz_qr_payment.hooks import fill_cz_account_numbers

        self.bank_account.write({"cz_account_number": False, "cz_bank_code": False})
        kept = self.env["res.partner.bank"].create({
            "account_number": "CZ38 2010 0000 0024 0183 5999",
            "partner_id": self.partner.id,
        })
        kept.cz_bank_code = "9999"
        # nesoulad s IBAN jen zaloguje (varování zachytí test, aby nebylo v logu běhu)
        with self.assertLogs("odoo.addons.cz_qr_payment.hooks", level="WARNING"):
            fill_cz_account_numbers(self.env)
        self.assertEqual(self.bank_account.cz_account_display, "19-2000145399/0800")
        self.assertEqual(kept.cz_bank_code, "9999")
