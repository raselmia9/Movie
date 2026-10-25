import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def log_status(message, color_type='blue'):
  # কালারফুল ডট ম্যাপিং
  dots = {'green': '🟢', 'red': '🔴', 'blue': '🔵', 'yellow': '🟡'}
  dot = dots.get(color_type, '🔵')

  status_text = f'{dot} {message}\n'
  print(status_text.strip())

  # status.txt ফাইলে স্ট্যাটাস লেখা (টাইম ছাড়া)
  with open('status.txt', 'a', encoding='utf-8') as f:
    f.write(status_text)


async def scrape_page():
  # প্রতিবার রান করার সময় আগের status.txt ফাইলটি পরিষ্কার করে নতুন করে শুরু করা
  with open('status.txt', 'w', encoding='utf-8') as f:
    f.write('🚀 Scraper Started Debugging Process...\n\n')

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

      # সম্পূর্ণ পেজের রেন্ডার্ড HTML কোড একটি ফাইলে সেভ করা
      html_content = await page.content()
      with open('page_source.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
      await log_status(
          'Successfully saved full page source to page_source.html', 'green'
      )

      # BeautifulSoup দিয়ে এলিমেন্ট চেক করা
      soup = BeautifulSoup(html_content, 'html.parser')
      images = soup.find_all('img')
      links = soup.find_all('a')
      await log_status(
          f'Found {len(images)} images and {len(links)} links on the page.',
          'green',
      )

      if len(images) > 0 and len(links) > 0:
        await log_status(
            'Elements detected successfully! Ready for mapping.', 'green'
        )
      else:
        await log_status(
            'Failed to find expected elements. Check page_source.html for'
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
