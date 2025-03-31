# Google Photos to Amazon Photos Transfer

This application transfers photos and related files from Google Photos to Amazon Photos using their respective APIs.

## Setup

### Prerequisites

- Python 3.6 or higher
- OpenSSL (for generating SSL certificates)
- Google Photos API credentials
- Amazon Photos API credentials

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/photo-transfer.git
   cd photo-transfer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### API Credentials Setup

#### Google Photos API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Photos Library API for your project
4. Create OAuth 2.0 credentials (OAuth client ID)
   - Application type: Desktop application
   - Name: Photo Transfer App (or any name you prefer)
5. Download the credentials and note your Client ID and Client Secret

#### Amazon Photos API

1. Go to the [Amazon Developer Console](https://developer.amazon.com/)
2. Register a new application or select an existing one
3. Enable the Amazon Photos API for your application
4. Create Security Profile credentials
   - Note your Client ID and Client Secret
   - Add `https://localhost:8000/callback` to the allowed redirect URLs

### Configuration

1. Create a `.env` file in the root directory (you can copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your API credentials:
   ```
   # Google Photos API credentials
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=https://localhost:8080/oauth2callback
   
   # Amazon Photos API credentials
   AMAZON_CLIENT_ID=your_amazon_client_id
   AMAZON_CLIENT_SECRET=your_amazon_client_secret
   # Leave AMAZON_REFRESH_TOKEN empty, it will be populated by the setup script
   
   # Application settings
   DOWNLOAD_DIR=./downloads
   MAX_PHOTOS_PER_BATCH=50
   TRANSFER_REPORT_PATH=./transfer_report.json
   ```

3. Generate SSL certificates for HTTPS redirect URIs:
   ```bash
   python generate_certificates.py
   ```
   This will create self-signed SSL certificates (`key.pem` and `cert.pem`) for local development.

4. Run the Amazon Photos authentication setup:
   ```bash
   python src/setup_amazon_auth.py
   ```
   This will:
   - Open a browser window for you to log in to your Amazon account
   - Ask for permission to access your Amazon Photos
   - Redirect back to your local server
   - Save the refresh token to your `.env` file
   
   > **Note**: When accessing the HTTPS redirect URIs, your browser may show a security warning about the self-signed certificate. This is expected for local development, and you can safely proceed past this warning.

## Usage

### Running the Transfer

Run the main script to start the transfer process:
```bash
python src/main.py
```

This will:
1. Authenticate with Google Photos (opens browser on first run)
2. Retrieve your photos from Google Photos
3. Download the photos to your local machine
4. Upload them to Amazon Photos
5. Generate a transfer report

### Command Line Options

The application supports several command line options:

```bash
python src/main.py --help
```

- `--max-photos N`: Limit the number of photos to transfer (default: all)
- `--download-dir PATH`: Specify a custom download directory
- `--report-path PATH`: Specify a custom report file path
- `--dry-run`: Simulate the transfer without actually downloading or uploading
- `--skip-albums`: Skip transferring albums and only transfer individual photos

### Transfer Report

After the transfer completes, a JSON report is generated with details about:
- Total photos processed
- Successfully transferred photos
- Failed transfers with error messages
- Skipped photos (already existing on Amazon Photos)

## Features

- Transfers photos while preserving metadata
- Maintains album structure with 1:1 mapping between Google Photos and Amazon Photos
- Handles rate limiting and retries
- Provides progress tracking
- Generates transfer reports with detailed statistics
