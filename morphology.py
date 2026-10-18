# -*- coding: utf-8 -*-
"""
Web arayüzü ile ChuvashFST motoru (chuvash_fst.py) arasındaki katman.

Motor yalnız yüzey biçimini üretir. Arayüzdeki ek zinciri
(Kök + İyelik + Çoğul + Hal) burada, motorun ara biçimleri son biçimle
karşılaştırılarak çıkarılır. Parçaların birleşimi her zaman son biçime eşittir;
bir ek yüzeyde kendi başına görünmüyorsa (ör. юлташ + у + на -> юлташна)
sonraki ekle birleşik gösterilir.
"""
import re

from chuvash_fst import ChuvashFST, ChuvashPhonology, UncountableNounError

_FST = ChuvashFST()

MAKS_UZUNLUK = 40

# (form kodu, motor kodu, kısa etiket, seçenek adı)
SAHISLAR = [
    ("1sg", "A1", "1.T.Ş", "1. Tekil şahıs (ben)"),
    ("2sg", "A2", "2.T.Ş", "2. Tekil şahıs (sen)"),
    ("3sg", "A3", "3.T.Ş", "3. Tekil şahıs (o)"),
    ("1pl", "B1", "1.Ç.Ş", "1. Çoğul şahıs (biz)"),
    ("2pl", "B2", "2.Ç.Ş", "2. Çoğul şahıs (siz)"),
    ("3pl", "B3", "3.Ç.Ş", "3. Çoğul şahıs (onlar)"),
]

# (motor kodu, Türkçe adı)
HALLER = [
    ("nominative", "Yalın"),
    ("genitive", "İlgi"),
    ("dative", "Yönelme"),
    ("locative", "Bulunma"),
    ("ablative", "Çıkma"),
    ("instrumental", "Vasıta"),
    ("abessive", "Yokluk"),
    ("causal", "Sebep"),
]

_SAHIS_MOTOR = {kod: motor for kod, motor, _, _ in SAHISLAR}
_SAHIS_ETIKET = {kod: etiket for kod, _, etiket, _ in SAHISLAR}
_HAL_ADI = dict(HALLER)

_COGUL_EKLERI = ("сем", "сен")          # eski hallerde сем -> сен
_KIRIL = re.compile(r"[а-яёӑӗӳҫ]")
_GECERLI = re.compile(r"^[а-яёӑӗӳҫ-]+$")


class AnalizHatasi(ValueError):
    """Kullanıcıya gösterilecek, girdiden kaynaklanan hata."""


def _ortak_onek(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _kok_dogrula(girdi):
    girdi = (girdi or "").strip()
    if not girdi:
        raise AnalizHatasi("Lütfen bir kök kelime girin.")
    if len(girdi) > MAKS_UZUNLUK:
        raise AnalizHatasi(f"Kelime çok uzun (en fazla {MAKS_UZUNLUK} harf).")
    if not _KIRIL.search(girdi.lower()):
        raise AnalizHatasi("Kelimeyi Kiril harfleriyle yazın (örn: лаша).")
    kok = ChuvashPhonology.normalize(girdi)
    if not _GECERLI.match(kok):
        raise AnalizHatasi("Kelimede Çuvaşça olmayan bir karakter var.")
    return kok


def _ayristir(kok, sahis, slot, cogul, hal, son):
    """Son biçimi Kök / İyelik / Sayı / Hal parçalarına böler."""
    asamalar = [("Kök", "Kök", "Kök", [kok, ChuvashPhonology.geminate(kok)])]
    if slot:
        asamalar.append(("İyelik", sahis, _SAHIS_ETIKET[sahis],
                         _FST.generate_variants(kok, slot)))
    if cogul:
        asamalar.append(("Sayı", "Çoğul", "Çoğul",
                         _FST.generate_variants(kok, slot, True)))
    if hal != "nominative":
        asamalar.append(("Hal", hal, _HAL_ADI[hal], None))

    parcalar, bas, bekleyen = [], 0, []
    for i, (tur, kod, etiket, adaylar) in enumerate(asamalar):
        if i == len(asamalar) - 1:
            bit = len(son)
        else:
            bit = max(_ortak_onek(a, son) for a in adaylar)
            if tur == "Kök" and bit * 2 < len(kok):
                bit = 0                                  # düzensiz gövde: атте -> ашшӗ
            if tur == "Sayı" and son[bas:bas + 3] in _COGUL_EKLERI:
                bit = bas + 3
        bekleyen.append((tur, kod, etiket))
        if bit <= bas:
            continue                                     # yüzeyde ayrı görünmüyor
        parcalar.append({
            "text": son[bas:bit],
            "code": "+".join(k for _, k, _ in bekleyen),
            "type": "+".join(t for t, _, _ in bekleyen),
            "label": " + ".join(e for _, _, e in bekleyen),
        })
        bas, bekleyen = bit, []
    if bekleyen:                                         # son ek boş kaldıysa öncekine katılır
        p = parcalar[-1]
        p["code"] += "".join("+" + k for _, k, _ in bekleyen)
        p["type"] += "".join("+" + t for t, _, _ in bekleyen)
        p["label"] += "".join(" + " + e for _, _, e in bekleyen)
    return parcalar


def _tablo(kok, slot, hal, cogul):
    try:
        _FST.generate_variants(kok, slot, True)
        sayilabilir = True
    except UncountableNounError:
        sayilabilir = False
    satirlar = []
    for kod, ad in HALLER:
        satirlar.append({
            "hal": kod,
            "ad": ad,
            "tekil": _FST.generate_variants(kok, slot, False, kod),
            "cogul": _FST.generate_variants(kok, slot, True, kod) if sayilabilir else None,
            "secili_tekil": kod == hal and not cogul,
            "secili_cogul": kod == hal and cogul,
        })
    return satirlar, sayilabilir


def analyze(root, person_code=None, is_plural=False, case="nominative"):
    """
    İsim çekimi yapar ve ek zincirini çıkarır.

    Args:
        root: kök kelime (Kiril; Latin ă ĕ ç ÿ da kabul edilir)
        person_code: '1sg', '2sg', '3sg', '1pl', '2pl', '3pl' ya da boş (iyeliksiz)
        is_plural: çoğul mu
        case: 'nominative', 'genitive', 'dative', 'locative', 'ablative',
              'instrumental', 'abessive', 'causal'

    Returns:
        dict: kok, parcalar, son, digerleri, tablo, sayilabilir
    Raises:
        AnalizHatasi: girdi geçersizse ya da sayılamayan isme çoğul istendiyse
    """
    kok = _kok_dogrula(root)
    if person_code and person_code not in _SAHIS_MOTOR:
        raise AnalizHatasi("Geçersiz şahıs seçimi.")
    if case not in _HAL_ADI:
        raise AnalizHatasi("Geçersiz hal seçimi.")
    slot = _SAHIS_MOTOR[person_code] if person_code else None

    tablo, sayilabilir = _tablo(kok, slot, case, is_plural)
    if is_plural and not sayilabilir:
        raise AnalizHatasi(f"«{kok}» sayılamayan bir isim; çoğul eki almaz. "
                           "Çoğul seçimini kaldırıp yeniden deneyin.")

    bicimler = _FST.generate_variants(kok, slot, is_plural, case)
    son = bicimler[0]
    return {
        "kok": kok,
        "parcalar": _ayristir(kok, person_code, slot, is_plural, case, son),
        "son": son,
        "digerleri": bicimler[1:],
        "tablo": tablo,
        "sayilabilir": sayilabilir,
    }
