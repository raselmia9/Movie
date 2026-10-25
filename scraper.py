import asyncio
import json
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# পরীক্ষামূলকভাবে শুধু ১০টি পেজ নিয়ে কাজ করব
CONCURRENT_TABS = 3
TOTAL_PAGES = 10


async def scrape_page(browser, page_number):
  page = await browser.new_page()
  movies_data = []

  # ওয়েবসাইটের পেজিনেশন বা রাউটিং ইউআরএল (প্রয়োজন অনুযায়ী পরিবর্তন করতে হবে)
  url = f'https://livezone.pages.dev/#/movies?page={page_number}'

  try:
    print(f'Opening page {page_number}...')
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(
        4000
    )  # JavaScript পুরোপুরি লোড হওয়ার জন্য কিছুটা বেশি সময় দেওয়া

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # ⚠️ এখানে সাইটের আসল HTML ক্লাস নেম বসাতে হবে।
    # বর্তমানে ডিফল্ট ডেমো ক্লাস দেওয়া আছে, যা আপনার সাইটের স্ট্রাকচার অনুযায়ী বদলাতে হবে।
    items = soup.select('.movie-card')  # উদাহরণস্বরূপ ক্লাস

    print(f'Page {page_number}: Found {len(items)} items.')

    for item in items:
      # সঠিক ট্যাগ বা ক্লাস দিয়ে এগুলো ধরতে হবে
      title_elem = item.select_one('.title')
      img_elem = item.select_one('img')
      link_elem = item.select_one('a')

      title = title_elem.text.strip() if title_elem else None
      img = (
          img_elem['src']
          if img_elem and img_elem.has_attr('src')
          else (
              img_elem['data-src']
              if img_elem and img_elem.has_attr('data-src')
              else None
          )
      )
      link = (
          link_elem['href'] if link_elem and link_elem.has_attr('href') else None
      )

      # যদি কোনোটার ডেটা না পাওয়া যায়, তবে সেটি স্কিপ বা ডিবাগ করা যাবে
      if not title and not img:
        continue

      if link and not link.startswith('http'):
        link = f'https://livezone.pages.dev{link}'

      # আপনার কাঙ্ক্ষিত ফরম্যাট অনুযায়ী ডেটা সাজানো
      details = (
          'Director : N/A\nCast(s) : N/A\nLanguage : Bengali\nQuality :'
          ' WEB-DL\nResolution : 720P\nSize : 1GB'
      )
      date = time.strftime('%m/%d/%Y %I:%M:%S %p')

      movies_data.append(
          {
              'title': title if title else 'N/A',
              'details': details,
              'img': img if img else 'N/A',
              'date': date,
              'link': link if link else 'N/A',
          }
      )

    print(f'Successfully scraped Page {page_number}')

  except Exception as e:
    print(f'Error on page {page_number}: {e}')
  finally:
    await page.close()

  return movies_data


async def main():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    all_movies = []

    for i in range(1, TOTAL_PAGES + 1, CONCURRENT_TABS):
      batch = range(i, min(i + CONCURRENT_TABS, TOTAL_PAGES + 1))
      print(f'\n--- Processing pages {list(batch)} ---')

      tasks = [scrape_page(browser, page_num) for page_num in batch]
      results = await asyncio.gather(*tasks)

      for page_result in results:
        all_movies.extend(page_result)

    await browser.close()

    # ফলাফল সেভ করা
    with open('movies.json', 'w', encoding='utf-8') as f:
      json.dump(all_movies, f, ensure_ascii=False, indent=2)

    print(
        f'\nTest completed! Total {len(all_movies)} movies saved to movies.json'
    )


if __name__ == '__main__':
  asyncio.run(main())
