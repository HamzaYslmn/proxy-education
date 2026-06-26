# proxy-education

Küçük bir eğitim projesi.

Bu projede **aynı Supabase veritabanına** iki farklı yoldan erişilir:

* **Direct:** tarayıcı → Supabase
* **Proxied:** tarayıcı → FastAPI proxy → Supabase

Amaç, Supabase’e tarayıcıdan doğrudan erişildiğinde PostgREST yüzeyinin neleri açığa çıkardığını ve araya doğru tasarlanmış ince bir proxy katmanı konduğunda bu risklerin nasıl sınırlandığını yan yana göstermektir.

Üst çubuktaki anahtarla **direct** ve **proxied** modları arasında geçiş yapabilirsiniz.

> ⚠️ **Yalnızca eğitim amaçlıdır.**
>
> Bu proje bilerek güvenlik hataları içerir:
>
> * fazla geniş yazılmış bir RLS politikası,
> * `SECURITY DEFINER` ile çalışan bir PostgreSQL fonksiyonu,
> * RLS hiç etkinleştirilmemiş bir tablo.
>
> Bu açıklar özellikle bırakılmıştır; aksi halde saldırı senaryoları çalışmazdı.
>
> Bu şemayı yalnızca size ait geçici bir Supabase projesinde deneyin.
> Asla production ortamına taşımayın.

## Projenin anlattığı şey

`supabase/public.sql` içinde üç bilinçli güvenlik hatası vardır.

Supabase’e doğrudan PostgREST üzerinden erişildiğinde bu hatalar istismar edilebilir. Proxy modunda ise aynı veritabanı kullanılır, fakat istekler daha dar ve kontrollü bir API’den geçirilir.

Proxy şunları yapar:

* embed/JOIN isteklerini reddeder,
* private veri okuma ve yazma işlemlerinde `id = kullanıcının uid’si` koşulunu sunucu tarafında zorlar,
* token olmadan istek kabul etmez,
* yalnızca önceden tanımlanmış tipli parametreleri kabul eder,
* sayfa boyutunu sınırlar,
* rate limit uygular,
* sadece uygulamanın ihtiyaç duyduğu yolları açar.

Bu yüzden `logs`, `/graphql`, `/rpc`, `/storage`, `/functions`, `/realtime` ve `/rest/v1/` şema kökü proxy üzerinden erişilemez.

Saldırı tablosu, bir saldırganın genelde izleyeceği sıraya göre düzenlenmiştir:

**keşif → okuma → pivot → ölçekleme → veri değiştirme / kötüye kullanım**

`pwn-tools` da testleri aynı sırayla çalıştırır.

| #  | Saldırı                                                          | Direct                                                               | Proxy                                                |
| -- | ---------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------- |
| 1  | GraphQL introspection `/graphql/v1 { __schema }`                 | tüm tablo ve tipleri listeler                                        | 404, çünkü `/graphql` route edilmez                  |
| 2  | GraphQL ile veri okuma `{ privateCollection … }`                 | `pg_graphql` üzerinden private notları sızdırır                      | 404                                                  |
| 3  | Şema dökümü `GET /rest/v1/`                                      | OpenAPI çıktısı ile tablo, kolon ve foreign key bilgilerini gösterir | 404, şema kökü açılmaz                               |
| 4  | Giriş yapmadan anon key ile okuma                                | auth olmadan veri dönebilir                                          | 401, token zorunludur                                |
| 5  | Filtresiz okuma `private?select=data`                            | tüm `private` tablosunu dökebilir                                    | yalnızca kendi satırınız döner                       |
| 6  | Başka kullanıcı hedefleme `private?id=eq.<victim>`               | kurban kullanıcının satırını okuyabilir                              | yine sadece kendi satırınız döner                    |
| 7  | UUID aralığıyla gezinme `private?id=gt.<0-uuid>`                 | satırlar ID aralığıyla gezilebilir, IDOR oluşur                      | sadece kendi satırınız döner, `gt` kullanılmaz       |
| 8  | RLS kapalı tablo `logs?select=*`                                 | korumasız tablo okunabilir                                           | 404, `logs` route edilmez                            |
| 9  | Resource embedding `public?select=*,private(*)`                  | ilişkili private verileri sızdırabilir                               | 422, embed reddedilir                                |
| 10 | RPC `/rpc/all_notes`                                             | `SECURITY DEFINER` nedeniyle RLS bypass edilebilir                   | 404, `/rpc` route edilmez                            |
| 11 | PostgREST operatörleri `or=`, `like=`                            | geniş filtreleme yüzeyi açıktır                                      | 422, sadece tipli parametreler kabul edilir          |
| 12 | Aşırı büyük limit `limit=100000`                                 | tablo tek istekte kazınabilir                                        | 422, limit 100 ile sınırlandırılır                   |
| 13 | `Prefer: count=exact`                                            | tüm tablonun gerçek satır sayısı öğrenilebilir                       | yalnızca kullanıcının görebildiği satır sayısı döner |
| 14 | Mass assignment, örn. sahte `created_at`                         | gerçek kolonlara doğrudan yazılabilir                                | 422, body yalnızca `data` alanını kabul eder         |
| 15 | Anon `DELETE` on `logs`                                          | RLS kapalı tablo herkes tarafından silinebilir                       | 404, `logs` route edilmez                            |
| 16 | 25 hızlı okuma isteği                                            | uygulama seviyesinde sınır yoktur                                    | 10/dk sonrası 429                                    |
| 17 | Storage bucket listeleme `GET /storage/v1/bucket`                | Storage API’ye ulaşılabilir                                          | 404, `/storage` route edilmez                        |
| 18 | Storage object listeleme `POST /storage/v1/object/list/<bucket>` | RLS gevşekse bucket içeriği gezilebilir                              | 404                                                  |
| 19 | Edge Function çağırma `POST /functions/v1/<fn>`                  | Functions gateway’e ulaşılabilir                                     | 404, `/functions` route edilmez                      |
| 20 | Realtime `WSS /realtime/v1`                                      | tablo değişimleri canlı izlenebilir                                  | desteklenmez, proxy yalnızca HTTP çalışır            |
| 21 | Auth config `GET /auth/v1/settings`                              | signup, autoconfirm ve OAuth provider bilgileri görülebilir          | forward edilir, Supabase ayarına bağlıdır            |
| 22 | Anon signup `POST /auth/v1/signup {}`                            | açıksa ücretsiz authenticated session alınabilir                     | forward edilir, Supabase ayarına bağlıdır            |
| 23 | OAuth redirect `authorize?redirect_to=evil`                      | allowlist yoksa open redirect riski doğar                            | forward edilir, Supabase ayarına bağlıdır            |

## Bu açıklar neden tehlikeli?

Supabase kullanırken tarayıcıya koyduğunuz **publishable anon key gizli değildir**.

Bu key zaten frontend bundle içinde bulunur. Yani sitenizi açan herkes o key’e erişebilir. Bu normaldir; Supabase mimarisi bunu varsayar.

Bu yüzden doğrudan Supabase erişiminde asıl güvenlik duvarı şudur:

**Row-Level Security, yani RLS.**

Eğer RLS doğru yazılmadıysa, eksik bırakıldıysa veya başka bir PostgreSQL özelliğiyle yanlışlıkla bypass edildiyse, anon key’e sahip herhangi biri veriye ulaşabilir.

Sorun genelde şuradan çıkar:

* bir SELECT policy fazla geniş yazılır,
* bir tabloda RLS açılmaz,
* `SECURITY DEFINER` fonksiyonu RLS’i bypass eder,
* `/rpc`, `/graphql`, `/storage` gibi yüzeyler unutulur,
* istemcinin gönderdiği filtrelere fazla güvenilir.

Bu projedeki amaç, “anon key zaten public, o zaman güvenlik nerede durmalı?” sorusunu pratik olarak göstermektir.

## 1. Keşif: API kendi haritasını verir

PostgREST ve GraphQL, geliştirici için çok kullanışlıdır; fakat doğrudan internete açık olduklarında saldırgana da çok fazla bilgi verirler.

`GET /rest/v1/` isteği OpenAPI şeması döndürebilir. Bu çıktıdan şunlar öğrenilebilir:

* tablo adları,
* kolon adları,
* veri tipleri,
* ilişkiler,
* foreign key bağlantıları.

GraphQL tarafında `/graphql/v1` üzerindeki introspection sorguları da benzer şekilde tüm GraphQL şemasını gösterebilir.

Yani saldırgan çoğu zaman tablo adlarını tahmin etmek zorunda kalmaz. API zaten kendi yapısını anlatır.

Introspection kapatılsa bile PostgREST’teki `200` ve `404` cevapları tablo adı tahmini için kullanılabilir. Örneğin tahmin edilen tablo varsa farklı, yoksa farklı cevap döner. Bu da yavaş ama etkili bir keşif yöntemi oluşturur.

GraphQL burada özellikle risklidir. Çünkü ekipler genelde REST tarafını düşünür, ama aynı verinin `/graphql/v1` üzerinden de erişilebilir olduğunu unutabilir.

## 2. Okuma: RLS tek başına tüm yükü taşır

Doğrudan Supabase erişiminde istemci filtreyi kendi belirler.

Örneğin istemci şunu diyebilir:

```http
GET /rest/v1/private?select=data
```

Eğer `private` tablosundaki SELECT policy yanlış yazıldıysa, tüm tablo dönebilir.

Başka bir örnek:

```http
GET /rest/v1/private?id=eq.<victim>
```

Bu istek başka bir kullanıcının satırını hedefler. RLS doğru değilse kurbanın verisi okunabilir.

Daha da kötüsü, saldırganın kurban ID listesine ihtiyacı olmayabilir. UUID alanları aralık sorgularıyla gezilebilir:

```http
GET /rest/v1/private?id=gt.<zero-uuid>
```

Bu, IDOR sınıfı bir problemdir. Yani kullanıcı, yalnızca kendi kaynağına erişmesi gerekirken başka kullanıcıların kaynaklarını da hedefleyebilir.

En kritik hata ise RLS’in hiç açılmadığı tablodur.

PostgreSQL’de bir tablo oluşturulduğunda RLS otomatik olarak aktif olmaz. Özellikle raw SQL ile tablo oluşturulduysa RLS’in ayrıca etkinleştirilmesi gerekir.

RLS kapalıysa, Supabase tarafında anon role verilmiş izinler doğrudan geçerli olur. Bu durumda tablo herkes tarafından okunabilir, yazılabilir veya silinebilir hale gelebilir.

Bu projedeki `logs` tablosu bu hatayı göstermek için vardır.

## 3. Pivot: Policy doğru olsa bile veri başka yoldan sızabilir

Bu projedeki en önemli derslerden biri şudur:

**RLS policy doğru olsa bile veri yine sızabilir.**

Örneğin `private` tablosunun SELECT policy’si doğru olabilir. Doğrudan okuma yaptığınızda yalnızca kendi satırınızı görürsünüz.

Fakat PostgREST’in **resource embedding** özelliği, ilişkili verileri tek istekte çekmeye izin verir:

```http
GET /rest/v1/public?select=*,private(*)
```

Normalde bu, frontend için kullanışlı bir JOIN benzeri davranıştır.

Risk, bu ilişkinin bir `SECURITY DEFINER` fonksiyonu üzerinden kurulmasıdır.

`SECURITY DEFINER` fonksiyonları çağıran kullanıcının yetkileriyle değil, fonksiyon sahibinin yetkileriyle çalışır. Fonksiyon sahibi yüksek yetkiliyse, RLS beklediğiniz şekilde uygulanmayabilir.

Sonuç olarak:

* `private` tablosunu doğrudan okuyunca sadece kendi satırınız gelir,
* ama `public` üzerinden embed ile okuyunca başka kullanıcıların private verileri sızabilir.

Bu çok tehlikeli bir durumdur. Çünkü geliştirici doğrudan endpoint’i test ettiğinde her şey doğru görünebilir. Fakat veri başka bir ilişki veya helper fonksiyon üzerinden yeniden açığa çıkmış olabilir.

Aynı risk RPC tarafında da vardır:

```http
POST /rest/v1/rpc/all_notes
```

Eğer bir RPC fonksiyonu `SECURITY DEFINER` olarak yazıldıysa ve içeride tüm notları döndürüyorsa, RLS policy doğru olsa bile veriyi sızdırabilir.

Kısaca:

**RLS doğru yazıldı diye sistem otomatik olarak güvenli olmaz. Veriye ulaşan tüm fonksiyonlar, ilişkiler ve expose edilen endpoint’ler de güvenli olmalıdır.**

## 4. Ölçekleme: Küçük bir sızıntı tüm tabloya dönüşür

PostgREST çok güçlü bir filtreleme yüzeyi sunar.

Örneğin:

* `or`,
* `like`,
* `not`,
* `in`,
* full-text search,
* sıralama,
* limit,
* range,
* count.

Bu özellikler uygulama geliştirirken faydalıdır. Fakat doğrudan internete açık olduklarında saldırganın elinde veri kazıma aracına dönüşebilirler.

Örneğin:

```http
GET /rest/v1/private?or=(...)
```

veya:

```http
GET /rest/v1/private?data=like.*test*
```

Bu tarz operatörler ile saldırgan veriyi parça parça arayabilir, gizli değerleri tahmin edebilir veya büyük tablo taramaları başlatabilir.

`limit=100000` gibi aşırı büyük limitler tek istekte çok fazla veri çekmeye yarar.

`Prefer: count=exact` ise veri dönmese bile gerçek satır sayısını gösterebilir. Bu da saldırgana sistemin büyüklüğü hakkında bilgi verir:

* kaç kullanıcı var,
* kaç kayıt var,
* hedef değerli mi,
* veri sızıntısı ne kadar büyük olabilir.

Proxy bu yüzden sınırsız PostgREST operatör yüzeyini açmaz. Onun yerine uygulamanın gerçekten ihtiyaç duyduğu parametreleri tipli şekilde tanımlar.

## 5. Değiştirme ve kötüye kullanım

Doğrudan PostgREST erişiminde istemci yalnızca UI’da görünen alanları değil, tabloda gerçekten var olan tüm yazılabilir kolonları gönderebilir.

Örneğin frontend normalde sadece `data` alanını güncelliyor olabilir. Ama saldırgan body içine başka kolonlar ekleyebilir:

```json
{
  "data": "test",
  "created_at": "2000-01-01",
  "role": "admin",
  "is_admin": true
}
```

Bu duruma **mass assignment** denir.

Eğer backend veya database policy bu alanları ayrıca kısıtlamıyorsa, saldırgan uygulamanın hiç göstermediği kolonları değiştirebilir.

Bu şu risklere yol açabilir:

* sahte tarih yazma,
* foreign key değiştirerek başka kullanıcıya ait ilişki kurma,
* rol veya yetki alanını değiştirme,
* internal state manipülasyonu,
* veri bütünlüğünü bozma.

RLS kapalı bir tabloda risk daha büyüktür. Anon role izinliyse saldırgan sadece veri okumaz; `INSERT`, `UPDATE` veya `DELETE` de yapabilir.

Bu projede `logs` tablosu bu davranışı göstermek için bilerek korumasız bırakılmıştır.

## 6. Rate limit yoksa saldırılar hızlanır

RLS doğru olsa bile uygulama seviyesinde rate limit olmaması ayrı bir problemdir.

Çünkü saldırgan şu işlemleri çok hızlı şekilde deneyebilir:

* tablo adı tahmini,
* kullanıcı ID tarama,
* filtre denemeleri,
* veri kazıma,
* credential stuffing,
* pahalı sorgularla sistemi yorma.

Postgres’in kendi kaynak sınırları vardır, fakat bu bir uygulama rate limit’i yerine geçmez.

Proxy bu yüzden istek hızını sınırlar. Örneğin bu projede kısa sürede çok fazla okuma isteği atıldığında 429 döner.

## 7. PostgREST dışındaki Supabase yüzeyleri

Supabase yalnızca `/rest/v1` endpoint’inden ibaret değildir.

Bir projede genelde şu yüzeyler de bulunur:

* `/graphql/v1`
* `/storage/v1`
* `/functions/v1`
* `/realtime/v1`
* `/auth/v1`

Saldırganlar sadece REST API’yi değil, bunların hepsini dener.

### Storage

Storage API üzerinden bucket listelenebilir veya obje izinleri test edilebilir.

RLS veya Storage policy gevşekse, dosya adları ve bucket yapısı sızabilir.

### Edge Functions

`/functions/v1/<fn>` public bir fonksiyon çağırma yüzeyi oluşturur.

Fonksiyon içinde auth kontrolü yoksa veya yanlış yapılmışsa, fonksiyon dışarıdan kötüye kullanılabilir.

### Realtime

Realtime WebSocket üzerinden tablo değişikliklerini canlı dinlemeye yarar.

RLS gevşekse saldırgan başka kullanıcıların yaptığı değişiklikleri gerçek zamanlı görebilir.

### Auth

Auth endpoint’leri bazı bilgileri açığa çıkarabilir:

* signup açık mı,
* email confirmation kapalı mı,
* autoconfirm var mı,
* hangi OAuth provider’lar aktif,
* redirect allowlist doğru mu.

Özellikle OAuth redirect ayarları yanlışsa, `redirect_to` parametresi open redirect veya token hırsızlığı riskine dönüşebilir.

## Proxy bu riskleri nasıl azaltır?

Proxy’nin temel yaklaşımı şudur:

**İstemciye güvenme. Supabase’i doğrudan public API gibi açma. Uygulamanın ihtiyaç duyduğu kadarını kontrollü şekilde expose et.**

Bu projedeki proxy şu kuralları uygular:

### 1. Dar API yüzeyi

Proxy sadece `public` ve `private` için route açar.

Şunlar route edilmez:

* `logs`,
* `/graphql`,
* `/rpc`,
* `/storage`,
* `/functions`,
* `/realtime`,
* `/rest/v1/` şema kökü.

Route edilmeyen her şey 404 döner.

Bu basit ama güçlü bir savunmadır: uygulamanın ihtiyacı olmayan endpoint internete açılmaz.

### 2. Token zorunluluğu

Private işlemler token olmadan kabul edilmez.

Token yoksa 401 döner.

Bu, anon key ile doğrudan tablo okuma davranışını keser.

### 3. Kullanıcı ID’si server-side zorlanır

Private veride istemcinin gönderdiği `id` filtresine güvenilmez.

Proxy her private okuma/yazma işleminde kullanıcı ID’sini token’dan çıkarır ve sorguya server-side olarak ekler:

```sql
id = auth.uid()
```

veya uygulama mantığında karşılığı:

```text
id = kullanıcının uid’si
```

Böylece istemci `id=eq.<victim>` veya `id=gt.<uuid>` gönderse bile başka kullanıcının verisini okuyamaz.

### 4. Embed ve JOIN yüzeyi kapatılır

Proxy, `select=*,private(*)` gibi embed isteklerini kabul etmez.

Bu sayede PostgREST resource embedding üzerinden `SECURITY DEFINER` veya computed relationship kaynaklı sızıntılar engellenir.

### 5. Bilinmeyen parametreler reddedilir

Proxy tüm PostgREST operatör yüzeyini açmaz.

Örneğin şunlar kabul edilmez:

* `or`,
* `like`,
* `not`,
* rastgele `select`,
* rastgele kolon filtresi,
* bilinmeyen query parametreleri.

Sadece uygulamanın kullanması gereken tipli parametreler kabul edilir.

Bilinmeyen veya izin verilmeyen parametrelerde 422 döner.

### 6. Body şeması dar tutulur

Yazma isteklerinde body serbest bırakılmaz.

Örneğin proxy yalnızca şunu kabul edebilir:

```json
{
  "data": "..."
}
```

Böylece istemci `created_at`, `role`, `is_admin` veya başka gerçek kolonlara değer göndermeye çalışsa bile istek reddedilir.

Bu, mass assignment riskini azaltır.

### 7. Limit ve rate limit uygulanır

Proxy sayfa boyutunu sınırlar.

Örneğin `limit=100000` kabul edilmez. Maksimum limit 100 gibi küçük bir değerle sınırlandırılır.

Ayrıca kısa sürede çok fazla istek gelirse 429 döner.

Bu, scraping ve enumeration hızını düşürür.

## Proxy’nin tek başına çözmediği alan: Auth redirect

Bu projede proxy bazı `/auth` endpoint’lerini forward eder.

Bu yüzden OAuth redirect güvenliği hâlâ Supabase dashboard ayarlarına bağlıdır.

Özellikle `redirect_to` değerleri allowlist ile sınırlandırılmalıdır.

Daha sıkı bir proxy tasarımında `/auth` endpoint’leri de tek tek allowlist’e alınabilir ve yalnızca gerçekten ihtiyaç duyulan auth yolları forward edilebilir.

## Ana ders

Aynı veritabanı, aynı RLS politikaları.

Direct modda istemci Supabase’in geniş API yüzeyine doğrudan ulaşır.

Proxy modunda ise istemci yalnızca uygulamanın izin verdiği dar API yüzeyini görür.

Fark şudur:

**Direct erişimde istemci filtreyi, endpoint’i ve operatörü seçer.**

**Proxy erişiminde sunucu neye izin verileceğini belirler.**

Bu proje şunu göstermeye çalışır:

RLS gereklidir ama tek başına yeterli değildir.

Güvenli bir Supabase mimarisi için şunlar birlikte düşünülmelidir:

* doğru RLS policy,
* RLS’in tüm tablolarda açık olması,
* `SECURITY DEFINER` fonksiyonlarının dikkatli kullanılması,
* RPC ve GraphQL yüzeylerinin kontrol edilmesi,
* Storage, Functions, Realtime ve Auth ayarlarının denetlenmesi,
* istemciden gelen filtrelere güvenilmemesi,
* dar ve tipli bir API katmanı,
* rate limit,
* mass assignment koruması,
* OAuth redirect allowlist’i.

Doğru güvenceye alınmış `public` ve `private` insert/update policy’leri bu demodaki ana sızıntı sebebi değildir.

Asıl problem şunlardır:

* fazla geniş SELECT policy,
* `SECURITY DEFINER` fonksiyonuyla RLS bypass edilmesi,
* RLS kapalı `logs` tablosu,
* doğrudan açılmış geniş Supabase API yüzeyi.

## Gerçek dünya araçları

`pwn-tools` canlı kontroller çalıştırır.

Realtime ayrıca not edilir, fakat doğrudan bağlanılmaz. Çünkü Realtime WebSocket kullanır; bu projedeki proxy ise yalnızca HTTP trafiğini işler.

Proxy’nin bu yüzeylere karşı verdiği cevap aynıdır:

**Uygulamanın ihtiyacı olmayan şeyi route etme.**

## Çalıştırma

1. Geçici bir Supabase projesi oluşturun.
2. `supabase/public.sql` dosyasını Supabase SQL Editor’e yapıştırıp çalıştırın.
3. Demo kullanıcılarının kayıt olabilmesi için email confirmation’ı kapatın:

   * Auth → Providers → Email → Email confirmation OFF
4. Backend için `SUPABASE_SERVICE_KEY` değerini `backend/src/.env` içine koyun.
5. Proxy’yi çalıştırın:

```bash
cd backend
./run.sh
```

Proxy `:8001` portunda çalışır.

6. Frontend’i çalıştırın:

```bash
cd frontend
pnpm i
pnpm dev
```

7. Tarayıcıda üst çubuktan **direct** ve **proxied** modları arasında geçiş yapın.

8. Saldırı testlerini çalıştırın:

```bash
cd pwn-tools
uv run python main.py test
```

Bu komut otomatik olarak 3 demo kullanıcı oluşturur.

Sonuçlarda:

* kırmızı: direct modda çalışan açıkları,
* yeşil: proxy tarafından engellenen istekleri gösterir.

Kendi test ortamınız için keşif komutu:

```bash
python main.py recon <site-url>
```

Bu komut hedef uygulamadaki Supabase URL, publishable key ve tablo yüzeylerini analiz etmeye çalışır.

Yalnızca size ait sistemlerde veya açık izin verilen test ortamlarında kullanın.
