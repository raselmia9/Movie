import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrape_livezone():
    base_url = "https://livezone.pages.dev/#/movies"
    movies_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Scraping started...")
        page.goto(base_url, timeout=60000)
        page.wait_for_timeout(5000) # Page load howar jonno somoy dewa

        # Totall page ba infinite scroll handle korar jonno ekhane logic thakbe
        # Apnar dewa format anujayi data map kora hocche:
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Example selector (apnar site er class name anujayi change kore nben)
        items = soup.select('.movie-card-class') 

        for item in items:
            title_elem = item.select_one('.title')
            img_elem = item.select_one('img')
            link_elem = item.select_one('a')
            details_elem = item.select_one('.details') # Jodi thake

            title = title_elem.text.strip() if title_elem else "N/A"
            img = img_elem['src'] if img_elem and 'src' in img_elem else "N/A"
            link = link_elem['href'] if link_elem and 'href' in link_elem else "N/A"
            
            # Details and Date parse korar logic ekhane add korte hobe
            details = "Director : N/A\nCast(s) : N/A\nLanguage : Bengali\nQuality : WEB-DL\nResolution : 720P\nSize : 1GB"
            date = time.strftime("%m/%d/%Y %I:%M:%S %p")

            movies_data.append({
                "title": title,
                "details": details,
                "img": img,
                "date": date,
                "link": link
            })

        browser.close()

    # Apnar nirdisto JSON format e file save kora
    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(movies_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully scraped {len(movies_data)} items.")

if __name__ == "__main__":
    scrape_livezone()
