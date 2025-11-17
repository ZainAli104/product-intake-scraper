"""
Best Buy Scraper HTTP Server
Provides REST API endpoints for list and product scraping

Endpoints:
  POST /scrape-list - Scrape first product from search results
  POST /scrape-product - Scrape full product details
  GET /health - Health check
"""

from flask import Flask, request, jsonify
import logging
import sys

# Import scrapers
from n8n_list_scraper import scrape_bestbuy_first_product
from n8n_main_scraper import scrape_bestbuy_product

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/scrape-list', methods=['POST'])
def list_scraper():
    """
    Scrape the first product from Best Buy search results

    Request body:
    {
        "search_url": "https://www.bestbuy.com/site/searchpage.jsp?st=iphone"
    }

    Response:
    {
        "status": "success",
        "name": "Product Name",
        "full_url": "https://www.bestbuy.com/product/...",
        "sku": "ABC123",
        "link": "/product/...",
        "image": "https://..."
    }
    """
    try:
        data = request.json
        search_url = data.get('search_url')

        if not search_url:
            return jsonify({
                'status': 'error',
                'message': 'search_url parameter is required'
            }), 400

        logger.info(f"List scraper requested for: {search_url}")
        result = scrape_bestbuy_first_product(search_url)

        logger.info(f"List scraper result: {result['status']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"List scraper error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/scrape-product', methods=['POST'])
def main_scraper():
    """
    Scrape full product details from Best Buy product page

    Request body:
    {
        "product_url": "https://www.bestbuy.com/product/apple-iphone-15/ABC123"
    }

    Response:
    {
        "status": "success",
        "url": "https://www.bestbuy.com/product/...",
        "name": "Product Name",
        "price": "$999.99",
        "rating": "4.5",
        "review_count": "1234",
        "sku": "ABC123",
        "upc": "123456789012",
        "model": "MODEL123",
        "in_stock": true,
        "availability": "In Stock"
    }
    """
    try:
        data = request.json
        product_url = data.get('product_url')

        if not product_url:
            return jsonify({
                'status': 'error',
                'message': 'product_url parameter is required'
            }), 400

        logger.info(f"Main scraper requested for: {product_url}")
        result = scrape_bestbuy_product(product_url)

        logger.info(f"Main scraper result: {result['status']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Main scraper error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Best Buy Scraper Server is running',
        'version': '1.0'
    }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'available_endpoints': [
            'POST /scrape-list',
            'POST /scrape-product',
            'GET /health'
        ]
    }), 404

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Bad request'
    }), 400

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("BEST BUY SCRAPER SERVER")
    print("="*70)
    print("\n✓ Server starting...")
    print("\nAvailable Endpoints:")
    print("  POST /scrape-list")
    print("    - Scrape first product from search results")
    print("    - Body: {\"search_url\": \"https://...\"}")
    print("\n  POST /scrape-product")
    print("    - Scrape full product details including UPC")
    print("    - Body: {\"product_url\": \"https://...\"}")
    print("\n  GET /health")
    print("    - Health check endpoint")
    print("\n" + "="*70)
    print("Server running on: http://0.0.0.0:5000")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
