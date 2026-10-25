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
    f.write('🚀 Playwright Click-Based Scraper Started...\n\n')

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

      images = page.locator('img')
      count = await images.count()

      await log_status(
          f'Total movie images found on page: {count}', 'blue'
      )
      movies_data = []

      # সুরক্ষার জন্য আমরা সর্বোচ্চ যতগুলো কার্ড পাওয়া যায় অথবা প্রথম কয়েকটি লুপ চালিয়ে চেক করতে পারি
      # এখানে সব কার্ডের ওপর লুপ চালানো হচ্ছে
      for i in range(count):
        try:
          # প্রতিবার ফ্রেশভাবে পেজ থেকে ইমেজ ও কার্ড লোকেট করা (স্টেল এলিমেন্ট এড়াতে)
          current_images = page.locator('img')
          if i >= await current_images.count():
            break

          img = current_images.nth(i)
          logo_url = (
              await img.get_attribute('src')
              or await img.get_attribute('data-src')
              or ''
          )

          # লোগো বা আইকন ফিল্টার করার জন্য (যদি খুব ছোট সাইজ বা লোগো হয়)
          if not logo_url:
            continue

          # মুভির টাইটেল সংগ্রহ করা
          parent = img.locator(
              'xpath=ancestor::a | ancestor::div[contains(@class, "card") or'
              ' contains(@class, "movie") or contains(@class, "item") or'
              ' contains(@class, "grid")]'
          ).first

          title = await img.get_attribute('alt') or ''
          if not title:
            title_elem = parent.locator('h3, h4, span, p, div').first
            if (await title_elem.count()) > 0:
              title = await title_elem.inner_text()

          if not title:
            title = 'Unknown Movie'

          # কার্ডে ক্লিক করার জন্য এলিমেন্ট নির্ধারণ (প্যারেন্ট বা কার্ডের ওপর ক্লিক করব)
          card_element = img.locator(
              'xpath=ancestor::div[contains(@class, "card") or'
              ' contains(@class, "movie") or contains(@class, "item")]'
          ).first
          if (await card_element.count()) == 0:
            card_element = parent

          # কার্ডে ক্লিক করা
          await card_element.click()

          # ডিটেইলস পেজ লোড হওয়ার জন্য ২ সেকেন্ড অপেক্ষা করা
          await page.wait_for_timeout(2500)

          # বর্তমান ডিটেইলস পেজের ইউআরএল সংগ্রহ করা
          detail_link = page.url

          # ডেটা ডিকশনারিতে যুক্ত করা
          movie_info = {
              'title': title.strip(),
              'logo_url': logo_url,
              'detail_link': detail_link,
          }

          if movie_info not in movies_data:
            movies_data.append(movie_info)
            print(
                f"[{len(movies_data)}] Title: {title.strip()} | Link:"
                f' {detail_link}'
            )

          # আবার মূল মুভিজ পেজে ফিরে যাওয়া
          await page.goto(base_url, timeout=60000)
          await page.wait_for_timeout(3000)  # পেজ রি-লোড হওয়ার জন্য অপেক্ষা

        except Exception as e:
          print(f'Error processing card {i}: {str(e)}')
          # কোনো কারণে এরর হলে মূল পেজে ব্যাক করার চেষ্টা করা
          try:
            await page.goto(base_url, timeout=30000)
            await page.wait_for_timeout(3000)
          except:
            pass
          continue

      if len(movies_data) > 0:
        await log_status(
            f'Successfully extracted {len(movies_data)} movies with real'
            ' detail links!',
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
            'Failed to extract movies with click action.', 'red'
        )

    except Exception as e:
      await log_status(f'An error occurred: {str(e)}', 'red')

    finally:
      await browser.close()
      await log_status('Browser closed successfully.', 'blue')


if __name__ == '__main__':
  asyncio.run(scrape_page())
