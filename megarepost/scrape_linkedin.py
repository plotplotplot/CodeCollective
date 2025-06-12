#!/usr/bin/env python3
"""
LinkedIn Video Downloader
Downloads videos from LinkedIn posts and extracts metadata to JSON
"""

import json
import re
import os
import requests
from urllib.parse import urlparse, unquote
from datetime import datetime
import argparse
from bs4 import BeautifulSoup
import time


class LinkedInVideoDownloader:
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_metadata_from_html(self, html_content):
        """Extract metadata from LinkedIn post HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}
        
        # Extract JSON-LD structured data
        json_ld_script = soup.find('script', {'type': 'application/ld+json'})
        if json_ld_script:
            try:
                json_data = json.loads(json_ld_script.string)
                metadata.update({
                    'title': json_data.get('headline', ''),
                    'description': json_data.get('description', ''),
                    'date_published': json_data.get('datePublished', ''),
                    'upload_date': json_data.get('uploadDate', ''),
                    'duration': json_data.get('duration', ''),
                    'thumbnail_url': json_data.get('thumbnailUrl', ''),
                    'video_url': json_data.get('contentUrl', ''),
                    'embed_url': json_data.get('embedUrl', ''),
                    'width': json_data.get('width', 0),
                    'height': json_data.get('height', 0),
                    'interaction_stats': json_data.get('interactionStatistic', [])
                })
                
                # Extract creator information
                creator = json_data.get('creator', {})
                if creator:
                    metadata['creator'] = {
                        'name': creator.get('name', ''),
                        'url': creator.get('url', ''),
                        'image_url': creator.get('image', {}).get('url', ''),
                        'type': creator.get('@type', ''),
                        'followers': creator.get('interactionStatistic', {}).get('userInteractionCount', 0)
                    }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON-LD: {e}")
        
        # Extract Open Graph metadata
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        for tag in og_tags:
            property_name = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            if property_name and content:
                metadata[f'og_{property_name}'] = content
        
        # Extract Twitter metadata
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', '')
            content = tag.get('content', '')
            if name and content:
                metadata[f'twitter_{name}'] = content
        
        # Extract canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            metadata['canonical_url'] = canonical.get('href', '')
        
        # Extract post ID from meta tags
        page_instance = soup.find('meta', {'id': 'config'})
        if page_instance:
            data_page_instance = page_instance.get('data-page-instance', '')
            if data_page_instance:
                metadata['page_instance'] = data_page_instance
        
        return metadata
    
    def download_video(self, video_url, filename):
        """Download video from URL"""
        try:
            print(f"Downloading video from: {video_url}")
            response = self.session.get(video_url, stream=True)
            response.raise_for_status()
            
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"Video downloaded successfully: {filepath}")
            return filepath
            
        except requests.RequestException as e:
            print(f"Error downloading video: {e}")
            return None
    
    def download_thumbnail(self, thumbnail_url, filename):
        """Download thumbnail image"""
        try:
            print(f"Downloading thumbnail from: {thumbnail_url}")
            response = self.session.get(thumbnail_url)
            response.raise_for_status()
            
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"Thumbnail downloaded successfully: {filepath}")
            return filepath
            
        except requests.RequestException as e:
            print(f"Error downloading thumbnail: {e}")
            return None
    
    def generate_filename(self, title, extension):
        """Generate safe filename from title"""
        # Remove special characters and limit length
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        safe_title = safe_title.strip('-')[:50]  # Limit to 50 characters
        
        if not safe_title:
            safe_title = f"linkedin_video_{int(time.time())}"
        
        return f"{safe_title}.{extension}"
    
    def process_html_file(self, html_file_path, download_media=True):
        """Process HTML file and extract video information"""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract metadata
            metadata = self.extract_metadata_from_html(html_content)
            
            # Add processing timestamp
            metadata['processed_at'] = datetime.now().isoformat()
            metadata['source_file'] = html_file_path
            
            # Generate base filename
            title = metadata.get('title', 'linkedin_video')
            base_filename = self.generate_filename(title, 'json').replace('.json', '')
            
            downloaded_files = {}
            
            if download_media:
                # Download video if available
                video_url = metadata.get('video_url')
                if video_url:
                    video_filename = f"{base_filename}.mp4"
                    video_path = self.download_video(video_url, video_filename)
                    if video_path:
                        downloaded_files['video'] = {
                            'filename': video_filename,
                            'path': video_path,
                            'url': video_url
                        }
                
                # Download thumbnail if available
                thumbnail_url = metadata.get('thumbnail_url')
                if thumbnail_url:
                    # Determine thumbnail extension from URL
                    parsed_url = urlparse(thumbnail_url)
                    thumbnail_ext = 'jpg'  # Default
                    if '.' in parsed_url.path:
                        thumbnail_ext = parsed_url.path.split('.')[-1].lower()
                        if thumbnail_ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                            thumbnail_ext = 'jpg'
                    
                    thumbnail_filename = f"{base_filename}_thumbnail.{thumbnail_ext}"
                    thumbnail_path = self.download_thumbnail(thumbnail_url, thumbnail_filename)
                    if thumbnail_path:
                        downloaded_files['thumbnail'] = {
                            'filename': thumbnail_filename,
                            'path': thumbnail_path,
                            'url': thumbnail_url
                        }
            
            # Add downloaded files info to metadata
            metadata['downloaded_files'] = downloaded_files
            
            # Save metadata to JSON file
            json_filename = f"{base_filename}.json"
            json_filepath = os.path.join(self.output_dir, json_filename)
            
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"Metadata saved to: {json_filepath}")
            
            return {
                'metadata': metadata,
                'json_file': json_filepath,
                'downloaded_files': downloaded_files
            }
            
        except Exception as e:
            print(f"Error processing HTML file: {e}")
            return None
    
    def process_url(self, url, download_media=True):
        """Process LinkedIn post URL directly"""
        try:
            print(f"Fetching content from: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            # Save HTML content temporarily
            temp_html_file = os.path.join(self.output_dir, 'temp_linkedin_post.html')
            with open(temp_html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Process the HTML content
            result = self.process_html_file(temp_html_file, download_media)
            
            # Clean up temporary file
            try:
                os.remove(temp_html_file)
            except:
                pass
            
            return result
            
        except requests.RequestException as e:
            print(f"Error fetching URL: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Download LinkedIn videos and extract metadata')
    parser.add_argument('input', help='LinkedIn post URL or HTML file path')
    parser.add_argument('-o', '--output', default='downloads', help='Output directory (default: downloads)')
    parser.add_argument('--no-download', action='store_true', help='Skip downloading media files')
    parser.add_argument('--json-only', action='store_true', help='Only extract metadata to JSON')
    
    args = parser.parse_args()
    
    downloader = LinkedInVideoDownloader(args.output)
    
    # Determine if input is URL or file path
    if args.input.startswith(('http://', 'https://')):
        # Process URL
        result = downloader.process_url(args.input, download_media=not (args.no_download or args.json_only))
    else:
        # Process HTML file
        result = downloader.process_html_file(args.input, download_media=not (args.no_download or args.json_only))
    
    if result:
        print("\n=== Processing Summary ===")
        print(f"JSON metadata: {result['json_file']}")
        
        if result['downloaded_files']:
            print("Downloaded files:")
            for file_type, file_info in result['downloaded_files'].items():
                print(f"  {file_type}: {file_info['filename']}")
        else:
            print("No media files downloaded")
        
        # Print key metadata
        metadata = result['metadata']
        print(f"\nTitle: {metadata.get('title', 'N/A')}")
        print(f"Creator: {metadata.get('creator', {}).get('name', 'N/A')}")
        print(f"Duration: {metadata.get('duration', 'N/A')}")
        print(f"Published: {metadata.get('date_published', 'N/A')}")
    
    else:
        print("Failed to process input")


if __name__ == "__main__":
    main()