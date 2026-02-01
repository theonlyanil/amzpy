"""
Amazon Session Manager Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides a robust session management system for Amazon scraping.
It handles:
- Browser impersonation with curl_cffi
- Request retries with intelligent backoff
- CAPTCHA/block detection and avoidance
- User-agent rotation with fake_useragent
- Proxy support
"""

import random
import time
from typing import Dict, Optional, Tuple, Any, Union

import curl_cffi.requests
from curl_cffi.requests.errors import RequestsError
from fake_useragent import UserAgent

# Default configuration (can be overridden by user)
DEFAULT_CONFIG = {
    'MAX_RETRIES': 3,
    'REQUEST_TIMEOUT': 25,
    'DELAY_BETWEEN_REQUESTS': (2, 5),
    'DEFAULT_IMPERSONATE': 'chrome120'  # part of curl_cffi's impersonation
}

# Default header template
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}


class AmzSession:
    """
    Enhanced session manager using curl_cffi for Amazon requests.
    
    This class implements sophisticated request handling including:
    - Browser fingerprint spoofing (via curl_cffi impersonation)
    - Randomized user agents (via fake_useragent)
    - CAPTCHA/anti-bot detection and avoidance
    - Intelligent retry logic with exponential backoff
    - Proxy support for IP rotation
    
    Attributes:
        country_code (str): Amazon domain country code (e.g., "com", "in", "co.uk")
        base_url (str): Constructed base URL for the Amazon domain
        session (curl_cffi.requests.Session): The curl_cffi session instance
        config (dict): Configuration parameters for request behavior
        ua_generator (UserAgent): User agent generator for browser fingerprinting
    """

    def __init__(self, country_code: str = "com", 
                 impersonate: str = None, 
                 proxies: Optional[Dict] = None,
                 config: Optional[Dict] = None):
        """
        Initialize the Amazon session manager.
        
        Args:
            country_code (str): Amazon domain country code (e.g. "com", "in")
            impersonate (str, optional): Browser to impersonate (e.g. "chrome119")
            proxies (Dict, optional): Proxy configuration for requests
            config (Dict, optional): Override default configuration parameters
        """
        # Initialize country and base URL
        self.country_code = country_code
        self.base_url = f"https://www.amazon.{self.country_code}/"
        
        # Set up configuration (with user overrides if provided)
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Initialize fake_useragent restricted to Chrome to match impersonation
        self.ua_generator = UserAgent(browsers=['Chrome'], os=['Windows', 'MacOS'])
        
        # Create curl_cffi session
        self.session = curl_cffi.requests.Session()
        
        # Set up headers with randomized user agent
        headers = DEFAULT_HEADERS.copy()
        headers['User-Agent'] = self.ua_generator.random
        self.session.headers = headers
        
        # Set browser impersonation if provided, otherwise use default
        self.session.impersonate = impersonate or self.config['DEFAULT_IMPERSONATE']

        # Get and Set Cookies from the base URL
        self.session.get(self.base_url, headers=headers)
        
        # Configure proxies if provided
        if proxies:
            self.session.proxies = proxies
            
        # Print session initialization info
        print(f"AmzSession initialized for amazon.{country_code}")
        print(f"Impersonating: {self.session.impersonate}")
        print(f"User-Agent: {headers['User-Agent'][:50]}...")
        print("Fetched cookies:", self.session.cookies.get_dict())
        if proxies:
            print(f"Using proxies: {proxies}")

    def get(self, url: str, headers: Optional[Dict] = None) -> Optional[curl_cffi.requests.Response]:
        """
        Perform a GET request using the curl_cffi session with smart retries.
        
        This method intelligently handles:
        - URL normalization (relative -> absolute)
        - Header merging
        - Random delays between requests
        - CAPTCHA and anti-bot detection
        - Automatic retries with exponential backoff
        - Error handling for network issues
        
        Args:
            url (str): URL to fetch (absolute or relative to base_url)
            headers (Dict, optional): Additional headers to merge with defaults
            
        Returns:
            Optional[curl_cffi.requests.Response]: Response object or None if all retries failed
        """
        # Normalize URL (handle both absolute and relative URLs)
        if not url.startswith("http"):
            if url.startswith("/"):
                url = f"{self.base_url.rstrip('/')}{url}"
            else:
                url = f"{self.base_url}{url}"

        # Merge headers with fresh random user agent for each request
        merged_headers = self.session.headers.copy()
        merged_headers['User-Agent'] = self.ua_generator.random
        if headers:
            merged_headers.update(headers)

        # Extract configuration for use in the retry loop
        max_retries = self.config['MAX_RETRIES']
        timeout = self.config['REQUEST_TIMEOUT']
        delay_range = self.config['DELAY_BETWEEN_REQUESTS']

        # Retry loop with exponential backoff
        for attempt in range(max_retries + 1):
            try:
                # Calculate delay with some randomization (increases with each attempt)
                delay_factor = 1 + (attempt * 0.5)  # Exponential backoff factor
                min_delay, max_delay = delay_range
                delay = random.uniform(min_delay * delay_factor, max_delay * delay_factor)
                
                # Log attempt information
                print(f"Request attempt {attempt+1}/{max_retries+1}: GET {url} (delay: {delay:.2f}s)")
                time.sleep(delay)

                # Make the actual request using curl_cffi
                response = self.session.get(
                    url,
                    headers=merged_headers,
                    timeout=timeout,
                    allow_redirects=True
                )

                # Handle HTTP error codes
                if response.status_code != 200:
                    print(f"Non-200 status code: {response.status_code}")
                    
                    # Handle server errors specifically (5xx)
                    if 500 <= response.status_code < 600 and attempt < max_retries:
                        print(f"Server error {response.status_code}, retrying...")
                        continue
                    
                    # For other status codes, continue but warn
                    print(f"Warning: Received HTTP {response.status_code} for {url}")

                # Check for CAPTCHA/blocking patterns in the content
                if "captcha" in response.text.lower() or "api-services-support@amazon.com" in response.text:
                    print("CAPTCHA or anti-bot measure detected in response")
                    
                    if attempt < max_retries:
                        # Apply a longer delay before the next retry for anti-bot
                        captcha_delay = delay * 3
                        print(f"Detected anti-bot measure. Waiting {captcha_delay:.2f}s before retry")
                        time.sleep(captcha_delay)
                        continue
                    
                    print("Failed to bypass anti-bot measures after all retries")
                
                # If everything is good, return the response
                print(f"Request successful: {url} (Status: {response.status_code})")
                return response

            except RequestsError as e:
                print(f"Network error on attempt {attempt+1}: {e}")
                if attempt == max_retries:
                    print(f"Max retries reached. Network error: {e}")
                    return None
                time.sleep(delay * 2)  # Longer delay after network error
                
            except Exception as e:
                print(f"Unexpected error on attempt {attempt+1}: {e}")
                if attempt == max_retries:
                    print(f"Max retries reached. Error: {e}")
                    return None
                time.sleep(delay * 2)
        
        return None
        
    def update_config(self, **kwargs):
        """
        Update session configuration parameters.
        
        Args:
            **kwargs: Configuration key-value pairs to update
        """
        self.config.update(kwargs)
        print(f"Updated session configuration: {kwargs}") 