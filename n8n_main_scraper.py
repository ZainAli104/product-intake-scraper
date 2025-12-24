"""
N8N-Compatible Main Scraper for Best Buy
Use this in N8N Code Node to scrape full product details including UPC.
"""

import time
import re
from typing import Dict, Optional
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
        Dict: Essential product information including:
              - name, description, model, upc, sku, price
              - status, message (for error handling)

    Example:
        result = scrape_bestbuy_product("https://www.bestbuy.com/product/...")
        print(result['upc'])  # Get the UPC
    """

    result = {
        'status': 'success',
        'message': '',
        'name': 'Not found',
        'price': 'Not available',
        'sku': 'N/A',
        'upc': 'Not available',
        'model': 'Not found',
        'description': ''
    }

    # Validate URL
    if not isinstance(product_url, str):
        result['status'] = 'error'
        result['message'] = 'product_url must be a string'
        return result

    if 'bestbuy.com' not in product_url or ('/product/' not in product_url and '/site/' not in product_url):
        result['status'] = 'error'
        result['message'] = 'Invalid Best Buy product URL'
        return result

    driver = None
    try:
        # Set up Chrome/Chromium options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Exclude automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Use Chromium binary if available (for Docker)
        import os
        if os.path.exists('/usr/bin/chromium'):
            chrome_options.binary_location = '/usr/bin/chromium'

        # Initialize webdriver
        driver = webdriver.Chrome(options=chrome_options)

        # Remove webdriver property
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Load page
        driver.get(product_url)
        time.sleep(5)

        # Check if we're on a country selection or redirect page
        current_url = driver.current_url
        page_title = driver.title.lower()

        # If redirected or on country selection, try to handle it
        if 'country' in page_title or 'choose' in page_title or current_url != product_url:
            # Try clicking US/America link if present
            try:
                us_links = driver.find_elements(By.XPATH,
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'united states') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'us')]"
                )
                if us_links:
                    us_links[0].click()
                    time.sleep(3)
            except:
                # If that fails, try navigating directly again
                driver.get(product_url)
                time.sleep(5)

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

        # Extract page text (needed for model and UPC extraction)
        page_text = soup.get_text()

        # Extract model number from specifications modal
        model = _extract_model(soup, page_text, driver if modal_opened else None)
        if model:
            result['model'] = model

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


def _extract_model(soup: BeautifulSoup, page_text: str, driver=None) -> Optional[str]:
    """Extract Model Number from specifications modal (same approach as UPC extraction)."""

    # Only extract from modal if driver is provided (modal was opened)
    if driver:
        try:
            # Try to find modal/dialog elements
            modal_elements = driver.find_elements(By.XPATH,
                "//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@role, 'dialog')]"
            )
            for modal in modal_elements:
                modal_text = modal.text
                # Look for "Model Number" followed by the value
                match = re.search(r'Model\s+Number\s+([A-Z0-9-/]+)', modal_text, re.IGNORECASE)
                if match:
                    model = match.group(1).strip()
                    if len(model) >= 5 and len(model) <= 25:
                        return model
        except:
            pass

    return None
