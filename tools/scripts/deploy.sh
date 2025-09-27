#!/bin/bash

# Project Aurum - Indonesian Quantitative Trading System
# Production Deployment Script
#
# This script handles blue-green deployments with comprehensive health checks
# and rollback capabilities for the Indonesian financial trading system.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_LOG="/var/log/aurum/deploy.log"
BACKUP_DIR="/opt/aurum/backups"
CONFIG_DIR="$PROJECT_ROOT/config"

# Environment variables
ENVIRONMENT="${ENVIRONMENT:-production}"
DEPLOY_TYPE="${DEPLOY_TYPE:-blue-green}"
VERSION="${VERSION:-latest}"
ROLLBACK_VERSION="${ROLLBACK_VERSION:-}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"
FORCE_DEPLOY="${FORCE_DEPLOY:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$DEPLOY_LOG"
}

info() { log "INFO" "${BLUE}$*${NC}"; }
success() { log "SUCCESS" "${GREEN}$*${NC}"; }
warning() { log "WARNING" "${YELLOW}$*${NC}"; }
error() { log "ERROR" "${RED}$*${NC}"; }

# Check if we're in Indonesian market hours
check_market_hours() {
    info "Checking Indonesian market hours..."

    local current_hour=$(TZ=Asia/Jakarta date +%H)
    local current_day=$(TZ=Asia/Jakarta date +%u)  # 1=Monday, 7=Sunday
    local current_time=$(TZ=Asia/Jakarta date '+%H:%M')

    info "Current Jakarta time: $(TZ=Asia/Jakarta date '+%Y-%m-%d %H:%M:%S WIB')"

    # Check if it's a weekday (Monday=1 to Friday=5)
    if [[ $current_day -ge 1 && $current_day -le 5 ]]; then
        # Check if it's during market hours (9:00-16:00 WIB)
        if [[ $current_hour -ge 9 && $current_hour -lt 16 ]]; then
            if [[ "$FORCE_DEPLOY" != "true" ]]; then
                error "Deployment blocked: Indonesian market is currently open (${current_time} WIB)"
                error "Market hours: 09:00-16:00 WIB, Monday-Friday"
                error "Use FORCE_DEPLOY=true to override (not recommended)"
                exit 1
            else
                warning "FORCE_DEPLOY enabled: Deploying during market hours"
            fi
        fi
    fi

    success "Safe to deploy - outside Indonesian market hours"
}

# Pre-deployment checks
pre_deployment_checks() {
    info "Running pre-deployment checks..."

    # Check if required tools are installed
    local required_tools=("docker" "docker-compose" "curl" "jq" "pg_dump")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "Required tool '$tool' is not installed"
            exit 1
        fi
    done

    # Check if environment files exist
    if [[ ! -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]]; then
        error "Environment file .env.$ENVIRONMENT not found"
        exit 1
    fi

    # Check if Docker images are available
    local image_tag="ghcr.io/your-username/project-aurum:$VERSION"
    if ! docker pull "$image_tag" &> /dev/null; then
        error "Docker image $image_tag not found or not accessible"
        exit 1
    fi

    # Check available disk space (minimum 5GB)
    local available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local min_space=5242880  # 5GB in KB
    if [[ $available_space -lt $min_space ]]; then
        error "Insufficient disk space. Available: ${available_space}KB, Required: ${min_space}KB"
        exit 1
    fi

    # Check if current deployment is healthy (for blue-green)
    if [[ "$DEPLOY_TYPE" == "blue-green" && -z "$ROLLBACK_VERSION" ]]; then
        local health_url="https://aurum-trading.com/health"
        if [[ "$ENVIRONMENT" == "staging" ]]; then
            health_url="https://staging.aurum-trading.com/health"
        fi

        if ! curl -f -s --max-time 10 "$health_url" > /dev/null; then
            warning "Current deployment appears unhealthy"
            if [[ "$FORCE_DEPLOY" != "true" ]]; then
                error "Aborting deployment due to unhealthy current state"
                error "Use FORCE_DEPLOY=true to override"
                exit 1
            fi
        fi
    fi

    success "Pre-deployment checks passed"
}

# Create backup
create_backup() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        warning "Skipping backup as requested"
        return 0
    fi

    info "Creating backup before deployment..."

    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/aurum_backup_${backup_timestamp}.sql"

    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"

    # Load environment variables
    source "$PROJECT_ROOT/.env.$ENVIRONMENT"

    # Create database backup
    info "Backing up database..."
    PGPASSWORD="$PROD_DB_PASSWORD" pg_dump \
        -h localhost \
        -p "${PROD_DB_PORT:-5432}" \
        -U "$PROD_DB_USER" \
        -d "$PROD_DB_NAME" \
        --verbose \
        --no-owner \
        --no-privileges \
        > "$backup_file"

    if [[ $? -eq 0 ]]; then
        success "Database backup created: $backup_file"

        # Compress backup
        gzip "$backup_file"
        success "Backup compressed: ${backup_file}.gz"

        # Clean up old backups (keep last 7 days)
        find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
        info "Cleaned up old backups"
    else
        error "Database backup failed"
        exit 1
    fi
}

# Deploy application
deploy_application() {
    info "Starting application deployment..."

    local compose_file="docker-compose.${ENVIRONMENT}.yml"
    local env_file=".env.$ENVIRONMENT"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: Would deploy with:"
        info "  Environment: $ENVIRONMENT"
        info "  Version: $VERSION"
        info "  Compose file: $compose_file"
        info "  Environment file: $env_file"
        return 0
    fi

    # Load environment variables
    export $(grep -v '^#' "$PROJECT_ROOT/$env_file" | xargs)

    if [[ "$DEPLOY_TYPE" == "blue-green" ]]; then
        deploy_blue_green
    else
        deploy_rolling
    fi
}

# Blue-green deployment
deploy_blue_green() {
    info "Performing blue-green deployment..."

    local blue_compose="docker-compose.${ENVIRONMENT}.yml"
    local green_compose="docker-compose.${ENVIRONMENT}.green.yml"

    # Check current environment color
    local current_color="green"
    if docker-compose -f "$blue_compose" -p aurum-blue ps api &> /dev/null; then
        current_color="blue"
    fi

    local new_color="blue"
    local new_compose="$blue_compose"
    local new_project="aurum-blue"

    if [[ "$current_color" == "blue" ]]; then
        new_color="green"
        new_compose="$green_compose"
        new_project="aurum-green"
    fi

    info "Current environment: $current_color"
    info "Deploying to: $new_color"

    # Create green compose file if it doesn't exist
    if [[ ! -f "$PROJECT_ROOT/$green_compose" ]]; then
        cp "$PROJECT_ROOT/$blue_compose" "$PROJECT_ROOT/$green_compose"
        sed -i "s/aurum_prod_/aurum_green_/g" "$PROJECT_ROOT/$green_compose"
        sed -i "s/aurum-blue/aurum-green/g" "$PROJECT_ROOT/$green_compose"
    fi

    # Deploy to new environment
    info "Deploying to $new_color environment..."
    cd "$PROJECT_ROOT"

    docker-compose -f "$new_compose" -p "$new_project" down --remove-orphans
    docker-compose -f "$new_compose" -p "$new_project" pull
    docker-compose -f "$new_compose" -p "$new_project" up -d

    # Wait for new environment to be ready
    wait_for_health "$new_project"

    # Run health checks
    if run_health_checks "$new_project"; then
        # Switch traffic
        switch_traffic "$current_color" "$new_color"

        # Monitor for a few minutes
        monitor_deployment "$new_color" 300  # 5 minutes

        # Clean up old environment
        cleanup_old_environment "$current_color"

        success "Blue-green deployment completed successfully"
    else
        error "Health checks failed, rolling back..."
        rollback_blue_green "$current_color" "$new_color"
        exit 1
    fi
}

# Rolling deployment (for staging)
deploy_rolling() {
    info "Performing rolling deployment..."

    local compose_file="docker-compose.${ENVIRONMENT}.yml"

    cd "$PROJECT_ROOT"

    # Pull new images
    docker-compose -f "$compose_file" pull

    # Rolling update services one by one
    local services=("celery_worker" "api" "frontend")

    for service in "${services[@]}"; do
        info "Updating service: $service"

        # Scale up new instance
        docker-compose -f "$compose_file" up -d --scale "$service=2" "$service"

        # Wait for new instance to be healthy
        sleep 30

        # Scale down to 1 (removes old instance)
        docker-compose -f "$compose_file" up -d --scale "$service=1" "$service"

        # Wait between services
        sleep 10
    done

    success "Rolling deployment completed"
}

# Wait for application health
wait_for_health() {
    local project_name="$1"
    local max_attempts=30
    local attempt=0

    info "Waiting for application to become healthy..."

    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose -p "$project_name" exec -T api curl -f http://localhost:8000/health &> /dev/null; then
            success "Application is healthy"
            return 0
        fi

        attempt=$((attempt + 1))
        info "Health check attempt $attempt/$max_attempts..."
        sleep 10
    done

    error "Application failed to become healthy within ${max_attempts}0 seconds"
    return 1
}

# Run comprehensive health checks
run_health_checks() {
    local project_name="$1"

    info "Running comprehensive health checks..."

    # API health check
    if ! docker-compose -p "$project_name" exec -T api curl -f http://localhost:8000/health/detailed; then
        error "API detailed health check failed"
        return 1
    fi

    # Database connectivity
    if ! docker-compose -p "$project_name" exec -T api python -c "
import asyncio
import asyncpg
import os
async def test_db():
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', 5432),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    result = await conn.fetchrow('SELECT 1 as test')
    await conn.close()
    print('Database connection successful')
asyncio.run(test_db())
    "; then
        error "Database connectivity check failed"
        return 1
    fi

    # Redis connectivity
    if ! docker-compose -p "$project_name" exec -T redis redis-cli ping; then
        error "Redis connectivity check failed"
        return 1
    fi

    # Critical endpoints test
    local endpoints=("/api/v1/status" "/api/v1/market/status" "/metrics")
    for endpoint in "${endpoints[@]}"; do
        if ! docker-compose -p "$project_name" exec -T api curl -f "http://localhost:8000$endpoint"; then
            error "Critical endpoint check failed: $endpoint"
            return 1
        fi
    done

    success "All health checks passed"
    return 0
}

# Switch traffic between environments
switch_traffic() {
    local old_color="$1"
    local new_color="$2"

    info "Switching traffic from $old_color to $new_color..."

    # Update load balancer configuration
    # This would typically involve updating nginx config or cloud load balancer

    # For this example, we'll simulate the traffic switch
    info "Updating load balancer configuration..."

    # Gradual traffic shift
    local shift_percentages=(25 50 75 100)
    for percentage in "${shift_percentages[@]}"; do
        info "Shifting ${percentage}% traffic to $new_color environment..."

        # In a real implementation, this would update the load balancer
        # to gradually shift traffic between blue and green environments

        sleep 30  # Wait between shifts

        # Monitor for errors
        if ! monitor_errors_brief; then
            error "Error spike detected during traffic shift"
            return 1
        fi
    done

    success "Traffic successfully switched to $new_color environment"
}

# Monitor deployment for errors
monitor_deployment() {
    local environment="$1"
    local duration="$2"

    info "Monitoring deployment for $duration seconds..."

    local start_time=$(date +%s)
    local end_time=$((start_time + duration))
    local error_count=0
    local max_errors=5

    while [[ $(date +%s) -lt $end_time ]]; do
        if ! curl -f -s --max-time 5 "https://aurum-trading.com/health" > /dev/null; then
            error_count=$((error_count + 1))
            warning "Health check failed (error count: $error_count)"

            if [[ $error_count -ge $max_errors ]]; then
                error "Too many health check failures during monitoring"
                return 1
            fi
        else
            error_count=0  # Reset error count on success
        fi

        sleep 10
    done

    success "Deployment monitoring completed successfully"
}

# Brief error monitoring
monitor_errors_brief() {
    local error_count=0
    local max_errors=2

    for i in {1..6}; do  # Check 6 times over 30 seconds
        if ! curl -f -s --max-time 5 "https://aurum-trading.com/health" > /dev/null; then
            error_count=$((error_count + 1))
            if [[ $error_count -ge $max_errors ]]; then
                return 1
            fi
        fi
        sleep 5
    done

    return 0
}

# Cleanup old environment
cleanup_old_environment() {
    local old_color="$1"

    info "Cleaning up $old_color environment..."

    # Wait a bit to ensure new environment is stable
    sleep 120

    local old_project="aurum-$old_color"
    local old_compose="docker-compose.${ENVIRONMENT}.yml"

    if [[ "$old_color" == "green" ]]; then
        old_compose="docker-compose.${ENVIRONMENT}.green.yml"
    fi

    # Stop old environment
    docker-compose -f "$old_compose" -p "$old_project" down

    # Clean up unused images
    docker image prune -f

    success "$old_color environment cleaned up"
}

# Rollback function
rollback_blue_green() {
    local stable_color="$1"
    local failed_color="$2"

    error "Rolling back to $stable_color environment..."

    # Switch traffic back
    switch_traffic "$failed_color" "$stable_color"

    # Stop failed environment
    local failed_project="aurum-$failed_color"
    local failed_compose="docker-compose.${ENVIRONMENT}.yml"

    if [[ "$failed_color" == "green" ]]; then
        failed_compose="docker-compose.${ENVIRONMENT}.green.yml"
    fi

    docker-compose -f "$failed_compose" -p "$failed_project" down

    error "Rollback completed"
}

# Rollback to specific version
rollback_to_version() {
    local version="$1"

    info "Rolling back to version: $version"

    # Update docker-compose with rollback version
    local compose_file="docker-compose.${ENVIRONMENT}.yml"
    local image_tag="ghcr.io/your-username/project-aurum:$version"

    # Create temporary compose file with rollback version
    local temp_compose="/tmp/docker-compose.rollback.yml"
    sed "s|image: ghcr.io/your-username/project-aurum:.*|image: $image_tag|g" \
        "$PROJECT_ROOT/$compose_file" > "$temp_compose"

    cd "$PROJECT_ROOT"

    # Deploy rollback version
    docker-compose -f "$temp_compose" pull
    docker-compose -f "$temp_compose" up -d

    # Wait for health
    if wait_for_health ""; then
        success "Rollback to version $version completed successfully"
    else
        error "Rollback failed - manual intervention required"
        exit 1
    fi

    # Clean up
    rm -f "$temp_compose"
}

# Post-deployment tasks
post_deployment_tasks() {
    info "Running post-deployment tasks..."

    # Run database migrations if needed
    if [[ -f "$PROJECT_ROOT/alembic.ini" ]]; then
        info "Running database migrations..."
        docker-compose exec api alembic upgrade head
    fi

    # Warm up cache
    info "Warming up application cache..."
    curl -s "https://aurum-trading.com/api/v1/market/status" > /dev/null || true

    # Send deployment notification
    send_deployment_notification

    success "Post-deployment tasks completed"
}

# Send deployment notification
send_deployment_notification() {
    local webhook_url="${SLACK_WEBHOOK_URL:-}"

    if [[ -n "$webhook_url" ]]; then
        local message="{
            \"text\": \"🚀 Project Aurum deployment completed\",
            \"attachments\": [
                {
                    \"color\": \"good\",
                    \"fields\": [
                        {
                            \"title\": \"Environment\",
                            \"value\": \"$ENVIRONMENT\",
                            \"short\": true
                        },
                        {
                            \"title\": \"Version\",
                            \"value\": \"$VERSION\",
                            \"short\": true
                        },
                        {
                            \"title\": \"Deployment Type\",
                            \"value\": \"$DEPLOY_TYPE\",
                            \"short\": true
                        },
                        {
                            \"title\": \"Time\",
                            \"value\": \"$(date -u '+%Y-%m-%d %H:%M:%S UTC')\",
                            \"short\": true
                        }
                    ]
                }
            ]
        }"

        curl -X POST -H 'Content-type: application/json' \
             --data "$message" \
             "$webhook_url" > /dev/null || true
    fi
}

# Main deployment function
main() {
    info "Starting Project Aurum deployment..."
    info "Environment: $ENVIRONMENT"
    info "Version: $VERSION"
    info "Deploy Type: $DEPLOY_TYPE"

    # Setup logging
    mkdir -p "$(dirname "$DEPLOY_LOG")"

    # Handle rollback if requested
    if [[ -n "$ROLLBACK_VERSION" ]]; then
        rollback_to_version "$ROLLBACK_VERSION"
        exit 0
    fi

    # Run deployment pipeline
    check_market_hours
    pre_deployment_checks
    create_backup
    deploy_application
    post_deployment_tasks

    success "🎉 Project Aurum deployment completed successfully!"
    info "Deployment log: $DEPLOY_LOG"
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Project Aurum Deployment Script for Indonesian Trading System

OPTIONS:
    -e, --environment ENV     Deployment environment (staging|production)
    -v, --version VERSION     Version/tag to deploy (default: latest)
    -t, --type TYPE          Deployment type (blue-green|rolling)
    -r, --rollback VERSION   Rollback to specific version
    -d, --dry-run           Perform dry run without actual deployment
    -f, --force             Force deployment (ignore market hours)
    -s, --skip-backup       Skip database backup
    -h, --help              Show this help message

EXAMPLES:
    $0 --environment staging --version v1.2.3
    $0 --environment production --type blue-green
    $0 --rollback v1.2.2
    $0 --dry-run --environment production

ENVIRONMENT VARIABLES:
    ENVIRONMENT            Target environment (staging|production)
    VERSION               Version to deploy
    DEPLOY_TYPE           Deployment strategy
    ROLLBACK_VERSION      Version to rollback to
    DRY_RUN              Dry run mode (true|false)
    FORCE_DEPLOY         Force deployment (true|false)
    SKIP_BACKUP          Skip backup (true|false)
    SLACK_WEBHOOK_URL    Slack notification webhook

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -t|--type)
            DEPLOY_TYPE="$2"
            shift 2
            ;;
        -r|--rollback)
            ROLLBACK_VERSION="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -f|--force)
            FORCE_DEPLOY="true"
            shift
            ;;
        -s|--skip-backup)
            SKIP_BACKUP="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    error "Invalid environment: $ENVIRONMENT"
    error "Must be either 'staging' or 'production'"
    exit 1
fi

# Validate deployment type
if [[ ! "$DEPLOY_TYPE" =~ ^(blue-green|rolling)$ ]]; then
    error "Invalid deployment type: $DEPLOY_TYPE"
    error "Must be either 'blue-green' or 'rolling'"
    exit 1
fi

# Run main function
main "$@"