#!/bin/bash

# Generate SSL certificates for development

set -e

CERT_DIR="./ssl"
DOMAIN="localhost"

echo "🔐 Generating SSL certificates for development..."

# Create directory if not exists
mkdir -p "$CERT_DIR"

# Generate private key
openssl genrsa -out "$CERT_DIR/key.pem" 2048

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/key.pem" -out "$CERT_DIR/csr.pem" \
    -subj "/C=US/ST=State/L=City/O=SuperDevSecOps/CN=$DOMAIN"

# Generate self-signed certificate
openssl x509 -req -days 365 -in "$CERT_DIR/csr.pem" \
    -signkey "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem"

# Clean up CSR
rm "$CERT_DIR/csr.pem"

# Set appropriate permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "✅ SSL certificates generated successfully!"
echo "📍 Location: $CERT_DIR"
echo "⚠️  These are self-signed certificates for development only!"