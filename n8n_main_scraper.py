"""
N8N-Compatible Main Scraper for Best Buy
Use this in N8N Code Node to scrape full product details including UPC.
"""

import time
import re
from typing import Dict, Optional, List
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


def scrape_bestbuy_product(product_url: str) -> Dict:
    """
    Scrape detailed product information from a Best Buy product page.

    Args:
        product_url (str): The Best Buy product page URL

    Returns:
        Dict: Complete product information including:
              - url, name, price, rating, review_count
              - sku, upc, model, availability, in_stock
              - categories, images, specifications
              - status, message (for error handling)

    Example:
        result = scrape_bestbuy_product("https://www.bestbuy.com/product/...")
        print(result['upc'])  # Get the UPC
    """

    result = {
        'status': 'success',
        'message': '',
        'url': product_url,
        'name': 'Not found',
        'price': 'Not available',
        'rating': 'No rating',
        'review_count': '0',
        'sku': 'N/A',
        'upc': 'Not available',
        'model': 'Not found',
        'availability': 'Availability unknown',
        'in_stock': False,
        'description': '',
        'categories': [],
        'images': [],
        'specifications': []
    }

    # Validate URL
    if not isinstance(product_url, str):
        result['status'] = 'error'
        result['message'] = 'product_url must be a string'
        return result

    if 'bestbuy.com' not in product_url or '/product/' not in product_url:
        result['status'] = 'error'
        result['message'] = 'Invalid Best Buy product URL'
        return result

    driver = None
    try:
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--headless')

        # Initialize webdriver
        driver = webdriver.Chrome(options=chrome_options)

        # Load page
        driver.get(product_url)
        time.sleep(3)

        # Wait for page content
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except:
            pass

        # Try to click Specifications section or button to load specs/UPC
        # Handle two different UI patterns:
        # Pattern 1: "Specifications" as clickable section (h2/h3)
        # Pattern 2: "See All Specifications" button
        modal_opened = False
        try:
            # Try multiple selectors to find the button/section (case-insensitive)
            spec_selectors = [
                # Try "See All Specifications" button first (more specific)
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all specifications')]",
                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all specifications')]",
                "//*[@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'see all specifications')]",
                # Try "Specifications" section header
                "//h2[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specifications')]",
                "//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specifications')]",
                "//*[@role='button' and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'specifications')]",
            ]
            
            for selector in spec_selectors:
                try:
                    spec_elements = driver.find_elements(By.XPATH, selector)
                    if spec_elements:
                        for spec_elem in spec_elements:
                            try:
                                # Scroll to element
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", spec_elem)
                                time.sleep(0.5)
                                
                                # Click the element
                                try:
                                    spec_elem.click()
                                except:
                                    driver.execute_script("arguments[0].click();", spec_elem)
                                
                                # Wait for modal/dialog to appear (check for modal, dialog, or overlay)
                                try:
                                    # Wait for either modal element or UPC text to appear
                                    WebDriverWait(driver, 5).until(
                                        lambda d: len(d.find_elements(By.XPATH, "//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@role, 'dialog')]")) > 0 or
                                                  len(d.find_elements(By.XPATH, "//*[contains(., 'UPC') or contains(., 'Universal Product Code')]")) > 0
                                    )
                                    modal_opened = True
                                    time.sleep(2)  # Additional wait for content to load
                                except:
                                    time.sleep(3)  # Fallback wait if explicit wait fails
                                    modal_opened = True  # Assume modal opened if we clicked
                                
                                break
                            except Exception as e:
                                continue
                        if modal_opened:
                            break
                except:
                    continue
        except:
            pass

        # Scroll to load more content
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(2)

        # Get page source AFTER modal might have opened
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Extract product name
        name_elem = soup.find('h1')
        if name_elem:
            result['name'] = name_elem.get_text(strip=True)

        # Extract price
        price_elem = soup.find('div', class_=lambda x: x and 'priceView' in (x or ''))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            if price_text:
                result['price'] = price_text

        # Extract rating
        rating_elem = soup.find('div', class_=lambda x: x and 'rating' in (x or '').lower())
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            if rating_text:
                result['rating'] = rating_text

        # Extract review count
        review_elem = soup.find('span', class_=lambda x: x and 'reviews' in (x or '').lower())
        if review_elem:
            review_text = review_elem.get_text(strip=True)
            if review_text:
                result['review_count'] = review_text

        # Extract model from text
        page_text = soup.get_text()
        model_match = re.search(r'Model[:\s]*([A-Z0-9]+/[A-Z0-9]+)(?:\s|SKU)', page_text, re.IGNORECASE)
        if not model_match:
            # Fallback: try without slash
            model_match = re.search(r'Model[:\s]*([A-Z0-9]+)', page_text, re.IGNORECASE)
        if model_match:
            result['model'] = model_match.group(1).strip()

        # Extract availability/stock
        if 'in stock' in page_text.lower():
            result['in_stock'] = True
            result['availability'] = 'In Stock'
        elif 'out of stock' in page_text.lower():
            result['in_stock'] = False
            result['availability'] = 'Out of Stock'

        # Extract UPC - Multiple methods
        # First try from the driver directly (to catch dynamically loaded modal content)
        upc = None
        if modal_opened:
            try:
                # Try to find UPC directly in the modal using Selenium
                upc_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upc') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'universal product code')]"
                )
                for elem in upc_elements:
                    elem_text = elem.text
                    match = re.search(r'(?:UPC|Universal Product Code)[\s:]*([0-9]{8,14})', elem_text, re.IGNORECASE)
                    if match:
                        candidate = match.group(1).strip()
                        if len(candidate) >= 8:
                            upc = candidate
                            break
                    # Also try to find numbers near UPC text
                    match = re.search(r'([0-9]{8,14})', elem_text)
                    if match:
                        candidate = match.group(1).strip()
                        if len(candidate) >= 8 and len(candidate) <= 14:
                            upc = candidate
                            break
            except:
                pass
        
        # Fallback to soup-based extraction
        if not upc:
            upc = _extract_upc(soup, page_text, driver if modal_opened else None)
        
        if upc:
            result['upc'] = upc

        # Extract SKU from URL if available
        url_parts = product_url.split('/')
        if len(url_parts) > 0:
            last_part = url_parts[-1]
            if last_part and not last_part.startswith('?'):
                sku_candidate = last_part.split('?')[0]
                if len(sku_candidate) > 3:  # SKU is usually longer
                    result['sku'] = sku_candidate

        # Extract images
        images = _extract_images(soup)
        result['images'] = images

        # Extract categories
        categories = _extract_categories(soup)
        result['categories'] = categories

        # Extract specifications
        specs = _extract_specifications(soup)
        result['specifications'] = specs

        # Extract description
        desc_elem = soup.find('div', class_=lambda x: x and 'description' in (x or '').lower())
        if desc_elem:
            result['description'] = desc_elem.get_text(strip=True)[:200]

        result['message'] = f'Successfully scraped: {result["name"]}'

    except Exception as e:
        result['status'] = 'error'
        result['message'] = f'Scraping failed: {str(e)}'

    finally:
        if driver:
            driver.quit()

    return result


def _extract_upc(soup: BeautifulSoup, page_text: str, driver=None) -> Optional[str]:
    """Extract UPC from various locations on page."""

    # Pattern 1: Direct UPC label (with various formats)
    patterns = [
        r'UPC[\s:]*([0-9]{8,14})',
        r'(?:GTIN|EAN)[\s:]*([0-9]{8,14})',
        r'Universal Product Code[\s:]*([0-9]{8,14})',
        r'UPC[^0-9]*([0-9]{11,14})',  # UPC-A is typically 12 digits
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            upc = match.group(1).strip()
            if len(upc) >= 8 and len(upc) <= 14:
                return upc

    # Pattern 2: Look in modal/dialog content if driver is provided
    if driver:
        try:
            # Try to find modal/dialog elements
            modal_elements = driver.find_elements(By.XPATH,
                "//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@role, 'dialog')]"
            )
            for modal in modal_elements:
                modal_text = modal.text
                for pattern in patterns:
                    match = re.search(pattern, modal_text, re.IGNORECASE)
                    if match:
                        upc = match.group(1).strip()
                        if len(upc) >= 8 and len(upc) <= 14:
                            return upc
        except:
            pass

    # Pattern 3: Look in specifications table/section
    specs_sections = soup.find_all(['table', 'div', 'section'], 
                                  class_=lambda x: x and ('spec' in (x or '').lower() or 'detail' in (x or '').lower()))
    for spec_section in specs_sections:
        spec_text = spec_section.get_text()
        # Look for UPC followed by numbers
        match = re.search(r'UPC[^0-9]*([0-9]{8,14})', spec_text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) >= 8 and len(candidate) <= 14:
                return candidate

    # Pattern 4: Look for standalone UPC-like numbers (11-14 digits) near "UPC" text
    lines = page_text.split('\n')
    for i, line in enumerate(lines):
        if 'upc' in line.lower() or 'universal product code' in line.lower():
            # Check current line and next few lines for UPC number
            search_text = ' '.join(lines[i:min(i+3, len(lines))])
            match = re.search(r'([0-9]{11,14})', search_text)
            if match:
                candidate = match.group(1).strip()
                if len(candidate) >= 11 and len(candidate) <= 14:
                    return candidate

    return None


def _extract_images(soup: BeautifulSoup) -> List[str]:
    """Extract product images from page."""
    images = []

    # Look for image containers
    img_elements = soup.find_all('img', class_=lambda x: x and 'product' in (x or '').lower())

    for img in img_elements[:10]:  # Limit to 10 images
        src = img.get('src') or img.get('data-src')
        if src and 'bestbuy' in src and src not in images:
            images.append(src)

    return images


def _extract_categories(soup: BeautifulSoup) -> List[str]:
    """Extract product categories/breadcrumbs."""
    categories = []

    # Look for breadcrumb navigation
    breadcrumb = soup.find('nav', class_=lambda x: x and 'breadcrumb' in (x or '').lower())
    if breadcrumb:
        items = breadcrumb.find_all('a')
        for item in items:
            text = item.get_text(strip=True)
            if text and text not in categories:
                categories.append(text)

    return categories


def _extract_specifications(soup: BeautifulSoup) -> List[Dict]:
    """Extract product specifications."""
    specs = []

    # Look for specifications section
    spec_section = soup.find('div', class_=lambda x: x and 'specification' in (x or '').lower())

    if spec_section:
        # Try to extract spec rows
        rows = spec_section.find_all(['tr', 'div'], class_=lambda x: x and 'row' in (x or '').lower())
        for row in rows[:5]:  # Limit to 5 specs
            cells = row.find_all(['td', 'div'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    specs.append({'key': key, 'value': value})

    if not specs:
        specs.append({'note': 'No specifications found'})

    return specs
