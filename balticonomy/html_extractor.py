#!/usr/bin/env python3
"""
HTML Text Extractor with URL Support

Extracts all visible text content from HTML files or URLs using BeautifulSoup.
Uses hashed filenames for cached downloads to avoid duplicate scraping.
"""

from bs4 import BeautifulSoup
import argparse
import sys
import os
import hashlib
import requests
from urllib.parse import urlparse
import time

def download_html(url, cache_dir='scrapes'):
    """
    Download HTML from URL and cache it with hashed filename.
    
    Args:
        url (str): URL to download
        cache_dir (str): Directory to store cached files
        
    Returns:
        str: Path to the downloaded/cached HTML file
    """
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Generate hashed filename
    hashed_filename = hashlib.md5(url.encode('utf-8')).hexdigest() + '.html'
    cached_file_path = os.path.join(cache_dir, hashed_filename)
    
    # Check if file already exists
    if os.path.exists(cached_file_path):
        print(f"Using cached file: {cached_file_path}")
        return cached_file_path

    print(f"Downloading: {url}")
    
    try:
        # Set up headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Download the HTML content
        if not url.startswith('http'):
            url = 'https://' + url  # Ensure URL starts with http/https
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        outtext = response.text
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        outtext = url
    
    # Save to cached file
    with open(cached_file_path, 'w', encoding='utf-8') as f:
        f.write(outtext)
    
    print(f"Downloaded and cached: {cached_file_path}")
    return cached_file_path
        

def is_url(string):
    """
    Check if a string is a valid URL.
    
    Args:
        string (str): String to check
        
    Returns:
        bool: True if string is a URL, False otherwise
    """
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

def url2text(url_in, output_file=None, preserve_formatting=False, cache_dir='scrapes'):
    """
    Extract text content from an HTML file or URL.
    
    Args:
        url_in (str): Path to HTML file or URL
        output_file (str, optional): Path to save extracted text. If None, prints to stdout
        preserve_formatting (bool): Whether to preserve some formatting (line breaks)
        cache_dir (str): Directory for caching downloaded HTML files
        
    Returns:
        str: Extracted text content
    """
    html_file_path = download_html(url_in, cache_dir)
    
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Extract text with proper spacing between elements
    if preserve_formatting:
        # Get text with formatting preserved and spaces between elements
        text = soup.get_text(separator=' ', strip=True)
        # Add line breaks for block elements
        for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'br']):
            if tag.string:
                tag.string.replace_with(tag.string + '\n')
    else:
        # Get text with spaces between elements to prevent words from running together
        text = soup.get_text(separator=' ', strip=True)
    
    # Clean up extra whitespace while preserving intentional spacing
    import re
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Clean up line breaks if preserving formatting
    if preserve_formatting:
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
    else:
        # For non-formatted text, ensure sentences don't run together
        text = text.replace('  ', ' ').strip()
    
    # Generate output filename if not specified and input was URL
    if output_file is None and is_url(url_in):
        # Create output filename based on URL hash
        os.makedirs("scrapes", exist_ok=True)
        url_hash = hashlib.md5(url_in.encode('utf-8')).hexdigest()
        output_file = os.path.join("scrapes", f"{url_hash}_text.txt")
    
    # Output the text
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Text extracted and saved to: {output_file}")
    else:
        print(text)
    
    return text

def main():
    parser = argparse.ArgumentParser(description='Extract text content from HTML files or URLs')
    parser.add_argument('input', help='Path to HTML file or URL')
    parser.add_argument('-o', '--output', help='Output file path (optional)')
    parser.add_argument('-f', '--format', action='store_true',
                       help='Preserve some formatting (line breaks)')
    parser.add_argument('-c', '--cache-dir', default='scrapes',
                       help='Directory for caching downloaded HTML files (default: scrapes)')
    
    args = parser.parse_args()
    
    url2text(args.input, args.output, args.format, args.cache_dir)

if __name__ == "__main__":
    # Example usage if run directly
    if len(sys.argv) == 1:
        print("HTML Text Extractor with URL Support")
        print("Usage examples:")
        print("  python html_extractor.py input.html")
        print("  python html_extractor.py https://example.com")
        print("  python html_extractor.py input.html -o output.txt")
        print("  python html_extractor.py https://example.com -o output.txt")
        print("  python html_extractor.py https://example.com -f -o formatted_output.txt")
        print("  python html_extractor.py https://example.com -c custom_cache_dir")
        print("\nFor help: python html_extractor.py -h")
        print("\nNote: URLs are cached using MD5 hashes to avoid re-downloading")
    else:
        main()