"""
Amazon Product Scraper Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the main module for the Amazon Product API using curl_cffi.
It orchestrates the scraping workflow including:
- Managing sessions through AmzSession
- Fetching product details
- Searching for products
- Handling configuration

The AmazonScraper class provides a simple interface for users
while handling the complexity of Amazon's anti-bot measures underneath.
"""

from typing import Dict, Optional, List, Union, Any
import re

from amzpy.session import AmzSession, DEFAULT_CONFIG
from amzpy.parser import parse_product_page, parse_search_page, parse_pagination_url
from amzpy.utils import parse_amazon_url


class AmazonScraper:
    """
    Main scraper class for Amazon product data using curl_cffi.
    
    This class provides a high-level interface to:
    - Fetch detailed information for individual products
    - Search for products and extract listings
    - Configure scraping behavior
    
    It handles browser impersonation, CAPTCHA avoidance, and parsing
    through the session and parser modules.
    
    Attributes:
        country_code (str): Amazon domain country code (e.g. "com", "in")
        session (AmzSession): Session manager for handling requests
        user_config (dict): User configuration parameters
    """

    def __init__(self, country_code: str = "com", impersonate: str = None, proxies: Optional[Dict] = None, **kwargs):
        """
        Initialize the Amazon scraper with the specified configuration.
        
        Args:
            country_code (str): Amazon domain country code (e.g. "com", "in")
            impersonate (str, optional): Browser to impersonate (e.g. "chrome119")
            proxies (Dict, optional): Proxy configuration for requests
            **kwargs: Additional configuration options (e.g. retries, delay, MAX_RETRIES, etc.)
        """
        self.country_code = country_code
        self.user_config = DEFAULT_CONFIG.copy()
        
        # Handle legacy/convenience parameter names
        if 'retries' in kwargs:
            self.user_config['MAX_RETRIES'] = kwargs.pop('retries')
        if 'delay' in kwargs:
            delay_val = kwargs.pop('delay')
            if isinstance(delay_val, (int, float)):
                self.user_config['DELAY_BETWEEN_REQUESTS'] = (delay_val, delay_val * 2)
            else:
                self.user_config['DELAY_BETWEEN_REQUESTS'] = delay_val
                
        if kwargs:
            self.user_config.update(kwargs)

        self.session = AmzSession(
            country_code=country_code,
            impersonate=impersonate,
            proxies=proxies,
            config=self.user_config
        )
        
        print(f"AmazonScraper initialized for amazon.{country_code}")
        
    def config(self, config_str: str = None, **kwargs) -> Dict:
        """
        Configure scraper parameters using either a string or keyword arguments.
        
        Examples:
            # Using string configuration
            scraper.config('MAX_RETRIES = 5, REQUEST_TIMEOUT = 30')
            
            # Using keyword arguments
            scraper.config(MAX_RETRIES=5, REQUEST_TIMEOUT=30)
        
        Args:
            config_str (str, optional): Configuration string in format 'PARAM1 = value1, PARAM2 = value2'
            **kwargs: Configuration parameters as keyword arguments
            
        Returns:
            Dict: Current configuration after updates
        """
        # Process string configuration if provided
        if config_str:
            # Parse the configuration string
            try:
                parts = config_str.split(',')
                for part in parts:
                    key, value = part.split('=', 1)
                    key = key.strip()
                    value = eval(value.strip())  # Safely evaluate the value
                    self.user_config[key] = value
            except Exception as e:
                print(f"Error parsing configuration string: {e}")
                print("Format should be: 'PARAM1 = value1, PARAM2 = value2'")
        
        # Process keyword arguments if provided
        if kwargs:
            self.user_config.update(kwargs)
        
        # Update the session configuration
        self.session.update_config(**self.user_config)
        
        return self.user_config

    def get_product_details(self, url: str) -> Optional[Dict]:
        """
        Fetch and parse details for a product using its Amazon URL.
        
        This method:
        1. Parses the product URL to extract the ASIN
        2. Constructs a canonical product URL
        3. Fetches the product page HTML
        4. Parses the HTML to extract structured data
        
        Args:
            url (str): Amazon product URL (any format with a valid ASIN)
            
        Returns:
            Dict: Extracted product details (title, price, etc.)
            None: If URL is invalid or scraping fails
        """
        # Parse the URL to extract base_url and product_id (ASIN)
        parsed_info = parse_amazon_url(url)
        if not parsed_info:
            print(f"Invalid Amazon product URL: {url}")
            return None

        base_url, product_id = parsed_info
        product_url = f"{base_url}dp/{product_id}"  # Construct canonical URL
        print(f"Fetching product data for ASIN: {product_id}")

        # Fetch the product page using the session
        response = self.session.get(product_url)
        if not response or not response.text:
            print(f"Failed to fetch product page for: {product_url}")
            return None
        
        # Parse the product page HTML, passing country code for URL formatting
        product_data = parse_product_page(
            html_content=response.text,
            url=product_url,
            country_code=self.country_code
        )
        
        if not product_data:
            print(f"Failed to extract product data from: {product_url}")
            return None
            
        print(f"Successfully extracted data for: {product_data.get('title', 'Unknown Product')[:50]}...")
        return product_data

    def search_products(self, query: str = None, search_url: str = None, max_pages: int = 1) -> List[Dict]:
        """
        Search for products on Amazon and extract product listings.
        
        This method supports two search approaches:
        1. Using a search query (e.g., "wireless headphones")
        2. Using a pre-constructed search URL (e.g., category pages, filtered searches)
        
        It will automatically paginate through results up to max_pages.
        
        Args:
            query (str, optional): Search query text (ignored if search_url is provided)
            search_url (str, optional): Pre-constructed search URL (takes precedence over query)
            max_pages (int): Maximum number of pages to scrape (default: 1)
            
        Returns:
            List[Dict]: List of product data dictionaries from search results
            Empty list: If search fails or no products are found
        """
        # Validate that we have either a query or a search URL
        if not query and not search_url:
            print("Error: Either a search query or search URL must be provided")
            return []
            
        # Construct search URL if only query was provided
        if not search_url and query:
            search_url = f"https://www.amazon.{self.country_code}/s?k={query.replace(' ', '+')}"
            
        print(f"Starting product search: {search_url}")
        
        all_products = []  # Collect products from all pages
        current_url = search_url
        current_page = 1
        
        # Paginate through search results
        while current_url and current_page <= max_pages:
            print(f"\nScraping search page {current_page}/{max_pages}: {current_url}")
            
            # Fetch the search page
            response = self.session.get(current_url)
            if not response or not response.text:
                print(f"Failed to fetch search page: {current_url}")
                break
                
            # Parse products from the current page, passing country code for URL formatting
            base_url = f"https://www.amazon.{self.country_code}"
            products = parse_search_page(
                response.text, 
                base_url,
                country_code=self.country_code
            )
            
            # Check if we got valid results
            if not products:
                print(f"No products found on page {current_page} (or page was blocked)")
                break
                
            print(f"Found {len(products)} products on page {current_page}")
            all_products.extend(products)
            
            # Stop if we've reached the requested number of pages
            if current_page >= max_pages:
                break
                
            # Get URL for the next page
            next_url = parse_pagination_url(response.text, base_url)
            if not next_url:
                print("No next page found. End of results.")
                break
                
            current_url = next_url
            current_page += 1
            
        print(f"\nSearch completed. Total products found: {len(all_products)}")
        return all_products
