import asyncio
import json
import os
from playwright.async_api import async_playwright


async def log_status(message, color_type='blue'):
  dots = {'green': '🟢', 'red': '🔴', 'blue': '🔵', 'yellow': '🟡'}
  dot = dots.get(color_type, '🔵')

  status_text = f'{dot} {message}\n'
  print(status_text.strip())

  with open('status.txt', 'a', encoding='utf-8') as f:
    f.write(status_text)


async def scrape_page():
  with open('status.txt', 'w', encoding='utf-8') as f:
    f.write('🚀 Playwright Scraper Started Extraction Process...\n\n')

  async with async_playwright() as p:
    await log_status('Browser launching...', 'blue')
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    url = 'https://livezone.pages.dev/#/movies'

    try:
      await log_status(f'Navigating to URL: {url}', 'blue')
      await page.goto(url, timeout=60000)

      await log_status(
          'Waiting for 10 seconds to let JavaScript fully render movie cards...',
          'yellow',
      )
      await page.wait_for_timeout(10000)

      images = page.locator('img')
      count = await images.count()

      await log_status(f'Total images found on page: {count}', 'blue')
      movies_data = []

      for i in range(count):
        img = images.nth(i)
        logo_url = (
            await img.get_attribute('src')
            or await img.get_attribute('data-src')
            or ''
        )

        # ইমেজের প্যারেন্ট বা কার্ড কন্টেইনার লোকেট করা
        parent = img.locator(
            'xpath=ancestor::a | ancestor::div[contains(@class, "card") or'
            ' contains(@class, "movie") or contains(@class, "item") or'
            ' contains(@class, "grid")]'
        ).first

        detail_link = ''
        title = ''

        try:
          # జాভাস্ক্রিপ্ট ইভালুয়েশনের মাধ্যমে সঠিক ডিটেইলস লিংক (href বা full URL) সংগ্রহ করা
          detail_link = await parent.evaluate('''el => {
                        let aTag = el.tagName.toLowerCase() === 'a' ? el : el.querySelector('a');
                        if (!aTag) {
                            // যদি কার্ডের ভেতরে বা চারপাশে অন্য কোনো ক্লিকএবল ট্যাগ থাকে
                            aTag = el.closest('a') || el.querySelector('[href]') || el.querySelector('[to]');
                        }
                        if (aTag) {
                            return aTag.href || aTag.getAttribute('href') || aTag.getAttribute('to') || '';
                        }
                        return '';
                    }''')

          title = await img.get_attribute('alt') or ''
          if not title:
            title_elem = parent.locator('h3, h4, span, p, div').first
            if (await title_elem.count()) > 0:
              title = await title_elem.inner_text()
        except:
          pass

        if not title:
          title = 'Unknown Movie'

        # লিংকের ফরম্যাট ঠিক করা
        if detail_link:
          if detail_link.startswith('/'):
            detail_link = f'https://livezone.pages.dev{detail_link}'
          elif not detail_link.startswith('http'):
            if not detail_link.startswith('#'):
              detail_link = f'https://livezone.pages.dev/#{detail_link}'
            else:
              detail_link = f'https://livezone.pages.dev/{detail_link}'
        else:
          detail_link = url

        if logo_url:
          movie_info = {
              'title': title.strip(),
              'logo_url': logo_url,
              'detail_link': detail_link,
          }

          if movie_info not in movies_data:
            movies_data.append(movie_info)

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies with links!',
            'green',
        )

        output_path = os.path.abspath('movies_data.json')
        with open(output_path, 'w', encoding='utf-8') as json_file:
          json.dump(movies_data, json_file, ensure_ascii=False, indent=4)

        await log_status(
            f'Saved extracted data successfully at: {output_path}', 'green'
        )
        print(f'📁 JSON File Location: {output_path}')

        for i, m in enumerate(movies_data[:5], 1):
          print(
              f"[{i}] Title: {m['title']} \n    Link: {m['detail_link']}\n   "
              f" Logo: {m['logo_url']}\n"
          )
      else:
        await log_status(
            'Still no movies found. Please check selectors.', 'red'
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
