#!/bin/bash

# Port Detection Utility for Project Aurum Scripts
# Functions to detect and find available ports

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is available
is_port_available() {
    local port=$1
    local protocol=${2:-tcp}  # tcp or udp

    case $protocol in
        "tcp")
            if command -v nc &> /dev/null; then
                # Use netcat if available
                ! nc -z localhost "$port" &>/dev/null
            elif command -v lsof &> /dev/null; then
                # Use lsof as fallback
                ! lsof -i :"$port" &>/dev/null
            elif command -v ss &> /dev/null; then
                # Use ss (modern Linux)
                ! ss -tuln | grep -q ":$port "
            else
                # Try to bind to the port as last resort
                ! timeout 2 bash -c "echo > /dev/tcp/localhost/$port" &>/dev/null 2>&1
            fi
            ;;
        "udp")
            if command -v nc &> /dev/null; then
                ! nc -u -z localhost "$port" &>/dev/null
            elif command -v ss &> /dev/null; then
                ! ss -uln | grep -q ":$port "
            else
                # UDP is harder to test, assume available if TCP tools aren't available
                return 0
            fi
            ;;
    esac
}

# Function to find next available port starting from given base port
find_available_port() {
    local base_port=$1
    local max_attempts=${2:-20}  # Try up to 20 ports
    local protocol=${3:-tcp}

    local current_port=$base_port
    local attempts=0

    echo -e "${BLUE}🔍 Checking for available ports starting from $base_port...${NC}" >&2

    while [ $attempts -lt $max_attempts ]; do
        if is_port_available "$current_port" "$protocol"; then
            echo -e "${GREEN}✅ Found available port: $current_port${NC}" >&2
            echo "$current_port"
            return 0
        fi

        echo -e "${YELLOW}⏳ Port $current_port is in use, trying next...${NC}" >&2
        ((current_port++))
        ((attempts++))

        # Small delay to avoid rapid port checks
        sleep 0.1
    done

    echo -e "${RED}❌ No available ports found in range $base_port-$((base_port + max_attempts - 1))${NC}" >&2
    return 1
}

# Function to find available port and update configuration file
update_port_in_config() {
    local config_file=$1
    local port_variable=$2
    local new_port=$3
    local service_name=${4:-"service"}

    if [[ -f "$config_file" ]]; then
        # Update port in environment file
        if grep -q "^$port_variable=" "$config_file"; then
            sed -i "s/^$port_variable=.*/$port_variable=$new_port/" "$config_file"
        elif grep -q "^# $port_variable=" "$config_file"; then
            sed -i "s/^# $port_variable=.*/$port_variable=$new_port/" "$config_file"
        else
            echo "$port_variable=$new_port" >> "$config_file"
        fi

        echo -e "${GREEN}✅ Updated $service_name port to $new_port in $config_file${NC}" >&2
    fi
}

# Function to get the port from a configuration file
get_port_from_config() {
    local config_file=$1
    local port_variable=$2
    local default_port=$3

    if [[ -f "$config_file" ]]; then
        local port=$(grep "^$port_variable=" "$config_file" | cut -d'=' -f2 | cut -d'"' -f2)
        echo "${port:-$default_port}"
    else
        echo "$default_port"
    fi
}

# Function to wait for port to become available (for shutdown)
wait_for_port_free() {
    local port=$1
    local timeout=${2:-30}
    local interval=1
    local elapsed=0

    echo -e "${BLUE}⏳ Waiting for port $port to become free...${NC}" >&2

    while [ $elapsed -lt $timeout ]; do
        if is_port_available "$port"; then
            echo -e "${GREEN}✅ Port $port is now available${NC}" >&2
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo -e "${YELLOW}⚠️  Port $port is still in use after $timeout seconds${NC}" >&2
    return 1
}

# Function to check if a process is running on a port
get_pid_on_port() {
    local port=$1

    if command -v lsof &> /dev/null; then
        lsof -ti :"$port" 2>/dev/null
    elif command -v ss &> /dev/null; then
        ss -ltnp | grep ":$port " | awk '{print $7}' | cut -d',' -f2
    fi
}

# Function to kill process on port if running
kill_process_on_port() {
    local port=$1
    local pid=$(get_pid_on_port "$port")

    if [[ -n "$pid" ]] && [[ "$pid" =~ ^[0-9]+$ ]]; then
        echo -e "${YELLOW}⚠️  Found process $pid running on port $port${NC}" >&2
        kill "$pid" 2>/dev/null

        # Wait for graceful shutdown
        sleep 2

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${RED}🔨 Force killing process $pid on port $port${NC}" >&2
            kill -9 "$pid" 2>/dev/null
        fi

        wait_for_port_free "$port" 10
        return 0
    else
        echo -e "${GREEN}✅ No process found running on port $port${NC}" >&2
        return 0
    fi
}

# Function to display port info
display_port_info() {
    local service=$1
    local port=$2
    local url=$3

    echo ""
    echo -e "${GREEN}🚀 $service is running!${NC}"
    echo -e "${BLUE}📍 Port: $port${NC}"
    echo -e "${BLUE}🔗 URL: $url${NC}"
    echo -e "${BLUE}⏹️  Press CTRL+C to stop${NC}"
    echo ""
}