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

    # Try multiple approaches to get the values
    helm_values = ""
    chart_parts = chart_name.split('/')
    
    # Try to determine repo_name and chart_name_only
    if len(chart_parts) > 1:
        repo_name = chart_parts[0]
        chart_name_only = chart_parts[1]
    else:
        # If we don't have a slash in the chart name, we need to get creative
        # We'll try to use the repository name as prefix or search for it
        if chart_repository:
            # Try to extract repo name from URL
            repo_url_parts = chart_repository.split('/')
            if repo_url_parts and len(repo_url_parts) >= 3:
                possible_repo_name = repo_url_parts[-2]
                # Clean up any .github.io part
                if '.github.io' in possible_repo_name:
                    possible_repo_name = possible_repo_name.split('.')[0]
                repo_name = possible_repo_name
            else:
                # Just try common names
                repo_name = "stable"
            chart_name_only = chart_name
        else:
            # Last resort
            repo_name = "stable"
            chart_name_only = chart_name
    
    # Approach 1: First try with --repo flag (most reliable)
    if chart_repository:
        helm_command = f"helm show values --repo {chart_repository} {chart_name_only}"
        if chart_version:
            helm_command += f" --version {chart_version}"
        print(f"Running command: {helm_command}")
        helm_values = run_helm_command(helm_command)
    
    # Approach 2: Try with repo/chart notation
    if not helm_values:
        full_chart_name = f"{repo_name}/{chart_name_only}"
        helm_command = f"helm show values {full_chart_name}"
        if chart_version:
            helm_command += f" --version {chart_version}"
        print(f"Running command: {helm_command}")
        helm_values = run_helm_command(helm_command)
    
    # Approach 3: Try using helm template as a fallback
    if not helm_values:
        print(f"Trying helm template approach...")
        if chart_repository:
            helm_command = f"helm template --repo {chart_repository} {chart_name_only}"
        else:
            helm_command = f"helm template {chart_name}"
        
        if chart_version:
            helm_command += f" --version {chart_version}"
        
        # Add --debug to get values in the output
        helm_command += " --debug"
        
        template_output = run_helm_command(helm_command)
        if template_output:
            # Try to extract values from the debug output
            try:
                # First look for the VALUES section
                values_start = template_output.find("USER-SUPPLIED VALUES:")
                values_end = template_output.find("COMPUTED VALUES:")
                
                if values_start > 0 and values_end > 0:
                    values_section = template_output[values_start:values_end].strip()
                    values_start_line = values_section.find('\n')
                    if values_start_line > 0:
                        helm_values = values_section[values_start_line:].strip()
                        print("Extracted values from template debug output")
                else:
                    # Try to find COMPUTED VALUES section as fallback
                    values_start = template_output.find("COMPUTED VALUES:")
                    values_end = template_output.find("HOOKS:")
                    
                    if values_start > 0 and values_end > 0:
                        values_section = template_output[values_start:values_end].strip()
                        values_start_line = values_section.find('\n')
                        if values_start_line > 0:
                            helm_values = values_section[values_start_line:].strip()
                            print("Extracted values from template debug output")
            except Exception as e:
                print(f"Error extracting values from template output: {str(e)}")
    
    # Approach 4: Pull the chart and extract values
    if not helm_values:
        temp_dir = "/tmp/helm-chart-pull"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Try to pull the chart
        print(f"Trying to fetch the chart using helm pull...")
        
        if chart_repository:
            pull_command = f"helm pull --repo {chart_repository} {chart_name_only}"
        else:
            pull_command = f"helm pull {repo_name}/{chart_name_only}"
            
        if chart_version:
            pull_command += f" --version {chart_version}"
        pull_command += f" --untar --untardir {temp_dir}"
        
        run_helm_command(pull_command)
        
        # Try to find the chart directory
        if os.path.exists(temp_dir):
            chart_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            if chart_dirs:
                values_path = os.path.join(temp_dir, chart_dirs[0], "values.yaml")
                if os.path.exists(values_path):
                    print(f"Found values.yaml in pulled chart at {values_path}")
                    try:
                        with open(values_path, "r") as f:
                            helm_values = f.read()
                    except Exception as e:
                        print(f"Error reading values.yaml from pulled chart: {str(e)}")

    if not helm_values:
        print(f"Failed to fetch values from chart {chart_name} after multiple attempts. Attempting to create default values.")
        
        # Create a default set of values for common chart types
        if chart_name_only.lower() == "localstack":
            print("Creating default values for localstack")
            helm_values = """
# Default values for localstack.
image:
  repository: localstack/localstack
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 4566

resources:
  limits:
    cpu: 1
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 512Mi

persistence:
  enabled: true
  size: 1Gi

debug: false
"""
        else:
            helm_values = "{}"
    
    # Load the Helm values into a Python dictionary
    try:
        helm_values_dict = yaml.safe_load(helm_values) or {}
        if helm_values_dict:
            print(f"Successfully loaded values for {chart_name}")
        else:
            print(f"No values found for {chart_name}, using empty object")
            helm_values_dict = {}
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
    """Update the Chart.yaml file with placeholders replaced by actual values from chart selection."""
    chart_yaml_path = "Chart.yaml"
    
    if not os.path.exists(chart_yaml_path):
        print(f"Warning: {chart_yaml_path} not found. Skipping update.")
        return
    
    try:
        with open(chart_yaml_path, "r") as f:
            chart_yaml_content = f.read()
    except Exception as e:
        print(f"Error reading {chart_yaml_path}: {str(e)}")
        return
    
    # Extract chart name without repo prefix
    chart_name_only = chart_name.split('/')[-1] if '/' in chart_name else chart_name
    chart_name_title = chart_name_only.capitalize()
    
    # Replace placeholders with actual values
    replacements = {
        "__CHART_NAME__": chart_name_only,
        "__CHART_NAME_TITLE__": chart_name_title,
        "__CHART_VERSION__": chart_version if chart_version else "latest",
        "__CHART_REPOSITORY__": chart_repository if chart_repository else ""
    }
    
    for placeholder, value in replacements.items():
        chart_yaml_content = chart_yaml_content.replace(placeholder, value)
    
    # Write back to Chart.yaml
    try:
        with open(chart_yaml_path, "w") as f:
            f.write(chart_yaml_content)
        print(f"Updated {chart_yaml_path} with metadata from {chart_name}")
    except Exception as e:
        print(f"Error writing to {chart_yaml_path}: {str(e)}")

if __name__ == "__main__":
    populate_values_from_helm_chart()
    update_chart_yaml()
    print("\nChart generation completed successfully!")
