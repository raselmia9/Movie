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
          'Waiting for 8 seconds to let JavaScript fully render movie cards...',
          'yellow',
      )
      await page.wait_for_timeout(8000)

      # প্লেরাইটের নিজস্ব লকেটর ব্যবহার করে মুভির কার্ড বা লিংকগুলো সরাসরি সিলেক্ট করা
      # সাইটের স্ট্রাকচার অনুযায়ী সাধারণত মুভি কার্ডগুলো 'a' ট্যাগের ভেতরে থাকে যাতে ছবি ও নাম থাকে
      movie_elements = page.locator('a')
      count = await movie_elements.count()

      await log_status(f'Total interactive links found: {count}', 'blue')
      movies_data = []

      for i in range(count):
        element = movie_elements.nth(i)

        # কার্ডের ভেতর img আছে কি না চেক করা
        img_locator = element.locator('img')
        if (await img_locator.count()) > 0:
          logo_url = (
              await img_locator.first.get_attribute('src')
              or await img_locator.first.get_attribute('data-src')
              or ''
          )
          detail_link = await element.get_attribute('href') or ''

          # মুভির টাইটেল খোঁজা (হেডিং, স্প্যান বা ইমেজের alt থেকে)
          title = ''
          for tag in ['h3', 'h4', 'span', 'div', 'p']:
            title_loc = element.locator(tag)
            if (await title_loc.count()) > 0:
              text = await title_loc.first.inner_text()
              if text and len(text.strip()) > 1:
                title = text.strip()
                break

          # যদি টেক্সট না পাওয়া যায়, তবে alt ট্যাগ ব্যবহার করা
          if not title:
            title = await img_locator.first.get_attribute('alt') or 'Unknown'

          # লিংক এবং লোগো থাকলে ডেটা লিস্টে যোগ করা
          if logo_url or title != 'Unknown':
            if detail_link.startswith('/'):
              detail_link = f'https://livezone.pages.dev{detail_link}'
            elif not detail_link.startswith('http'):
              detail_link = f'https://livezone.pages.dev/{detail_link}'

            movie_info = {
                'title': title,
                'logo_url': logo_url,
                'detail_link': detail_link,
            }

            if movie_info not in movies_data and logo_url:
              movies_data.append(movie_info)

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies using'
            ' Playwright!',
            'green',
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
            'Failed to extract movies. Please check if selectors need'
            ' adjustment.',
            'red',
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
