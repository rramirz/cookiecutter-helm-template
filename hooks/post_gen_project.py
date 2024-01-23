import subprocess
import yaml

# Use the provided chart_name, chart_version, and chart_repository
chart_name = "{{cookiecutter.chart_name}}"
chart_version = "{{cookiecutter.chart_version}}"
chart_repository = "{{cookiecutter.chart_repository}}"

# Define the path to the values.yaml file in your template using chart_name
values_yaml_path = f"values.yaml"

# Function to run a Helm command and return the output
def run_helm_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    return result.stdout

# Function to populate values from Helm chart to values.yaml
def populate_values_from_helm_chart():
    # Check if Helm is available
    try:
        run_helm_command("helm version --short")
    except FileNotFoundError:
        print("Helm not found. Please make sure Helm is installed.")
        return

    # Use Helm to get the values from the chart repository
    helm_command = f"helm show values {chart_name} --repo {chart_repository} --version {chart_version}"
    helm_values = run_helm_command(helm_command)

    # Load the Helm values into a Python dictionary
    helm_values_dict = yaml.safe_load(helm_values)

    # Modify the structure of the values dictionary
    modified_values_dict = {chart_name: helm_values_dict}

    # Write the modified Helm values to the values.yaml file in your template
    with open(values_yaml_path, "w") as values_file:
        yaml.dump(modified_values_dict, values_file)

    print("Values populated from Helm chart to values.yaml")

if __name__ == "__main__":
    populate_values_from_helm_chart()

