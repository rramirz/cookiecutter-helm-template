import subprocess
import yaml
import os
import sys
import json

# Try to get values from temporary file first (created by pre_gen_project.py)
tmp_file = os.path.join(os.getcwd(), "_cookiecutter_helm_vars.json")
chart_name = None
chart_version = None
chart_repository = None

try:
    if os.path.exists(tmp_file):
        with open(tmp_file, "r") as f:
            tmp_data = json.load(f)
            chart_name = tmp_data.get("chart_name")
            chart_version = tmp_data.get("chart_version")
            chart_repository = tmp_data.get("chart_repository")
        # Remove the temporary file
        os.remove(tmp_file)
except Exception as e:
    print(f"Warning: Could not read temporary file: {str(e)}")

# If not found in temp file, try environment variables
if not chart_name:
    chart_name = os.environ.get("COOKIECUTTER_CHART_NAME", "{{cookiecutter.chart_name}}")
if not chart_version:
    chart_version = os.environ.get("COOKIECUTTER_CHART_VERSION", "{{cookiecutter.chart_version}}")
if not chart_repository:
    chart_repository = os.environ.get("COOKIECUTTER_CHART_REPOSITORY", "{{cookiecutter.chart_repository}}")

# Fallback to direct template values if needed
if not chart_name or chart_name == "{{cookiecutter.chart_name}}":
    chart_name = "{{cookiecutter.chart_name}}"

# Clean up empty strings
if not chart_version or chart_version == "" or chart_version == "{{cookiecutter.chart_version}}":
    chart_version = None
if not chart_repository or chart_repository == "" or chart_repository == "{{cookiecutter.chart_repository}}":
    chart_repository = None

# Define the path to the values.yaml file
values_yaml_path = "values.yaml"

# Function to run a Helm command and return the output
def run_helm_command(command):
    try:
        print(f"Running: {command}")
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
    if chart_repository:
        print(f"Repository: {chart_repository}")
    if chart_version:
        print(f"Version: {chart_version}")

    # Build the helm command appropriately
    if "/" in chart_name:  # If chart_name includes repo prefix
        helm_command = f"helm show values {chart_name}"
    else:
        helm_command = f"helm show values {chart_name}"
    
    # Add repo flag only if repository is specified
    if chart_repository:
        helm_command += f" --repo {chart_repository}"
    
    # Add version flag only if version is specified
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
            print(f"Successfully fetched values from chart {chart_name}")
        except yaml.YAMLError as e:
            print(f"Error parsing YAML values: {str(e)}")
            helm_values_dict = {}

    # Create a separate section for the chart's values
    chart_key = chart_name.split('/')[-1] if '/' in chart_name else chart_name  # Get the chart name without repo prefix
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
    
    # Set version if available
    if chart_version and chart_version != "":
        chart_data["version"] = chart_version
    else:
        # Get the version from pre_gen environment or set a default
        default_version = "0.1.0"
        chart_data["version"] = default_version
    
    # Set appVersion
    chart_data["appVersion"] = chart_version if chart_version and chart_version != "" else "latest"
    
    # Add source info
    if chart_repository and chart_repository != "":
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
