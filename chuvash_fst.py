#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChuvashFST: Çuvaşça iyelik + çoğul + 8 hal (padej) üretici.

Sıra: kök + iyelik + çoğul + hal

Kullanım:
    from chuvash_fst import generate_word
    generate_word("лаша", poss="A1", is_plural=True, case="genitive")  # лашамсенӗн
    generate_word("тетрадь", poss="A3", case="locative")               # тетрадӗнче

İyelik kodları: A1/A2/A3 = 1./2./3. tekil, B1/B2/B3 = 1./2./3. çoğul.
Hal adları: nominative, genitive, dative, locative, ablative (ESKİ);
            instrumental, abessive, causal (YENİ). A1..A8 ve Türkçe adlar da kabul edilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

PossSpec = Union[None, str, Tuple[int, str]]


class UncountableNounError(ValueError):
    """Sayılamayan/soyut/yön bildiren sözcüğe çoğul eki getirilmeye çalışıldı."""


# ----------------------------------------------------------------------------
# 1) Sesbilgisi
# ----------------------------------------------------------------------------
class ChuvashPhonology:
    """Ses uyumu, hece sayımı, ikizleşme ve yazım normalizasyonu."""

    # о: Rusça alıntılarda görülür; kalın kabul edilir.
    BACK_VOWELS = frozenset("аӑыуо")
    FRONT_VOWELS = frozenset("эӗиӳе")
    VOWELS = BACK_VOWELS | FRONT_VOWELS
    CONSONANTS = frozenset("йцкнгшщзхфвпрлджячсмтбюь")

    _NORM = str.maketrans({
        "ă": "ӑ", "ĕ": "ӗ", "ç": "ҫ", "ÿ": "ӳ",
        "a": "а", "e": "е", "c": "с", "o": "о", "p": "р", "x": "х",
        "y": "у", "k": "к", "m": "м", "t": "т", "b": "в", "i": "и",
    })

    @classmethod
    def normalize(cls, word: str) -> str:
        return word.strip().lower().translate(cls._NORM)

    @classmethod
    def syllable_count(cls, word: str) -> int:
        return sum(1 for ch in word if ch in cls.VOWELS)

    @classmethod
    def harmony(cls, word: str, soft_sign_front: bool = False) -> str:
        """'back' / 'front'. Son ünlüye bakılır; ünlü yoksa 'back'."""
        if soft_sign_front and word.endswith("ь"):
            return "front"
        for ch in reversed(word):
            if ch in cls.BACK_VOWELS:
                return "back"
            if ch in cls.FRONT_VOWELS:
                return "front"
        return "back"

    @classmethod
    def geminate(cls, word: str) -> str:
        """
        ӑ/ӗ ile biten, 2 heceli, öncesinde TEK ünsüz olan sözcüklerde ünsüzü
        ikizleştirir (сӑвӑ -> сӑввӑ). 3 hece / çift ünsüz: değişmez.
        """
        if (word and word[-1] in "ӑӗ"
                and cls.syllable_count(word) == 2
                and len(word) >= 3
                and word[-2] in cls.CONSONANTS
                and word[-3] in cls.VOWELS):
            return word[:-1] + word[-2] + word[-1]
        return word


# ----------------------------------------------------------------------------
# 2) Gövde (iyelikli biçim + üretim sırasında gereken bilgiler)
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Stem:
    surface: str                      # yüzey gövde (kök + iyelik)
    root: str                         # iyeliksiz kök
    slot: Optional[str]               # A1..B3 veya None (iyeliksiz)
    revert: Optional[str] = None      # т/д -> ч değişimi olduysa geri dönüş gövdesi


# ----------------------------------------------------------------------------
# 3) Ana sınıf
# ----------------------------------------------------------------------------
class ChuvashFST:
    SLOTS = ("A1", "A2", "A3", "B1", "B2", "B3")
    _TUPLE_SLOTS = {(1, "sg"): "A1", (2, "sg"): "A2", (3, "sg"): "A3",
                    (1, "pl"): "B1", (2, "pl"): "B2", (3, "pl"): "B3"}

    OLD_CASES = ("nominative", "genitive", "dative", "locative", "ablative")
    NEW_CASES = ("instrumental", "abessive", "causal")
    CASES = OLD_CASES + NEW_CASES

    _CASE_ALIASES = {
        "nominative": ("nom", "a1", "yalın", "yalin", "тӗп"),
        "genitive": ("gen", "a2", "ilgi", "камӑнлӑх"),
        "dative": ("dat", "a3", "yönelme", "yonelme", "пару"),
        "locative": ("loc", "a4", "bulunma", "вырӑн"),
        "ablative": ("abl", "a5", "çıkma", "cikma", "туху"),
        "instrumental": ("ins", "a6", "vasıta", "vasita", "пӗрлӗлӗх"),
        "abessive": ("abe", "a7", "yokluk", "ҫуклӑх"),
        "causal": ("cau", "a8", "sebep", "пирки"),
    }

    CH_SHIFT_ENDINGS = ("дь", "ть", "д", "т")   # 3. şahısta -> чӗ

    KINSHIP_THIRD: Dict[str, str] = {            # 3. şahıs -ӑшӗ/-ӗшӗ
        "кукка": "куккӑшӗ", "аппа": "аппӑшӗ", "мучи": "мучӑшӗ",
    }
    IRREGULAR_THIRD: Dict[str, str] = {          # düzensizler
        "атте": "ашшӗ", "анне": "амӑшӗ",
    }

    UNCOUNTABLE_WORDS: Set[str] = {"сӗт", "утӑ", "кӑнтӑр"}
    ABSTRACT_SUFFIXES = ("лӑх", "лӗх")

    def __init__(self, soft_sign_front: bool = False,
                 extra_kinship: Optional[Dict[str, str]] = None,
                 extra_uncountable: Iterable[str] = ()) -> None:
        """
        soft_sign_front: True ise ь ile biten sözcükler ince ek alır.
        extra_kinship: {kök: 3. şahıs biçimi}
        extra_uncountable: çoğul alamayan ek sözcükler
        """
        self.soft_sign_front = soft_sign_front
        self.phon = ChuvashPhonology
        self.kinship: Dict[str, str] = {}
        for k, v in {**self.KINSHIP_THIRD, **self.IRREGULAR_THIRD, **(extra_kinship or {})}.items():
            self.add_kinship(k, v)
        self.uncountable: Set[str] = {self.phon.normalize(w) for w in self.UNCOUNTABLE_WORDS}
        for w in extra_uncountable:
            self.add_uncountable(w)
        self._case_map = {a: c for c, al in self._CASE_ALIASES.items() for a in (c, *al)}

    def add_kinship(self, root: str, third_person_form: str) -> None:
        self.kinship[self.phon.normalize(root)] = self.phon.normalize(third_person_form)

    def add_uncountable(self, word: str) -> None:
        self.uncountable.add(self.phon.normalize(word))

    # ---- küçük yardımcılar -------------------------------------------------
    def _h(self, word: str) -> str:
        return self.phon.harmony(word, self.soft_sign_front)

    @staticmethod
    def _pick(h: str, back: str, front: str) -> str:
        return back if h == "back" else front

    @staticmethod
    def _ending_class(word: str) -> str:
        last = word[-1]
        if last in "аео":
            return "ae"
        if last in "ӑӗ":
            return "ye"
        if last in "уӳ":
            return "uu"
        if last == "и":
            return "i"
        return "cons"

    @staticmethod
    def _uu_stem(root: str) -> str:
        return root[:-1] + ("ӑв" if root[-1] == "у" else "ӗв")

    def _is_uncountable(self, root: str) -> bool:
        return root in self.uncountable or root.endswith(self.ABSTRACT_SUFFIXES)

    # ---- girdi çözümleme -----------------------------------------------------
    def _parse_case(self, case: str) -> str:
        key = str(case).strip().lower()
        if key not in self._case_map:
            raise ValueError(f"Bilinmeyen hal: {case!r}")
        return self._case_map[key]

    def _parse_poss(self, poss: PossSpec) -> Optional[str]:
        if poss is None:
            return None
        if isinstance(poss, tuple) and poss in self._TUPLE_SLOTS:
            return self._TUPLE_SLOTS[poss]
        if isinstance(poss, str) and poss.strip().upper() in self.SLOTS:
            return poss.strip().upper()
        raise ValueError(f"Geçersiz iyelik: {poss!r} (A1..A3, B1..B3)")

    # ---- İYELİK ---------------------------------------------------------------
    def _consonant_final(self, stem: str, slot: str, allow_shift: bool = True) -> str:
        """Ünsüzle biten gövde + iyelik. Sondaki ь ünlü başlı ekten önce düşer."""
        h = self._h(stem)
        core = stem[:-1] if stem.endswith("ь") else stem
        if slot == "A1":
            return core + self._pick(h, "ӑм", "ӗм")
        if slot == "A2":
            return core + self._pick(h, "у", "ӳ")
        if slot == "B1":
            return core + self._pick(h, "ӑмӑр", "ӗмӗр")
        if slot == "B2":
            return core + self._pick(h, "ӑр", "ӗр")
        if allow_shift:                              # A3/B3: т, ть, д, дь -> ч
            for e in self.CH_SHIFT_ENDINGS:
                if stem.endswith(e):
                    return stem[:-len(e)] + "чӗ"
        return core + "ӗ"

    def _vowel_ae(self, root: str, slot: str) -> str:
        h, base = self._h(root), root[:-1]
        return {"A1": root + "м",
                "A2": base + self._pick(h, "у", "ӳ"),
                "A3": base + "и",
                "B1": root + self._pick(h, "мӑр", "мӗр"),
                "B2": base + self._pick(h, "ӑр", "ӗр"),
                "B3": base + "и"}[slot]

    def _vowel_ye(self, root: str, slot: str) -> str:
        s = self.phon.geminate(root)
        h, base = self._h(s), s[:-1]
        return {"A1": s + "м",
                "A2": base + self._pick(h, "у", "ӳ"),
                "A3": base + "и",
                "B1": s + self._pick(h, "мӑр", "мӗр"),
                "B2": s + "р",
                "B3": base + "и"}[slot]

    def _possessive_stems(self, root: str, slot: Optional[str]) -> List[Stem]:
        if slot is None:
            return [Stem(root, root, None)]
        third = slot in ("A3", "B3")
        if third and root in self.kinship:                       # İstisna: akrabalık
            return [Stem(self.kinship[root], root, slot)]
        kind = self._ending_class(root)
        if kind == "cons":
            surface = self._consonant_final(root, slot)
            revert = None
            if third and any(root.endswith(e) for e in self.CH_SHIFT_ENDINGS):
                revert = self._consonant_final(root, slot, allow_shift=False)
            return [Stem(surface, root, slot, revert)]
        if kind == "ae":
            stems = [Stem(self._vowel_ae(root, slot), root, slot)]
            if third and root.endswith("о"):                     # пальто -> пальти / пальтовӗ
                stems.append(Stem(root + "вӗ", root, slot))
            return stems
        if kind == "ye":
            return [Stem(self._vowel_ye(root, slot), root, slot)]
        if kind == "uu":
            return [Stem(self._consonant_final(self._uu_stem(root), slot), root, slot)]
        return [Stem(self._consonant_final(root + "й", slot), root, slot)]

    # ---- HAL -----------------------------------------------------------------
    def _new_suffix(self, stem: str, case: str) -> str:
        h = self._h(stem)
        return {"instrumental": self._pick(h, "па", "пе"),
                "abessive": self._pick(h, "сӑр", "сӗр"),
                "causal": self._pick(h, "шӑн", "шӗн")}[case]

    def _locative(self, stem: str, ablative: bool) -> List[str]:
        n = "н" if ablative else ""
        h = self._h(stem)
        ra, ta = self._pick(h, "ра", "ре"), self._pick(h, "та", "те")
        if stem.endswith(("ль", "л", "н")):
            return [stem + ra + n, stem + ta + n]
        if stem.endswith("р"):
            return [stem + ta + n]
        return [stem + ra + n]

    def _plain_case(self, surface: str, case: str, bare: bool) -> List[str]:
        """İyeliksiz kök ya da A1/B1/B2 gövdeleri (ünsüzle biter)."""
        if case == "nominative":
            return [surface]
        kind = self._ending_class(surface) if bare else "cons"
        s = self.phon.geminate(surface) if kind == "ye" else surface
        h = self._h(s)
        if case in self.NEW_CASES:
            return [s + self._new_suffix(s, case)]
        if case in ("locative", "ablative"):
            return self._locative(s, case == "ablative")
        core = s[:-1] if (kind == "cons" and s.endswith("ь")) else s
        if case == "genitive":
            if kind == "cons":
                return [core + self._pick(h, "ӑн", "ӗн")]
            if kind == "ae":
                return [s + self._pick(h, "нӑн", "нӗн")]
            if kind == "uu":
                u = self._uu_stem(s)
                return [u + self._pick(self._h(u), "ӑн", "ӗн")]
            return [s + "н"]                                   # ye, i
        # dative
        if kind == "cons":
            return [core + self._pick(h, "а", "е")]
        if kind == "ae":
            return [s + self._pick(h, "на", "не")]
        if kind == "ye":
            return [s[:-1] + self._pick(h, "а", "е")]
        if kind == "uu":
            u = self._uu_stem(s)
            return [u + self._pick(self._h(u), "а", "е")]
        return [s + "й" + self._pick(h, "а", "е")]            # i

    def _vowel_possessed_case(self, st: Stem, case: str) -> List[str]:
        """A2, A3, B3 iyelikli (ünlüyle biten) gövde + tekil hal."""
        s = st.surface
        if case == "nominative":
            return [s]
        if case == "genitive":
            return [s + "н"]
        if case == "dative":
            if self._ending_class(st.root) == "cons":          # юлташ+у+на -> юлташна
                return [st.root + self._pick(self._h(st.root), "на", "не")]
            return [s + self._pick(self._h(s), "на", "не")]    # лашуна, лашине
        if case in ("locative", "ablative"):
            base = st.revert or s                              # тетрачӗ -> тетрадӗнче
            n = "н" if case == "ablative" else ""
            if st.slot == "A2":
                return [base + "н" + self._pick(self._h(base), "та", "те") + n]
            return [base + "нче" + n]
        return [s + self._new_suffix(s, case)]                 # yeni padej: н yok

    def _plural_case(self, surface: str, case: str) -> List[str]:
        if case == "nominative":
            return [surface + "сем"]
        if case in self.NEW_CASES:
            pl = surface + "сем"
            return [pl + self._new_suffix(pl, case)]
        pl = surface + "сен"                                   # eski padej: сем -> сен
        h = self._h(pl)
        return [pl + {"genitive": self._pick(h, "ӑн", "ӗн"),
                      "dative": self._pick(h, "а", "е"),
                      "locative": "че",
                      "ablative": "чен"}[case]]

    # ---- ANA İŞLEV -------------------------------------------------------------
    def generate_variants(self, root: str, poss: PossSpec = None, is_plural: bool = False,
                          case: str = "nominative") -> List[str]:
        base = self.phon.normalize(root)
        if not base:
            raise ValueError("Boş kök")
        case = self._parse_case(case)
        slot = self._parse_poss(poss)
        if is_plural and self._is_uncountable(base):
            raise UncountableNounError(f"{base!r} çoğul eki alamaz")

        out: List[str] = []
        for st in self._possessive_stems(base, slot):
            if is_plural:
                forms = self._plural_case(st.surface, case)
            elif slot in ("A2", "A3", "B3"):
                forms = self._vowel_possessed_case(st, case)
            else:
                forms = self._plain_case(st.surface, case, bare=slot is None)
            out.extend(forms)
        return list(dict.fromkeys(out))

    def generate_word(self, root: str, poss: PossSpec = None, is_plural: bool = False,
                      case: str = "nominative") -> str:
        """Birincil biçimi döndürür; alternatifler için generate_variants kullanın."""
        return self.generate_variants(root, poss, is_plural, case)[0]


_DEFAULT = ChuvashFST()


def generate_word(root: str, poss: PossSpec = None, is_plural: bool = False,
                  case: str = "nominative") -> str:
    return _DEFAULT.generate_word(root, poss, is_plural, case)


def generate_variants(root: str, poss: PossSpec = None, is_plural: bool = False,
                      case: str = "nominative") -> List[str]:
    return _DEFAULT.generate_variants(root, poss, is_plural, case)


# ----------------------------------------------------------------------------
# 4) Testler
# ----------------------------------------------------------------------------
def _run_tests() -> int:
    g, v = generate_word, generate_variants
    count = 0

    def eq(expected: str, *args, **kw) -> None:
        nonlocal count
        got = g(*args, **kw)
        assert got == expected, f"{args} {kw}: {got} != {expected}"
        count += 1

    def eqv(expected: List[str], *args, **kw) -> None:
        nonlocal count
        got = v(*args, **kw)
        assert got == expected, f"{args} {kw}: {got} != {expected}"
        count += 1

    def raises(exc, fn) -> None:
        nonlocal count
        try:
            fn()
        except exc:
            count += 1
        else:
            raise AssertionError(f"{exc.__name__} bekleniyordu")

    # --- İyelik: ünsüz / а,е / ӑ,ӗ / у,ӳ / и ---------------------------------
    for slot, exp in zip(("A1", "A2", "A3", "B1", "B2", "B3"),
                         ("лашам", "лашу", "лаши", "лашамӑр", "лашӑр", "лаши")):
        eq(exp, "лаша", poss=slot)
    for slot, exp in zip(("A1", "A2", "A3", "B1", "B2", "B3"),
                         ("сӗтелӗм", "сӗтелӳ", "сӗтелӗ", "сӗтелӗмӗр", "сӗтелӗр", "сӗтелӗ")):
        eq(exp, "сӗтел", poss=slot)
    eq("ӗнӳ", "ӗне", poss="A2")
    eq("ӗнемӗр", "ӗне", poss="B1")
    eq("палатӑмӑр", "палат", poss="B1")
    for slot, exp in zip(("A1", "A2", "A3", "B1", "B2"),
                         ("сӑввӑм", "сӑвву", "сӑвви", "сӑввӑмӑр", "сӑввӑр")):
        eq(exp, "сӑвӑ", poss=slot)                      # ikizleşme
    eq("сӗллӗм", "сӗлӗ", poss="A1")
    eq("пӗрчӗм", "пӗрчӗ", poss="A1")                    # çift ünsüz: ikizleşme yok
    eq("пӑчкӑм", "пӑчкӑ", poss="A1")
    eq("ҫырӑвӑм", "ҫыру", poss="A1")
    eq("ҫырӑву", "ҫыру", poss="A2")
    eq("ҫырӑвӗ", "ҫыру", poss="A3")
    eq("ҫырӑвӑмӑр", "ҫыру", poss="B1")
    eq("кӗрӗвӗм", "кӗрӳ", poss="A1")
    eq("шӑшийӗм", "шӑши", poss="A1")
    eq("шӑшийӳ", "шӑши", poss=(2, "sg"))
    eq("шӑшийӗ", "шӑши", poss="A3")
    eq("шӑшийӗмӗр", "шӑши", poss="B1")

    # --- İyelik istisnaları -----------------------------------------------------
    eq("тетрачӗ", "тетрадь", poss="A3")
    eq("тетрачӗ", "тетрат", poss="B3")
    eq("турачӗ", "турат", poss="A3")
    eq("туратӑм", "турат", poss="A1")                   # yalnızca 3. şahıs
    eq("тетрадӑм", "тетрадь", poss="A1")                # ь ünlü başlı ekten önce düşer
    assert ChuvashFST(soft_sign_front=True).generate_word("тетрадь", "A1") == "тетрадӗм"; count += 1
    eq("портфелӗ", "портфель", poss="A3")
    eq("куккӑшӗ", "кукка", poss="A3")
    eq("аппӑшӗ", "аппа", poss="B3")
    eq("мучӑшӗ", "мучи", poss="A3")
    eq("ашшӗ", "атте", poss="A3")
    eq("амӑшӗ", "анне", poss="A3")
    eq("аппам", "аппа", poss="A1")                      # diğer şahıslar standart
    eq("аттем", "атте", poss="A1")
    eqv(["пальти", "пальтовӗ"], "пальто", poss="A3")    # Rusça alıntı
    eq("пальтом", "пальто", poss="A1")

    # --- Çoğul ve sayılamayanlar ---------------------------------------------------
    eq("ачасем", "ача", is_plural=True)
    eq("лашамсем", "лаша", poss="A1", is_plural=True)
    for w in ("сӗт", "утӑ", "кӑнтӑр", "ӑслӑх", "ырлӗх"):
        raises(UncountableNounError, lambda w=w: g(w, is_plural=True))
    eq("сӗтӗн", "сӗт", case="genitive")                 # tekilde sorun yok
    assert ChuvashFST(extra_uncountable=["шыв"]).uncountable >= {"шыв"}; count += 1

    # --- Eski padejler (iyeliksiz, tekil) ---------------------------------------------
    eq("ачанӑн", "ача", case="genitive")
    eq("ачана", "ача", case="dative")
    eq("ачара", "ача", case="locative")
    eq("ачаран", "ача", case="ablative")
    eq("сӗтелӗн", "сӗтел", case="genitive")
    eq("сӗтеле", "сӗтел", case="dative")
    eqv(["сӗтелре", "сӗтелте"], "сӗтел", case="locative")     # л: ра/ре veya та/те
    eqv(["сӗтелрен", "сӗтелтен"], "сӗтел", case="ablative")
    eqv(["килре", "килте"], "кил", case="locative")
    eqv(["товарта"], "товар", case="locative")                # р: yalnızca та/те
    eqv(["товартан"], "товар", case="ablative")
    eq("чӗчӗкӗн", "чӗчӗк", case="genitive")
    eq("пуллӑн", "пулӑ", case="genitive")                     # ikizleşme
    eq("пулла", "пулӑ", case="dative")
    eq("сӗллӗн", "сӗлӗ", case="genitive")
    eq("сӑввӑн", "сӑвӑ", case="genitive")
    eq("сӑвва", "сӑвӑ", case="dative")
    eq("пӑчкӑн", "пӑчкӑ", case="genitive")
    eq("пӑчка", "пӑчкӑ", case="dative")
    eq("ҫырӑвӑн", "ҫыру", case="genitive")                    # у -> ӑв
    eq("ҫырӑва", "ҫыру", case="dative")
    eq("кӗрӗвӗн", "кӗрӳ", case="genitive")
    eq("кӗрӗве", "кӗрӳ", case="dative")
    eq("ҫырура", "ҫыру", case="locative")
    eq("шӑшин", "шӑши", case="genitive")                      # и -> yalnızca н
    eq("шӑшийе", "шӑши", case="dative")                       # и -> й girer
    eq("шӑшире", "шӑши", case="locative")
    eq("шӑширен", "шӑши", case="ablative")
    eq("портфелӗн", "портфель", case="genitive")
    eq("портфеле", "портфель", case="dative")
    eq("портфельре", "портфель", case="locative")

    # --- Yeni padejler (iyeliksiz) ------------------------------------------------------
    eq("ачапа", "ача", case="instrumental")
    eq("ачасӑр", "ача", case="abessive")
    eq("ачашӑн", "ача", case="causal")
    eq("сӗтелпе", "сӗтел", case="instrumental")
    eq("сӗтелсӗр", "сӗтел", case="abessive")
    eq("сӗтелшӗн", "сӗтел", case="causal")
    eq("пуллӑшӑн", "пулӑ", case="causal")
    eq("пуллӑпа", "пулӑ", case="instrumental")
    eq("ҫырупа", "ҫыру", case="instrumental")
    eq("шӑшипе", "шӑши", case="instrumental")

    # --- Takma adlar ---------------------------------------------------------------------
    eq("ачана", "ача", case="A3")
    eq("ачашӑн", "ача", case="sebep")
    eq("ачапа", "ача", case="пӗрлӗлӗх")
    raises(ValueError, lambda: g("ача", case="vocative"))
    raises(ValueError, lambda: g("ача", poss="C1"))
    raises(ValueError, lambda: g(""))

    # --- Çoğul + hal: сем -> сен (eski), сем kalır (yeni) ------------------------------------
    eq("ачасенӗн", "ача", is_plural=True, case="genitive")
    eq("ачасене", "ача", is_plural=True, case="dative")
    eq("ачасенче", "ача", is_plural=True, case="locative")
    eq("ачасенчен", "ача", is_plural=True, case="ablative")
    eq("ачасемпе", "ача", is_plural=True, case="instrumental")
    eq("ачасемсӗр", "ача", is_plural=True, case="abessive")
    eq("ачасемшӗн", "ача", is_plural=True, case="causal")
    eq("лашамӑн", "лаша", poss="A1", case="genitive")
    eq("лашамсенӗн", "лаша", poss="A1", is_plural=True, case="genitive")
    eq("тусусенче", "тус", poss="A2", is_plural=True, case="locative")
    eq("тусӗсене", "тус", poss="A3", is_plural=True, case="dative")

    # --- İyelik + eski padej kesişimi ----------------------------------------------------------
    # Yönelme: ünlüyle biten kök -> н girer; ünsüzle biten kök -> iyelik düşer
    eq("лашуна", "лаша", poss="A2", case="dative")
    eq("лашине", "лаша", poss="A3", case="dative")
    eq("пуллине", "пулӑ", poss="A3", case="dative")
    eq("юлташна", "юлташ", poss="A2", case="dative")
    eq("юлташна", "юлташ", poss="A3", case="dative")
    eq("юлташна", "юлташ", poss="B3", case="dative")
    eq("хӗрне", "хӗр", poss="A3", case="dative")
    eq("тусӑма", "тус", poss="A1", case="dative")             # A1: normal ünsüz kuralı
    eq("ашшӗне", "атте", poss="A3", case="dative")
    # Bulunma / çıkma: A1 ра, A2 н+та, A3 н+че
    eq("тусӑмра", "тус", poss="A1", case="locative")
    eq("тусӑмран", "тус", poss="A1", case="ablative")
    eq("тусунта", "тус", poss="A2", case="locative")
    eq("тусунтан", "тус", poss="A2", case="ablative")
    eq("тусӗнче", "тус", poss="A3", case="locative")
    eq("тусӗнчен", "тус", poss="A3", case="ablative")
    eq("тусӗнче", "тус", poss="B3", case="locative")
    eq("тусӑмӑрта", "тус", poss="B1", case="locative")        # р ile biter -> та
    eq("тусӑрта", "тус", poss="B2", case="locative")
    eq("лашунта", "лаша", poss="A2", case="locative")
    eq("лашинче", "лаша", poss="A3", case="locative")
    eq("лашинчен", "лаша", poss="A3", case="ablative")
    eq("ашшӗнче", "атте", poss="A3", case="locative")
    eq("амӑшӗнчен", "анне", poss="A3", case="ablative")
    eq("сӗтелӳнте", "сӗтел", poss="A2", case="locative")
    eq("лашин", "лаша", poss="A3", case="genitive")
    eq("лашун", "лаша", poss="A2", case="genitive")
    eq("сӗтелӗн", "сӗтел", poss="A3", case="genitive")

    # --- Geri dönüşüm: тетрачӗ -> тетрадӗнче (yalnızca bulunma/çıkma) ----------------------------
    eq("тетрачӗ", "тетрадь", poss="A3")
    eq("тетрадӗнче", "тетрадь", poss="A3", case="locative")
    eq("тетрадӗнчен", "тетрадь", poss="A3", case="ablative")
    eq("тетрадӗнче", "тетрадь", poss="B3", case="locative")
    eq("туратӗнче", "турат", poss="A3", case="locative")
    eq("туратӗнчен", "турат", poss="A3", case="ablative")
    eq("тетрачӗн", "тетрадь", poss="A3", case="genitive")     # diğer hallerde ч kalır
    eq("тетрачӗпе", "тетрадь", poss="A3", case="instrumental")
    eq("тетрадьна", "тетрадь", poss="A3", case="dative")      # iyelik düşer, kök aynen
    assert ChuvashFST(soft_sign_front=True).generate_word(
        "тетрадь", "A3", case="dative") == "тетрадьне"; count += 1

    # --- İyelik + yeni padej: н kaynaştırması YOK -----------------------------------------------
    eq("кӑранташӗпе", "кӑранташ", poss="A3", case="instrumental")
    eq("кӑранташӗнчен", "кӑранташ", poss="A3", case="ablative")    # eski padejde н var
    eq("портфелӗшӗн", "портфель", poss="A3", case="causal")
    eq("кӑранташусӑр", "кӑранташ", poss="A2", case="abessive")
    eq("кӑранташӗсӗр", "кӑранташ", poss="A3", case="abessive")
    eq("лашупа", "лаша", poss="A2", case="instrumental")
    eq("ачипе", "ача", poss="A3", case="instrumental")
    eq("тусӑмпа", "тус", poss="A1", case="instrumental")
    eq("пуллӑмшӑн", "пулӑ", poss="A1", case="causal")

    # --- Rusça alıntı 'о' + hal ---------------------------------------------------------------------
    eqv(["пальтине", "пальтовӗне"], "пальто", poss="A3", case="dative")
    eqv(["пальтинче", "пальтовӗнче"], "пальто", poss="A3", case="locative")

    print(f"Tüm testler geçti ({count} kontrol).")
    return count


# ----------------------------------------------------------------------------
# 5) Etkileşimli menü (Pydroid 3 / terminal: argüman gerekmez)
# ----------------------------------------------------------------------------
def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "0"


def _yes(text: str) -> bool:
    return text.lower() in ("e", "evet", "y", "yes", "1")


def _interactive() -> None:
    fst = _DEFAULT
    print("=== Çuvaşça çekim motoru (ChuvashFST) ===")
    print("Latin ă ĕ ç ÿ yazımı da kabul edilir. Boş bırakılan alan = yok/yalın.")
    while True:
        print("\n1) Tek biçim üret")
        print("2) Bir kökün 8 halini göster")
        print("3) Bir kökün tüm iyelik biçimlerini göster")
        print("4) Testleri çalıştır")
        print("0) Çıkış")
        choice = _ask("Seçim: ")
        try:
            if choice == "0":
                break
            elif choice == "1":
                root = _ask("Kök (örn. лаша): ")
                poss = _ask("İyelik (A1 A2 A3 B1 B2 B3): ").upper() or None
                plural = _yes(_ask("Çoğul? (e/h): "))
                case = _ask("Hal (nominative genitive dative locative ablative "
                            "instrumental abessive causal): ") or "nominative"
                print("\n=>", " / ".join(fst.generate_variants(root, poss, plural, case)))
            elif choice == "2":
                root = _ask("Kök: ")
                poss = _ask("İyelik (boş = yok): ").upper() or None
                plural = _yes(_ask("Çoğul? (e/h): "))
                for c in fst.CASES:
                    forms = fst.generate_variants(root, poss, plural, c)
                    print(f"{c:13} {' / '.join(forms)}")
            elif choice == "3":
                root = _ask("Kök: ")
                for s in fst.SLOTS:
                    forms = fst.generate_variants(root, s, False, "nominative")
                    print(f"{s}  {' / '.join(forms)}")
            elif choice == "4":
                _run_tests()
        except UncountableNounError as e:
            print("Hata (çoğul alamaz):", e)
        except ValueError as e:
            print("Hata:", e)


if __name__ == "__main__":
    _interactive()
