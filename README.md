# Next Stop Packers Movers — local clone

Static clone of [https://www.nextstoppackersmovers.com](https://www.nextstoppackersmovers.com).

All **35 sitemap pages** are included, plus 404 pages, form targets, and assets (CSS, JS, images, fonts).

## Run locally

```bash
cd /Users/jeetsharma/nextstop-packers-movers
python3 -m http.server 8765
```

Open [http://localhost:8765](http://localhost:8765).

## Pages cloned

**Core**
- `index.html` — Home
- `about.html`
- `certificates.html`
- `citywise.html`
- `pricing.html`
- `enquiry.html`
- `contact.html`
- `faqs.html`
- `beaware-of-fraud.html`
- `page404.html`

**Services (9)**
- `home-shifting-service.html`
- `office-shifting-service.html`
- `vehicale-transportation-services.html`
- `warehousing-and-storage-service.html`
- `packing-and-unpacking-service.html`
- `loading-unloading-service.html`
- `door-to-door-service.html`
- `local-area-shifting-service.html`
- `goods-insurance-service.html`

**Citywise locations (12)**
- `packers-and-movers-adyar.html`
- `packers-and-movers-tambaram.html`
- `packers-and-movers-omr-road.html`
- `packers-and-movers-velachery.html`
- `packers-and-movers-ecr-road.html`
- `packers-and-movers-alwarpet.html`
- `packers-and-movers-mrc-nagar.html`
- `packers-and-movers-navalur.html`
- `packers-and-movers-anna-nagar.html`
- `packers-and-movers-kk-nagar.html`
- `packers-and-movers-nungambakkam.html`
- `packers-and-movers-guduvancheri.html`

**Legal**
- `privacy-policy.html`
- `cookie-policy.html`
- `term-and-conditions.html`
- `disclaimer.html`
- `cancel-and-refund-policy.html`

The live site also links three service URLs that already 404 on production (`cargo-service.html`, `international-relocation-service.html`, `logistics-and-transporation-service.html`). Those are included as the same 404 page.

## Notes

- Layout, CSS, JS, images, and fonts are copied from the live site.
- Quote forms still post to the original PHP endpoints; `captcha.php` is server-side and will not generate new codes locally.
- Google Ads / Maps embeds stay pointed at the live third-party URLs.
