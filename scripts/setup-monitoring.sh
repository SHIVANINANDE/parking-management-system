# Monitoring & Observability Setup Script

#!/bin/bash

set -e

echo "🔍 Setting up Monitoring & Observability for Parking Management System"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create monitoring directories
print_status "Creating monitoring directories..."
mkdir -p docker/monitoring/{elasticsearch,logstash/config,kibana/dashboards,grafana/dashboards,alertmanager/templates}
mkdir -p docker/monitoring/{prometheus/rules,filebeat,metricbeat}

# Set appropriate permissions
chmod -R 755 docker/monitoring

# Create Elasticsearch configuration
print_status "Setting up Elasticsearch configuration..."
cat > docker/monitoring/elasticsearch/elasticsearch.yml << 'EOF'
cluster.name: "parking-logs-cluster"
network.host: 0.0.0.0
discovery.type: single-node
xpack.security.enabled: false
xpack.monitoring.collection.enabled: true

# Performance settings
indices.memory.index_buffer_size: 10%
indices.memory.min_index_buffer_size: 48mb
bootstrap.memory_lock: true

# Logging
logger.org.elasticsearch.discovery: DEBUG
EOF

# Create Logstash configuration
print_status "Setting up Logstash configuration..."
cat > docker/monitoring/logstash/config/logstash.yml << 'EOF'
http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: [ "http://elasticsearch:9200" ]
xpack.monitoring.enabled: true
config.reload.automatic: true
config.reload.interval: 3s
EOF

# Create Metricbeat configuration
print_status "Setting up Metricbeat configuration..."
cat > docker/monitoring/metricbeat/metricbeat.yml << 'EOF'
metricbeat.config.modules:
  path: ${path.config}/modules.d/*.yml
  reload.enabled: false

metricbeat.modules:
- module: system
  metricsets:
    - cpu
    - load
    - memory
    - network
    - process
    - process_summary
    - socket_summary
    - filesystem
    - fsstat
  enabled: true
  period: 10s
  processes: ['.*']

- module: docker
  metricsets:
    - container
    - cpu
    - diskio
    - healthcheck
    - info
    - memory
    - network
  hosts: ["unix:///var/run/docker.sock"]
  period: 10s
  enabled: true

output.elasticsearch:
  hosts: ['elasticsearch:9200']
  index: "parking-metrics-%{+yyyy.MM.dd}"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/metricbeat
  name: metricbeat
  keepfiles: 7
  permissions: 0644

setup.template.enabled: true
setup.template.pattern: "parking-metrics-*"
EOF

# Create AlertManager email template
print_status "Setting up AlertManager templates..."
cat > docker/monitoring/alertmanager/templates/email.tmpl << 'EOF'
{{ define "email.subject" }}
[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "email.html" }}
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background-color: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { padding: 20px; }
        .alert { margin: 15px 0; padding: 15px; border-left: 4px solid #dc3545; background-color: #f8d7da; }
        .resolved { border-left-color: #28a745; background-color: #d4edda; }
        .footer { background-color: #f8f9fa; padding: 15px; border-radius: 0 0 8px 8px; text-align: center; font-size: 12px; color: #666; }
        .button { display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 10px 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Parking System Alert</h2>
            <p>{{ .Alerts | len }} alert(s) require attention</p>
        </div>
        <div class="content">
            {{ range .Alerts }}
            <div class="alert {{ if eq .Status "resolved" }}resolved{{ end }}">
                <h3>{{ .Annotations.summary }}</h3>
                <p><strong>Description:</strong> {{ .Annotations.description }}</p>
                <p><strong>Severity:</strong> {{ .Labels.severity }}</p>
                <p><strong>Instance:</strong> {{ .Labels.instance }}</p>
                <p><strong>Started:</strong> {{ .StartsAt.Format "2006-01-02 15:04:05 UTC" }}</p>
                {{ if .Annotations.runbook_url }}
                <a href="{{ .Annotations.runbook_url }}" class="button">View Runbook</a>
                {{ end }}
            </div>
            {{ end }}
        </div>
        <div class="footer">
            <p>This alert was generated by the Parking Management System monitoring.</p>
            <p>Time: {{ .CommonAnnotations.timestamp }}</p>
        </div>
    </div>
</body>
</html>
{{ end }}
EOF

# Create sample Grafana dashboard
print_status "Setting up Grafana dashboards..."
cat > docker/monitoring/grafana/dashboards/parking-overview.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Parking System Overview",
    "tags": ["parking", "overview"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{endpoint}} - {{method}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Parking Occupancy",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(parking_spot_occupancy{status=\"occupied\"} / (parking_spot_occupancy{status=\"occupied\"} + parking_spot_occupancy{status=\"available\"}))",
            "legendFormat": "Occupancy Rate"
          }
        ],
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_usage_percent",
            "legendFormat": "CPU Usage"
          },
          {
            "expr": "system_memory_usage_percent",
            "legendFormat": "Memory Usage"
          }
        ],
        "gridPos": {"h": 8, "w": 16, "x": 8, "y": 8}
      }
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "30s"
  }
}
EOF

# Start monitoring stack
print_status "Starting monitoring stack..."

# Create network if it doesn't exist
docker network create monitoring 2>/dev/null || true
docker network create app-network 2>/dev/null || true

# Start the monitoring services
docker-compose -f docker/monitoring/docker-compose.monitoring.yml up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."

services=("elasticsearch:9200" "prometheus:9090" "grafana:3000" "kibana:5601")
for service in "${services[@]}"; do
    IFS=':' read -r service_name port <<< "$service"
    if curl -f -s "http://localhost:$port" > /dev/null; then
        print_status "$service_name is healthy ✅"
    else
        print_warning "$service_name may not be ready yet ⚠️"
    fi
done

# Install Python dependencies for monitoring
print_status "Installing monitoring dependencies..."
cd backend
pip install -r ../docker/monitoring/requirements-monitoring.txt 2>/dev/null || pip install prometheus-client structlog pythonjsonlogger psutil aioredis

cd ..

print_status "✅ Monitoring & Observability setup completed!"
echo ""
echo "🎯 Access Points:"
echo "   📊 Grafana:     http://localhost:3001 (admin/admin123)"
echo "   📈 Prometheus:  http://localhost:9090"
echo "   🔍 Kibana:      http://localhost:5601"
echo "   📧 AlertManager: http://localhost:9093"
echo "   🔧 Health Check: http://localhost:8000/health"
echo "   📊 Metrics:     http://localhost:8000/metrics"
echo ""
echo "🚀 Next Steps:"
echo "   1. Update your email settings in docker/monitoring/alertmanager/alertmanager.yml"
echo "   2. Configure Slack webhook URLs for notifications"
echo "   3. Import custom dashboards in Grafana"
echo "   4. Review alert rules in docker/monitoring/prometheus/rules/"
echo ""
echo "📖 Documentation: Check docker/monitoring/README.md for detailed configuration"
