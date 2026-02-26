from typing import Tuple, Optional
import re

def parse_amazon_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Parse Amazon product URL to extract base URL and product ID
    
    Args:
        url (str): Full Amazon product URL
        
    Returns:
        Tuple[str, str]: (base_url, product_id) if valid
        None: If URL is invalid
    """
    # Clean up the URL
    url = url.strip()
    
    # Match Amazon domain
    domain_match = re.search(r'https?://(?:www\.)?amazon\.([a-z.]+)', url)
    if not domain_match:
        return None
        
    domain = domain_match.group(1)
    base_url = f"https://www.amazon.{domain}/"
    
    # Extract product ID
    product_id = extract_asin(url)
    
    if not product_id:
        return None
        
    return base_url, product_id

def extract_asin(url: str) -> Optional[str]:
    """
    Extract ASIN (Amazon Standard Identification Number) from any Amazon URL.
    Handles various formats: /dp/, /gp/product/, /gp/aw/d/, etc.
    
    Args:
        url (str): Amazon URL (full or relative)
        
    Returns:
        str: 10-character ASIN if found, None otherwise
    """
    if not url:
        return None
        
    # Common Amazon URL patterns for product IDs
    patterns = [
        r'/(?:dp|gp/product|gp/aw/d|aw/d|product|gp/d)/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
        r'/([A-Z0-9]{10})(?:/|\?|$)' # Last resort: 10-char alphanumeric after a slash
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None

def format_canonical_url(url: str, asin: str, country_code: str = None) -> str:
    """
    Format a canonical Amazon product URL in the form amazon.{country}/dp/{asin}
    
    Args:
        url (str): Original Amazon URL
        asin (str): ASIN of the product
        country_code (str, optional): Country code (e.g., "com", "in")
        
    Returns:
        str: Canonical URL
    """
    if not asin:
        return url  # Return original if no ASIN available
        
    # If country_code is not provided, try to extract it from the original URL
    if not country_code:
        try:
            parsed_url = urlparse(url)
            domain_parts = parsed_url.netloc.split('.')
            # Extract country code from domain (e.g., www.amazon.com -> com)
            if len(domain_parts) >= 3 and 'amazon' in domain_parts:
                amazon_index = domain_parts.index('amazon')
                if amazon_index + 1 < len(domain_parts):
                    country_code = domain_parts[amazon_index + 1]
        except Exception:
            country_code = "com"  # Default to .com if extraction fails
    
    # Default to .com if still no country code
    if not country_code:
        country_code = "com"
        
    # Create canonical URL
    return f"https://www.amazon.{country_code}/dp/{asin}"

# Function to extract brand name from text
def extract_brand_name(text):
    match = re.search(r'visit the (.+?) store', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None