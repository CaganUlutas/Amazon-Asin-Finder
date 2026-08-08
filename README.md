# Amazon ASIN Finder

Profesyonel seviyede çalışan bir Amazon ASIN Crawler masaüstü uygulaması.

## Özellikler

- **Amazon.com arama URL'lerinden ASIN çıkarma** — Tek seferde 1-50 URL
- **Gelişmiş filtreleme** — Fiyat, puan, yorum, Prime, marka hariç tutma
- **Görev sistemi** — Bağımsız çalışan görevler, ilerleme takibi
- **TXT/CSV dışa aktarma** — Filtreye uyan ASIN listesi
- **Modern dark theme** — Kurumsal görünüm
- **Performanslı** — Headless browser, tek instance, düşük RAM

## Kurulum

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Playwright tarayıcısını yükle
playwright install chromium
```

## Kullanım

```bash
python main.py
```

## Teknolojiler

- **Python 3.11+**
- **PySide6** — Kullanıcı arayüzü
- **Playwright** — Headless browser tarama
- **qasync** — Async/Qt entegrasyonu
- **aiosqlite** — Async SQLite veritabanı
