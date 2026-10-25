import asyncio
import json
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

      # সরাসরি সমস্ত <img> ট্যাগগুলো লোকেট করা (যেহেতু প্রতিটি মুভির একটি লোগো/পোস্টার ইমেজ থাকতেই হবে)
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

        # যদি লোগো বা ইমেজ লিংক খালি থাকে, তবে বাদ দেব
        if not logo_url or 'logo' in logo_url or 'icon' in logo_url:
          # সাইটের লোগো বা ছোট আইকন বাদ দিয়ে মুভির পোস্টার ফিল্টার করার জন্য
          pass

        # ইমেজের পেరেন্ট বা কার্ড এলিমেন্ট থেকে টাইটেল এবং লিংক খোঁজা
        parent = img.locator('xpath=ancestor::a | ancestor::div[contains(@class, "card") or contains(@class, "movie")]').first
        
        detail_link = ""
        title = ""
        
        try:
          # যদি প্যারেন্ট কোনো লিংক হয়
          tag_name = await parent.evaluate('el => el.tagName.toLowerCase()')
          if tag_name == 'a':
            detail_link = await parent.get_attribute('href') or ''
          else:
            # যদি কার্ডের ভেতরে কোনো <a> ট্যাগ থাকে
            link_inside = parent.locator('a').first
            if (await link_inside.count()) > 0:
              detail_link = await link_inside.get_attribute('href') or ''
              
          # টাইটেল খোঁজা
          title = await img.get_attribute('alt') or ''
          if not title or title == '':
            title_elem = parent.locator('h3, h4, span, p').first
            if (await title_elem.count()) > 0:
              title = await title_elem.inner_text()
        except:
          pass

        if not title:
          title = "Unknown Movie"

        if logo_url:
          if detail_link.startswith('/'):
            detail_link = f'https://livezone.pages.dev{detail_link}'
          elif not detail_link.startswith('http') and detail_link:
            detail_link = f'https://livezone.pages.dev/{detail_link}'

          movie_info = {
              'title': title.strip(),
              'logo_url': logo_url,
              'detail_link': detail_link if detail_link else url,
          }

          if movie_info not in movies_data:
            movies_data.append(movie_info)

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies!', 'green'
        )

        with open('movies_data.json', 'w', encoding='utf-8') as json_file:
          json.dump(movies_data, json_file, ensure_ascii=False, indent=4)
        await log_status(
            'Saved extracted data to movies_data.json successfully!', 'green'
        )

        for i, m in enumerate(movies_data[:5], 1):
          print(
              f"[{i}] Title: {m['title']} \n    Link: {m['detail_link']}\n   "
              f" Logo: {m['logo_url']}\n"
          )
      else:
        await log_status(
            'Still no movies found. The page might require scrolling or a'
            ' different selector.',
            'red',
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
