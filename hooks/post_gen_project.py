import subprocess
import yaml
import os
import sys

# Try to get values from environment variables first (set by pre_gen_project.py)
chart_name = os.environ.get("COOKIECUTTER_CHART_NAME", "{{cookiecutter.chart_name}}")
chart_version = os.environ.get("COOKIECUTTER_CHART_VERSION", "{{cookiecutter.chart_version}}")
chart_repository = os.environ.get("COOKIECUTTER_CHART_REPOSITORY", "{{cookiecutter.chart_repository}}")

# Define the path to the values.yaml file in your template using chart_name
values_yaml_path = f"values.yaml"

# Function to run a Helm command and return the output
def run_helm_command(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        if result.returncode != 0:
            print(f"Warning: Command '{command}' failed with error: {result.stderr}")
            return ""
        return result.stdout
    except Exception as e:
        print(f"Error running command '{command}': {str(e)}")
        return ""

# Function to populate values from Helm chart to values.yaml
def populate_values_from_helm_chart():
    # Check if Helm is available
    try:
        helm_version = run_helm_command("helm version --short")
        if not helm_version:
            print("Helm not found or not working properly. Please make sure Helm is installed.")
            return
        print(f"Using Helm {helm_version.strip()}")
    except FileNotFoundError:
        print("Helm not found. Please make sure Helm is installed.")
        return

    print(f"Fetching values from chart: {chart_name}")
    print(f"Repository: {chart_repository}")
    print(f"Version: {chart_version}")

    # Use Helm to get the values from the chart repository
    helm_command = f"helm show values {chart_name} --repo {chart_repository}"
    if chart_version:
        helm_command += f" --version {chart_version}"
    
    helm_values = run_helm_command(helm_command)

    if not helm_values:
        print(f"Failed to fetch values from chart {chart_name}. Using empty values.")
        helm_values_dict = {}
    else:
        # Load the Helm values into a Python dictionary
        try:
            helm_values_dict = yaml.safe_load(helm_values) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML values: {str(e)}")
            helm_values_dict = {}

    # Create a separate section for the chart's values
    chart_key = chart_name.split('/')[-1]  # Get the chart name without repo prefix
    modified_values_dict = {chart_key: helm_values_dict}

    # Make sure values.yaml exists and is readable
    try:
        with open(values_yaml_path, "r") as values_file:
            existing_values = yaml.safe_load(values_file) or {}
    except (FileNotFoundError, yaml.YAMLError):
        existing_values = {}

    # Merge the existing values with the chart values
    merged_values = {**existing_values, **modified_values_dict}

    # Write the merged values to the values.yaml file
    try:
        with open(values_yaml_path, "w") as values_file:
            yaml.dump(merged_values, values_file, default_flow_style=False, sort_keys=False)
        print(f"Values populated from {chart_name} to {values_yaml_path}")
    except Exception as e:
        print(f"Error writing to {values_yaml_path}: {str(e)}")

def update_chart_yaml():
    """Update the Chart.yaml file with additional metadata from the selected chart."""
    chart_yaml_path = "Chart.yaml"
    
    if not os.path.exists(chart_yaml_path):
        print(f"Warning: {chart_yaml_path} not found. Skipping update.")
        return
    
    try:
        with open(chart_yaml_path, "r") as f:
            chart_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error reading {chart_yaml_path}: {str(e)}")
        return
    
    # Add additional metadata
    chart_data["description"] = f"Wrapper chart for {chart_name}"
    chart_data["appVersion"] = chart_version if chart_version else "latest"
    
    # Add source info
    if chart_repository:
        chart_data["sources"] = [chart_repository]
    
    # Write back to Chart.yaml
    try:
        with open(chart_yaml_path, "w") as f:
            yaml.dump(chart_data, f, default_flow_style=False, sort_keys=False)
        print(f"Updated {chart_yaml_path} with metadata from {chart_name}")
    except Exception as e:
        print(f"Error writing to {chart_yaml_path}: {str(e)}")

if __name__ == "__main__":
    populate_values_from_helm_chart()
    update_chart_yaml()
    print("\nChart generation completed successfully!")
