"""
Amazon HTML Parsing Module
~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains parsing functions for Amazon pages:
- Product detail pages (individual products)
- Search results pages (listings of products)

It uses BeautifulSoup to extract structured data from Amazon's HTML.
"""


import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, Optional, TYPE_CHECKING, Any, List, Tuple

# Using string annotation to avoid circular imports
if TYPE_CHECKING:
    from amzpy.session import AmzSession

from amzpy.utils import extract_brand_name, format_canonical_url, parse_amazon_url, extract_asin


def parse_product_page(html_content: str, url: str = None, country_code: str = None) -> Optional[Dict]:
    """
    Parse Amazon product page HTML and extract structured product data.
    
    This function extracts key product information including:
    - Product title
    - Price and currency
    - Brand name
    - Product image URL
    
    Args:
        html_content (str): Raw HTML content of the product page
        url (str, optional): Product URL for reference
        country_code (str, optional): Country code for URL formatting
        
    Returns:
        Dict: Extracted product information 
        None: If parsing fails or HTML indicates a CAPTCHA/block
    """
    if not html_content:
        print("Error: Received empty HTML content")
        return None
        
    # Use lxml parser for better performance
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Check for CAPTCHA / Block Page before detailed parsing
    if "captcha" in html_content.lower() or "api-services-support@amazon.com" in html_content:
        print("Possible CAPTCHA or block page detected in HTML content")
        return None
    
    try:
        # Extract product title
        title_element = soup.select_one('#productTitle')
        title = title_element.text.strip() if title_element else None
        
        # Extract price information
        # We check multiple price selectors since Amazon's HTML structure varies
        price = None
        price_whole = soup.select_one('.a-price-whole')
        price_fraction = soup.select_one('.a-price-fraction')
        
        if price_whole:
            # Get whole number part
            price_text = price_whole.text.strip('.').replace(',', '')
            # Add decimal part if available
            if price_fraction:
                fraction_text = price_fraction.text.strip()
                price = float(f"{price_text}.{fraction_text}")
            else:
                price = float(price_text)
        
        # Alternative price selectors for different Amazon layouts
        if price is None:
            price_element = soup.select_one('span.a-offscreen')
            if price_element:
                price_text = price_element.text.strip()
                # Extract numeric value from price text (e.g., "$29.99" -> 29.99)
                price_match = re.search(r'[\d,]+\.?\d*', price_text)
                if price_match:
                    price = float(price_match.group().replace(',', ''))
        
        # Extract currency symbol
        currency_element = soup.select_one('.a-price-symbol')
        currency = currency_element.text.strip() if currency_element else None
        
        # Extract currency from alternate sources if first method fails
        if not currency and price is not None:
            price_element = soup.select_one('span.a-offscreen')
            if price_element:
                price_text = price_element.text.strip()
                currency_match = re.search(r'^[^\d]+', price_text)
                if currency_match:
                    currency = currency_match.group().strip()

        # Extract brand name
        brand_name = None
        brand_element = soup.select_one('#bylineInfo')
        if brand_element:
            brand_name = extract_brand_name(brand_element.text.strip())
            
        # Try alternative brand selectors if first method fails
        if not brand_name:
            # Try looking in the product details section
            detail_bullets = soup.select('#detailBullets_feature_div li')
            for bullet in detail_bullets:
                if 'brand' in bullet.text.lower():
                    brand_name = bullet.select_one('.a-text-bold + span')
                    if brand_name:
                        brand_name = brand_name.text.strip()
                    break
        
        # Extract main product image
        img_element = soup.select_one('#landingImage') or soup.select_one('#imgBlkFront')
        img_url = img_element.get('src') if img_element else None
        
        # Try to get high-resolution image URL if available
        if img_element and not img_url:
            data_old_hires = img_element.get('data-old-hires')
            data_a_dynamic_image = img_element.get('data-a-dynamic-image')
            
            if data_old_hires:
                img_url = data_old_hires
            elif data_a_dynamic_image:
                # This attribute contains a JSON string with multiple image URLs
                try:
                    image_dict = json.loads(data_a_dynamic_image)
                    # Get the URL with the highest resolution
                    if image_dict:
                        img_url = list(image_dict.keys())[0]
                except Exception:
                    pass
        
        # Extract ASIN (Amazon Standard Identification Number)
        asin = None
        if url:
            asin = extract_asin(url)
                
        # Extract ratings if available
        rating = None
        rating_element = soup.select_one('#acrPopover') or soup.select_one('span.a-icon-alt')
        if rating_element:
            rating_text = rating_element.get('title', '') or rating_element.text
            rating_match = re.search(r'([\d\.]+)\s+out\s+of\s+5', rating_text)
            if rating_match:
                rating = float(rating_match.group(1))
        
        # Format canonical URL if ASIN is available
        canonical_url = format_canonical_url(url, asin, country_code) if asin else url
        
        # Build the final product data dictionary
        product_data = {
            "title": title,
            "price": price,
            "img_url": img_url,
            "currency": currency,
            "brand": brand_name,
            "url": canonical_url,
            "asin": asin,
            "rating": rating
        }
        
        return product_data
        
    except Exception as e:
        print(f"Error parsing product page: {e}")
        return None


def parse_search_page(html_content: str, base_url: str = None, country_code: str = None) -> List[Dict]:
    """
    Parse Amazon search results page HTML and extract product listings.
    
    This function extracts a list of products from search or category pages:
    - Product title, URL, and ASIN
    - Price and currency
    - Thumbnail image
    - Ratings and review count when available
    - Prime eligibility
    - Color variants
    - Discounts
    
    Args:
        html_content (str): Raw HTML content of the search results page
        base_url (str, optional): Base URL for resolving relative URLs
        country_code (str, optional): Country code for URL formatting
        
    Returns:
        List[Dict]: List of extracted product data dictionaries
        Empty list: If parsing fails or HTML indicates a CAPTCHA/block
    """
    if not html_content:
        print("Error: Received empty HTML content for search page")
        return []
    
    # Use lxml parser for better performance on large search pages
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Check for CAPTCHA / Block Page before detailed parsing
    if "captcha" in html_content.lower() or "api-services-support@amazon.com" in html_content:
        print("CAPTCHA or block page detected in search results")
        return []
    
    # Prepare results list
    results = []

    try:
        # Try to locate search result containers - Amazon has multiple formats
        # Try the most common selectors first
        product_containers = soup.select('div[data-component-type="s-search-result"]')
        
        # Alternative selectors for different Amazon layouts
        if not product_containers:
            product_containers = soup.select('.s-result-item[data-asin]')
        
        if not product_containers:
            # Try more generic selectors as fallback
            product_containers = soup.select('.s-result-item')
        
        print(f"Found {len(product_containers)} potential product containers")
        
        # Process each product container
        for container in product_containers:
            
            try:
                # Skip sponsored listings if they don't have complete data
                if 'AdHolder' in container.get('class', []):
                    continue
                
                # Skip non-product containers (sometimes Amazon includes dividers, etc.)
                # Extract ASIN (Amazon Standard Identification Number)
                asin = container.get('data-asin') or container.get('asin')
                if not asin or asin == "":
                    continue
                
                # Initialize product data dictionary
                product_data = {"asin": asin}
                
                # Extract product URL and title (multiple possible selectors)
                title_link = None
                
                # Try various title selectors that appear across different Amazon layouts
                title_selectors = [
                    'h2 a.a-link-normal',             # Common layout
                    '.a-text-normal[href]',           # Alternative layout
                    'h2.a-size-base-plus a',          # Layout from example
                    'a.s-line-clamp-2',               # Another layout from example
                    '.a-text-normal[data-hover]',     # Alternative layout
                    '.a-size-base-plus[aria-label]'   # Layout with aria-label
                ]
                
                for selector in title_selectors:
                    title_link = container.select_one(selector)
                    if title_link:
                        break
                
                if title_link:
                    # Extract title - check multiple attributes
                    if title_link.get('aria-label'):
                        product_data['title'] = title_link.get('aria-label')
                    elif title_link.select_one('span'):
                        product_data['title'] = title_link.select_one('span').text.strip()
                    else:
                        product_data['title'] = title_link.text.strip()
                    
                    # Extract URL from href attribute
                    href = title_link.get('href')
                    if href:
                        # Handle relative URLs
                        if href.startswith('/'):
                            product_url = urljoin(base_url, href) if base_url else href
                        else:
                            product_url = href
                            
                        # Store the URL but also create a canonical version
                        product_data['url'] = format_canonical_url(product_url, asin, country_code)
                
                # Extract brand (multiple possible locations)
                brand_selectors = [
                    '.a-row .a-size-base-plus.a-color-base',  # Common location
                    '.a-size-base-plus:not([aria-label])',    # Alternative location
                    'h2 .a-size-base-plus',                   # Format from example
                    '.s-line-clamp-1 span'                    # Another common format
                ]
                
                for selector in brand_selectors:
                    brand_elem = container.select_one(selector)
                    if brand_elem and brand_elem.text.strip():
                        product_data['brand'] = brand_elem.text.strip()
                        break
                
                # Extract price information (multiple possible selectors)
                # First, look for the a-price structure (most common)
                price_element = container.select_one('.a-price .a-offscreen')
                if price_element:
                    price_text = price_element.text.strip()
                    # Parse price and currency
                    currency_match = re.search(r'^[^\d]+', price_text)
                    price_match = re.search(r'[\d,]+\.?\d*', price_text)
                    
                    if currency_match:
                        product_data['currency'] = currency_match.group().strip()
                    
                    if price_match:
                        price_str = price_match.group().replace(',', '')
                        # Only convert to float if it's a valid number (not just a decimal point)
                        if price_str and price_str != ".":
                            try:
                                product_data['price'] = float(price_str)
                            except ValueError:
                                # If conversion fails, just log and continue without price
                                print(f"Warning: Could not convert price string: '{price_str}'")
                        
                # If price not found, try alternative selectors
                if 'price' not in product_data:
                    price_whole = container.select_one('.a-price-whole')
                    price_fraction = container.select_one('.a-price-fraction')
                    if price_whole:
                        price_text = price_whole.text.strip().replace(',', '')
                        if price_text and price_text != ".":
                            try:
                                if price_fraction:
                                    fraction_text = price_fraction.text.strip()
                                    if fraction_text and fraction_text != ".":
                                        product_data['price'] = float(f"{price_text}.{fraction_text}")
                                else:
                                    product_data['price'] = float(price_text)
                            except ValueError:
                                print(f"Warning: Could not convert price parts: '{price_text}' and '{fraction_text if price_fraction else ''}'")
                            
                # Extract currency symbol if not already found
                if 'currency' not in product_data and container.select_one('.a-price-symbol'):
                    product_data['currency'] = container.select_one('.a-price-symbol').text.strip()
                
                # Extract original price and calculate discount (if available)
                original_price_elem = container.select_one('.a-price.a-text-price .a-offscreen')
                if original_price_elem:
                    original_price_text = original_price_elem.text.strip()
                    price_match = re.search(r'[\d,]+\.?\d*', original_price_text)
                    if price_match:
                        price_str = price_match.group().replace(',', '')
                        if price_str and price_str != ".":
                            try:
                                original_price = float(price_str)
                                product_data['original_price'] = original_price
                                
                                # Calculate discount percentage if both prices are available
                                if 'price' in product_data and product_data['price'] > 0:
                                    discount = round(100 - (product_data['price'] / original_price * 100))
                                    product_data['discount_percent'] = discount
                            except ValueError:
                                print(f"Warning: Could not convert original price string: '{price_str}'")
                
                # Extract discount percentage directly if available
                discount_text = container.select_one('span:-soup-contains("% off")')
                if discount_text and 'discount_percent' not in product_data:
                    discount_match = re.search(r'(\d+)%', discount_text.text)
                    if discount_match:
                        product_data['discount_percent'] = int(discount_match.group(1))
                
                # Extract product image (multiple possible selectors)
                img_selectors = [
                    'img.s-image',                     # Common layout
                    '.s-image img',                    # Alternative layout
                    '.a-section img[srcset]',          # Layout from example
                    '.s-product-image-container img'   # Another layout
                ]
                
                for selector in img_selectors:
                    img_element = container.select_one(selector)
                    if img_element:
                        # First try to get the highest resolution version using srcset
                        if img_element.get('srcset'):
                            srcset = img_element.get('srcset')
                            srcset_parts = srcset.split(',')
                            if srcset_parts:
                                # Get the last one (usually highest resolution)
                                highest_res = srcset_parts[-1].strip().split(' ')[0]
                                product_data['img_url'] = highest_res
                        # Fallback to src attribute
                        if 'img_url' not in product_data and img_element.get('src'):
                            product_data['img_url'] = img_element.get('src')
                        break
                
                # Extract ratings (multiple possible formats)
                rating_selectors = [
                    'i.a-icon-star-small',            # Common layout
                    '.a-icon-star',                   # Alternative layout
                    'span.a-icon-alt',                # Text inside span
                    'i.a-star-mini-4',                # Format from example
                    '[aria-label*="out of 5 stars"]'  # Aria-label format
                ]
                
                for selector in rating_selectors:
                    rating_element = container.select_one(selector)
                    if rating_element:
                        # Try to extract from aria-label first
                        if rating_element.get('aria-label') and 'out of 5' in rating_element.get('aria-label'):
                            rating_text = rating_element.get('aria-label')
                        # Try alt text next
                        elif rating_element.get('alt') and 'out of 5' in rating_element.get('alt'):
                            rating_text = rating_element.get('alt')
                        # Try inner text or parent text
                        else:
                            rating_text = rating_element.text.strip()
                            # If no text, try parent
                            if not rating_text and rating_element.parent:
                                rating_text = rating_element.parent.text.strip()
                            
                        # Extract the numeric rating
                        rating_match = re.search(r'([\d\.]+)(?:\s+out\s+of\s+5)?', rating_text)
                        if rating_match:
                            rating_str = rating_match.group(1)
                            if rating_str and rating_str != ".":
                                try:
                                    product_data['rating'] = float(rating_str)
                                except ValueError:
                                    print(f"Warning: Could not convert rating string: '{rating_str}'")
                            break
                
                # Extract reviews count (multiple possible formats)
                reviews_selectors = [
                    'span[aria-label*="reviews"]',                 # Common layout
                    '.a-size-base.s-underline-text',               # Format from example
                    'a:-soup-contains("ratings")',                 # Alternative text-based
                    'a:-soup-contains("reviews")',                 # Another alternative
                    '.a-link-normal .a-size-base'                  # Generic link to reviews
                ]
                
                for selector in reviews_selectors:
                    reviews_element = container.select_one(selector)
                    if reviews_element:
                        reviews_text = ""
                        # Try aria-label first
                        if reviews_element.get('aria-label'):
                            reviews_text = reviews_element.get('aria-label')
                        # Otherwise use text content
                        else:
                            reviews_text = reviews_element.text.strip()
                        
                        # Extract digits with K/M suffix handling
                        reviews_match = re.search(r'([\d,\.]+)(?:K|k|M)?', reviews_text)
                        if reviews_match:
                            count_text = reviews_match.group(1).replace(',', '')
                            if count_text and count_text != ".":
                                try:
                                    count = float(count_text)
                                    
                                    # Handle K/M suffixes
                                    if 'K' in reviews_text or 'k' in reviews_text:
                                        count *= 1000
                                    elif 'M' in reviews_text:
                                        count *= 1000000
                                        
                                    product_data['reviews_count'] = int(count)
                                except ValueError:
                                    print(f"Warning: Could not convert reviews count: '{count_text}'")
                            break
                
                # Check for Prime eligibility
                prime_selectors = [
                    'i.a-icon-prime',                     # Common layout
                    '.a-icon-prime',                      # Alternative layout
                    'span:-soup-contains("Prime")',       # Text-based detection
                    '.aok-relative.s-icon-text-medium',   # Format from example
                    '[aria-label="Prime"]'                # Aria-label based
                ]
                
                product_data['prime'] = any(container.select_one(selector) for selector in prime_selectors)
                
                # Extract color variants if available
                color_variants = []
                color_swatches = container.select('.s-color-swatch-outer-circle')
                
                if color_swatches:
                    for swatch in color_swatches:
                        color_link = swatch.select_one('a')
                        if color_link:
                            color_name = color_link.get('aria-label', '')
                            color_url = color_link.get('href', '')
                            color_asin = None
                            
                            # Try to extract ASIN from URL
                            if color_url:
                                color_asin = extract_asin(color_url)
                                
                            if color_name:
                                if color_url.startswith('/'):
                                    color_url = urljoin(base_url, color_url) if base_url else color_url
                                
                                # Format the canonical URL for color variant
                                canonical_color_url = format_canonical_url(color_url, color_asin, country_code) if color_asin else color_url
                                
                                color_variants.append({
                                    'name': color_name,
                                    'url': canonical_color_url,
                                    'asin': color_asin
                                })
                
                if color_variants:
                    product_data['color_variants'] = color_variants
                
                # Extract "Amazon's Choice" or "Best Seller" badges
                badge_text = None
                badge_element = (
                    container.select_one('.a-badge-text') or 
                    container.select_one('.s-badge-text') or 
                    container.select_one('.a-badge-label')
                )
                if badge_element:
                    badge_text = badge_element.text.strip()
                    if not badge_text and badge_element.get('aria-label'):
                        badge_text = badge_element.get('aria-label')
                    
                    if badge_text:
                        product_data['badge'] = badge_text
                
                # Extract delivery information
                delivery_element = container.select_one('.a-row:-soup-contains("delivery")') or container.select_one('[aria-label*="delivery"]')
                if delivery_element:
                    delivery_text = delivery_element.text.strip()
                    product_data['delivery_info'] = delivery_text
                
                # Extract "Deal" information
                deal_element = container.select_one('span:-soup-contains("Deal")') or container.select_one('.a-badge:-soup-contains("Deal")')
                if deal_element:
                    product_data['deal'] = True
                
                # Add the product to our results list if we have the key information
                if product_data.get('title') and product_data.get('asin'):
                    results.append(product_data)
                
            except Exception as e:
                print(f"Error parsing individual search result: {e}")
                continue  # Skip this item and continue with the next
        
        return results
        
    except Exception as e:
        print(f"Error parsing search page: {e}")
        return []


def parse_pagination_url(html_content: str, base_url: str = None) -> Optional[str]:
    """
    Extract the URL for the next page from search results pagination.
    
    Args:
        html_content (str): Raw HTML content of the search results page
        base_url (str, optional): Base URL for resolving relative URLs
        
    Returns:
        Optional[str]: URL of the next page, or None if there isn't one
    """
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Try multiple selectors for pagination "Next" button
    next_link = (
        soup.select_one('a.s-pagination-next:not(.s-pagination-disabled)') or
        soup.select_one('li.a-last:not(.a-disabled) a') or
        soup.select_one('a:has(span:contains("Next"))') or
        soup.select_one('a[aria-label="Go to next page"]')
    )
    
    if next_link and next_link.get('href'):
        next_url = next_link['href']
        # Handle relative URLs
        if next_url.startswith('/'):
            return urljoin(base_url, next_url) if base_url else next_url
        return next_url
    
    return None
