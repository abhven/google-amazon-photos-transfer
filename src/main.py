#!/usr/bin/env python3
"""
Google Photos to Amazon Photos Transfer
Main application entry point
"""

import os
import sys
import logging
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Use relative imports when running as a module
try:
    from src.google_photos import GooglePhotosClient
    from src.amazon_photos import AmazonPhotosClient
    from src.transfer_manager import TransferManager
except ModuleNotFoundError:
    # Use direct imports when running the script directly
    from google_photos import GooglePhotosClient
    from amazon_photos import AmazonPhotosClient
    from transfer_manager import TransferManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('photo_transfer.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Transfer photos from Google Photos to Amazon Photos')
    
    parser.add_argument('--max-photos', type=int, help='Maximum number of photos to transfer')
    parser.add_argument('--download-dir', type=str, help='Directory to download photos to')
    parser.add_argument('--report-path', type=str, help='Path to save the transfer report')
    parser.add_argument('--dry-run', action='store_true', help='Simulate the transfer without actually downloading or uploading')
    parser.add_argument('--skip-albums', action='store_true', help='Skip transferring albums and only transfer individual photos')
    
    return parser.parse_args()

def main():
    """Main function to orchestrate the photo transfer process"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up directories and paths
    download_dir = args.download_dir or os.getenv('DOWNLOAD_DIR', './downloads')
    report_path = args.report_path or os.getenv('TRANSFER_REPORT_PATH', './transfer_report.json')
    
    # Create download directory if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Initialize clients
        logger.info("Initializing Google Photos client...")
        google_client = GooglePhotosClient()
        
        logger.info("Initializing Amazon Photos client...")
        amazon_client = AmazonPhotosClient()
        
        # Initialize transfer manager
        transfer_manager = TransferManager(
            google_client=google_client,
            amazon_client=amazon_client,
            download_dir=download_dir
        )
        
        # Start the transfer process
        logger.info("Starting photo transfer process...")
        
        # Check if this is a dry run
        if args.dry_run:
            logger.info("DRY RUN MODE: No actual downloads or uploads will be performed")
            
        # Check if albums should be skipped
        transfer_albums = not args.skip_albums
        if args.skip_albums:
            logger.info("Skipping album transfer as requested")
        else:
            logger.info("Albums will be transferred with 1:1 mapping between Google Photos and Amazon Photos")
        
        transfer_stats = transfer_manager.start_transfer(
            max_photos=args.max_photos,
            dry_run=args.dry_run,
            transfer_albums=transfer_albums
        )
        
        # Generate transfer report
        generate_transfer_report(transfer_stats, report_path)
        
        logger.info(f"Transfer completed. Transferred {transfer_stats['success']} photos successfully.")
        logger.info(f"Transfer report saved to {report_path}")
        
    except Exception as e:
        logger.error(f"An error occurred during the transfer process: {str(e)}")
        sys.exit(1)

def generate_transfer_report(stats, report_path):
    """Generate a JSON report of the transfer process"""
    # Create a summary that includes album statistics if available
    summary = f"Successfully transferred {stats['success']} photos, {stats['failed']} failed"
    
    # Add album statistics if available
    if 'albums_total' in stats:
        summary += f", {stats['albums_success']} albums transferred successfully"
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats,
        'summary': summary
    }
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Transfer report generated at {report_path}")

if __name__ == "__main__":
    main()
