# FastAPI Metrics Application

A production-ready FastAPI application with built-in metrics collection using Prometheus and Grafana for monitoring.



## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Metrics Reference](#metrics-reference)
4. [Deployment](#deployment)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)

## Features

- Real-time metrics collection
- Database performance monitoring
- HTTP request tracking
- Custom business metrics
- Docker Compose deployment
- Prometheus and Grafana integration
- Rate limiting and security features

## Getting Started

### Prerequisites

- Docker 20.10.0+
- Docker Compose 2.0.0+
- Python 3.8+ (for local development)

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd fastapi-metrics-app
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - API: http://localhost:8000
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)
   - PGAdmin: http://localhost:5050

## Metrics Reference

### Database Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `db_query_duration_seconds` | Histogram | Query execution time | operation, status |
| `db_operations_total` | Counter | Total database operations | operation, status |
| `db_connections_active` | Gauge | Active database connections | - |

### HTTP Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `http_request_duration_seconds` | Histogram | Request processing time | method, path, status_code |
| `http_requests_total` | Counter | Total HTTP requests | method, path, status_code |

### Business Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `custom_events_total` | Counter | Custom business events | event_type, source |

## Deployment

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=appdb
DB_USER=appuser
DB_PASSWORD=apppass123

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale application
docker-compose up -d --scale app=3
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | API Server |
| Prometheus | 9090 | Metrics Server |
| Grafana | 3000 | Dashboard UI |
| PGAdmin | 5050 | Database Admin |

## Configuration

### Database Settings

```env
DB_MAX_CONNECTIONS=20
DB_SSL=false
```

### Application Settings

```env
APP_LOG_LEVEL=INFO
CORS_ORIGINS=*
```

### Rate Limiting

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
```

## Monitoring

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi-app'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['app:8000']
```

### Grafana Setup

1. Access Grafana at http://localhost:3000
2. Add Prometheus data source:
   - URL: `http://prometheus:9090`
   - Access: Server
3. Import the provided dashboard

### Example Prometheus Query Responses

![Prometheus Query Response 1](Prometheus%20Time%20Series%20Collection%20and%20Processing%20Server_page-0001.jpg)
*Figure 1: Example Prometheus Query Response - Time Series Data*

![Prometheus Query Response 2](Prometheus%20Time%20Series%20Collection%20and%20Processing%20Server_page-0002.jpg)
*Figure 2: Example Prometheus Query Response - Metrics Visualization*


## License

MIT

## Support

For issues and feature requests, please use the [issue tracker](https://github.com/yourusername/fastapi-metrics-app/issues).
