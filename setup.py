from setuptools import setup, find_packages

setup(
    name="amzpy",
    version="0.1.0",
    description="A lightweight Amazon scraper library.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Anil Sardiwal",
    author_email="theonlyanil@gmail.com",
    url="https://github.com/theonlyanil/amzpy",
    packages=find_packages(),
    license_files = ('LICENSE'),
    install_requires=[
        "requests",
        "beautifulsoup4",
        "fake-useragent",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.6",
        keywords="amazon, scraper, web-scraping, product-data, e-commerce",
)
