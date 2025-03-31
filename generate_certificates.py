#!/usr/bin/env python3
"""
Generate self-signed SSL certificates for local development
"""

import os
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def generate_certificates():
    """Generate self-signed SSL certificates for local development"""
    try:
        # Check if OpenSSL is installed
        subprocess.run(['openssl', 'version'], check=True, capture_output=True)
        
        # Generate private key
        logger.info("Generating private key...")
        subprocess.run([
            'openssl', 'genrsa',
            '-out', 'key.pem',
            '2048'
        ], check=True)
        
        # Generate certificate signing request
        logger.info("Generating certificate signing request...")
        subprocess.run([
            'openssl', 'req',
            '-new',
            '-key', 'key.pem',
            '-out', 'csr.pem',
            '-subj', '/CN=localhost'
        ], check=True)
        
        # Generate self-signed certificate
        logger.info("Generating self-signed certificate...")
        subprocess.run([
            'openssl', 'x509',
            '-req',
            '-days', '365',
            '-in', 'csr.pem',
            '-signkey', 'key.pem',
            '-out', 'cert.pem'
        ], check=True)
        
        # Clean up CSR
        os.remove('csr.pem')
        
        logger.info("SSL certificates generated successfully:")
        logger.info("  - Private key: key.pem")
        logger.info("  - Certificate: cert.pem")
        logger.info("\nNOTE: These are self-signed certificates for local development only.")
        logger.info("When using these certificates, your browser will show a security warning.")
        logger.info("You can safely proceed past this warning for local development purposes.")
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating certificates: {e}")
        if e.stderr:
            logger.error(f"Error details: {e.stderr.decode('utf-8')}")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    if os.path.exists('key.pem') and os.path.exists('cert.pem'):
        logger.info("SSL certificates already exist. Delete them if you want to generate new ones.")
        sys.exit(0)
    
    if generate_certificates():
        sys.exit(0)
    else:
        sys.exit(1)
