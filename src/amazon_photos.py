"""
Amazon Photos API Client
Handles authentication and interaction with Amazon Photos API
"""

import os
import logging
import requests
import json
import time
import mimetypes
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

logger = logging.getLogger(__name__)

class AmazonPhotosClient:
    """Client for interacting with Amazon Photos API"""
    
    # Amazon Photos API endpoints
    BASE_URL = 'https://api.amazon.com/drive/v1'
    AUTH_URL = 'https://api.amazon.com/auth/o2/token'
    UPLOAD_URL = f'{BASE_URL}/files'
    NODES_URL = f'{BASE_URL}/nodes'
    
    def __init__(self):
        """Initialize the Amazon Photos client"""
        self.session = None
        self.access_token = None
        self.token_expires_at = 0
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Amazon Photos API"""
        try:
            # Get Amazon credentials from environment variables
            client_id = os.getenv('AMAZON_CLIENT_ID')
            client_secret = os.getenv('AMAZON_CLIENT_SECRET')
            refresh_token = os.getenv('AMAZON_REFRESH_TOKEN')
            
            if not client_id or not client_secret:
                raise ValueError("Amazon API credentials not found in environment variables")
            
            # If we have a refresh token, use it to get a new access token
            if refresh_token:
                logger.info("Using refresh token to authenticate with Amazon Photos API")
                self._refresh_access_token(client_id, client_secret, refresh_token)
            else:
                # For initial setup, we need to go through the OAuth2 flow
                # This would typically be done in a separate setup script
                logger.error("No refresh token found. Please run the setup script first.")
                raise ValueError("No refresh token found for Amazon Photos API")
            
            logger.info("Successfully authenticated with Amazon Photos API")
        
        except Exception as e:
            logger.error(f"Error authenticating with Amazon Photos: {str(e)}")
            raise
    
    def _refresh_access_token(self, client_id, client_secret, refresh_token):
        """Refresh the access token using the refresh token"""
        try:
            # Prepare the token request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret
            }
            
            # Make the token request
            response = requests.post(self.AUTH_URL, data=data)
            response.raise_for_status()
            
            # Parse the response
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = time.time() + token_data['expires_in']
            
            # Create a session with the access token
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            })
            
            logger.info("Successfully refreshed Amazon Photos API access token")
        
        except Exception as e:
            logger.error(f"Error refreshing Amazon Photos API access token: {str(e)}")
            raise
    
    def _ensure_authenticated(self):
        """Ensure that we have a valid access token"""
        # If the token is about to expire (within 60 seconds), refresh it
        if time.time() > (self.token_expires_at - 60):
            logger.info("Access token is about to expire, refreshing...")
            self.authenticate()
    
    def _get_photos_folder_id(self):
        """Get the ID of the Photos folder in Amazon Drive"""
        self._ensure_authenticated()
        
        try:
            # Query for the Photos folder
            params = {
                'filters': 'kind:FOLDER AND name:Photos',
                'asset': 'ALL'
            }
            
            response = self.session.get(self.NODES_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get('count', 0) > 0:
                # Return the first matching folder ID
                return data['data'][0]['id']
            
            # If the Photos folder doesn't exist, create it
            logger.info("Photos folder not found, creating it...")
            return self._create_photos_folder()
        
        except Exception as e:
            logger.error(f"Error getting Photos folder ID: {str(e)}")
            raise
    
    def _create_photos_folder(self):
        """Create a Photos folder in Amazon Drive"""
        self._ensure_authenticated()
        
        try:
            # Get the root folder ID
            response = self.session.get(f"{self.NODES_URL}/root")
            response.raise_for_status()
            root_id = response.json()['id']
            
            # Create the Photos folder
            data = {
                'name': 'Photos',
                'kind': 'FOLDER',
                'parents': [root_id]
            }
            
            response = self.session.post(self.NODES_URL, json=data)
            response.raise_for_status()
            
            folder_id = response.json()['id']
            logger.info(f"Created Photos folder with ID: {folder_id}")
            
            return folder_id
        
        except Exception as e:
            logger.error(f"Error creating Photos folder: {str(e)}")
            raise
    
    def upload_photo(self, file_path, metadata=None):
        """Upload a photo to Amazon Photos"""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {
                'success': False,
                'filename': os.path.basename(file_path),
                'error': 'File not found'
            }
        
        self._ensure_authenticated()
        filename = os.path.basename(file_path)
        
        try:
            # Get the Photos folder ID
            photos_folder_id = self._get_photos_folder_id()
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif file_path.lower().endswith('.png'):
                    content_type = 'image/png'
                elif file_path.lower().endswith('.gif'):
                    content_type = 'image/gif'
                elif file_path.lower().endswith(('.mp4', '.mov')):
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'
            
            # Step 1: Create the upload session
            logger.info(f"Creating upload session for {filename}...")
            
            # Prepare metadata for the file
            file_metadata = {
                'name': filename,
                'kind': 'FILE',
                'parents': [photos_folder_id]
            }
            
            # Add custom metadata if provided
            if metadata:
                # Amazon Photos supports custom properties in the metadata field
                custom_metadata = {}
                for key, value in metadata.items():
                    if value is not None:
                        custom_metadata[key] = str(value)
                
                if custom_metadata:
                    file_metadata['properties'] = custom_metadata
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create the upload session
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.UPLOAD_URL}/upload",
                headers=headers,
                json={
                    'contentType': content_type,
                    'name': filename,
                    'parents': [photos_folder_id],
                    'size': file_size
                }
            )
            response.raise_for_status()
            
            # Get the upload URL
            upload_data = response.json()
            upload_url = upload_data['uploadUrl']
            
            # Step 2: Upload the file
            logger.info(f"Uploading {filename} to Amazon Photos...")
            
            with open(file_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    data=f,
                    headers={
                        'Content-Type': content_type
                    }
                )
                upload_response.raise_for_status()
            
            # Step 3: Complete the upload by creating the node
            logger.info(f"Completing upload for {filename}...")
            
            # The file ID is in the upload response
            file_id = upload_data['id']
            
            # Update the file metadata if needed
            if metadata:
                update_response = self.session.patch(
                    f"{self.NODES_URL}/{file_id}",
                    json={'properties': custom_metadata}
                )
                update_response.raise_for_status()
            
            logger.info(f"Successfully uploaded {filename} to Amazon Photos")
            
            # Return the file information
            return {
                'success': True,
                'filename': filename,
                'id': file_id,
                'url': f"https://www.amazon.com/clouddrive/share/{file_id}"
            }
        
        except Exception as e:
            logger.error(f"Error uploading {filename} to Amazon Photos: {str(e)}")
            return {
                'success': False,
                'filename': filename,
                'error': str(e)
            }
    
    def list_photos(self, max_items=1000, album_id=None):
        """List photos in Amazon Photos
        
        Args:
            max_items (int, optional): Maximum number of items to return. Defaults to 1000.
            album_id (str, optional): Album ID to list photos from. Defaults to None.
            
        Returns:
            list: List of photo items
        """
        self._ensure_authenticated()
        
        try:
            if album_id:
                # Query for photos in the specific album
                params = {
                    'filters': f"kind:FILE AND parents:{album_id}",
                    'limit': max_items,
                    'asset': 'ALL'
                }
            else:
                # Get the Photos folder ID
                photos_folder_id = self._get_photos_folder_id()
                
                # Query for photos in the Photos folder
                params = {
                    'filters': f"kind:FILE AND parents:{photos_folder_id}",
                    'limit': max_items,
                    'asset': 'ALL'
                }
            
            response = self.session.get(self.NODES_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('data', [])
            
            logger.info(f"Found {len(items)} items in Amazon Photos")
            
            return items
        
        except Exception as e:
            logger.error(f"Error listing photos in Amazon Photos: {str(e)}")
            return []
            
    def list_albums(self, max_items=100):
        """List albums in Amazon Photos
        
        Args:
            max_items (int, optional): Maximum number of albums to return. Defaults to 100.
            
        Returns:
            list: List of album items
        """
        self._ensure_authenticated()
        
        try:
            # Query for albums (folders with label ALBUM)
            params = {
                'filters': "kind:FOLDER AND labels:ALBUM",
                'limit': max_items,
                'asset': 'ALL'
            }
            
            response = self.session.get(self.NODES_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            albums = data.get('data', [])
            
            logger.info(f"Found {len(albums)} albums in Amazon Photos")
            
            return albums
        
        except Exception as e:
            logger.error(f"Error listing albums in Amazon Photos: {str(e)}")
            return []
    
    def create_album(self, name, description=None):
        """Create a new album in Amazon Photos
        
        Args:
            name (str): Name of the album
            description (str, optional): Description of the album. Defaults to None.
            
        Returns:
            dict: Album information if successful, None otherwise
        """
        self._ensure_authenticated()
        
        try:
            # Get the Photos folder ID as the parent
            photos_folder_id = self._get_photos_folder_id()
            
            # Prepare album metadata
            album_data = {
                'name': name,
                'kind': 'FOLDER',
                'parents': [photos_folder_id],
                'labels': ['ALBUM']
            }
            
            # Add description if provided
            if description:
                album_data['description'] = description
            
            # Create the album
            response = self.session.post(self.NODES_URL, json=album_data)
            response.raise_for_status()
            
            album = response.json()
            logger.info(f"Created album '{name}' with ID: {album['id']}")
            
            return album
        
        except Exception as e:
            logger.error(f"Error creating album '{name}': {str(e)}")
            return None
    
    def get_album_by_name(self, name):
        """Get an album by name
        
        Args:
            name (str): Name of the album to find
            
        Returns:
            dict: Album information if found, None otherwise
        """
        self._ensure_authenticated()
        
        try:
            # Query for albums with the specified name
            params = {
                'filters': f"kind:FOLDER AND labels:ALBUM AND name:'{name}'",
                'asset': 'ALL'
            }
            
            response = self.session.get(self.NODES_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get('count', 0) > 0:
                album = data['data'][0]
                logger.info(f"Found album '{name}' with ID: {album['id']}")
                return album
            
            logger.info(f"Album '{name}' not found")
            return None
        
        except Exception as e:
            logger.error(f"Error getting album '{name}': {str(e)}")
            return None
    
    def add_photo_to_album(self, photo_id, album_id):
        """Add a photo to an album
        
        Args:
            photo_id (str): ID of the photo to add
            album_id (str): ID of the album to add the photo to
            
        Returns:
            bool: True if successful, False otherwise
        """
        self._ensure_authenticated()
        
        try:
            # Add the photo to the album by updating its parents
            # First, get the current photo node to see its existing parents
            response = self.session.get(f"{self.NODES_URL}/{photo_id}")
            response.raise_for_status()
            
            photo_data = response.json()
            current_parents = photo_data.get('parents', [])
            
            # Add the album ID to the parents if it's not already there
            if album_id not in current_parents:
                current_parents.append(album_id)
                
                # Update the photo's parents
                update_data = {
                    'parents': current_parents
                }
                
                update_response = self.session.patch(
                    f"{self.NODES_URL}/{photo_id}",
                    json=update_data
                )
                update_response.raise_for_status()
                
                logger.info(f"Added photo {photo_id} to album {album_id}")
                return True
            
            # Photo is already in the album
            logger.info(f"Photo {photo_id} is already in album {album_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding photo {photo_id} to album {album_id}: {str(e)}")
            return False
