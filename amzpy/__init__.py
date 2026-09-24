"""
AmzPy - Amazon Product Scraper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A lightweight Python library for scraping product information from Amazon.
Now using curl_cffi for better anti-bot protection.

Basic usage:
    >>> from amzpy import AmazonScraper
    >>> scraper = AmazonScraper()
    >>> details = scraper.get_product_details("https://www.amazon.com/dp/B0D4J2QDVY")
    >>> print(details)

:copyright: (c) 2026 by Anil Sardiwal.
:license: MIT, see LICENSE for more details.
"""

from .scraper import AmazonScraper

__version__ = "0.2.0"
__author__ = "Anil Sardiwal"
__license__ = "MIT"
