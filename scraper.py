
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

START_URL = "https://livezone.pages.dev/#/movies"
OUTPUT_FILE = "movie_index.json"
MAX_PAGES = 716
WAIT_MS = 1200

CARD_SCRIPT = r"""
() => {
    const results = [];
    const seen = new Set();

    for (const img of document.querySelectorAll("img")) {
        let link = img.closest("a[href]");

        if (!link) {
            let parent = img.parentElement;

            for (let i = 0; i < 6 && parent; i++) {
                link = parent.querySelector("a[href]");
                if (link) break;
                parent = parent.parentElement;
            }
        }

        if (!link) continue;

        const url = link.href || "";
        if (!url || url.startsWith("javascript:")) continue;

        let card = link;

        for (let i = 0; i < 5 && card.parentElement; i++) {
            const text = (card.innerText || "").trim();
            if (text.length >= 2 && text.length < 700) break;
            card = card.parentElement;
        }

        const text = (card.innerText || link.innerText || "").trim();
        const heading = card.querySelector(
            "h1,h2,h3,h4,[class*='title'],[class*='name']"
        );

        const title = (
            heading?.innerText ||
            link.getAttribute("title") ||
            img.getAttribute("alt") ||
            text.split("\n")[0] ||
            ""
        ).trim().replace(/\s+/g, " ");

        const image = img.currentSrc || img.src ||
                      img.getAttribute("data-src") || "";

        const key = url + "|" + title;

        if (!title || !image || seen.has(key)) continue;

        seen.add(key);

        results.push({
            title: title,
            img: image,
            url: url,
            card_text: text
        });
    }

    return results;
}
"""


async def main():
    movies = {}
    visited_pages = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            viewport={"width": 1365, "height": 900}
        )

        print("Opening LiveZone Movies...")

        await page.goto(
            START_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        for page_number in range(1, MAX_PAGES + 1):
            cards = await page.evaluate(CARD_SCRIPT)

            signature = tuple(
                sorted(card["url"] for card in cards)
            )

            if signature and signature in visited_pages:
                print("Repeated page detected. Stopping.")
                break

            if signature:
                visited_pages.add(signature)

            added = 0

            for card in cards:
                title = card["title"].strip()
                detail_url = urljoin(page.url, card["url"])
                image_url = urljoin(page.url, card["img"])

                if "#/movies" in detail_url.rstrip("/"):
                    continue

                if detail_url not in movies:
                    movies[detail_url] = {
                        "title": title,
                        "img": image_url,
                        "url": detail_url
                    }
                    added += 1

            print(
                f"Page {page_number}: "
                f"{len(cards)} cards, "
                f"{added} new, "
                f"{len(movies)} total"
            )

            if page_number >= MAX_PAGES:
                break

            # Try common Next buttons and pagination arrows.
            next_button = page.locator(
                'button[aria-label*="next" i], '
                'a[aria-label*="next" i], '
                'button[title*="next" i], '
                'a[title*="next" i]'
            ).first

            try:
                if await next_button.count() and \
                   await next_button.is_visible() and \
                   await next_button.is_enabled():

                    await next_button.click(timeout=3000)
                    await page.wait_for_timeout(WAIT_MS)
                    continue

            except Exception:
                pass

            candidates = page.locator(
                'button, a, [role="button"]'
            )

            clicked = False
            count = await candidates.count()

            for i in range(min(count, 250)):
                element = candidates.nth(i)

                try:
                    if not await element.is_visible():
                        continue

                    label = (
                        await element.inner_text()
                    ).strip().lower()

                    aria = (
                        await element.get_attribute("aria-label")
                        or ""
                    ).lower()

                    if label in {"next", "›", "❯", "→", "»"} \
                       or "next" in aria:

                        disabled = await element.get_attribute(
                            "disabled"
                        )

                        aria_disabled = await element.get_attribute(
                            "aria-disabled"
                        )

                        if disabled is None and aria_disabled != "true":
                            await element.click(timeout=3000)
                            await page.wait_for_timeout(WAIT_MS)
                            clicked = True
                            break

                except Exception:
                    continue

            if not clicked:
                print("Next-page control not found.")
                break

        await browser.close()

    output = list(movies.values())

    Path(OUTPUT_FILE).write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nFinished: {len(output)} movies saved.")
    print(f"Output: {OUTPUT_FILE}")

    if not output:
        print(
            "No cards detected. The site's actual DOM/API "
            "may require adjusting the selectors."
        )


if __name__ == "__main__":
    asyncio.run(main())
