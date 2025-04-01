import subprocess
import json
import os
from cookiecutter.exceptions import FailedHookException

def run_helm_command(command):
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise FailedHookException(f"Command failed: {e.stderr.strip()}")

def find_chart_details(chart_name):
    # Search for the chart in the Helm repo
    search_output = run_helm_command(f"helm search repo {chart_name} -o json")
    charts = json.loads(search_output)
    
    if not charts:
        raise FailedHookException(f"No charts found for '{chart_name}' in Helm repositories.")
    
    # Get the list of versions and the latest chart
    latest_chart = charts[0]
    versions = [chart["version"] for chart in charts]
    repo_name = latest_chart["name"].split('/')[0]
    
    # Get the repository URL
    chart_repo = run_helm_command("helm repo list -o json")
    chart_repo_list = json.loads(chart_repo)
    repo_url = next((repo["url"] for repo in chart_repo_list if repo["name"] == repo_name), None)
    
    if not repo_url:
        raise FailedHookException(f"Repository URL not found for repo '{repo_name}'.")
    
    return versions, repo_url

def select_version(versions):
    print("\nAvailable versions:")
    for i, version in enumerate(versions, start=1):
        print(f"{i}. {version}")
    
    choice = input(f"Choose a version [1-{len(versions)}] (default: latest): ").strip()
    
    if choice.isdigit():
        choice_index = int(choice) - 1
        if 0 <= choice_index < len(versions):
            return versions[choice_index]
    
    # Default to the latest version
    print(f"Defaulting to the latest version: {versions[0]}")
    return versions[0]

def main():
    chart_name = "{{ cookiecutter.chart_name }}"
    if chart_name == "my-chart":
        raise FailedHookException("You must specify a chart name.")
    
    print(f"Searching Helm repositories for chart: {chart_name}")
    versions, chart_repo = find_chart_details(chart_name)
    
    # Let the user select a version
    selected_version = select_version(versions)
    
    print(f"\nSelected chart details:")
    print(f"  Chart Name: {chart_name}")
    print(f"  Chart Version: {selected_version}")
    print(f"  Chart Repository: {chart_repo}")
    
    # Instead of trying to modify cookiecutter.json directly, 
    # set environment variables that can be used in cookiecutter templates
    os.environ["COOKIECUTTER_CHART_VERSION"] = selected_version
    os.environ["COOKIECUTTER_CHART_REPOSITORY"] = chart_repo
    
    # If you want to make these variables available to other files in the template
    # Create a temporary file in a location that will be copied to the output directory
    temp_config = {
        "chart_version": selected_version,
        "chart_repository": chart_repo
    }
    
    # Create a file in the template directory that will be copied to the output
    with open("chart_config.json", "w") as f:
        json.dump(temp_config, f, indent=2)

if __name__ == "__main__":
    main()
