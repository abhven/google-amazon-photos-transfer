#!/usr/bin/env python3
"""
Mock test for Google Photos to Amazon Photos Transfer
This script simulates the transfer process without real API credentials
"""

import os
import sys
import logging
import json
from datetime import datetime
import time
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mock_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MockGooglePhotosClient:
    """Mock client for simulating Google Photos API"""
    
    def __init__(self):
        """Initialize the mock Google Photos client"""
        logger.info("Initializing Mock Google Photos client...")
        self.media_items = self._generate_mock_media_items()
    
    def _generate_mock_media_items(self):
        """Generate mock media items for testing"""
        items = []
        for i in range(10):
            items.append({
                'id': f'photo_{i}',
                'filename': f'photo_{i}.jpg',
                'baseUrl': f'https://example.com/photo_{i}',
                'mimeType': 'image/jpeg',
                'mediaMetadata': {
                    'creationTime': '2023-01-01T00:00:00Z',
                    'width': '1920',
                    'height': '1080'
                }
            })
        return items
    
    def list_media_items(self, page_size=50, page_token=None):
        """Mock list media items from Google Photos"""
        logger.info(f"Mock fetching media items (page_size={page_size}, page_token={page_token})")
        
        # Simulate pagination
        if page_token:
            # If there's a page token, we've already returned all items
            return [], None
        
        return self.media_items, None
    
    def download_media_item(self, media_item, download_dir):
        """Mock download a media item from Google Photos"""
        item_id = media_item['id']
        filename = media_item['filename']
        
        # Create download path
        download_path = os.path.join(download_dir, filename)
        
        # Simulate download by creating an empty file
        with open(download_path, 'w') as f:
            f.write(f"Mock content for {filename}")
        
        logger.info(f"Mock downloaded {filename}")
        
        # Return metadata along with the download path
        return {
            'id': item_id,
            'filename': filename,
            'path': download_path,
            'mime_type': 'image/jpeg',
            'creation_time': media_item.get('mediaMetadata', {}).get('creationTime'),
            'width': media_item.get('mediaMetadata', {}).get('width'),
            'height': media_item.get('mediaMetadata', {}).get('height')
        }

class MockAmazonPhotosClient:
    """Mock client for simulating Amazon Photos API"""
    
    def __init__(self):
        """Initialize the mock Amazon Photos client"""
        logger.info("Initializing Mock Amazon Photos client...")
        self.uploaded_photos = []
        self.photos_folder_id = 'mock-photos-folder-id'
    
    def _get_photos_folder_id(self):
        """Mock getting the Photos folder ID"""
        logger.info("Mock getting Photos folder ID")
        return self.photos_folder_id
    
    def upload_photo(self, file_path, metadata=None):
        """Mock upload a photo to Amazon Photos"""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {
                'success': False,
                'filename': os.path.basename(file_path),
                'error': 'File not found'
            }
        
        filename = os.path.basename(file_path)
        logger.info(f"Mock uploading {filename} to Amazon Photos...")
        
        # Simulate upload delay
        time.sleep(0.2)
        
        # Generate a mock file ID
        file_id = f"mock-file-{len(self.uploaded_photos)}"
        
        # Add to uploaded photos
        self.uploaded_photos.append({
            'id': file_id,
            'filename': filename,
            'metadata': metadata,
            'folder_id': self.photos_folder_id
        })
        
        logger.info(f"Mock successfully uploaded {filename} to Amazon Photos")
        
        # Return success with Amazon Photos specific format
        return {
            'success': True,
            'filename': filename,
            'id': file_id,
            'url': f'https://www.amazon.com/clouddrive/share/{file_id}'
        }

class MockTransferManager:
    """Mock manager for the transfer process"""
    
    def __init__(self, google_client, amazon_client, download_dir):
        """Initialize the mock transfer manager"""
        self.google_client = google_client
        self.amazon_client = amazon_client
        self.download_dir = download_dir
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def start_transfer(self):
        """Start the mock transfer process"""
        logger.info("Starting mock transfer process")
        
        # Get media items from Google Photos
        media_items, _ = self.google_client.list_media_items()
        
        if not media_items:
            logger.info("No media items to process")
            return self.stats
        
        self.stats['total'] = len(media_items)
        
        # Process each media item
        logger.info(f"Processing batch of {len(media_items)} media items")
        for media_item in tqdm(media_items, desc="Transferring photos"):
            self._process_media_item(media_item)
        
        logger.info(f"Mock transfer completed. Stats: {self.stats}")
        return self.stats
    
    def _process_media_item(self, media_item):
        """Process a single media item"""
        filename = media_item['filename']
        
        try:
            # Download the media item
            download_result = self.google_client.download_media_item(
                media_item, 
                self.download_dir
            )
            
            if not download_result:
                logger.warning(f"Failed to download {filename}")
                self.stats['failed'] += 1
                return
            
            # Prepare metadata
            metadata = {
                'google_photos_id': download_result['id'],
                'creation_time': download_result.get('creation_time'),
                'width': download_result.get('width'),
                'height': download_result.get('height'),
                'mime_type': download_result.get('mime_type')
            }
            
            # Upload to Amazon Photos
            upload_result = self.amazon_client.upload_photo(
                download_result['path'],
                metadata=metadata
            )
            
            # Handle upload result
            if upload_result and upload_result.get('success'):
                logger.info(f"Successfully transferred {filename}")
                self.stats['success'] += 1
            else:
                logger.warning(f"Failed to upload {filename} to Amazon Photos")
                self.stats['failed'] += 1
            
            # Clean up downloaded file
            if os.path.exists(download_result['path']):
                os.remove(download_result['path'])
                logger.debug(f"Removed temporary file: {download_result['path']}")
        
        except Exception as e:
            logger.error(f"Error processing media item {filename}: {str(e)}")
            self.stats['failed'] += 1

def generate_transfer_report(stats, report_path):
    """Generate a JSON report of the transfer process"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats,
        'summary': f"Successfully transferred {stats['success']} photos, {stats['failed']} failed"
    }
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Transfer report generated at {report_path}")

def main():
    """Main function to orchestrate the mock photo transfer process"""
    # Create download directory if it doesn't exist
    download_dir = './downloads'
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Initialize mock clients
        google_client = MockGooglePhotosClient()
        amazon_client = MockAmazonPhotosClient()
        
        # Initialize mock transfer manager
        transfer_manager = MockTransferManager(
            google_client=google_client,
            amazon_client=amazon_client,
            download_dir=download_dir
        )
        
        # Start the transfer process
        logger.info("Starting mock photo transfer process...")
        transfer_stats = transfer_manager.start_transfer()
        
        # Generate transfer report
        report_path = './mock_transfer_report.json'
        generate_transfer_report(transfer_stats, report_path)
        
        logger.info(f"Mock transfer completed. Transferred {transfer_stats['success']} photos successfully.")
        logger.info(f"Transfer report saved to {report_path}")
        
    except Exception as e:
        logger.error(f"An error occurred during the mock transfer process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
