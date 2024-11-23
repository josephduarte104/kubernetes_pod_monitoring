import time
import csv
from kubernetes import client, config
import logging
from logging.handlers import RotatingFileHandler
from matplotlib.animation import FuncAnimation
import threading
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime

def setup_logger(log_file):
    logger = logging.getLogger("PodMonitoringLogger")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    logger.addHandler(handler)
    return logger

def convert_cpu_to_millicores(cpu):
    if cpu.endswith('n'):
        return int(cpu[:-1]) / 1_000_000
    elif cpu.endswith('u'):
        return int(cpu[:-1]) / 1_000
    elif cpu.endswith('m'):
        return int(cpu[:-1])
    else:
        return int(cpu) * 1000

def convert_memory_to_mb(memory):
    if memory.endswith('Ki'):
        return int(memory[:-2]) / 1024
    elif memory.endswith('Mi'):
        return int(memory[:-2])
    elif memory.endswith('Gi'):
        return int(memory[:-2]) * 1024
    else:
        return int(memory) / (1024 * 1024)

def monitor_pod_resources(logger, csv_file):
    config.load_kube_config()
    metrics_client = client.CustomObjectsApi()

    pod_metrics = metrics_client.list_namespaced_custom_object(
        "metrics.k8s.io", "v1beta1", "default", "pods"
    )
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["Timestamp", "Namespace", "Pod", "Container", "CPU (millicores)", "Memory (MB)"])
        for pod in pod_metrics['items']:
            namespace = pod['metadata']['namespace']
            pod_name = pod['metadata']['name']
            containers = pod['containers']
            for container in containers:
                # Correctly access 'usage' field
                usage = container.get('usage', {})
                cpu_millicores = convert_cpu_to_millicores(usage.get('cpu', '0'))
                memory_mb = convert_memory_to_mb(usage.get('memory', '0'))
                log_entry = {
                    "Timestamp": datetime.now().isoformat(),
                    "Namespace": namespace,
                    "Pod": pod_name,
                    "Container": container['name'],
                    "CPU (millicores)": cpu_millicores,
                    "Memory (MB)": memory_mb
                }
                logger.info(log_entry)
                writer.writerow(log_entry)

def write_csv_header(csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["Timestamp", "Namespace", "Pod", "Container", "CPU (millicores)", "Memory (MB)"])
        writer.writeheader()

def live_plot(csv_file):
    fig, (ax_cpu, ax_memory) = plt.subplots(2, 1, sharex=True)
    ax_cpu.set_ylabel('CPU (millicores)')
    ax_memory.set_ylabel('Memory (MB)')
    ax_memory.set_xlabel('Time')
    fig.suptitle('Live Pod Resource Usage')

    # Dictionary to hold time-series data for each pod
    pod_data = defaultdict(lambda: {'cpu': [], 'memory': [], 'time': []})
    global_time = 0

    def update(_):
        nonlocal global_time
        global_time += 1

        # Read new data from CSV
        new_data = defaultdict(lambda: {'cpu': 0, 'memory': 0})
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                pod = row['Pod']
                new_data[pod]['cpu'] = float(row['CPU (millicores)'])
                new_data[pod]['memory'] = float(row['Memory (MB)'])

        # Update pod data
        for pod, usage in new_data.items():
            pod_data[pod]['cpu'].append(usage['cpu'])
            pod_data[pod]['memory'].append(usage['memory'])
            pod_data[pod]['time'].append(global_time)

        # Plot CPU and memory usage
        ax_cpu.clear()
        ax_memory.clear()
        ax_cpu.set_ylabel('CPU (millicores)')
        ax_memory.set_ylabel('Memory (MB)')
        ax_memory.set_xlabel('Time')
        fig.suptitle('Live Pod Resource Usage')

        for pod, usage in pod_data.items():
            if len(usage['time']) > 0:  # Only plot if data exists
                ax_cpu.plot(usage['time'], usage['cpu'], label=f'{pod} CPU')
                ax_memory.plot(usage['time'], usage['memory'], label=f'{pod} Memory')

        # Add legends if there is valid data
        if pod_data:
            ax_cpu.legend(loc='upper left')
            ax_memory.legend(loc='upper left')

    anim = FuncAnimation(fig, update, interval=5000)  # Assign to a variable
    plt.show()

def main():
    log_file = "/Users/jduarte/DevOps/k8smonitoring/pod_metrics.log"
    csv_file = "/Users/jduarte/DevOps/k8smonitoring/pod_metrics.csv"

    logger = setup_logger(log_file)
    write_csv_header(csv_file)

    while True:
        monitor_pod_resources(logger, csv_file)
        time.sleep(30)

if __name__ == "__main__":
    plot_thread = threading.Thread(target=main)
    plot_thread.start()
    live_plot("/Users/jduarte/DevOps/k8smonitoring/pod_metrics.csv")

