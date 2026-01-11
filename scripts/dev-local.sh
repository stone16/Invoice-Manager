#!/bin/bash
# Local Development Script
# Usage: ./scripts/dev-local.sh [command]
# Commands:
#   start    - Start all services (db + backend + frontend)
#   stop     - Stop all services
#   db       - Start database only
#   backend  - Start backend only (assumes db is running)
#   frontend - Start frontend only
#   setup    - Initial setup (create venv, install deps)
#   logs     - Show logs from all services

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if database is running
check_db() {
    if docker ps | grep -q invoice_db_dev; then
        return 0
    else
        return 1
    fi
}

# Start database
start_db() {
    log_info "Starting PostgreSQL database..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.dev.yml up -d

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker exec invoice_db_dev pg_isready -U postgres > /dev/null 2>&1; then
            log_success "Database is ready!"
            return 0
        fi
        sleep 1
    done
    log_error "Database failed to start"
    return 1
}

# Stop database
stop_db() {
    log_info "Stopping database..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.dev.yml down
}

# Setup Python virtual environment
setup_backend() {
    log_info "Setting up backend..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi

    # Activate venv and install dependencies
    log_info "Installing backend dependencies..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$BACKEND_DIR/requirements.txt"

    log_success "Backend setup complete!"
}

# Setup frontend
setup_frontend() {
    log_info "Setting up frontend..."
    cd "$FRONTEND_DIR"
    npm install
    log_success "Frontend setup complete!"
}

# Setup local .env if not exists
setup_env() {
    if [ ! -f "$BACKEND_DIR/.env" ] || grep -q "db:5432" "$BACKEND_DIR/.env"; then
        log_info "Setting up local .env file..."
        # Keep existing API key if present
        if [ -f "$BACKEND_DIR/.env" ]; then
            EXISTING_KEY=$(grep "OPENAI_API_KEY" "$BACKEND_DIR/.env" | cut -d'=' -f2)
        fi
        cp "$BACKEND_DIR/.env.local" "$BACKEND_DIR/.env"
        if [ -n "$EXISTING_KEY" ]; then
            sed -i.bak "s/your-openai-api-key-here/$EXISTING_KEY/" "$BACKEND_DIR/.env"
            rm -f "$BACKEND_DIR/.env.bak"
        fi
        log_success "Local .env configured!"
    fi
}

# Start backend
start_backend() {
    if ! check_db; then
        log_warn "Database not running. Starting it first..."
        start_db
    fi

    setup_env

    log_info "Starting backend server..."
    cd "$BACKEND_DIR"
    if [ ! -d "$VENV_DIR" ]; then
        log_warn "Backend venv not found. Running setup..."
        setup_backend
    fi
    source "$VENV_DIR/bin/activate"

    # Run database migrations if needed
    log_info "Running database migrations..."
    alembic upgrade head 2>/dev/null || log_warn "No migrations to run or alembic not configured"

    # Start uvicorn with hot reload
    log_success "Backend starting at http://localhost:8000"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Start frontend
start_frontend() {
    log_info "Starting frontend dev server..."
    cd "$FRONTEND_DIR"

    # Set API URL to local backend
    export VITE_API_URL=http://localhost:8000

    log_success "Frontend starting at http://localhost:5173"
    npm run dev
}

# Full setup
full_setup() {
    log_info "Running full setup..."
    setup_backend
    setup_frontend
    setup_env
    log_success "Full setup complete! Run './scripts/dev-local.sh start' to start development servers."
}

# Start all services
start_all() {
    log_info "Starting all services..."

    # Start database
    start_db

    # Check if backend venv exists
    if [ ! -d "$VENV_DIR" ]; then
        log_warn "Backend not set up. Running setup first..."
        setup_backend
    fi

    setup_env

    # Start backend in background
    log_info "Starting backend in background..."
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    alembic upgrade head 2>/dev/null || true
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/invoice_backend.pid

    # Wait a bit for backend to start
    sleep 3

    # Start frontend
    log_info "Starting frontend..."
    cd "$FRONTEND_DIR"
    export VITE_API_URL=http://localhost:8000
    npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/invoice_frontend.pid

    log_success "All services started!"
    echo ""
    echo "  Backend:  http://localhost:8000"
    echo "  Frontend: http://localhost:5173"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services"

    # Wait for interrupt
    trap "stop_all; exit 0" INT TERM
    wait
}

# Stop all services
stop_all() {
    log_info "Stopping all services..."

    # Stop backend
    if [ -f /tmp/invoice_backend.pid ]; then
        kill $(cat /tmp/invoice_backend.pid) 2>/dev/null || true
        rm /tmp/invoice_backend.pid
    fi

    # Stop frontend
    if [ -f /tmp/invoice_frontend.pid ]; then
        kill $(cat /tmp/invoice_frontend.pid) 2>/dev/null || true
        rm /tmp/invoice_frontend.pid
    fi

    # Also kill any uvicorn/node processes for this project
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite.*invoice" 2>/dev/null || true

    # Stop database
    stop_db

    log_success "All services stopped!"
}

# Show help
show_help() {
    echo "Invoice Manager - Local Development Script"
    echo ""
    echo "Usage: ./scripts/dev-local.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup    - Initial setup (create venv, install deps)"
    echo "  start    - Start all services (db + backend + frontend)"
    echo "  stop     - Stop all services"
    echo "  db       - Start database only"
    echo "  backend  - Start backend only (assumes db is running)"
    echo "  frontend - Start frontend only"
    echo "  logs     - Show database logs"
    echo "  help     - Show this help message"
    echo ""
    echo "Quick Start:"
    echo "  1. ./scripts/dev-local.sh setup"
    echo "  2. ./scripts/dev-local.sh start"
    echo ""
}

# Show database logs
show_logs() {
    log_info "Showing database logs..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.dev.yml logs -f
}

# Main
case "${1:-help}" in
    setup)
        full_setup
        ;;
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    db)
        start_db
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
