# Abonelik Takibi Kampanyaları

Türkiye'deki abonelik kampanyalarını yalnızca resmî banka, operatör ve hizmet
sağlayıcı sayfalarından toplayan ücretsiz veri akışıdır.

- `campaigns.json`: Android uygulamasının okuduğu yayın akışı
- `sources.json`: Taranmasına izin verilen resmî kaynaklar
- `scripts/update_campaigns.py`: Kampanya bağlantılarını bulan ve süresi geçenleri ayıran tarayıcı
- `.github/workflows/update-campaigns.yml`: Her gün otomatik güncelleme

Bir kart yalnızca `sources.json` içindeki resmî alan adlarından gelebilir. Uygulama
kartı açtığında kullanıcı her zaman kampanyanın resmî sayfasına yönlendirilir.
