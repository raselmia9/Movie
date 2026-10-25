import asyncio
import json
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# একসাথে কয়টি ট্যাব বা পেজ প্রসেস হবে (আপনার পিসি বা GitHub Actions-এর ক্ষমতা অনুযায়ী ৪ থেকে ৮ দিতে পারেন)
CONCURRENT_TABS = 5
TOTAL_PAGES = 716


async def scrape_page(browser, page_number):
  page = await browser.new_page()
  movies_data = []

  # ওয়েবসাইটের পেজিনেশন বা রাউটিং ইউআরএল (প্রয়োজন অনুযায়ী পরিবর্তন করুন)
  url = f'https://livezone.pages.dev/#/movies?page={page_number}'

  try:
    print(f'Opening page {page_number}...')
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(3000)  # কনটেন্ট লোড হওয়ার জন্য অপেক্ষা

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # মুভি কার্ডগুলোর সিলেক্টর (আপনার সাইটের HTML স্ট্রাকচার অনুযায়ী বদলাতে হবে)
    items = soup.select('.movie-card-class')

    for item in items:
      title_elem = item.select_one('.title')
      img_elem = item.select_one('img')
      link_elem = item.select_one('a')

      title = title_elem.text.strip() if title_elem else 'N/A'
      img = img_elem['src'] if img_elem and 'src' in img_elem else 'N/A'
      link = link_elem['href'] if link_elem and 'href' in link_elem else 'N/A'

      # আপনার দেওয়া ফরম্যাট অনুযায়ী ডেমো বা এক্সট্রাক্টেড ডিটেইলস
      details = (
          'Director : N/A\nCast(s) : N/A\nLanguage : Bengali\nQuality :'
          ' WEB-DL\nResolution : 720P\nSize : 1GB'
      )
      date = time.strftime('%m/%d/%Y %I:%M:%S %p')

      movies_data.append(
          {
              'title': title,
              'details': details,
              'img': img,
              'date': date,
              'link': link,
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

    # পেজগুলোকে ব্যাচ আকারে প্যারালালি রান করার লুপ
    for i in range(1, TOTAL_PAGES + 1, CONCURRENT_TABS):
      batch = range(i, min(i + CONCURRENT_TABS, TOTAL_PAGES + 1))
      print(f'\n--- Processing pages {list(batch)} ---')

      tasks = [scrape_page(browser, page_num) for page_num in batch]
      results = await asyncio.gather(*tasks)

      for page_result in results:
        all_movies.extend(page_result)

    await browser.close()

    # আপনার কাঙ্ক্ষিত JSON ফরম্যাটে সেভ করা
    with open('movies.json', 'w', encoding='utf-8') as f:
      json.dump(all_movies, f, ensure_ascii=False, indent=2)

    print(f'\nAll done! Total {len(all_movies)} movies saved to movies.json')


if __name__ == '__main__':
  asyncio.run(main())
