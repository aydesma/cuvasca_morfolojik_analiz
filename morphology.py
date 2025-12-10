# -*- coding: utf-8 -*-
VOWELS = {'а', 'ӑ', 'ы', 'у', 'э', 'ӗ', 'и', 'ӳ'}  # Ünlüler
CONSONANTS = {'й', 'ц', 'к', 'н', 'г', 'ш', 'щ', 'з', 'х', 'ф', 'в', 'п', 'р', 'л', 'д', 'ж', 'ч', 'с', 'м', 'т', 'б', 'ю', 'я'}  # Ünsüzler

BACK_VOWELS = {'а', 'ӑ', 'ы', 'у'}  # Kalın ünlüler
FRONT_VOWELS = {'э', 'ӗ', 'и', 'ӳ'}  # İnce ünlüler

def get_vowel_harmony(word):
    """Kelimenin ünlü uyumunu belirler."""
    for char in reversed(word):
        if char in BACK_VOWELS:
            return 'back'
        elif char in FRONT_VOWELS:
            return 'front'
    return 'back'

def get_last_letter_type(word):
    """Son harfin ünlü/ünsüz olduğunu belirler."""
    if not word:
        return 'consonant'
    return 'vowel' if word[-1] in VOWELS else 'consonant'

def has_single_consonant_before_ăĕ(word):
    """ӑ/ӗ'den önce tek ünsüz var mı kontrol eder (iki heceli kelime için)."""
    if len(word) >= 2 and word[-1] in {'ӑ', 'ӗ'}:
        if word[-2] in CONSONANTS:
            vowel_count = sum(1 for char in word if char in VOWELS)
            return vowel_count >= 2
    return False

# 1. TEKİL ŞAHIS İYELİK EKİ
def get_first_singular_possessive(word):
    if not word:
        return word, ""
    
    harmony = get_vowel_harmony(word)
    last_char = word[-1]
    
    # Kural 3: у/ӳ ile biten
    if last_char in {'у', 'ӳ'}:
        if harmony == 'back':
            return word[:-1], 'ӑвӑм'
        else:
            return word[:-1], 'ӗвӗм'
    
    # Kural 4: ӑ/ӗ ile biten ve öncesinde tek ünsüz (İKİZLEŞME - ă/ĕ DÜŞMEZ!)
    if has_single_consonant_before_ăĕ(word):
        consonant = word[-2]
        stem = word[:-2] + consonant * 2
        return stem + word[-1], 'м'
    
    # Kural 1: Ünsüzle biten
    if get_last_letter_type(word) == 'consonant':
        return word, ('ӑм' if harmony == 'back' else 'ӗм')
    
    # Kural 2: Ünlüyle biten (a, e, ă, ĕ, ы, и, ӳ)
    return word, 'м'

# 2. TEKİL ŞAHIS İYELİK EKİ  
def get_second_singular_possessive(word):
    if not word:
        return word, ""
    
    harmony = get_vowel_harmony(word)
    last_char = word[-1]
    suffix = 'у' if harmony == 'back' else 'ӳ'
    
    # Kural 1: a/э ile biten (a ve э sesleri düşer)
    if last_char in {'а', 'э'}:
        return word[:-1], suffix
    
    # Kural 2: ӑ/ӗ ile biten ve öncesinde tek ünsüz (İKİZLEŞME - ă/ĕ DÜŞER!)
    if has_single_consonant_before_ăĕ(word):
        consonant = word[-2]
        stem = word[:-2] + consonant * 2
        return stem, suffix
    
    return word, suffix

# 3. TEKİL ŞAHIS İYELİK EKİ
def get_third_singular_possessive(word):
    if not word:
        return word, ""
    
    harmony = get_vowel_harmony(word)
    last_char = word[-1]
    
    # Kural 4: т/д ile biten
    if last_char in {'т', 'д'}:
        return word[:-1], 'чӗ'
    
    # Kural 3: у/ӳ ile biten
    if last_char in {'у', 'ӳ'}:
        if harmony == 'back':
            return word[:-1], 'ӑвӗ'
        else:
            return word[:-1], 'ӗвӗ'
    
    # Kural 2: и ile biten
    if last_char == 'и':
        return word, 'йӗ'
    
    # Kural 1: a/э/ă/ĕ ile biten (a/э/ă/ĕ sesleri düşer)
    if last_char in {'а', 'э', 'ӑ', 'ӗ'}:
        # ӑ/ӗ ile biten ve öncesinde tek ünsüz (İKİZLEŞME - ă/ĕ DÜŞER!)
        if last_char in {'ӑ', 'ӗ'} and has_single_consonant_before_ăĕ(word):
            consonant = word[-2]
            stem = word[:-2] + consonant * 2
            return stem, 'ӗ'
        else:
            return word[:-1], 'ӗ'
    
    # Diğer ünlülerle biten (ы/у/ӳ): direkt +ӗ
    return word, 'ӗ'

# 1. ÇOĞUL ŞAHIS İYELİK EKİ
def get_first_plural_possessive(word):
    """1. çoğul şahıs (bizim)"""
    if not word:
        return word, ""
    
    harmony = get_vowel_harmony(word)
    last_char = word[-1]
    
    # у/ӳ ile biten
    if last_char in {'у', 'ӳ'}:
        if harmony == 'back':
            return word[:-1], 'ӑвӑмӑр'
        else:
            return word[:-1], 'ӗвӗмӗр'
    
    # ӑ/ӗ ile biten ve öncesinde tek ünsüz (İKİZLEŞME)
    if has_single_consonant_before_ăĕ(word):
        consonant = word[-2]
        stem = word[:-2] + consonant * 2
        suffix = 'мӑр' if harmony == 'back' else 'мӗр'
        return stem + word[-1], suffix
    
    # Ünsüzle biten
    if get_last_letter_type(word) == 'consonant':
        return word, ('ӑмӑр' if harmony == 'back' else 'ӗмӗр')
    
    # Ünlüyle biten (a, e, ă, ĕ, ы, и, ӳ)
    return word, ('мӑр' if harmony == 'back' else 'мӗр')

# 2. ÇOĞUL ŞAHIS İYELİK EKİ
def get_second_plural_possessive(word):
    """2. çoğul şahıs (sizin)"""
    if not word:
        return word, ""
    
    harmony = get_vowel_harmony(word)
    last_char = word[-1]
    
    # у/ӳ ile biten
    if last_char in {'у', 'ӳ'}:
        if harmony == 'back':
            return word[:-1], 'ӑвӑр'
        else:
            return word[:-1], 'ӗвӗр'
    
    # ӑ/ӗ ile biten ve öncesinde tek ünsüz (İKİZLEŞME)
    if has_single_consonant_before_ăĕ(word):
        consonant = word[-2]
        stem = word[:-2] + consonant * 2
        return stem, ('ӑр' if harmony == 'back' else 'ӗр')
    
    # Ünsüzle biten
    if get_last_letter_type(word) == 'consonant':
        return word, ('ӑр' if harmony == 'back' else 'ӗр')
    
    # Ünlüyle biten
    return word, ('р' if harmony == 'back' else 'р')

# 3. ÇOĞUL ŞAHIS İYELİK EKİ
def get_third_plural_possessive(word):
    """3. çoğul şahıs (onların) - 3. tekil ile aynı kurallar"""
    return get_third_singular_possessive(word)

def analyze(root, person_code, is_plural):
    """
    İsim çekim analizi yapar.
    
    Args:
        root: Kök kelime
        person_code: '1sg', '2sg', '3sg', '1pl', '2pl', '3pl' veya boş
        is_plural: True/False
    
    Returns:
        parts: Analiz parçaları listesi [{'text': '...', 'code': '...', 'type': '...'}]
        final_word: Oluşturulan kelime
    """
    parts = []
    current_word = root
    
    # 1. Kök
    parts.append({
        "text": root,
        "code": "Kök",
        "type": "Kök"
    })
    
    # İyelik Eki
    suffix_text = ""
    if person_code:
        stem = current_word
        suffix = ""
        
        if person_code == '1sg': # 1. Tekil
            stem, suffix = get_first_singular_possessive(current_word)
        elif person_code == '2sg': # 2. Tekil
            stem, suffix = get_second_singular_possessive(current_word)
        elif person_code == '3sg': # 3. Tekil
            stem, suffix = get_third_singular_possessive(current_word)
        elif person_code == '1pl': # 1. Çoğul
            stem, suffix = get_first_plural_possessive(current_word)
        elif person_code == '2pl': # 2. Çoğul
            stem, suffix = get_second_plural_possessive(current_word)
        elif person_code == '3pl': # 3. Çoğul
            stem, suffix = get_third_plural_possessive(current_word)
            
        if suffix:
            parts.append({
                "text": suffix,
                "code": person_code,
                "type": "İyelik"
            })
            current_word = stem + suffix

    # Sayı (Çoğul) Eki
    if is_plural:
        # Çuvaşça çoğul eki -сем
        suffix = 'сем'
        parts.append({
            "text": suffix,
            "code": "Çoğul",
            "type": "Sayı"
        })
        current_word = current_word + suffix
    
    return parts, current_word
