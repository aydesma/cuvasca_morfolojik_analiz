# -*- coding: utf-8 -*-
"""Motorun kendi test setini (chuvash_fst._run_tests) unittest altında koşturur."""
import contextlib
import io
import unittest

import chuvash_fst


class MotorTestleri(unittest.TestCase):
    def test_motorun_kendi_kontrolleri_gecer(self):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            sayi = chuvash_fst._run_tests()
        self.assertGreaterEqual(sayi, 163)
        self.assertIn("Tüm testler geçti", cikti.getvalue())


if __name__ == "__main__":
    unittest.main()
