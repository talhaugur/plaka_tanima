# 🚗 Akıllı Plaka Tanımalı Bariyer Sistemi

Raspberry Pi tabanlı, kamera ve LDR sensörü kullanan otomatik bariyer kontrol sistemi. Araç yaklaştığında plakayı okur, yetkili plakaysa kapıyı açar. Web paneli üzerinden uzaktan yönetilebilir.

---

## 📷 Sistem Nasıl Çalışır?

```
Araç yaklaşır (LDR algılar)
        ↓
Kamera fotoğraf çeker
        ↓
PlateRecognizer API plakayı okur
        ↓
Yetkili listesiyle karşılaştırır
        ↓
Yetkili ✅ → Step motor kapıyı açar
Yetkisiz ❌ → Kapı kapalı kalır
```

---

## 🛠️ Donanım Gereksinimleri

| Bileşen | Detay |
|---|---|
| Raspberry Pi | 4B önerilir |
| Kamera | Pi Camera (rpicam destekli) |
| Step Motor | 28BYJ-48 + ULN2003 sürücü |
| LDR Sensörü | Araç algılama için |
| Güç Kaynağı | 5V / min 3A |

### Pin Bağlantıları

| GPIO | Bağlantı |
|---|---|
| GPIO 18 | Motor IN1 |
| GPIO 23 | Motor IN2 |
| GPIO 24 | Motor IN3 |
| GPIO 25 | Motor IN4 |
| GPIO 17 | LDR Sensör |

---

## 💻 Kurulum

### 1. Repoyu klonla

```bash
git clone https://github.com/talhaugur/plaka_tanima.git
cd plaka_tanima
```

### 2. Gerekli kütüphaneleri kur

```bash
pip install flask gpiozero requests
```

### 3. API Token ayarla

`plaka_tanima.py` dosyasını aç, token satırını güncelle:

```python
API_TOKEN = "senin_token_buraya"
```

> PlateRecognizer API anahtarı için: [platerecognizer.com](https://platerecognizer.com)

### 4. İzinli plakaları ekle

`plakalar.txt` dosyasına her satıra bir plaka yaz:

```
34ABC123
06XYZ789
```

### 5. Çalıştır

```bash
python3 plaka_tanima.py
```

---

## 🌐 Web Paneli

Sistem çalışınca tarayıcıdan aç:

```
http://<raspberry-pi-ip>:5000
```

Web panelinden yapabileceklerin:

- ✅ Kapıyı manuel aç / kapat
- 📋 İzinli plaka ekle / sil
- 📸 Son geçiş fotoğrafını gör
- 🕐 Son geçiş plakasını ve saatini takip et

---

## 📁 Dosya Yapısı

```
plaka_tanima/
├── plaka_tanima.py     # Ana uygulama
├── plakalar.txt        # İzinli plakalar listesi (otomatik oluşur)
├── plaka.jpg           # Geçici kamera görüntüsü
└── son_gecis.jpg       # Son geçiş fotoğrafı
```

---

## ⚙️ Mimari

Sistem 3 bağımsız thread ile çalışır:

| Thread | Görev |
|---|---|
| `Web-Flask` | HTTP isteklerini karşılar, her zaman aktif |
| `Sensor-Plaka` | Araç algılama + kamera + API kontrolü |
| `Motor-Kontrol` | Kapı açma/kapama, güvenlik kontrolü |

Thread'ler `Event` ve `Queue` ile haberleşir — birbirini bloklamaz.

---

## 🔒 Güvenlik Özellikleri

- Kapı kapanırken LDR araç algılarsa **otomatik geri açılır**
- Araç geçmeden kapı kapanmaz
- Web panelinden araç varken zorla kapatma engellenir

---

## 📦 Bağımlılıklar

```
flask
gpiozero
requests
```

---

## 📄 Lisans

MIT License — özgürce kullanabilirsin.
