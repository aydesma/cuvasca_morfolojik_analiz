# -*- coding: utf-8 -*-
"""Uyarlayıcı katman (morphology.py): ek zinciri, tablo ve girdi denetimi."""
import unittest

from chuvash_fst import ChuvashPhonology, generate_variants
from morphology import HALLER, SAHISLAR, AnalizHatasi, analyze

ORNEK_KOKLER = [
    # arayüzdeki "Örnek Getir" listesi
    "анне", "атте", "кукамай", "кукаçи", "шӑллӑм", "пичче", "аппа", "йӑмӑк",
    "куç", "пуç", "алӑ", "ура", "пӳрне", "шӑл", "хӑлха", "чӗре",
    "кил", "алӑк", "чӳрече", "сӗтел", "пӳлӗм", "сад", "телефон", "компьютер",
    "шыв", "ту", "юханшыв", "тинӗс", "йывӑç", "чечек", "çулçӑ", "пӗлӗт", "çумӑр",
    "лаша", "йытӑ", "кушак", "кайӑк", "сурӑх", "ӗне",
    "тӑван", "ял", "хула", "çул", "кун", "уйӑх", "вӑхӑт",
    "кӗнеке", "тетрадь", "карандаш", "ручка", "парта", "шкул", "класс",
    "учитель", "вӗренекен", "студент", "университет", "библиотека",
    "магазин", "пазар", "çӑкӑр", "сӗт", "çу", "аш", "пулӑ", "çимӗç",
    "улма", "çырла", "хӗвел", "çӑлтӑр", "çер", "уй", "вӑрман",
    # motor testlerindeki özel durumlar
    "сӑвӑ", "сӗлӗ", "пӗрчӗ", "пӑчкӑ", "ҫыру", "кӗрӳ", "шӑши", "турат", "тетрат",
    "портфель", "кукка", "мучи", "пальто", "ача", "тус", "юлташ", "хӗр",
    "кӑранташ", "товар", "чӗчӗк", "палат", "утӑ", "кӑнтӑр", "ӑслӑх", "ырлӗх",
]
SAHIS_KODLARI = [None] + [kod for kod, _, _, _ in SAHISLAR]
HAL_KODLARI = [kod for kod, _ in HALLER]
SIRA = {"Kök": 0, "İyelik": 1, "Sayı": 2, "Hal": 3}


def zincir(sonuc):
    return [(p["text"], p["label"]) for p in sonuc["parcalar"]]


class TumKombinasyonlar(unittest.TestCase):
    def test_parcalar_son_bicimi_olusturur_ve_motorla_ayni(self):
        sayi = 0
        for kok in ORNEK_KOKLER:
            for sahis in SAHIS_KODLARI:
                for cogul in (False, True):
                    for hal in HAL_KODLARI:
                        with self.subTest(kok=kok, sahis=sahis, cogul=cogul, hal=hal):
                            try:
                                s = analyze(kok, sahis, cogul, hal)
                            except AnalizHatasi as e:
                                self.assertTrue(cogul, f"tekilde hata: {e}")
                                self.assertIn("sayılamayan", str(e))
                                continue
                            slot = dict((k, m) for k, m, _, _ in SAHISLAR).get(sahis)
                            motor = generate_variants(kok, slot, cogul, hal)
                            self.assertEqual(s["son"], motor[0])
                            self.assertEqual(s["digerleri"], motor[1:])
                            self.assertEqual("".join(p["text"] for p in s["parcalar"]), s["son"])
                            self.assertTrue(all(p["text"] for p in s["parcalar"]))
                            turler = [t for p in s["parcalar"] for t in p["type"].split("+")]
                            beklenen = ["Kök"] + (["İyelik"] if sahis else []) \
                                + (["Sayı"] if cogul else []) + (["Hal"] if hal != "nominative" else [])
                            self.assertEqual(turler, beklenen)
                            self.assertEqual(turler, sorted(turler, key=SIRA.get))
                            sayi += 1
        self.assertGreater(sayi, 10000)


class EkZinciri(unittest.TestCase):
    def test_ornek_ayristirmalar(self):
        durumlar = [
            (("лаша", "2sg"), [("лаш", "Kök"), ("у", "2.T.Ş")]),
            (("лаша", "3sg", False, "dative"), [("лаш", "Kök"), ("и", "3.T.Ş"), ("не", "Yönelme")]),
            (("лаша", "1sg", True, "genitive"),
             [("лаша", "Kök"), ("м", "1.T.Ş"), ("сен", "Çoğul"), ("ӗн", "İlgi")]),
            (("тус", "2sg", True, "locative"),
             [("тус", "Kök"), ("у", "2.T.Ş"), ("сен", "Çoğul"), ("че", "Bulunma")]),
            (("ача", None, True, "instrumental"), [("ача", "Kök"), ("сем", "Çoğul"), ("пе", "Vasıta")]),
            (("сӑвӑ", "2sg"), [("сӑвв", "Kök"), ("у", "2.T.Ş")]),                # ikizleşme
            (("пулӑ", None, False, "genitive"), [("пуллӑ", "Kök"), ("н", "İlgi")]),
            (("ача",), [("ача", "Kök")]),
            # у/ӳ ile biten kök: gövde ӑв/ӗв kökte kalır
            (("ту", "1sg"), [("тӑв", "Kök"), ("ӑм", "1.T.Ş")]),
            (("ҫыру", None, False, "genitive"), [("ҫырӑв", "Kök"), ("ӑн", "İlgi")]),
            (("ҫыру", None, False, "locative"), [("ҫыру", "Kök"), ("ра", "Bulunma")]),
            (("кӗрӳ", "1pl"), [("кӗрӗв", "Kök"), ("ӗмӗр", "1.Ç.Ş")]),
        ]
        for args, beklenen in durumlar:
            with self.subTest(args=args):
                self.assertEqual(zincir(analyze(*args)), beklenen)

    def test_yuzeyde_gorunmeyen_ek_sonrakiyle_birlesir(self):
        self.assertEqual(zincir(analyze("юлташ", "2sg", False, "dative")),
                         [("юлташ", "Kök"), ("на", "2.T.Ş + Yönelme")])
        self.assertEqual(zincir(analyze("тетрадь", "3sg", False, "locative")),
                         [("тетрад", "Kök"), ("ӗнче", "3.T.Ş + Bulunma")])

    def test_duzensiz_govde_kokle_birlesir(self):
        self.assertEqual(zincir(analyze("атте", "3sg", False, "dative")),
                         [("ашшӗ", "Kök + 3.T.Ş"), ("не", "Yönelme")])
        self.assertEqual(zincir(analyze("анне", "3sg")), [("амӑшӗ", "Kök + 3.T.Ş")])

    def test_e_ile_biten_kok_dogru_cekilir(self):
        # eski motor "е"yi ünlü saymıyordu: аннеӑм, пиччеӗм
        self.assertEqual(analyze("анне", "1sg")["son"], "аннем")
        self.assertEqual(analyze("пичче", "3sg")["son"], "пиччи")

    def test_alternatif_bicimler(self):
        s = analyze("сӗтел", None, False, "locative")
        self.assertEqual((s["son"], s["digerleri"]), ("сӗтелре", ["сӗтелте"]))
        s = analyze("пальто", "3sg", False, "dative")
        self.assertEqual((s["son"], s["digerleri"]), ("пальтине", ["пальтовӗне"]))

    def test_latin_harfler_normalize_edilir(self):
        s = analyze("кукаçи", "1sg")
        self.assertEqual(s["kok"], "кукаҫи")
        self.assertEqual(s["son"], "кукаҫийӗм")
        self.assertEqual(analyze("ЛАША", "1sg")["son"], "лашам")


def hucre(sonuc, cogul, hal, sahis):
    tablo = next(t for t in sonuc["tablo"] if t["cogul"] == cogul)
    satir = next(r for r in tablo["satirlar"] if r["hal"] == hal)
    return next(h for h in satir["hucreler"] if h["sahis"] == (sahis or ""))


def secililer(sonuc):
    return [(t["cogul"], r["hal"], h["sahis"], h["bicimler"])
            for t in sonuc["tablo"] for r in t["satirlar"] for h in r["hucreler"] if h["secili"]]


class Tablo(unittest.TestCase):
    """Paradigma: tekil ve çoğul için 8 hal × (Ø + 6 iyelik); seçimden bağımsız."""

    def test_duzen(self):
        s = analyze("лаша", "1sg", True, "genitive")
        self.assertEqual([t["ad"] for t in s["tablo"]], ["Tekil", "Çoğul"])
        for t in s["tablo"]:
            self.assertEqual([r["hal"] for r in t["satirlar"]], HAL_KODLARI)
            for r in t["satirlar"]:
                self.assertEqual([h["sahis"] for h in r["hucreler"]], [""] + SAHIS_KODLARI[1:])
        self.assertEqual(hucre(s, False, "genitive", "1sg")["bicimler"], ["лашамӑн"])
        self.assertEqual(hucre(s, True, "genitive", "1sg")["bicimler"], ["лашамсенӗн"])
        self.assertEqual(secililer(s), [(True, "genitive", "1sg", ["лашамсенӗн"])])

    def test_iyelik_secimi_tabloyu_degistirmez(self):
        # Esma'nın bildirdiği durum: ҫын + 3. tekil + yalın; yalın satırının Ø sütunu iyeliksiz kalmalı
        s = analyze("Çын", "3sg", False, "nominative")
        self.assertEqual(hucre(s, False, "nominative", None)["bicimler"], ["ҫын"])
        self.assertEqual(hucre(s, False, "nominative", "3sg")["bicimler"], ["ҫынӗ"])
        self.assertEqual(secililer(s), [(False, "nominative", "3sg", ["ҫынӗ"])])
        iyeliksiz = analyze("ҫын")
        self.assertEqual([[h["bicimler"] for r in t["satirlar"] for h in r["hucreler"]] for t in s["tablo"]],
                         [[h["bicimler"] for r in t["satirlar"] for h in r["hucreler"]] for t in iyeliksiz["tablo"]])

    def test_sayilamayan_isimde_cogul_tablosu_yok(self):
        s = analyze("сӗт", None, False, "genitive")
        self.assertFalse(s["sayilabilir"])
        self.assertEqual([t["ad"] for t in s["tablo"]], ["Tekil"])
        self.assertEqual(s["son"], "сӗтӗн")


class SonucTabloTutarliligi(unittest.TestCase):
    """Sonuç kutusu, ek zinciri ve tablo her kombinasyonda birbirini tutar."""

    def test_secili_hucre_sonucla_ayni_ve_yalin_o_kok(self):
        for kok in ORNEK_KOKLER + ["ача-пӑча", "кукка-атте"]:
            for sahis in SAHIS_KODLARI:
                for cogul in (False, True):
                    for hal in HAL_KODLARI:
                        with self.subTest(kok=kok, sahis=sahis, cogul=cogul, hal=hal):
                            try:
                                s = analyze(kok, sahis, cogul, hal)
                            except AnalizHatasi:
                                continue
                            self.assertEqual(secililer(s), [(cogul, hal, sahis or "", [s["son"]] + s["digerleri"])])
                            self.assertEqual(hucre(s, False, "nominative", None)["bicimler"], [s["kok"]])

    def test_her_hucre_tiklaninca_kendi_bicimini_verir(self):
        for kok in ("лаша", "ҫын", "атте", "тетрадь", "пальто", "сӗт", "ача-пӑча"):
            s = analyze(kok)
            for t in s["tablo"]:
                for r in t["satirlar"]:
                    for h in r["hucreler"]:
                        with self.subTest(kok=kok, cogul=t["cogul"], hal=r["hal"], sahis=h["sahis"]):
                            tik = analyze(s["kok"], h["sahis"] or None, t["cogul"], r["hal"])
                            self.assertEqual([tik["son"]] + tik["digerleri"], h["bicimler"])


class TireliBilesik(unittest.TestCase):
    """Tireli bileşikte ekler son kelimeye göre gelir; öndeki kısım değişmez."""

    def test_tum_kombinasyonlar_son_kelimeyle_ayni(self):
        for kok in ("ача-пӑча", "юрӑ-сӑвӑ", "кукка-атте", "апат-ҫимӗҫ", "пӗр-пӗр-ача", "лаша-утӑ"):
            on, kelime = kok.rsplit("-", 1)
            on += "-"
            for sahis in SAHIS_KODLARI:
                for cogul in (False, True):
                    for hal in HAL_KODLARI:
                        with self.subTest(kok=kok, sahis=sahis, cogul=cogul, hal=hal):
                            try:
                                tek = analyze(kelime, sahis, cogul, hal)
                            except AnalizHatasi:
                                with self.assertRaises(AnalizHatasi):
                                    analyze(kok, sahis, cogul, hal)
                                continue
                            s = analyze(kok, sahis, cogul, hal)
                            self.assertEqual(s["kok"], kok)
                            self.assertEqual(s["son"], on + tek["son"])
                            self.assertEqual(s["digerleri"], [on + b for b in tek["digerleri"]])
                            self.assertEqual("".join(p["text"] for p in s["parcalar"]), s["son"])
                            self.assertEqual([p["label"] for p in s["parcalar"]],
                                             [p["label"] for p in tek["parcalar"]])
                            self.assertEqual(
                                [[h["bicimler"] for r in t["satirlar"] for h in r["hucreler"]] for t in s["tablo"]],
                                [[[on + b for b in h["bicimler"]] for r in t["satirlar"] for h in r["hucreler"]]
                                 for t in tek["tablo"]])

    def test_ornekler(self):
        self.assertEqual(zincir(analyze("ача-пӑча", "3sg", True, "dative")),
                         [("ача-пӑч", "Kök"), ("и", "3.T.Ş"), ("сен", "Çoğul"), ("е", "Yönelme")])
        self.assertEqual(zincir(analyze("кукка-атте", "3sg", False, "dative")),
                         [("кукка-ашшӗ", "Kök + 3.T.Ş"), ("не", "Yönelme")])
        self.assertEqual(analyze("юрӑ-сӑвӑ", "2sg")["son"], "юрӑ-сӑвву")

    def test_sayilamazlik_son_kelimeye_bakar(self):
        with self.assertRaisesRegex(AnalizHatasi, "«лаша-утӑ» sayılamayan"):
            analyze("лаша-утӑ", None, True)
        self.assertEqual(analyze("сӗт-ҫу", None, True)["son"], "сӗт-ҫусем")

    def test_unicode_tire_ve_latin_harf(self):
        self.assertEqual(analyze("ача‑пӑча", "1sg")["son"], "ача-пӑчам")
        self.assertEqual(analyze("ача‐пӑча")["kok"], "ача-пӑча")
        self.assertEqual(analyze("Ача-Пӑча", "1sg")["son"], "ача-пӑчам")


class GirdiDenetimi(unittest.TestCase):
    def hata(self, *args):
        with self.assertRaises(AnalizHatasi) as cm:
            analyze(*args)
        return str(cm.exception)

    def test_gecersiz_girdiler(self):
        self.assertIn("kök kelime", self.hata(""))
        self.assertIn("kök kelime", self.hata("   "))
        self.assertIn("Kiril", self.hata("kitap"))
        self.assertIn("Kiril", self.hata("123"))
        self.assertIn("Çuvaşça olmayan", self.hata("лаша1"))
        self.assertIn("Çuvaşça olmayan", self.hata("<script>лаша"))
        self.assertIn("çok uzun", self.hata("а" * 41))
        self.assertIn("şahıs", self.hata("лаша", "4sg"))
        self.assertIn("hal", self.hata("лаша", None, False, "vocative"))
        for kelime in ("ь", "ъ", "кщк"):
            with self.subTest(kelime=kelime):
                self.assertIn("ünlü yok", self.hata(kelime))
        for kelime in ("лаша-", "-а", "ача--пӑча"):
            with self.subTest(kelime=kelime):
                self.assertIn("Tire iki kelimenin", self.hata(kelime))
        self.assertIn("Çuvaşça olmayan", self.hata("ача - пӑча"))
        self.assertIn("Çuvaşça olmayan", self.hata("ача-1"))
        self.assertIn("ünlü yok", self.hata("кщк-лаша"))

    def test_ayrisik_ve_benzer_harfler_kabul_edilir(self):
        import unicodedata
        for kelime, beklenen in (("сӑвӑ", "сӑввӑм"), ("кукамай", "кукамайӑм"), ("кӗрӳ", "кӗрӗвӗм")):
            with self.subTest(kelime=kelime):
                ayrisik = unicodedata.normalize("NFD", kelime)
                self.assertNotEqual(ayrisik, kelime)
                self.assertEqual(analyze(ayrisik, "1sg")["son"], beklenen)
        self.assertEqual(analyze("с̧ыру")["kok"], "ҫыру")
        self.assertEqual(analyze("кӗрӱ")["kok"], "кӗрӳ")

    def test_sayilamayan_isme_cogul(self):
        for kok in ("сӗт", "утӑ", "ӑслӑх"):
            with self.subTest(kok=kok):
                self.assertIn("sayılamayan", self.hata(kok, None, True))

    def test_normalize_motorla_ayni(self):
        self.assertEqual(analyze(" Лаша ")["kok"], ChuvashPhonology.normalize(" Лаша "))


if __name__ == "__main__":
    unittest.main()
