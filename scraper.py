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
    f.write('🚀 Playwright SPA Click & Inspect Scraper Started...\n\n')

  async with async_playwright() as p:
    await log_status('Browser launching...', 'blue')
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()

    base_url = 'https://livezone.pages.dev/#/movies'

    try:
      await log_status(f'Navigating to URL: {base_url}', 'blue')
      await page.goto(base_url, timeout=60000)

      await log_status(
          'Waiting for 10 seconds to let JavaScript fully render movie cards...',
          'yellow',
      )
      await page.wait_for_timeout(10000)

      # পেজের সমস্ত মুভি কার্ড বা ছবি শনাক্ত করা
      images = page.locator('img')
      count = await images.count()

      await log_status(
          f'Total movie images found on page: {count}', 'blue'
      )
      movies_data = []

      for i in range(count):
        try:
          current_images = page.locator('img')
          if i >= await current_images.count():
            break

          img = current_images.nth(i)
          logo_url = (
              await img.get_attribute('src')
              or await img.get_attribute('data-src')
              or ''
          )

          if not logo_url:
            continue

          # কার্ডের প্যারেন্ট এলিমেন্ট বা কন্টেইনার বের করা
          parent = img.locator(
              'xpath=ancestor::a | ancestor::div[contains(@class, "card") or'
              ' contains(@class, "movie") or contains(@class, "item") or'
              ' contains(@class, "grid") or contains(@class, "cursor-pointer")]'
          ).first

          title = await img.get_attribute('alt') or ''
          if not title:
            title_elem = parent.locator('h3, h4, span, p, div').first
            if (await title_elem.count()) > 0:
              title = await title_elem.inner_text()

          if not title:
            title = 'Unknown Movie'

          # কার্ডে ক্লিক করার আগের অবস্থা এবং ক্লিকের পর ডাইনামিক লিংক বা আইডি খোঁজার লজিক
          # জাভাস্ক্রিপ্ট ইভালুয়েট করে কার্ডের ভেতরের ডাটা বা অনক্লিক হ্যান্ডলার থেকে আইডি/পাথ বের করা
          card_element = parent
          if (await card_element.count()) == 0:
            card_element = img

          # কার্ডে ক্লিক করা
          await card_element.click()
          await page.wait_for_timeout(2000)  # পপআপ বা ভিউ লোড হওয়ার জন্য অপেক্ষা

          # ক্লিকের পর পেজে নতুন কোনো ডিটেইলস লিংক, আইডি বা রাউট জেনারেট হয়েছে কি না তা চেক করা
          extracted_link = await page.evaluate('''() => {
                        // যদি মো달 বা ডিটেইলস ভিউতে কোনো ইউনিক লিংক বা ক্লোজ বাটন বা ভিডিও সোর্স থাকে
                        const activeLink = window.location.href;
                        
                        // কার্ড বা উপাদানের ভেতরের ডেটা অ্যাট্রিবিউট খোঁজা
                        const currentPath = window.location.hash;
                        return currentPath;
                    }''')

          # যদি হ্যাশ রাউট পরিবর্তন না হয়, তবে কার্ডের নিজস্ব কোনো আইডি বা ডাটা-অ্যাট্রিবিউট আছে কিনা দেখি
          detail_link = f'https://livezone.pages.dev/{extracted_link}'

          movie_info = {
              'title': title.strip(),
              'logo_url': logo_url,
              'detail_link': detail_link if detail_link else base_url,
          }

          if movie_info not in movies_data:
            movies_data.append(movie_info)
            print(
                f"[{len(movies_data)}] Title: {title.strip()} | Link:"
                f' {detail_link}'
            )

          # ব্যাক করার জন্য ব্রাউজারের ব্যাক বা আবার মূল পেজে যাওয়া
          await page.goto(base_url, timeout=60000)
          await page.wait_for_timeout(3000)

        except Exception as e:
          print(f'Error on card {i}: {str(e)}')
          try:
            await page.goto(base_url, timeout=30000)
            await page.wait_for_timeout(3000)
          except:
            pass
          continue

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies with dynamic'
            ' links!',
            'green',
        )

        output_path = os.path.abspath('movies_data.json')
        with open(output_path, 'w', encoding='utf-8') as json_file:
          json.dump(movies_data, json_file, ensure_ascii=False, indent=4)

        await log_status(
            f'Saved extracted data successfully at: {output_path}', 'green'
        )
        print(f'📁 JSON File Location: {output_path}')

      else:
        await log_status(
            'Failed to extract movies with dynamic actions.', 'red'
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
