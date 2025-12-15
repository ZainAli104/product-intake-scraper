"""
N8N-Compatible List Scraper for Best Buy
Use this in N8N Code Node to scrape the first product from Best Buy search results.
"""

import time
from typing import Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

try:
    import chromedriver_binary
except ImportError:
    pass


def scrape_bestbuy_first_product(search_url: str) -> Dict:
    """
    Scrape the first product from a Best Buy search/list page.

    Args:
        search_url (str): The Best Buy search/list page URL

    Returns:
        Dict: Product info with keys: name, link, full_url, image, sku, status, message

    Example:
        result = scrape_bestbuy_first_product("https://www.bestbuy.com/site/searchpage.jsp?st=iphone")
        print(result['full_url'])  # Use this URL with main scraper
    """

    result = {
        'status': 'success',
        'message': '',
        'name': 'Not found',
        'link': 'Not found',
        'full_url': 'Not found',
        'image': 'Not found',
        'sku': 'Not found'
    }

    # Validate URL
    if not isinstance(search_url, str):
        result['status'] = 'error'
        result['message'] = 'search_url must be a string'
        return result

    if 'bestbuy.com' not in search_url or ('searchpage' not in search_url and '/site/' not in search_url):
        result['status'] = 'error'
        result['message'] = 'Invalid Best Buy search/list URL'
        return result

    driver = None
    try:
        # Set up Chrome/Chromium options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--headless')
        # Use Chromium binary if available (for Docker)
        import os
        if os.path.exists('/usr/bin/chromium'):
            chrome_options.binary_location = '/usr/bin/chromium'

        # Initialize webdriver
        driver = webdriver.Chrome(options=chrome_options)

        # Load page
        driver.get(search_url)
        time.sleep(3)

        # Try to close country/region selection modal
        try:
            us_button = driver.find_element(By.XPATH, "//*[contains(text(), 'United States')]")
            driver.execute_script("arguments[0].click();", us_button)
            time.sleep(2)
        except:
            pass  # Modal might not exist

        # Wait for products to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/product/')]"))
            )
        except:
            pass

        # Scroll to load products
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(2)

        # Parse page
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract first product
        product_links = soup.find_all('a', href=lambda x: x and '/product/' in x)

        if not product_links:
            # Try alternative selector
            product_containers = soup.find_all('div', class_=lambda x: x and 'sku-item' in x.lower())
            if product_containers:
                first_product = product_containers[0]
                product_link_elem = first_product.find('a', href=lambda x: x and '/product/' in x)
                if product_link_elem:
                    product_links = [product_link_elem]

        if product_links:
            first_product_link = product_links[0]
            product_url = first_product_link.get('href', '')

            if product_url:
                # Extract product name
                product_name = first_product_link.get_text(strip=True)
                if not product_name:
                    product_name = first_product_link.get('title', '')

                # Build full URL
                base_url = 'https://www.bestbuy.com'
                if product_url.startswith('http'):
                    full_url = product_url
                else:
                    full_url = base_url + product_url

                # Extract SKU from URL
                parts = product_url.split('/')
                sku = 'Not found'
                if len(parts) > 0:
                    last_part = parts[-1]
                    if last_part and not last_part.startswith('?'):
                        sku = last_part.split('?')[0]

                # Extract image
                image_url = 'Not found'
                try:
                    img_elem = first_product_link.find('img')
                    if not img_elem:
                        parent = first_product_link.parent
                        while parent and parent.name != 'body':
                            img_elem = parent.find('img')
                            if img_elem:
                                break
                            parent = parent.parent

                    if img_elem:
                        src = img_elem.get('src') or img_elem.get('data-src')
                        if src:
                            image_url = src
                except:
                    pass

                # Update result
                result['name'] = product_name if product_name else 'Not found'
                result['link'] = product_url
                result['full_url'] = full_url
                result['image'] = image_url
                result['sku'] = sku
                result['message'] = f'Found product: {result["name"]}'
        else:
            result['status'] = 'error'
            result['message'] = 'No products found on page'

    except Exception as e:
        result['status'] = 'error'
        result['message'] = f'Scraping failed: {str(e)}'

    finally:
        if driver:
            driver.quit()

    return result
