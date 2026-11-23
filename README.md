# Getaway Grid website

The website of the [Getaway Grid](https://www.youtube.com/channel/UCxIEYej2cN1V1TJPKy382-w) YouTube channel. It updates itself.

## How it works

- Every hour, GitHub runs `.github/workflows/update-site.yml`.
- `generator/fetch.py` asks the YouTube Data API for the channel's uploads. It keeps **only public videos** (`status.privacyStatus == "public"`), so private, unlisted and scheduled videos never show up. It marks Shorts as videos of 3 minutes or less that are vertical or open at `youtube.com/shorts/…`.
- `generator/build.py` turns that list into plain HTML pages in `_site/`: home, all videos, Shorts, one page per video, and About. It also writes the sitemap and Open Graph tags.
- GitHub Pages publishes `_site/`.

The API key is a read-only key kept in the repo secret `YT_API_KEY`. It is never in the code. The site never uses YouTube login tokens.

## Things you can change

- Tagline and About text: `site.config.json`
- Colors and layout: `static/assets/style.css`
- Logo and icons: `static/assets/`

After a change is pushed, the site rebuilds by itself. To force an update right away, open the **Actions** tab, then **Update site**, then **Run workflow**.

## Use your own domain (for example getawaygrid.com)

1. Buy the domain from any registrar (Namecheap, Cloudflare, Porkbun…).
2. In the registrar's DNS settings, add:
   - for `www`: a **CNAME** record pointing to `YOUR-GITHUB-NAME.github.io`
   - for the bare domain (`@`): four **A** records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
3. On GitHub, open the repo's **Settings**, then **Pages**, then **Custom domain**. Type `www.yourdomain.com`, click **Save**, and once the check passes, tick **Enforce HTTPS**.
4. In **Settings**, open **Secrets and variables**, then **Actions**, then the **Variables** tab. Add a variable named `CUSTOM_DOMAIN` with the value `www.yourdomain.com`, so every rebuild keeps the domain.
5. Run the workflow once. Links, the sitemap and share previews switch to the new address by themselves.

DNS changes can take anywhere from a few minutes to a day.
