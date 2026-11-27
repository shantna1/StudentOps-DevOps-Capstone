# Grafana panel queries
CPU cores: sum(rate(container_cpu_usage_seconds_total{namespace="studentops",container="app"}[5m]))
Memory bytes: sum(container_memory_working_set_bytes{namespace="studentops",container="app"})
Ready pods: kube_pod_status_ready{namespace="studentops",condition="true"}
Application requests/sec: sum(rate(flask_http_request_total[5m]))
Scrape health: up{job="studentops"}
