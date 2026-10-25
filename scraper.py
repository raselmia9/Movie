import asyncio
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def log_status(message, color_type='blue'):
  # কালারফুল ডট ম্যাপিং
  dots = {'green': '🟢', 'red': '🔴', 'blue': '🔵', 'yellow': '🟡'}
  dot = dots.get(color_type, '🔵')

  status_text = f'{dot} {message}\n'
  print(status_text.strip())

  # status.txt ফাইলে স্ট্যাটাস লেখা
  with open('status.txt', 'a', encoding='utf-8') as f:
    f.write(status_text)


async def scrape_page():
  # প্রতিবার রান করার সময় আগের status.txt ফাইলটি পরিষ্কার করে নতুন করে শুরু করা
  with open('status.txt', 'w', encoding='utf-8') as f:
    f.write('🚀 Scraper Started Extraction Process...\n\n')

  async with async_playwright() as p:
    await log_status('Browser launching...', 'blue')
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    url = 'https://livezone.pages.dev/#/movies'

    try:
      await log_status(f'Navigating to URL: {url}', 'blue')
      await page.goto(url, timeout=60000)

      await log_status(
          'Waiting for 5 seconds to let JavaScript render elements...', 'yellow'
      )
      await page.wait_for_timeout(5000)

      # সম্পূর্ণ পেজের রেন্ডার্ড HTML কোড সংগ্রহ করা
      html_content = await page.content()
      with open('page_source.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
      await log_status(
          'Successfully saved full page source to page_source.html', 'green'
      )

      # BeautifulSoup দিয়ে পার্স করা
      soup = BeautifulSoup(html_content, 'html.parser')

      movies_data = []

      # মুভি কার্ড বা লিংকগুলো খুঁজে বের করার লজিক
      # সাইটের স্ট্রাকচার অনুযায়ী সমস্ত সম্ভাব্য 'a' ট্যাগ বা কার্ড চেক করা হচ্ছে যাতে img এবং text আছে
      cards = soup.find_all('a')

      await log_status('Extracting movie details (Title, Logo, Link)...', 'blue')

      for card in cards:
        img = card.find('img')
        if img:
          # মুভির টাইটেল খোঁজা (ট্যাগ বা ইমেজের alt অ্যাট্রিবিউট থেকে)
          title_tag = card.find(['h3', 'h4', 'span', 'p'])
          title = (
              title_tag.get_text(strip=True)
              if title_tag
              else img.get('alt', 'N/A')
          )

          # যদি টাইটেল খুব ছোট বা ফালতু হয়, alt চেক করতে পারেন
          if not title or title == 'N/A':
            title = img.get('alt', 'Unknown Movie')

          logo_url = img.get('src') or img.get('data-src') or ''
          detail_link = card.get('href') or ''

          # বৈধ লিংক এবং লোগো থাকলে লিস্টে যুক্ত করা
          if detail_link and logo_url:
            # যদি হ্যাশ বা রিলেটিভ লিংক হয়
            if detail_link.startswith('/'):
              detail_link = f'https://livezone.pages.dev{detail_link}'

            movie_info = {
                'title': title,
                'logo_url': logo_url,
                'detail_link': detail_link,
            }

            # ডুপ্লিকেট এড়াতে চেক করা
            if movie_info not in movies_data:
              movies_data.append(movie_info)

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies!', 'green'
        )

        # সংগৃহীত ডেটা JSON ফাইলে সেভ করা
        with open('movies_data.json', 'w', encoding='utf-8') as json_file:
          json.dump(movies_data, json_file, ensure_ascii=False, indent=4)
        await log_status(
            'Saved extracted data to movies_data.json successfully!', 'green'
        )

        # কনসোলে প্রথম ৫টি মুভির তথ্য প্রিন্ট করে দেখানো
        for i, m in enumerate(movies_data[:5], 1):
          print(
              f"[{i}] Title: {m['title']} \n    Link: {m['detail_link']}\n   "
              f" Logo: {m['logo_url']}\n"
          )
      else:
        await log_status(
            'Failed to extract movies. Please check page_source.html'
            ' structure.',
            'red',
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
