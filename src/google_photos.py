"""
Google Photos API Client
Handles authentication and interaction with Google Photos API
"""

import os
import pickle
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GooglePhotosClient:
    """Client for interacting with Google Photos API"""
    
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
    API_SERVICE_NAME = 'photoslibrary'
    API_VERSION = 'v1'
    
    def __init__(self):
        """Initialize the Google Photos client"""
        self.credentials = None
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google Photos API"""
        # Check if we have saved credentials
        token_path = 'token.pickle'
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.credentials = pickle.load(token)
        
        # If credentials don't exist or are invalid, get new ones
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing Google Photos credentials...")
                self.credentials.refresh(Request())
            else:
                logger.info("Getting new Google Photos credentials...")
                client_config = {
                    'installed': {
                        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                        'redirect_uris': [os.getenv('GOOGLE_REDIRECT_URI')],
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://oauth2.googleapis.com/token',
                    }
                }
                flow = InstalledAppFlow.from_client_config(
                    client_config, self.SCOPES)
                # Use HTTPS for the redirect URI
                self.credentials = flow.run_local_server(port=8080, ssl_keyfile='key.pem', ssl_certfile='cert.pem')
            
            # Save the credentials for the next run
            with open(token_path, 'wb') as token:
                pickle.dump(self.credentials, token)
        
        # Build the service
        self.service = build(
            self.API_SERVICE_NAME, 
            self.API_VERSION, 
            credentials=self.credentials,
            static_discovery=False
        )
        logger.info("Successfully authenticated with Google Photos API")
    
    def list_media_items(self, page_size=50, page_token=None, album_id=None):
        """List media items from Google Photos
        
        Args:
            page_size (int, optional): Number of items to return per page. Defaults to 50.
            page_token (str, optional): Token for the next page. Defaults to None.
            album_id (str, optional): Album ID to list media items from. Defaults to None.
            
        Returns:
            tuple: (media_items, next_page_token)
        """
        logger.info(f"Fetching media items (page_size={page_size}, page_token={page_token}, album_id={album_id})")
        try:
            if album_id:
                # List media items from a specific album
                results = self.service.mediaItems().search(
                    body={
                        'pageSize': page_size,
                        'pageToken': page_token,
                        'albumId': album_id
                    }
                ).execute()
            else:
                # List all media items
                results = self.service.mediaItems().list(
                    pageSize=page_size,
                    pageToken=page_token
                ).execute()
            
            media_items = results.get('mediaItems', [])
            next_page_token = results.get('nextPageToken')
            
            logger.info(f"Fetched {len(media_items)} media items")
            return media_items, next_page_token
        
        except Exception as e:
            logger.error(f"Error fetching media items: {str(e)}")
            raise
            
    def list_albums(self, page_size=50, page_token=None):
        """List albums from Google Photos
        
        Args:
            page_size (int, optional): Number of albums to return per page. Defaults to 50.
            page_token (str, optional): Token for the next page. Defaults to None.
            
        Returns:
            tuple: (albums, next_page_token)
        """
        logger.info(f"Fetching albums (page_size={page_size}, page_token={page_token})")
        try:
            results = self.service.albums().list(
                pageSize=page_size,
                pageToken=page_token
            ).execute()
            
            albums = results.get('albums', [])
            next_page_token = results.get('nextPageToken')
            
            logger.info(f"Fetched {len(albums)} albums")
            return albums, next_page_token
        
        except Exception as e:
            logger.error(f"Error fetching albums: {str(e)}")
            raise
            
    def get_album_details(self, album_id):
        """Get details of a specific album
        
        Args:
            album_id (str): Album ID to get details for
            
        Returns:
            dict: Album details
        """
        logger.info(f"Fetching details for album {album_id}")
        try:
            album = self.service.albums().get(
                albumId=album_id
            ).execute()
            
            return album
        
        except Exception as e:
            logger.error(f"Error fetching album details: {str(e)}")
            raise
    
    def download_media_item(self, media_item, download_dir):
        """Download a media item from Google Photos"""
        import requests
        import os
        
        item_id = media_item['id']
        filename = media_item['filename']
        base_url = media_item['baseUrl']
        mime_type = media_item['mimeType']
        
        # Determine download URL based on media type
        if mime_type.startswith('image/'):
            download_url = f"{base_url}=d"  # Full resolution download
        elif mime_type.startswith('video/'):
            download_url = f"{base_url}=dv"  # Video download
        else:
            logger.warning(f"Unsupported media type: {mime_type} for {filename}")
            return None
        
        # Create download path
        download_path = os.path.join(download_dir, filename)
        
        try:
            logger.info(f"Downloading {filename} from Google Photos...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded {filename}")
            
            # Return metadata along with the download path
            return {
                'id': item_id,
                'filename': filename,
                'path': download_path,
                'mime_type': mime_type,
                'creation_time': media_item.get('mediaMetadata', {}).get('creationTime'),
                'width': media_item.get('mediaMetadata', {}).get('width'),
                'height': media_item.get('mediaMetadata', {}).get('height')
            }
        
        except Exception as e:
            logger.error(f"Error downloading {filename}: {str(e)}")
            if os.path.exists(download_path):
                os.remove(download_path)
            return None
