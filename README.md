# Pod Monitoring

This project monitors Kubernetes pod resources and logs the data to a CSV file and a log file. It also provides a live plot of the resource usage.

## Setup

### 1. Create a `.env` file

Create a `.env` file in the root directory of your project and add the following content:

You can create a new file named `README.md` in the root directory of your project and add the above content to it.

Sure, here is the `README.md` file content:

```markdown
# Pod Monitoring

This project monitors Kubernetes pod resources and logs the data to a CSV file and a log file. It also provides a live plot of the resource usage.

## Setup

### 1. Create a `.env` file

Create a `.env` file in the root directory of your project and add the following content:

```
KUBECONFIG=/path/to/your/kubeconfig
```

Replace `/path/to/your/kubeconfig` with the actual path to your Kubernetes configuration file.

### 2. Install the required libraries

Run the following command to install the required libraries:

```sh
pip install -r 

requirements.txt


```

### 3. Run the program

To run the program, execute the following command:

```sh
python 

pod_monitoring.py


```

This will start monitoring the pod resources and logging the data to the specified CSV and log files. It will also display a live plot of the resource usage.

## Files

- `pod_monitoring.py`: The main script that monitors pod resources and logs the data.
- `requirements.txt`: The file containing the list of required libraries.
- `.gitignore`: The file specifying which files and directories to ignore in the repository.
- `README.md`: This file, containing instructions on how to set up and run the project.

## Notes

- Ensure that your Kubernetes cluster is up and running and that you have the necessary permissions to access the metrics API.
- The log file and CSV file paths are hardcoded in the `main` function of `pod_monitoring.py`. You can modify these paths as needed.
```
