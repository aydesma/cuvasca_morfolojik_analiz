# Çuvaşça Morfolojik Analiz

Site: https://cuvasca-morfolojik-analiz.vercel.app/

Çuvaşça isim çekimi: **kök + iyelik + çoğul + hal**. Girilen kök için seçilen
iyelik (yok, 1./2./3. tekil, 1./2./3. çoğul), sayı ve 8 halden biri üretilir;
ek zinciri, varsa alternatif biçimler ve seçili iyelik için 8 hal × tekil/çoğul
tablosu gösterilir.

Haller: yalın, ilgi, yönelme, bulunma, çıkma (eski); vasıta, yokluk, sebep (yeni).

## Dosyalar

- `chuvash_fst.py` — çekim motoru (ChuvashFST). Tek başına da çalışır:
  `python chuvash_fst.py` etkileşimli menüyü açar.
- `morphology.py` — motor ile arayüz arasındaki katman: girdi denetimi, ek
  zincirinin çıkarılması, hal tablosu.
- `app.py`, `templates/index.html` — Flask arayüzü.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
python app.py
# http://localhost:3000
```

## Testler

```bash
python -m unittest
```

Motorun kendi 163 kontrolü, bütün kök × iyelik × sayı × hal kombinasyonlarında
ek zincirinin son biçimi oluşturduğu ve form akışı sınanır.
