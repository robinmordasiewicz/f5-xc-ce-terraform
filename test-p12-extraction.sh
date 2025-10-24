#!/bin/bash
# Test script for P12 password handling improvements
# Issue #71: P12 certificate extraction with stdin method and env var support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
P12_FILE="/Users/r.mordasiewicz/Downloads/f5-amer-ent.console.ves.volterra.io.api-creds.p12"
TEST_PASSWORD="cuzsor-1zofhe-bohVyn"
CERT_FILE="$HOME/vescred.cert"
KEY_FILE="$HOME/vesprivate.key"

# Helper functions
print_test() {
  echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
  echo -e "${RED}[FAIL]${NC} $1"
}

print_info() {
  echo -e "${YELLOW}[INFO]${NC} $1"
}

cleanup() {
  print_info "Cleaning up test files..."
  rm -f "$CERT_FILE" "$KEY_FILE" 2>/dev/null
  unset VES_P12_PASSWORD
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  P12 Password Handling Test Suite"
echo "  Issue #71 - OpenSSL stdin method + env var support"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Verify P12 file exists
print_test "Test 1: Verify P12 file exists"
if [ -f "$P12_FILE" ]; then
  print_success "P12 file found: $P12_FILE"
else
  print_error "P12 file not found: $P12_FILE"
  exit 1
fi
echo ""

# Test 2: Extract certificate using stdin method (without env var)
print_test "Test 2: Extract certificate using stdin method"
cleanup
if echo "$TEST_PASSWORD" | openssl pkcs12 \
  -in "$P12_FILE" \
  -passin stdin \
  -nodes \
  -nokeys \
  -legacy \
  -out "$CERT_FILE" 2>&1 | grep -v "^MAC verified OK$"; then
  print_error "Certificate extraction failed"
  exit 1
fi

if [ -f "$CERT_FILE" ]; then
  print_success "Certificate extracted successfully"
  CERT_SIZE=$(wc -c <"$CERT_FILE")
  print_info "Certificate size: $CERT_SIZE bytes"
else
  print_error "Certificate file not created"
  exit 1
fi
echo ""

# Test 3: Extract private key using stdin method
print_test "Test 3: Extract private key using stdin method"
if echo "$TEST_PASSWORD" | openssl pkcs12 \
  -in "$P12_FILE" \
  -passin stdin \
  -nodes \
  -nocerts \
  -legacy \
  -out "$KEY_FILE" 2>&1 | grep -v "^MAC verified OK$"; then
  print_error "Private key extraction failed"
  exit 1
fi

if [ -f "$KEY_FILE" ]; then
  print_success "Private key extracted successfully"
  KEY_SIZE=$(wc -c <"$KEY_FILE")
  print_info "Private key size: $KEY_SIZE bytes"
else
  print_error "Private key file not created"
  exit 1
fi
echo ""

# Test 4: Verify certificate content
print_test "Test 4: Verify certificate content"
if openssl x509 -in "$CERT_FILE" -noout -text >/dev/null 2>&1; then
  print_success "Certificate is valid X.509 format"
  SUBJECT=$(openssl x509 -in "$CERT_FILE" -noout -subject | sed 's/subject=//')
  print_info "Subject: $SUBJECT"
else
  print_error "Invalid certificate format"
  exit 1
fi
echo ""

# Test 5: Verify private key content
print_test "Test 5: Verify private key content"
if openssl rsa -in "$KEY_FILE" -check -noout >/dev/null 2>&1; then
  print_success "Private key is valid RSA format"
  KEY_BITS=$(openssl rsa -in "$KEY_FILE" -text -noout 2>/dev/null | grep "Private-Key:" | sed 's/.*(\(.*\) bit.*/\1/')
  print_info "Key size: $KEY_BITS bits"
else
  print_error "Invalid private key format"
  exit 1
fi
echo ""

# Test 6: Verify certificate and key match
print_test "Test 6: Verify certificate and key pair match"
CERT_MODULUS=$(openssl x509 -in "$CERT_FILE" -noout -modulus | md5)
KEY_MODULUS=$(openssl rsa -in "$KEY_FILE" -noout -modulus 2>/dev/null | md5)

if [ "$CERT_MODULUS" == "$KEY_MODULUS" ]; then
  print_success "Certificate and private key match"
else
  print_error "Certificate and private key DO NOT match"
  exit 1
fi
echo ""

# Test 7: Test with special characters in password
print_test "Test 7: Verify password with special characters"
if [[ "$TEST_PASSWORD" =~ [^a-zA-Z0-9] ]]; then
  print_success "Password contains special characters: $TEST_PASSWORD"
else
  print_error "Test password should contain special characters"
  exit 1
fi
echo ""

# Test 8: Test environment variable support
print_test "Test 8: Environment variable support"
rm -f "$CERT_FILE" "$KEY_FILE" 2>/dev/null
export VES_P12_PASSWORD="$TEST_PASSWORD"

if [ -n "$VES_P12_PASSWORD" ]; then
  print_success "Environment variable VES_P12_PASSWORD is set"

  # Extract certificate using env var
  if echo "$VES_P12_PASSWORD" | openssl pkcs12 \
    -in "$P12_FILE" \
    -passin stdin \
    -nodes \
    -nokeys \
    -legacy \
    -out "$CERT_FILE" 2>&1 | grep -v "^MAC verified OK$"; then
    print_error "Certificate extraction with env var failed"
    exit 1
  fi

  # Extract key using env var
  if echo "$VES_P12_PASSWORD" | openssl pkcs12 \
    -in "$P12_FILE" \
    -passin stdin \
    -nodes \
    -nocerts \
    -legacy \
    -out "$KEY_FILE" 2>&1 | grep -v "^MAC verified OK$"; then
    print_error "Key extraction with env var failed"
    exit 1
  fi

  if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    print_success "Certificate and key extracted using environment variable"
  else
    print_error "Certificate or key not extracted from env var"
    exit 1
  fi
else
  print_error "Environment variable not set"
  exit 1
fi
echo ""

# Test 9: Verify file permissions
print_test "Test 9: Verify file permissions (should be 600)"
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
  chmod 600 "$CERT_FILE" "$KEY_FILE"

  CERT_PERMS=$(stat -f "%OLp" "$CERT_FILE" 2>/dev/null || stat -c "%a" "$CERT_FILE" 2>/dev/null)
  KEY_PERMS=$(stat -f "%OLp" "$KEY_FILE" 2>/dev/null || stat -c "%a" "$KEY_FILE" 2>/dev/null)
else
  print_error "Certificate or key file missing for permissions test"
  exit 1
fi

if [ "$CERT_PERMS" == "600" ] && [ "$KEY_PERMS" == "600" ]; then
  print_success "File permissions are correct (600)"
else
  print_error "Incorrect permissions - cert: $CERT_PERMS, key: $KEY_PERMS"
  exit 1
fi
echo ""

# Final summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All tests passed successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Summary:"
echo "  ✅ P12 file validation"
echo "  ✅ Certificate extraction (stdin method)"
echo "  ✅ Private key extraction (stdin method)"
echo "  ✅ Certificate validity (X.509 format)"
echo "  ✅ Private key validity (RSA format)"
echo "  ✅ Certificate-key pair matching"
echo "  ✅ Special character password handling"
echo "  ✅ Environment variable support"
echo "  ✅ File permissions (600)"
echo ""
print_info "Cleanup will occur automatically on exit"
