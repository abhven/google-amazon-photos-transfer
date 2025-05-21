"""
Transfer Manager
Coordinates the transfer of photos from Google Photos to Amazon Photos
"""

import os
import logging
import time
from tqdm import tqdm

logger = logging.getLogger(__name__)

class TransferManager:
    """Manages the transfer of photos from Google Photos to Amazon Photos"""
    
    def __init__(self, google_client, amazon_client, download_dir):
        """Initialize the transfer manager"""
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

    def _get_batch_size(self):
        """Return the batch size for transfers."""
        return int(os.getenv('MAX_PHOTOS_PER_BATCH', 50))
    
    def start_transfer(self, max_photos=None, dry_run=False, transfer_albums=True):
        """Start the transfer process
        
        Args:
            max_photos (int, optional): Maximum number of photos to transfer. Defaults to None (all photos).
            dry_run (bool, optional): If True, simulate the transfer without actually downloading or uploading. Defaults to False.
            transfer_albums (bool, optional): If True, transfer albums with 1:1 mapping. Defaults to True.
        
        Returns:
            dict: Transfer statistics
        """
        logger.info("Starting transfer process")
        
        try:
            # First, transfer albums if requested
            if transfer_albums:
                logger.info("Starting album transfer process")
                self._transfer_albums(dry_run=dry_run)
            
            # Get batch size from environment or use default
            batch_size = self._get_batch_size()
            next_page_token = None
            
            # Track how many photos we've processed for max_photos limit
            photos_processed = 0
            
            # Process media items in batches
            while True:
                # Check if we've reached the max_photos limit
                if max_photos is not None and photos_processed >= max_photos:
                    logger.info(f"Reached maximum number of photos to transfer: {max_photos}")
                    break
                
                # Calculate how many photos to fetch in this batch
                current_batch_size = batch_size
                if max_photos is not None:
                    remaining = max_photos - photos_processed
                    if remaining < batch_size:
                        current_batch_size = remaining
                
                # Get a batch of media items from Google Photos
                media_items, next_page_token = self.google_client.list_media_items(
                    page_size=current_batch_size,
                    page_token=next_page_token
                )
                
                if not media_items:
                    logger.info("No more media items to process")
                    break
                
                self.stats['total'] += len(media_items)
                
                # Process each media item in the batch
                logger.info(f"Processing batch of {len(media_items)} media items")
                self._process_batch(media_items, dry_run=dry_run)
                
                # Update the count of processed photos
                photos_processed += len(media_items)
                
                # If there's no next page token, we've processed all media items
                if not next_page_token:
                    logger.info("No more pages to process")
                    break
                
                # Small delay to avoid rate limiting
                time.sleep(1)
            
            # If we transferred albums, now process photos in each album to maintain the structure
            if transfer_albums and self.album_mapping and not dry_run:
                logger.info("Processing photos in albums to maintain album structure")
                self._process_album_photos(max_photos=max_photos, dry_run=dry_run)
            
            logger.info(f"Transfer completed. Stats: {self.stats}")
            return self.stats
        
        except Exception as e:
            logger.error(f"Error during transfer process: {str(e)}")
            raise
    
    def _process_batch(self, media_items, dry_run=False):
        """Process a batch of media items
        
        Args:
            media_items (list): List of media items to process
            dry_run (bool, optional): If True, simulate the transfer without actually downloading or uploading. Defaults to False.
        """
        for media_item in tqdm(media_items, desc="Transferring photos"):
            self._process_media_item(media_item, dry_run=dry_run)
    
    def _process_media_item(self, media_item, dry_run=False):
        """Process a single media item
        
        Args:
            media_item (dict): Media item to process
            dry_run (bool, optional): If True, simulate the transfer without actually downloading or uploading. Defaults to False.
        
        Returns:
            dict: Upload result if successful, None otherwise
        """
        item_id = media_item['id']
        filename = media_item['filename']
        
        try:
            if dry_run:
                # Simulate download and upload in dry run mode
                logger.info(f"[DRY RUN] Would download {filename} from Google Photos")
                logger.info(f"[DRY RUN] Would upload {filename} to Amazon Photos")
                self.stats['success'] += 1
                return {'success': True, 'id': 'dry-run-id', 'filename': filename}
            
            # Download the media item from Google Photos
            download_result = self.google_client.download_media_item(
                media_item, 
                self.download_dir
            )
            
            if not download_result:
                logger.warning(f"Failed to download {filename}")
                self.stats['failed'] += 1
                return None
            
            # Prepare metadata for upload
            metadata = {
                'google_photos_id': item_id,
                'creation_time': download_result.get('creation_time'),
                'width': download_result.get('width'),
                'height': download_result.get('height'),
                'mime_type': download_result.get('mime_type')
            }
            
            # Upload the media item to Amazon Photos
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
            
            return upload_result
        
        except Exception as e:
            logger.error(f"Error processing media item {filename}: {str(e)}")
            self.stats['failed'] += 1
            return None
    
    def _transfer_albums(self, dry_run=False):
        """Transfer albums from Google Photos to Amazon Photos
        
        Args:
            dry_run (bool, optional): If True, simulate the transfer without actually creating albums. Defaults to False.
        """
        try:
            # Get all albums from Google Photos
            albums, next_page_token = self.google_client.list_albums()
            self.stats['albums_total'] = len(albums)
            
            logger.info(f"Found {len(albums)} albums in Google Photos")
            
            # Process each album
            for album in albums:
                google_album_id = album['id']
                album_title = album['title']
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would create album '{album_title}' in Amazon Photos")
                    self.album_mapping[google_album_id] = f"dry-run-album-{google_album_id}"
                    self.stats['albums_success'] += 1
                    continue
                
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
            
        except Exception as e:
            logger.error(f"Error transferring albums: {str(e)}")
            raise
    
    def _process_album_photos(self, max_photos=None, dry_run=False):
        """Process photos in each album to maintain the album structure
        
        Args:
            max_photos (int, optional): Maximum number of photos to process per album. Defaults to None.
            dry_run (bool, optional): If True, simulate the process. Defaults to False.
        """
        try:
            # Process each Google album
            for google_album_id, amazon_album_id in self.album_mapping.items():
                logger.info(f"Processing photos in album with ID: {google_album_id}")
                
                # Get album details
                album_details = self.google_client.get_album_details(google_album_id)
                album_title = album_details['title']
                
                # Get batch size from environment or use default
                batch_size = self._get_batch_size()
                next_page_token = None
                photos_processed = 0

                # Cache existing photos in the target Amazon album once
                existing_photos = {
                    p['name']: p['id']
                    for p in self.amazon_client.list_photos(album_id=amazon_album_id)
                }
                
                # Process media items in the album in batches
                while True:
                    # Check if we've reached the max_photos limit
                    if max_photos is not None and photos_processed >= max_photos:
                        logger.info(f"Reached maximum number of photos to transfer for album '{album_title}': {max_photos}")
                        break
                    
                    # Calculate how many photos to fetch in this batch
                    current_batch_size = batch_size
                    if max_photos is not None:
                        remaining = max_photos - photos_processed
                        if remaining < batch_size:
                            current_batch_size = remaining
                    
                    # Get a batch of media items from the album
                    media_items, next_page_token = self.google_client.list_media_items(
                        page_size=current_batch_size,
                        page_token=next_page_token,
                        album_id=google_album_id
                    )
                    
                    if not media_items:
                        logger.info(f"No more media items to process in album '{album_title}'")
                        break
                    
                    logger.info(f"Processing batch of {len(media_items)} media items from album '{album_title}'")
                    
                    # Process each media item in the batch
                    for media_item in media_items:
                        item_id = media_item['id']
                        filename = media_item['filename']
                        
                        if dry_run:
                            logger.info(f"[DRY RUN] Would add photo {filename} to album '{album_title}' in Amazon Photos")
                            continue
                        
                        # Check if this photo already exists in the target album
                        if filename in existing_photos:
                            # Photo already exists, add it to the album
                            photo_id = existing_photos[filename]
                            logger.info(f"Found existing photo {filename} with ID: {photo_id}")
                            
                            # Add the photo to the album
                            if self.amazon_client.add_photo_to_album(photo_id, amazon_album_id):
                                logger.info(f"Added photo {filename} to album '{album_title}' in Amazon Photos")
                            else:
                                logger.warning(f"Failed to add photo {filename} to album '{album_title}' in Amazon Photos")
                        else:
                            # Photo doesn't exist yet, transfer it first
                            logger.info(f"Photo {filename} not found in Amazon Photos, transferring it first")
                            upload_result = self._process_media_item(media_item, dry_run=False)
                            
                            if upload_result and upload_result.get('success'):
                                # Add the photo to the album
                                photo_id = upload_result['id']
                                # Remember the new photo so we don't upload it again
                                existing_photos[filename] = photo_id
                                if self.amazon_client.add_photo_to_album(photo_id, amazon_album_id):
                                    logger.info(f"Added photo {filename} to album '{album_title}' in Amazon Photos")
                                else:
                                    logger.warning(f"Failed to add photo {filename} to album '{album_title}' in Amazon Photos")
                    
                    # Update the count of processed photos
                    photos_processed += len(media_items)
                    
                    # If there's no next page token, we've processed all media items in this album
                    if not next_page_token:
                        logger.info(f"No more pages to process for album '{album_title}'")
                        break
                    
                    # Small delay to avoid rate limiting
                    time.sleep(1)
            
            logger.info("Album photo processing completed")
            
        except Exception as e:
            logger.error(f"Error processing album photos: {str(e)}")
            raise
