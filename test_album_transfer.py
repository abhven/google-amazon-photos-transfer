#!/usr/bin/env python3
"""
Test script for album transfer functionality
This script tests the album transfer logic without making actual API calls
"""

import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockGooglePhotosClient:
    """Mock Google Photos client for testing"""
    
    def __init__(self):
        """Initialize the mock client"""
        self.albums = [
            {'id': 'album1', 'title': 'Vacation 2023'},
            {'id': 'album2', 'title': 'Family Photos'},
            {'id': 'album3', 'title': 'Work Events'}
        ]
        self.media_items = {
            'album1': [
                {'id': 'photo1', 'filename': 'beach.jpg'},
                {'id': 'photo2', 'filename': 'sunset.jpg'}
            ],
            'album2': [
                {'id': 'photo3', 'filename': 'family_dinner.jpg'},
                {'id': 'photo4', 'filename': 'birthday.jpg'}
            ],
            'album3': [
                {'id': 'photo5', 'filename': 'conference.jpg'},
                {'id': 'photo6', 'filename': 'team_lunch.jpg'}
            ]
        }
    
    def list_albums(self, page_size=50, page_token=None):
        """List albums from Google Photos"""
        logger.info("Mock: Listing albums from Google Photos")
        return self.albums, None
    
    def get_album_details(self, album_id):
        """Get details of a specific album"""
        logger.info(f"Mock: Getting details for album {album_id}")
        for album in self.albums:
            if album['id'] == album_id:
                return album
        return None
    
    def list_media_items(self, page_size=50, page_token=None, album_id=None):
        """List media items from Google Photos"""
        logger.info(f"Mock: Listing media items from album {album_id}")
        if album_id and album_id in self.media_items:
            return self.media_items[album_id], None
        return [], None
    
    def download_media_item(self, media_item, download_dir):
        """Mock downloading a media item"""
        logger.info(f"Mock: Downloading {media_item['filename']}")
        return {
            'path': os.path.join(download_dir, media_item['filename']),
            'creation_time': datetime.now().isoformat(),
            'width': 1920,
            'height': 1080,
            'mime_type': 'image/jpeg'
        }

class MockAmazonPhotosClient:
    """Mock Amazon Photos client for testing"""
    
    def __init__(self):
        """Initialize the mock client"""
        self.albums = []
        self.photos = []
    
    def list_albums(self, max_items=100):
        """List albums in Amazon Photos"""
        logger.info("Mock: Listing albums from Amazon Photos")
        return self.albums
    
    def create_album(self, name, description=None):
        """Create a new album in Amazon Photos"""
        logger.info(f"Mock: Creating album '{name}' in Amazon Photos")
        album_id = f"amazon-{len(self.albums) + 1}"
        album = {
            'id': album_id,
            'name': name,
            'description': description
        }
        self.albums.append(album)
        return album
    
    def get_album_by_name(self, name):
        """Get an album by name"""
        logger.info(f"Mock: Finding album '{name}' in Amazon Photos")
        for album in self.albums:
            if album['name'] == name:
                return album
        return None
    
    def upload_photo(self, file_path, metadata=None):
        """Upload a photo to Amazon Photos"""
        logger.info(f"Mock: Uploading {os.path.basename(file_path)} to Amazon Photos")
        photo_id = f"photo-{len(self.photos) + 1}"
        photo = {
            'id': photo_id,
            'name': os.path.basename(file_path),
            'metadata': metadata,
            'success': True
        }
        self.photos.append(photo)
        return photo
    
    def list_photos(self, max_items=1000, album_id=None):
        """List photos in Amazon Photos"""
        logger.info(f"Mock: Listing photos from Amazon Photos, album_id={album_id}")
        return self.photos
    
    def add_photo_to_album(self, photo_id, album_id):
        """Add a photo to an album"""
        logger.info(f"Mock: Adding photo {photo_id} to album {album_id}")
        return True

class TestTransferManager:
    """Test transfer manager for album transfer functionality"""
    
    def __init__(self, google_client, amazon_client, download_dir):
        """Initialize the test transfer manager"""
        self.google_client = google_client
        self.amazon_client = amazon_client
        self.download_dir = download_dir
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'albums_total': 0,
            'albums_success': 0,
            'albums_failed': 0
        }
        # Map to store Google album ID to Amazon album ID mapping
        self.album_mapping = {}
    
    def test_album_transfer(self):
        """Test album transfer functionality"""
        logger.info("Starting album transfer test")
        
        # Get all albums from Google Photos
        albums, _ = self.google_client.list_albums()
        self.stats['albums_total'] = len(albums)
        
        logger.info(f"Found {len(albums)} albums in Google Photos")
        
        # Process each album
        for album in albums:
            google_album_id = album['id']
            album_title = album['title']
            
            logger.info(f"Processing album '{album_title}' ({google_album_id})")
            
            # Check if album already exists in Amazon Photos
            existing_album = self.amazon_client.get_album_by_name(album_title)
            
            if existing_album:
                logger.info(f"Album '{album_title}' already exists in Amazon Photos with ID: {existing_album['id']}")
                self.album_mapping[google_album_id] = existing_album['id']
                self.stats['albums_success'] += 1
            else:
                # Create the album in Amazon Photos
                description = album.get('productUrl', '')
                new_album = self.amazon_client.create_album(album_title, description=description)
                
                if new_album:
                    logger.info(f"Created album '{album_title}' in Amazon Photos with ID: {new_album['id']}")
                    self.album_mapping[google_album_id] = new_album['id']
                    self.stats['albums_success'] += 1
                else:
                    logger.error(f"Failed to create album '{album_title}' in Amazon Photos")
                    self.stats['albums_failed'] += 1
        
        logger.info(f"Album transfer completed. {self.stats['albums_success']} albums transferred successfully.")
        
        # Process photos in each album
        self.test_album_photos()
        
        return self.stats
    
    def test_album_photos(self):
        """Test processing photos in each album"""
        logger.info("Testing album photo processing")
        
        # Process each Google album
        for google_album_id, amazon_album_id in self.album_mapping.items():
            # Get album details
            album_details = self.google_client.get_album_details(google_album_id)
            album_title = album_details['title']
            
            logger.info(f"Processing photos in album '{album_title}' ({google_album_id})")
            
            # Get media items from the album
            media_items, _ = self.google_client.list_media_items(album_id=google_album_id)
            
            if not media_items:
                logger.info(f"No media items in album '{album_title}'")
                continue
            
            logger.info(f"Found {len(media_items)} media items in album '{album_title}'")
            
            # Process each media item in the album
            for media_item in media_items:
                item_id = media_item['id']
                filename = media_item['filename']
                
                logger.info(f"Processing media item '{filename}' ({item_id})")
                
                # Download the media item from Google Photos
                download_result = self.google_client.download_media_item(media_item, self.download_dir)
                
                # Upload the media item to Amazon Photos
                upload_result = self.amazon_client.upload_photo(
                    download_result['path'],
                    metadata={'google_photos_id': item_id}
                )
                
                if upload_result and upload_result.get('success'):
                    logger.info(f"Successfully transferred {filename}")
                    self.stats['success'] += 1
                    
                    # Add the photo to the album
                    photo_id = upload_result['id']
                    if self.amazon_client.add_photo_to_album(photo_id, amazon_album_id):
                        logger.info(f"Added photo {filename} to album '{album_title}' in Amazon Photos")
                    else:
                        logger.warning(f"Failed to add photo {filename} to album '{album_title}' in Amazon Photos")
                else:
                    logger.warning(f"Failed to upload {filename} to Amazon Photos")
                    self.stats['failed'] += 1
        
        logger.info("Album photo processing completed")
        return self.stats

def main():
    """Main function to run the test"""
    # Create download directory
    download_dir = './test_downloads'
    os.makedirs(download_dir, exist_ok=True)
    
    # Initialize mock clients
    google_client = MockGooglePhotosClient()
    amazon_client = MockAmazonPhotosClient()
    
    # Initialize test transfer manager
    transfer_manager = TestTransferManager(
        google_client=google_client,
        amazon_client=amazon_client,
        download_dir=download_dir
    )
    
    # Run the test
    logger.info("Starting album transfer test")
    stats = transfer_manager.test_album_transfer()
    
    # Generate test report
    report = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats,
        'summary': f"Successfully transferred {stats['success']} photos, {stats['failed']} failed, {stats['albums_success']} albums transferred successfully"
    }
    
    with open('test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Test completed. Stats: {stats}")
    logger.info(f"Test report saved to test_report.json")

if __name__ == "__main__":
    main()
