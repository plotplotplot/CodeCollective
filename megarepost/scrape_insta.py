import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import requests

def setup_selenium_driver():
    """Configure and return a Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Update this path to your chromedriver location
    service = Service('/usr/local/bin/chromedriver')  # Update this path
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def download_instagram_reel(reel_url, output_dir='downloads'):
    """
    Downloads an Instagram Reel video using Selenium to handle JavaScript rendering.
    
    Args:
        reel_url (str): URL of the Instagram Reel
        output_dir (str): Directory to save the video and metadata
    """
    try:
        # Validate URL
        parsed = urlparse(reel_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL provided")
            
        if 'instagram.com' not in parsed.netloc:
            raise ValueError("URL must be from instagram.com")
            
        if '/reel/' not in reel_url:
            raise ValueError("URL must be an Instagram Reel")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up Selenium
        driver = setup_selenium_driver()
        driver.get(reel_url)
        
        # Wait for page to load (adjust time as needed)
        time.sleep(5)
        
        # Try to find video element
        video_element = driver.find_element(By.TAG_NAME, 'video')
        if not video_element:
            raise Exception("Could not find video element on page")
            
        video_url = video_element.get_attribute('src')
        if not video_url:
            raise Exception("Video element has no source URL")
            
        # Get metadata from meta tags
        title = driver.title
        description = driver.find_element(By.XPATH, '//meta[@property="og:description"]').get_attribute('content')
        thumbnail_url = driver.find_element(By.XPATH, '//meta[@property="og:image"]').get_attribute('content')
        
        # Extract username
        publisher = reel_url.split('/')[3]
        publisher_url = f"https://www.instagram.com/{publisher}/"
        video_id = reel_url.split('/')[-2]
        
        # Download the video
        video_filename = f"{video_id}.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(video_url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Prepare metadata
        metadata = {
            "video_url": reel_url,
            "video_file": video_filename,
            "title": title,
            "description": description,
            "publisher": publisher,
            "publisher_url": publisher_url,
            "download_time": str(datetime.now()),
            "thumbnail_url": thumbnail_url,
            "video_id": video_id
        }
        
        # Save metadata
        metadata_path = os.path.join(output_dir, f"{video_id}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully downloaded Reel to {video_path}")
        return metadata
        
    except Exception as e:
        print(f"Error downloading Reel: {str(e)}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    # Example usage
    reel_url = "https://www.instagram.com/reel/C5Xj5aZJQJK/"  # Test with a working reel
    download_instagram_reel(reel_url)