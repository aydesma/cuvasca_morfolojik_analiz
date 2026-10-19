# -*- coding: utf-8 -*-
"""Flask uygulaması: form akışı, hata gösterimi ve kaçış."""
import json
import re
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

    def sonuc(self, html):
        """Sonuç kutusundaki kelime (sayfanın başka yerindeki biçimlerle karışmasın)."""
        m = re.search(r'id="finalWord"[^>]*>\s*(.*?)\s*</p>', html, re.S)
        return m and m.group(1)

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
        self.assertEqual(self.sonuc(html), "лашине")
        self.assertIn("Analiz Sonucu", html)
        self.assertIn('value="3sg" selected', html)
        self.assertIn('value="dative" selected', html)
        self.assertIn("Paradigma", html)

    def test_cogul_ve_iyelik_ve_hal(self):
        html = self.post(root="лаша", sahis="1sg", plural="on", hal="genitive")
        self.assertEqual(self.sonuc(html), "лашамсенӗн")
        self.assertIn('aria-pressed="true"', html)

    def test_iyeliksiz_yalin(self):
        html = self.post(root="кил", sahis="", plural="", hal="nominative")
        self.assertIn('id="finalWord"', html)
        self.assertIn('value="" selected', html)

    def test_tablo_kok_ve_hucre_bilgisini_tasir(self):
        html = self.post(root="Лаша", sahis="3sg", plural="", hal="dative")
        self.assertIn('id="paradigma" data-root="лаша"', html)
        secili = re.findall(r'<button[^>]*aria-current="true"[^>]*>', html)
        self.assertEqual(len(secili), 1)
        self.assertIn('data-hal="dative" data-sahis="3sg" data-cogul="0"', secili[0])

    def test_paradigma_yalin_satiri_iyeliksiz_sutunu_icerir(self):
        # Esma'nın bildirdiği durum: ҫын + 3. tekil + yalın
        html = self.post(root="Çын", sahis="3sg", plural="", hal="nominative")

        def hucre(sahis):
            m = re.search(r'data-hal="nominative" data-sahis="%s" data-cogul="0"[^>]*>(.*?)</button>' % sahis,
                          html, re.S)
            return re.sub(r"<[^>]+>|\s+", "", m.group(1))

        self.assertEqual(hucre(""), "ҫын")
        self.assertEqual(hucre("3sg"), "ҫынӗ")
        self.assertRegex(html, r'Ø<span[^>]*>iyeliksiz</span>')
        self.assertRegex(html, r'id="finalWord"[^>]*>\s*ҫынӗ\s*<')

    def test_tireli_bilesik_cekilir(self):
        html = self.post(root="Ача-Пӑча", sahis="3sg", plural="on", hal="dative")
        self.assertIn("Analiz Sonucu", html)
        self.assertEqual(self.sonuc(html), "ача-пӑчисене")
        self.assertIn('id="paradigma" data-root="ача-пӑча"', html)
        self.assertNotIn('role="alert"', html)

    def test_alternatif_bicim_gosterilir(self):
        html = self.post(root="сӗтел", sahis="", plural="", hal="locative")
        self.assertEqual(self.sonuc(html), "сӗтелре")
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
        # aynı kelimeyi veren farklı seçimler (3sg / 3pl -> лаши) ayrı kayıt olabilsin
        self.assertEqual((kayit["sahis"], kayit["cogul"], kayit["hal"]), ("2sg", False, "nominative"))
        # eski motorun ürettiği geçmiş (eski anahtar) yeni sonuçlarla karışmaz
        self.assertIn("depo.sil('chuvashHistory');", html)
        self.assertNotIn("depo.oku('chuvashHistory')", html)

    def test_yalniz_bosluk_mesaj_verir(self):
        for bos in ("", "   ", " "):
            with self.subTest(bos=repr(bos)):
                html = self.post(root=bos, sahis="", plural="", hal="nominative")
                self.assertIn('role="alert"', html)
                self.assertIn("kök kelime girin", html)

    def test_kutuda_normalize_kok_gorunur(self):
        html = self.post(root="Çын", sahis="3sg", plural="", hal="nominative")
        self.assertIn('value="ҫын"', html)
        html = self.post(root="Çын1", sahis="", plural="", hal="nominative")     # hatada kullanıcının yazdığı kalır
        self.assertIn('value="Çын1"', html)
        self.assertIn("«1»", html)


if __name__ == "__main__":
    unittest.main()
