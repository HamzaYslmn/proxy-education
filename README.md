# proxy-education

Küçük bir öğretici proje. **Aynı Supabase veritabanına** iki farklı yoldan erişiliyor:

**direct**: tarayıcı → Supabase
**proxied**: tarayıcı → FastAPI proxy → Supabase

Böylece ham PostgREST erişiminin neleri açığa çıkardığını ve doğru RLS ile çalışan ince bir proxy katmanının bunları nasıl kapattığını yan yana görebilirsin. Üst bardaki anahtarla iki mod arasında geçiş yapabilirsin.

> ⚠️ **Sadece eğitim amaçlıdır.** `supabase/notsafe.sql` bilerek eklenmiş güvenlik açıkları içerir:
> RLS’i bypass eden bir `SECURITY DEFINER` fonksiyonu, aynı tuzağın RPC versiyonu ve RLS hiç açılmamış bir tablo.
> Böylece saldırılar gerçekten çalışır. `supabase/safe.sql` ise bunun sertleştirilmiş karşılığıdır.
> Bunu yalnızca sana ait, çöpe atılabilir bir Supabase projesinde çalıştır. `notsafe.sql` dosyasını asla production’a kopyalama.

## Dersin özeti

`supabase/notsafe.sql` üç bilinçli hata yerleştirir. Direct PostgREST erişimi bu hatalara takılır. Proxy ise embed kullanımını reddeder, `id = your uid` filtresini zorunlu kılar, token ister, yalnızca typed query API açar, sayfa boyutunu ve rate limit’i sınırlar, sadece `public` / `private` route eder. Bu yüzden `logs`, `/graphql`, `/rpc` ve schema root erişilemez hale gelir.

`supabase/safe.sql`, aynı iki tablonun hataları temizlenmiş halidir: RLS açık, tüm işlemler owner-only. Onu çalıştırınca direct saldırıların da sustuğunu görebilirsin.

Tablo, bir saldırganın pratikte ilerleme sırasına göre düzenlenmiştir:

**recon → read → pivot → scale → tamper/abuse**

`pwn-tools` da saldırıları bu sırayla çalıştırır.

| #  | Saldırı                                                     | Direct                                                   | Proxy                                 |
| -- | ----------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------- |
| 1  | GraphQL scan `/graphql/v1 { __schema }`                     | tüm tabloları enumerate eder                             | 404 (`/graphql` route edilmez)        |
| 2  | GraphQL read `{ privateCollection … }`                      | pg_graphql üzerinden notları sızdırır                    | 404                                   |
| 3  | Schema dump `GET /rest/v1/`                                 | OpenAPI: tüm tablo/kolon/FK bilgisi                      | 404 (root açılmaz)                    |
| 4  | Anonymous read (anon key, login yok)                        | auth olmadan veri sızdırır                               | 401 (token gerekli)                   |
| 5  | Unfiltered `private?select=data`                            | tüm tabloyu döker                                        | sadece senin satırın (`uid` zorlanır) |
| 6  | Cross-user `private?id=eq.<victim>`                         | kurbanı okur                                             | senin satırın, başkasının değil       |
| 7  | UUID enumeration `private?id=gt.<0-uuid>`                   | tüm satırları gezer (IDOR)                               | senin satırın (`gt` yok sayılır)      |
| 8  | RLS-disabled table `logs?select=*`                          | korumasız tabloyu okur                                   | 404 (route edilmez)                   |
| 9  | JOIN/embed `public?select=*,private(*)`                     | tüm kullanıcıların notlarını sızdırır                    | 422 (embeds reddedilir)               |
| 10 | RPC `/rpc/all_notes` (`SECURITY DEFINER`)                   | RLS’i bypass eder, her şeyi sızdırır                     | 404 (`/rpc` route edilmez)            |
| 11 | Filter ops `or=`, `like=`                                   | tüm PostgREST operator yüzeyi açık                       | 422 (sadece typed params)             |
| 12 | Oversized `limit=100000`                                    | tek istekte tablo scrape eder                            | 422 (limit 100 ile sınırlandırılır)   |
| 13 | Count leak (`Prefer: count=exact`)                          | tüm tablonun satır sayısını sızdırır                     | sadece senin count’un (`id` zorlanır) |
| 14 | Mass assignment (`created_at` forge etme)                   | gerçek kolonların hepsi yazılabilir                      | 422 (body sadece `data`)              |
| 15 | Anon `DELETE` on `logs`                                     | herkes RLS kapalı tabloyu silebilir                      | 404 (route edilmez)                   |
| 16 | 25 hızlı read                                               | app-level sınır yok                                      | 10/dk sonrası 429                     |
| 17 | Storage bucket list `GET /storage/v1/bucket`                | Storage API erişilebilir                                 | 404 (route edilmez)                   |
| 18 | Storage object list `POST /storage/v1/object/list/<bucket>` | SELECT RLS gevşekse bucket dosyalarını gezer             | 404 (route edilmez)                   |
| 19 | Edge `POST /functions/v1/<fn>`                              | Functions gateway erişilebilir                           | 404 (route edilmez)                   |
| 20 | Realtime `WSS /realtime/v1`                                 | canlı tablo değişiklik stream’i                          | desteklenmez (proxy HTTP-only)        |
| 21 | Auth config `GET /auth/v1/settings`                         | signup / autoconfirm / OAuth provider bilgisini sızdırır | forward edilir (Supabase config)      |
| 22 | Anonymous sign-in `POST /auth/v1/signup {}`                 | açıksa ücretsiz authenticated session verir              | forward edilir (Supabase config)      |
| 23 | OAuth `authorize?redirect_to=evil`                          | allowlist yoksa open redirect                            | forward edilir (Supabase config)      |

## Bunlar neden tehlikeli ve saldırganlar nasıl kullanır?

Direct erişimde **publishable / anon key zaten public’tir**. Tarayıcıya gömülü gelir, yani her ziyaretçi bu key’e zaten sahiptir. Bu durumda saldırgan ile verin arasındaki **tek gerçek duvar Row-Level Security’dir**.

Tek bir gevşek policy, RLS’i kapalı unutulmuş bir tablo, bir `SECURITY DEFINER` fonksiyonu veya unutulmuş bir endpoint her şeyi açığa çıkarabilir. Bir saldırganın “anon key elimde” noktasından “tüm kullanıcı verileri elimde” noktasına nasıl gittiği aşağıdaki sırayla görülebilir.

**Recon — API kendini haritalandırır.** PostgREST ve pg_graphql self-describing çalışır. `GET /rest/v1/` bir OpenAPI dokümanı döndürür. `/graphql/v1` üzerindeki `__schema` ise tüm GraphQL schema bilgisini verir: her tablo, kolon, type ve foreign key. Saldırgan kör tahmin yapmak zorunda kalmaz. Introspection kapatılsa bile PostgREST’in **200-vs-404** davranışı, tahmin edilen tablo adlarını istek istek doğrulamaya yeter.

GraphQL daha sinsi bir yüzeydir: **varsayılan olarak açıktır ve unutması kolaydır**. Ekipler REST tarafını sıkılaştırır ama aynı verinin `/graphql/v1` üzerinden erişilebilir olduğunu fark etmeyebilir.

**Read — tüm işi RLS yapar.** Okuma işlemi tek istektir. Saldırgan sadece anon key ile, login olmadan `private?select=data` isteği atar. Eğer herhangi bir SELECT policy fazla gevşekse tüm tablo döner. `id=eq.<victim>` tek bir kullanıcıyı hedefler. `id=gt.<zero-uuid>` ise **id aralığı üzerinden tüm satırları gezer**. Bu klasik IDOR’dur; kurban listesine gerek yoktur.

En kötüsü **RLS hiç açılmamış** bir tablodur (`logs`). Raw SQL ile oluşturulan tablolarda RLS varsayılan olarak **kapalıdır**. Bu, Supabase’deki en yaygın hatalardan biridir. RLS kapalıysa anon role üzerindeki default grant’ler doğrudan uygulanır ve herkes tabloyu okuyabilir.

Bunlar çalışır çünkü **filtreyi client seçer, tek gate ise veritabanıdır**.

**Pivot — policy doğru olsa bile.** Asıl tehlikeli kısım burasıdır: `private` tablosundaki SELECT policy aslında **doğrudur**. Direct read sadece kendi satırını döndürür. Fakat **resource embedding** (`public?select=*,private(*)`) ile `private`, `public` üzerinden bir **`SECURITY DEFINER` computed relationship** aracılığıyla okunur. PostgREST bu fonksiyonu embed olarak açar. Fonksiyon owner yetkisiyle çalışır ve **RLS’i tamamen bypass eder**. Böylece direct read kilitli kalırken JOIN tüm kullanıcıların satırını sızdırır.

Aynı `SECURITY DEFINER` tuzağı RPC tarafında da görülür (`/rpc/all_notes`). Açıkta kalan tek bir helper fonksiyon, policy’den bağımsız olarak her şeyi sızdırabilir. İkisi de gerçek dünyadaki Supabase ihlallerinde sık görülen sınıflardır. Ders şu: RLS policy doğru olsa bile, definer function veriyi gizlice yeniden açığa çıkarıyorsa bu yeterli değildir.

**Scale — tek satır tüm tabloya dönüşür.** PostgREST tüm **operator setini** açar: `or`, `like`, `not`, `in`, full-text ve benzeri. Doğru RLS altında bile bunlar **boolean-oracle enumeration** için kullanılabilir; gizli değerler karakter karakter çıkarılabilir. `like '%…%'` ise table-scan DoS üretir.

`limit=100000` tek istekte tüm veriyi scrape eder. `Prefer: count=exact` ise tek bir satır okumadan **kesin satır sayısını** sızdırır: kaç kullanıcın var, veri setin ne kadar büyük, ihlalin değeri ne kadar.

**Tamper & abuse.** Yazma istekleri yalnızca UI’ın kullandığı alanlara değil, **gerçek tüm kolonlara** gidebilir: `created_at`, internal `role` / `is_admin`, foreign key vb. Bu mass assignment → privilege escalation zincirine dönebilir.

Bir tabloda **RLS kapalıysa**, anon role o tabloya serbestçe `INSERT`, `UPDATE` ve **`DELETE`** atabilir. Saldırgan sadece veriyi okumaz; silebilir de. **Application-level rate limit yoksa**, yukarıdaki tüm saldırılar tam hızda çalışır: scraping, enumeration, credential stuffing. Sınır pratikte sadece Postgres olur.

**PostgREST dışı yüzeyler — diğer Supabase API’leri.** Bir proje sadece tablolardan ibaret değildir. **Storage** (`/storage/v1`) anon key ile bucket enumerate etmeye ve object permission probe etmeye izin verebilir. **Edge Functions** (`/functions/v1`) public invoke gateway açar. **Realtime** (`wss /realtime/v1`) tablo değişikliklerini canlı stream eder; gevşek RLS, diğer kullanıcıların yazmalarını gerçek zamanlı sızdırabilir. **OAuth** authorize zincirleri (`/auth/v1/authorize?redirect_to=…`) ise `redirect_to` allowlist edilmemişse token theft’e dönüşebilir.

Saldırganlar sadece REST API’yi değil, bunların hepsini yoklar.

**Proxy bunların hepsini nasıl durdurur?** Proxy çağırana asla güvenmez. **Dar ve typed bir API** açar: sadece uygulamanın ihtiyaç duyduğu kolonlar ve filtreler vardır. Her private read/write işleminde **`id = your uid` server-side zorlanır**. Embed ve bilinmeyen parametreler reddedilir (422). Gerçek token zorunludur (401). Page size ve rate limit sınırlandırılır. Route yüzeyi küçüktür: sadece `public` / `private` ve login için gereken auth endpoint’leri açıktır.

Bu yüzden `logs`, `/graphql`, `/rpc`, `/storage`, `/functions`, `/realtime` ve schema root 404 döner. Proxy’nin tek başına çözemediği nokta **OAuth redirect** güvenliğidir. `/auth` forward edildiği için redirect güvenliği Supabase dashboard’daki allowlist’e kalır. Daha sıkı bir proxy, forward ettiği auth path’lerini de allowlist edebilir.

Aynı veritabanı, aynı RLS. Fark, çağıranı hostile kabul eden bir gateway katmanıdır.

Doğru güvenceye alınmış tablolardaki write işlemleri leak’in kendisi değildir. `public` / `private` insert/update policy’leri owner-only çalışır. Açık; bozuk SELECT policy, `SECURITY DEFINER` fonksiyonu ve RLS kapalı `logs` tablosudur.

## Gerçek dünya araçları

Aynı yanlış konfigürasyonları yayımlanmış Supabase scanner’ları da arar: **supabase-pwn**, **supabomb**, **supashield**.

`pwn-tools/`, bu projenin kendi live check versiyonunu çalıştırır. Realtime not edilir ama bağlanılmaz; çünkü WebSocket kullanır ve proxy HTTP-only çalışır. Proxy’nin hepsine cevabı aynıdır: Uygulamanın ihtiyacı olmayan şeyi route etme.

## Çalıştırma

1. Çöpe atılabilir bir Supabase projesi oluştur. SQL editor’e `supabase/notsafe.sql` dosyasını yapıştır. Sertleştirilmiş sürümü görmek için `supabase/safe.sql` kullan. Demo kullanıcılarının kayıt olabilmesi için **email confirmation OFF** yap: Auth → Providers → Email.

2. **Backend:** `backend/src/.env` içinde `SUPABASE_SERVICE_KEY` ayarla, sonra çalıştır:

   ```bash
   cd backend && ./run.sh
   ```

   Proxy `:8001` üzerinde açılır.

3. **Frontend:** çalıştır:

   ```bash
   cd frontend && pnpm i && pnpm dev
   ```

   Sonra üst bardan **direct / proxied** modları arasında geçiş yap.

4. **Saldırıları gör:** çalıştır:

   ```bash
   cd pwn-tools && uv run python main.py test
   ```

   Komut otomatik olarak 3 demo kullanıcı oluşturur. Kırmızı direct, yeşil proxy sonucudur.

   Alternatif olarak bir siteden Supabase URL, key ve tablo bilgisi çıkarmak için:

   ```bash
   python main.py recon <site-url>
   ```
