# AmzPy - Amazon Product Scraper [![PyPI](https://img.shields.io/pypi/v/amzpy)](https://pypi.org/project/amzpy/)
![AmzPy Logo](https://i.imgur.com/QxrE60H.png)

<a href="https://www.producthunt.com/posts/amzpy?embed=true&utm_source=badge-featured&utm_medium=badge&utm_souce=badge-amzpy" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=812920&theme=neutral&t=1737654254074" alt="AmzPy - A&#0032;lightweight&#0032;Amazon&#0032;product&#0032;scraper&#0032;library&#0046; | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>

AmzPy is a lightweight Python library for scraping product information from Amazon. It provides a simple interface to fetch product details like title, price, currency, and image URL while handling anti-bot measures automatically using curl_cffi for enhanced protection.

## Features

- Easy-to-use API for scraping Amazon product data
- Supports multiple Amazon domains (.com, .in, .co.uk, etc.)
- Enhanced anti-bot protection using curl_cffi with browser impersonation
- Automatic retries on detection with intelligent delay management
- Support for proxies to distribute requests
- Dynamic configuration options
- Extract color variants, discounts, delivery information, and more
- Clean and typed Python interface

## Installation

Install using pip:
```bash
pip install amzpy
```

## Basic Usage

### Fetching Product Details

```python
from amzpy import AmazonScraper

# Create scraper with default settings (amazon.com)
scraper = AmazonScraper()

# Fetch product details
url = "https://www.amazon.com/dp/B0D4J2QDVY"
product = scraper.get_product_details(url)

if product:
    print(f"Title: {product['title']}")
    print(f"Price: {product['currency']}{product['price']}")
    print(f"Brand: {product['brand']}")
    print(f"Rating: {product['rating']}")
    print(f"Image URL: {product['img_url']}")
```

### Searching for Products

```python
from amzpy import AmazonScraper

# Create scraper for a specific Amazon domain
scraper = AmazonScraper(country_code="in")

# Search by query - get up to 2 pages of results
products = scraper.search_products(query="wireless earbuds", max_pages=2)

# Display the results
for i, product in enumerate(products[:5], 1):
    print(f"{i}. {product['title']} - {product['currency']}{product['price']}")
```

## Advanced Usage

### Configuration Options

AmzPy offers flexible configuration options that can be set in multiple ways:

```python
# Method 1: Set at initialization
scraper = AmazonScraper(
    country_code="in",
    impersonate="chrome119",
    proxies={"http": "http://user:pass@proxy.example.com:8080"}
)

# Method 2: Using string-based configuration
scraper.config('MAX_RETRIES = 5, REQUEST_TIMEOUT = 30, DELAY_BETWEEN_REQUESTS = (3, 8)')

# Method 3: Using keyword arguments
scraper.config(MAX_RETRIES=4, DEFAULT_IMPERSONATE="safari15")
```

### Advanced Search Features

The search functionality can extract rich product data including:

```python
# Search for products with 5 pages of results
products = scraper.search_products(query="men sneakers size 9", max_pages=5)

# Or search using a pre-constructed URL (e.g., filtered searches)
url = "https://www.amazon.in/s?i=shoes&rh=n%3A1983518031&s=popularity-rank"
products = scraper.search_products(search_url=url, max_pages=3)

# Access comprehensive product data
for product in products:
    # Basic information
    print(f"Title: {product.get('title')}")
    print(f"ASIN: {product.get('asin')}")
    print(f"URL: https://www.amazon.{scraper.country_code}/dp/{product.get('asin')}")
    print(f"Brand: {product.get('brand')}")
    print(f"Price: {product.get('currency')}{product.get('price')}")
    
    # Discount information
    if 'original_price' in product:
        print(f"Original Price: {product.get('currency')}{product.get('original_price')}")
        print(f"Discount: {product.get('discount_percent')}% off")
    
    # Ratings and reviews
    print(f"Rating: {product.get('rating')} / 5.0 ({product.get('reviews_count')} reviews)")
    
    # Color variants
    if 'color_variants' in product:
        print(f"Available in {len(product['color_variants'])} colors")
        for variant in product['color_variants']:
            print(f"  - {variant['name']}: https://www.amazon.{scraper.country_code}/dp/{variant['asin']}")
    
    # Additional information
    print(f"Prime Eligible: {'Yes' if product.get('prime') else 'No'}")
    if 'delivery_info' in product:
        print(f"Delivery: {product.get('delivery_info')}")
    if 'badge' in product:
        print(f"Badge: {product.get('badge')}")
```

### Working with Proxies

To distribute requests and avoid IP blocks, you can use proxies:

```python
# HTTP/HTTPS proxies
proxies = {
    "http": "http://user:pass@proxy.example.com:8080",
    "https": "http://user:pass@proxy.example.com:8080"
}

# SOCKS5 proxies
proxies = {
    "http": "socks5://user:pass@proxy.example.com:1080",
    "https": "socks5://user:pass@proxy.example.com:1080" 
}

scraper = AmazonScraper(proxies=proxies)
```

### Browser Impersonation

AmzPy uses curl_cffi's browser impersonation to mimic real browser requests, significantly improving success rates when scraping Amazon:

```python
# Specify a particular browser to impersonate
scraper = AmazonScraper(impersonate="chrome119")  # Chrome 119
scraper = AmazonScraper(impersonate="safari15")   # Safari 15
scraper = AmazonScraper(impersonate="firefox115") # Firefox 115
```

## Configuration Reference

These configuration parameters can be adjusted:

| Parameter | Default | Description |
|-----------|---------|-------------|
| MAX_RETRIES | 3 | Maximum number of retry attempts for failed requests |
| REQUEST_TIMEOUT | 25 | Request timeout in seconds |
| DELAY_BETWEEN_REQUESTS | (2, 5) | Random delay range between requests (min, max) in seconds |
| DEFAULT_IMPERSONATE | 'chrome119' | Default browser to impersonate |

## Requirements

- Python 3.6+
- curl_cffi (for enhanced anti-bot protection)
- beautifulsoup4
- lxml (for faster HTML parsing)
- fake_useragent

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.