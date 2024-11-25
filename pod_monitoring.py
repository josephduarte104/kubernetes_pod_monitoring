import time
import csv
from kubernetes import client, config
import logging
from logging.handlers import RotatingFileHandler
from matplotlib.animation import FuncAnimation
import threading
import matplotlib
matplotlib.use('Agg')  # Use the Agg backend for non-interactive plotting
import matplotlib.pyplot as plt
from collections import defaultdict, deque
from datetime import datetime
import os
from dotenv import load_dotenv
from flask import Flask, render_template, send_file
from flask_socketio import SocketIO, emit
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Load environment variables from .env file
load_dotenv()

# Set namespace and interval from environment variables
NAMESPACE = os.getenv('NAMESPACE', 'default')
INTERVAL = int(os.getenv('INTERVAL', 5))

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app)

# Historical metrics storage
history_length = 10  # Number of data points to keep
cpu_history = defaultdict(lambda: deque(maxlen=history_length))
memory_history = defaultdict(lambda: deque(maxlen=history_length))
timestamps = deque(maxlen=history_length)

# Logging setup
def setup_logger(log_file):
    logger = logging.getLogger("PodMonitoringLogger")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger('pod_monitoring.log')

# Convert Kubernetes CPU formats to millicores
def convert_cpu_to_millicores(cpu):
    if cpu.endswith('n'):
        return int(cpu[:-1]) / 1_000_000
    elif cpu.endswith('u'):
        return int(cpu[:-1]) / 1_000
    elif cpu.endswith('m'):
        return int(cpu[:-1])
    else:
        return int(cpu) * 1000

# Convert Kubernetes memory formats to MiB
def convert_memory_to_mib(memory):
    if memory.endswith('Ki'):
        return int(memory[:-2]) / 1024
    elif memory.endswith('Mi'):
        return int(memory[:-2])
    elif memory.endswith('Gi'):
        return int(memory[:-2]) * 1024
    else:
        return int(memory)

# Fetch pod metrics from the Kubernetes API
def get_pod_metrics():
    """
    Fetches metrics for all pods in a specified Kubernetes namespace.

    This function loads the Kubernetes configuration, initializes the CustomObjectsApi,
    and retrieves the CPU and memory usage metrics for each pod in the specified namespace.
    The metrics are aggregated per pod and returned as a dictionary.

    Returns:
        dict: A dictionary where the keys are pod names and the values are dictionaries
              containing 'cpu' (in millicores) and 'memory' (in MiB) usage.

    Raises:
        Exception: If there is an error fetching the pod metrics, an error is logged and
                   an empty dictionary is returned.
    """
    config.load_kube_config()
    custom_api = client.CustomObjectsApi()
    try:
        metrics = custom_api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=NAMESPACE,
            plural="pods"
        )
        data = defaultdict(lambda: {'cpu': 0, 'memory': 0})
        for item in metrics['items']:
            pod_name = item['metadata']['name']
            for container in item['containers']:
                data[pod_name]['cpu'] += convert_cpu_to_millicores(container['usage']['cpu'])
                data[pod_name]['memory'] += convert_memory_to_mib(container['usage']['memory'])
        return data
    except Exception as e:
        logger.error(f"Error fetching pod metrics: {e}")
        return {}

# Update metrics history
def update_metrics():
    metrics = get_pod_metrics()
    timestamp = datetime.now().strftime('%H:%M:%S')
    timestamps.append(timestamp)
    for pod_name, data in metrics.items():
        cpu_history[pod_name].append(data['cpu'])
        memory_history[pod_name].append(data['memory'])
    logger.info(f"Metrics updated at {timestamp}")

# Periodic update thread
def periodic_update():
    while True:
        update_metrics()
        time.sleep(INTERVAL)

# Flask routes for rendering graphs
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/live-graph-cpu')
def live_graph_cpu():
    update_metrics()  # Ensure metrics are up-to-date
    fig, ax = plt.subplots(figsize=(10, 5))  # Adjust size as needed
    for pod_name, cpu_usage in cpu_history.items():
        ax.plot(timestamps, cpu_usage, label=pod_name)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Usage (millicores)', fontsize=12)
    ax.legend(loc='upper left', fontsize=10)
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for better visibility
    plt.tight_layout(pad=2.0)  # Adjust padding to prevent cutoff
    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    canvas.print_png(img)
    img.seek(0)
    plt.close(fig)  # Close the figure to free memory
    return send_file(img, mimetype='image/png')

@app.route('/live-graph-memory')
def live_graph_memory():
    update_metrics()  # Ensure metrics are up-to-date
    fig, ax = plt.subplots(figsize=(10, 5))  # Adjust size as needed
    for pod_name, memory_usage in memory_history.items():
        ax.plot(timestamps, memory_usage, label=pod_name)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Memory Usage (Mi)', fontsize=12)
    ax.legend(loc='upper left', fontsize=10)
    plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for better visibility
    plt.tight_layout(pad=2.0)  # Adjust padding to prevent cutoff
    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    canvas.print_png(img)
    img.seek(0)
    plt.close(fig)  # Close the figure to free memory
    return send_file(img, mimetype='image/png')

# Handle SocketIO connection
@socketio.on('connect')
def handle_connect():
    emit('response', {'data': 'Connected'})

# Main entry point
if __name__ == '__main__':
    threading.Thread(target=periodic_update, daemon=True).start()
    socketio.run(app, debug=True)
