#!/bin/bash
# Check FlareSolverr availability and configuration for PriceRecon

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default FlareSolverr endpoints to check
DEFAULT_ENDPOINTS=(
    "http://localhost:8191"
    "http://localhost:8191/v1"
    "http://docker-app-vm:8191/v1"
    "http://byparr:8191/v1"
)

# Get configured endpoint from config.yml or env
CONFIGURED_ENDPOINT=""
if [ -f "config.yml" ]; then
    CONFIGURED_ENDPOINT=$(grep "flaresolverr_url:" config.yml | sed 's/.*: "\(.*\)"/\1/' || echo "")
fi
if [ -z "${CONFIGURED_ENDPOINT}" ] && [ -n "${PRICERECON_FLARESOLVERR_URL:-}" ]; then
    CONFIGURED_ENDPOINT="${PRICERECON_FLARESOLVERR_URL}"
fi

echo "=== FlareSolverr Configuration Check ==="
echo

# Show configured endpoint
if [ -n "${CONFIGURED_ENDPOINT}" ]; then
    echo -e "Configured endpoint: ${GREEN}${CONFIGURED_ENDPOINT}${NC}"
else
    echo -e "Configured endpoint: ${YELLOW}None (will use default)${NC}"
fi
echo

# Check configured endpoint first if set
if [ -n "${CONFIGURED_ENDPOINT}" ]; then
    echo "Testing configured endpoint: ${CONFIGURED_ENDPOINT}"
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${CONFIGURED_ENDPOINT}" 2>&1 || echo "failed")
    if [ "${STATUS}" = "200" ] || [ "${STATUS}" = "400" ]; then
        echo -e "  ${GREEN}✓ FlareSolverr is reachable${NC}"
        echo -e "  ${GREEN}✓ Connectors requiring FlareSolverr should work${NC}"
        echo
        echo "FlareSolverr-dependent connectors (12):"
        echo "  - AO.com"
        echo "  - Back Market"
        echo "  - Box"
        echo "  - CDKeys"
        echo "  - Currys"
        echo "  - Depop"
        echo "  - Etsy"
        echo "  - Mercari"
        echo "  - OnBuy"
        echo "  - Overclockers"
        echo "  - Scan"
        echo "  - Very.co.uk"
        exit 0
    else
        echo -e "  ${RED}✗ FlareSolverr is NOT reachable (HTTP ${STATUS})${NC}"
        echo
        echo "FlareSolverr-dependent connectors will FAIL."
        echo
    fi
else
    echo "No configured endpoint found. Checking common endpoints..."
    echo
    FOUND=0
    for endpoint in "${DEFAULT_ENDPOINTS[@]}"; do
        echo "Testing: ${endpoint}"
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${endpoint}" 2>&1 || echo "failed")
        if [ "${STATUS}" = "200" ] || [ "${STATUS}" = "400" ]; then
            echo -e "  ${GREEN}✓ FlareSolverr found at ${endpoint}${NC}"
            echo
            echo "Set this endpoint in config.yml:"
            echo "  flaresolverr_url: \"${endpoint}\""
            echo
            echo "Or via environment variable:"
            echo "  export PRICERECON_FLARESOLVERR_URL=\"${endpoint}\""
            FOUND=1
            break
        else
            echo -e "  ${RED}✗ Not reachable${NC}"
        fi
        echo
    done
    
    if [ "${FOUND}" = "0" ]; then
        echo -e "${RED}No working FlareSolverr endpoint found${NC}"
        echo
    fi
fi

# Show deployment instructions if FlareSolverr is missing
if [ "${FOUND:-0}" = "0" ] && [ "${STATUS:-failed}" != "200" ]; then
    echo "=== Deploying FlareSolverr ==="
    echo
    echo "FlareSolverr is required for 12 PriceRecon connectors."
    echo "Start it with Docker:"
    echo
    cat << 'EOF'
docker run -d \
  --name flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  flaresolverr/flaresolverr:latest

# Verify it's running:
curl http://localhost:8191

# Then configure in config.yml:
flaresolverr_url: "http://localhost:8191"

# Or for Docker Compose deployments on media_back network:
# (Update docker-compose.yml to include FlareSolverr service)
EOF
    echo
    echo "For existing Docker Compose setup, add to docker-compose.yml:"
    echo
    cat << 'EOF'
  flaresolverr:
    image: flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    ports:
      - "8191:8191"
    environment:
      - LOG_LEVEL=info
    networks:
      - media_back
EOF
    echo
    exit 1
fi