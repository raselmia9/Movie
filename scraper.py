
import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

START_URL = "https://livezone.pages.dev/#/movies"
OUTPUT = "debug_report.json"

responses = []
api_candidates = []


def inspect_json(data, source_url):
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            keys = {str(k).lower(): k for k in obj.keys()}

            title_key = next(
                (keys[k] for k in ("title", "name", "moviename")
                 if k in keys), None
            )
            image_key = next(
                (keys[k] for k in (
                    "img", "image", "poster", "thumbnail",
                    "logo", "posterurl", "imageurl"
                ) if k in keys), None
            )
            link_key = next(
                (keys[k] for k in (
                    "url", "link", "href", "detailurl",
                    "watchurl", "slug", "id"
                ) if k in keys), None
            )

            if title_key and image_key:
                title = obj.get(title_key)
                image = obj.get(image_key)

                if isinstance(title, str) and isinstance(image, str):
                    found.append({
                        "title": title.strip(),
                        "img": image,
                        "url": str(obj.get(link_key, "")) if link_key else "",
                        "source_api": source_url
                    })

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return found


async def main():
    all_records = {}
    network_urls = set()
    api_records = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def on_response(response):
            url = response.url

            if url.startswith(("data:", "blob:")):
                return

            content_type = response.headers.get("content-type", "")
            if "json" not in content_type.lower():
                return

            network_urls.add(url)

            try:
                data = await response.json()
                candidates = inspect_json(data, url)

                if candidates:
                    api_records[url] = candidates
                    print(
                        "JSON CANDIDATE:",
                        url,
                        "| records:", len(candidates)
                    )
            except Exception:
                pass

        page.on("response", on_response)

        print("Opening LiveZone...")
        await page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )
        await page.wait_for_timeout(8000)

        print("Current URL:", page.url)
        print("Page title:", await page.title())

        # Report actual DOM counts instead of assuming card selectors.
        dom_info = await page.evaluate("""() => ({
            images: document.images.length,
            anchors: document.querySelectorAll('a[href]').length,
            buttons: document.querySelectorAll('button').length,
            bodyText: (document.body?.innerText || '').slice(0, 2500),
            imagesSample: Array.from(document.images).slice(0, 15).map(i => ({
                alt: i.alt,
                src: i.currentSrc || i.src
            })),
            linksSample: Array.from(document.querySelectorAll('a[href]'))
                .slice(0, 25).map(a => ({
                    text: (a.innerText || '').trim().slice(0, 100),
                    href: a.href
                }))
        })""")

        print("DOM images:", dom_info["images"])
        print("DOM links:", dom_info["anchors"])

        # Give delayed API requests time to finish.
        await page.wait_for_timeout(4000)

        # Save a diagnostic report so we can identify the actual API.
        report = {
            "page_title": await page.title(),
            "current_url": page.url,
            "dom": dom_info,
            "json_response_urls": sorted(network_urls),
            "api_candidates": api_records
        }

        Path(OUTPUT).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        await browser.close()

    print("\nDiagnostic report saved:", OUTPUT)
    print("JSON responses:", len(network_urls))
    print("Candidate APIs:", len(api_records))

    # Produce a preliminary list if JSON objects were recognized.
    for source, records in api_records.items():
        for record in records:
            title = record["title"]
            image = record["img"]
            url = record["url"]

            if not title or not image:
                continue

            key = url or (title + "|" + image)
            all_records[key] = {
                "title": title,
                "details": "",
                "img": image,
                "date": "",
                "link": ""
            }

    if all_records:
        Path("movies.json").write_text(
            json.dumps(list(all_records.values()),
                       ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print("Preliminary movies.json:", len(all_records), "records")


if __name__ == "__main__":
    asyncio.run(main())
