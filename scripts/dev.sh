#!/usr/bin/env bash
#
# Invoice Manager Development Server
#
# Automatically finds available ports for multi-worktree development.
# Uses Docker for database (safer), local processes for backend/frontend.
#
# Port ranges:
#   Backend:  18081-18089 (FastAPI/uvicorn)
#   Frontend: 15174-15182 (Vite)
#   Database: 5435 (shared Docker container)
#
# Usage:
#   ./scripts/dev.sh              # Auto-detect available ports
#   ./scripts/dev.sh --port 18085 # Force specific backend port
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if a port is available
is_port_available() {
    local port=$1
    ! lsof -i :"$port" >/dev/null 2>&1
}

# Wait for database to be ready (with health check)
wait_for_db() {
    echo "[*] Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec invoice_db pg_isready -U postgres -d invoice_db >/dev/null 2>&1; then
            echo -e "${GREEN}[+] Database ready!${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}[ERROR] Database failed to become ready after ${max_attempts}s${NC}"
    exit 1
}

# Find available port pair (backend + frontend)
find_available_ports() {
    for i in {1..9}; do
        local backend_port=$((18080 + i))
        local frontend_port=$((15173 + i))

        if is_port_available "$backend_port" && is_port_available "$frontend_port"; then
            echo "$backend_port $frontend_port"
            return 0
        fi
    done

    # No available ports found
    return 1
}

# Parse arguments
CUSTOM_PORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            if [[ -z "${2:-}" ]]; then
                echo "Missing value for --port"
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]]; then
                echo "Port must be numeric"
                exit 1
            fi
            CUSTOM_PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--port PORT]"
            echo ""
            echo "Options:"
            echo "  --port PORT   Force specific backend port (frontend = PORT - 2907)"
            echo ""
            echo "Without options, automatically finds available ports."
            echo ""
            echo "Port ranges:"
            echo "  Backend:  18081-18089"
            echo "  Frontend: 15174-15182"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Determine ports
if [[ -n "$CUSTOM_PORT" ]]; then
    API_PORT="$CUSTOM_PORT"
    OFFSET=$((CUSTOM_PORT - 18080))
    VITE_PORT=$((15173 + OFFSET))

    if (( API_PORT < 18081 || API_PORT > 18089 )); then
        echo -e "${RED}[ERROR] Backend port must be between 18081-18089${NC}"
        exit 1
    fi
    if (( VITE_PORT < 15174 || VITE_PORT > 15182 )); then
        echo -e "${RED}[ERROR] Frontend port must be between 15174-15182${NC}"
        exit 1
    fi

    # Verify custom ports are available
    if ! is_port_available "$API_PORT"; then
        echo -e "${RED}[ERROR] Backend port $API_PORT is already in use${NC}"
        exit 1
    fi
    if ! is_port_available "$VITE_PORT"; then
        echo -e "${RED}[ERROR] Frontend port $VITE_PORT is already in use${NC}"
        exit 1
    fi
else
    # Auto-detect available ports
    if ! ports=$(find_available_ports); then
        echo -e "${RED}[ERROR] No available port pairs found (tried 18081-18089 / 15174-15182)${NC}"
        echo -e "${RED}        Please free up some ports or use --port to specify manually${NC}"
        exit 1
    fi
    read API_PORT VITE_PORT <<< "$ports"
fi

VITE_API_URL="http://localhost:$API_PORT"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}              Invoice Manager Development Server            ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Frontend:${NC}  http://localhost:${VITE_PORT}"
echo -e "  ${GREEN}Backend:${NC}   http://localhost:${API_PORT}"
echo -e "  ${GREEN}API Docs:${NC}  http://localhost:${API_PORT}/docs"
echo -e "  ${GREEN}Database:${NC}  postgresql://localhost:5435/invoice_db"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Export environment variables
export API_PORT
export VITE_PORT
export VITE_API_URL

# Check if database container exists and is running
DB_CONTAINER="invoice_db"
DB_STATUS=$(docker container inspect -f '{{.State.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "not_found")

case "$DB_STATUS" in
    "running")
        echo -e "${GREEN}[+] Database already running (shared container)${NC}"
        ;;
    "exited"|"created")
        echo -e "${YELLOW}[!] Database container exists but stopped. Starting...${NC}"
        docker start "$DB_CONTAINER"
        wait_for_db
        ;;
    "not_found")
        echo -e "${YELLOW}[!] Database container not found. Creating...${NC}"
        docker compose up -d db
        wait_for_db
        ;;
    *)
        echo -e "${RED}[!] Database in unexpected state: $DB_STATUS. Attempting restart...${NC}"
        docker restart "$DB_CONTAINER" 2>/dev/null || docker compose up -d db
        wait_for_db
        ;;
esac

# Check and create backend .env if needed
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}[!] Creating backend/.env from .env.example...${NC}"
    # Use localhost for database when running locally
    cat > backend/.env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5435/invoice_db
DEBUG=true
# Add your API keys below:
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
EOF
    echo -e "${CYAN}    Note: Edit backend/.env to add your API keys${NC}"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "[*] Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Activate Python virtual environment if it exists
if [ -d "backend/venv" ]; then
    echo "[*] Activating Python virtual environment..."
    source backend/venv/bin/activate
fi

# Start backend
echo "[*] Starting backend on port $API_PORT..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port "$API_PORT" &
BACKEND_PID=$!
cd ..

# Wait for backend to start with timeout
BACKEND_READY=false
for i in {1..30}; do
    if curl -s "http://localhost:$API_PORT/docs" > /dev/null 2>&1; then
        BACKEND_READY=true
        echo -e "${GREEN}[+] Backend ready!${NC}"
        break
    fi
    sleep 1
done

# Check if backend started successfully
if [ "$BACKEND_READY" = false ]; then
    echo -e "${RED}[ERROR] Backend failed to start on port $API_PORT after 30 seconds${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start frontend
echo "[*] Starting frontend on port $VITE_PORT..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    echo -e "${YELLOW}[!] Installing/updating frontend dependencies...${NC}"
    npm install
    touch node_modules
fi

# Start Vite with dynamic port and API URL
VITE_API_URL="$VITE_API_URL" npm run dev -- --port "$VITE_PORT" &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
FRONTEND_READY=false
for i in {1..30}; do
    if curl -s "http://localhost:$VITE_PORT" > /dev/null 2>&1; then
        FRONTEND_READY=true
        echo -e "${GREEN}[+] Frontend ready!${NC}"
        break
    fi
    sleep 1
done

if [ "$FRONTEND_READY" = false ]; then
    echo -e "${YELLOW}[!] Frontend may still be starting... Check http://localhost:$VITE_PORT${NC}"
fi

echo ""
echo -e "${GREEN}[+] All services started!${NC}"
echo -e "    Open: ${BLUE}http://localhost:${VITE_PORT}${NC}"
echo ""
echo "    Press Ctrl+C to stop"
echo ""

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
