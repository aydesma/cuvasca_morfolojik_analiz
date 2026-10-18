# -*- coding: utf-8 -*-
"""Flask uygulaması: form akışı, hata gösterimi ve kaçış."""
import json
import unittest

from app import app


class Uygulama(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def post(self, **form):
        r = self.client.post("/", data=form)
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)

    def test_ana_sayfa(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for alan in ('name="root"', 'name="sahis"', 'name="plural"', 'name="hal"'):
            self.assertIn(alan, html)
        self.assertIn("Yok (iyeliksiz)", html)
        self.assertNotIn("Analiz Sonucu", html)

    def test_cekim_ve_secimlerin_korunmasi(self):
        html = self.post(root="лаша", sahis="3sg", plural="", hal="dative")
        self.assertIn("лашине", html)
        self.assertIn("Analiz Sonucu", html)
        self.assertIn('value="3sg" selected', html)
        self.assertIn('value="dative" selected', html)
        self.assertIn("Tüm Haller", html)

    def test_cogul_ve_iyelik_ve_hal(self):
        html = self.post(root="лаша", sahis="1sg", plural="on", hal="genitive")
        self.assertIn("лашамсенӗн", html)
        self.assertIn('aria-pressed="true"', html)

    def test_iyeliksiz_yalin(self):
        html = self.post(root="кил", sahis="", plural="", hal="nominative")
        self.assertIn('id="finalWord"', html)
        self.assertIn('value="" selected', html)

    def test_tablo_kendi_kok_ve_iyeligini_tasir(self):
        html = self.post(root="Лаша", sahis="3sg", plural="", hal="dative")
        self.assertIn('data-root="лаша" data-sahis="3sg"', html)

    def test_tireli_bilesik_cekilir(self):
        html = self.post(root="Ача-Пӑча", sahis="3sg", plural="on", hal="dative")
        self.assertIn("Analiz Sonucu", html)
        self.assertIn("ача-пӑчисене", html)
        self.assertIn('data-root="ача-пӑча" data-sahis="3sg"', html)
        self.assertNotIn('role="alert"', html)

    def test_alternatif_bicim_gosterilir(self):
        html = self.post(root="сӗтел", sahis="", plural="", hal="locative")
        self.assertIn("сӗтелре", html)
        self.assertIn("Diğer biçim", html)
        self.assertIn("сӗтелте", html)

    def test_sayilamayan_cogul_hata_verir(self):
        html = self.post(root="сӗт", sahis="", plural="on", hal="nominative")
        self.assertIn('role="alert"', html)
        self.assertIn("sayılamayan", html)
        self.assertNotIn("Analiz Sonucu", html)

    def test_kurcalanmis_form_500_vermez(self):
        html = self.post(root="лаша", sahis="9xx", plural="", hal="vocative")
        self.assertIn('role="alert"', html)

    def test_zararli_girdi_kacislanir(self):
        yuk = '<img src=x onerror=alert(1)>'
        html = self.post(root=yuk, sahis="", plural="", hal="nominative")
        self.assertNotIn(yuk, html)
        self.assertIn("&lt;img", html)

    def test_gecmis_kaydi_json_ile_gomulur(self):
        html = self.post(root="лаша", sahis="2sg", plural="", hal="nominative")
        bas = html.index("const newEntry = ") + len("const newEntry = ")
        kayit = json.loads(html[bas:html.index(";\n", bas)])
        self.assertEqual(kayit["root"], "лаша")
        self.assertEqual(kayit["word"], "лашу")
        self.assertEqual([p["label"] for p in kayit["parts"]], ["Kök", "2.T.Ş"])


if __name__ == "__main__":
    unittest.main()
