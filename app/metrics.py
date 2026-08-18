from prometheus_client import Counter, Gauge, Histogram

# Counter: only goes up. Good for "how many times has X happened"
REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total number of requests received",
    ["endpoint", "method"]
)

ERROR_COUNT = Counter(
    "app_errors_total",
    "Total number of errors returned",
    ["endpoint"]
)

# Gauge: goes up AND down. Good for "current value of X right now"
CPU_LOAD = Gauge(
    "app_simulated_cpu_percent",
    "Simulated CPU load percentage"
)

MEMORY_LOAD = Gauge(
    "app_simulated_memory_mb",
    "Simulated memory usage in MB"
)

# Histogram: buckets of values. Good for latency distributions.
REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"]
)