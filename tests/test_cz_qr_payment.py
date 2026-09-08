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
            "acc_number": "CZ65 0800 0000 1920 0014 5399",
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
            "acc_number": "CZ38 2010 0000 0024 0183 5999",
            "partner_id": self.partner.id,
        })
        self.assertEqual(account.cz_account_display, "2401835999/2010")

    def test_qr_method_available(self):
        methods = dict(self.env["res.partner.bank"].get_available_qr_methods_in_sequence())
        self.assertIn("qr_czk", methods)

    def test_spd_values(self):
        vals = self.bank_account._get_qr_vals(
            "qr_czk", 1500.0, self.czk, self.no_partner, "Objednávka č. 42", "202600005",
        )
        self.assertEqual(vals[0], "SPD*1.0")
        self.assertIn("ACC:CZ6508000000192000145399", vals)
        self.assertIn("AM:1500.00", vals)
        self.assertIn("CC:CZK", vals)
        self.assertIn("RN:Ranc Na Samotach", vals)
        self.assertIn("X-VS:202600005", vals)
        self.assertIn("MSG:Objednavka c. 42", vals)
        self.assertNotIn("PT:IP", vals)

    def test_spd_values_pos(self):
        vals = self.bank_account.with_context(is_online_qr=True)._get_qr_vals(
            "qr_czk", 0, self.czk, self.no_partner, "", "",
        )
        self.assertIn("PT:IP", vals)
        self.assertFalse([v for v in vals if v.startswith("AM:")])
        self.assertFalse([v for v in vals if v.startswith("X-VS:")])

    def test_qr_image(self):
        image = self.bank_account.build_qr_code_base64(
            1500.0, "Test", "202600005", self.czk, self.no_partner, "qr_czk", silent_errors=False,
        )
        self.assertTrue(image.startswith("data:image/png;base64,"))

    def test_foreign_iban_not_eligible(self):
        account = self.env["res.partner.bank"].create({
            "acc_number": "DE89 3704 0044 0532 0130 00",
            "partner_id": self.partner.id,
        })
        self.assertFalse(account.cz_account_display)
        self.assertTrue(account._get_error_messages_for_qr("qr_czk", self.no_partner, self.eur))
