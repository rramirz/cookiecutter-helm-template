import subprocess
import json
import os
import sys
from cookiecutter.exceptions import FailedHookException

def run_helm_command(command):
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise FailedHookException(f"Command failed: {e.stderr.strip()}")

def get_chart_name():
    chart_name = input("\nEnter the name of the Helm chart you want to install: ").strip()
    if not chart_name:
        raise FailedHookException("Chart name cannot be empty.")
    return chart_name

def find_chart_details(chart_name):
    # Search for the chart in the Helm repo
    print(f"Searching Helm repositories for chart: {chart_name}")
    search_output = run_helm_command(f"helm search repo {chart_name} -o json")
    charts = json.loads(search_output)
    
    if not charts:
        # Chart not found, ask if user wants to add a new repo
        add_repo = input(f"No charts found for '{chart_name}' in existing repositories. Would you like to add a new repository? (y/n): ").strip().lower()
        if add_repo == 'y' or add_repo == 'yes':
            repo_name = input("Enter repository name: ").strip()
            repo_url = input("Enter repository URL: ").strip()
            
            if not repo_name or not repo_url:
                raise FailedHookException("Repository name and URL cannot be empty.")
            
            print(f"Adding Helm repository '{repo_name}' with URL '{repo_url}'...")
            run_helm_command(f"helm repo add {repo_name} {repo_url}")
            run_helm_command("helm repo update")
            
            # Search again after adding the new repo
            search_output = run_helm_command(f"helm search repo {chart_name} -o json")
            charts = json.loads(search_output)
            
            if not charts:
                raise FailedHookException(f"Still no charts found for '{chart_name}' after adding repository.")
        else:
            raise FailedHookException(f"Operation cancelled. No charts found for '{chart_name}'.")
    
    # Get the list of versions and the latest chart
    latest_chart = charts[0]
    versions = sorted(set([chart["version"] for chart in charts]), reverse=True)
    chart_name_parts = latest_chart["name"].split('/')
    repo_name = chart_name_parts[0]
    
    # In case the chart_name was partial, get the full chart name
    full_chart_name = latest_chart["name"]
    
    # Get the repository URL
    chart_repo = run_helm_command("helm repo list -o json")
    chart_repo_list = json.loads(chart_repo)
    repo_url = next((repo["url"] for repo in chart_repo_list if repo["name"] == repo_name), None)
    
    if not repo_url:
        raise FailedHookException(f"Repository URL not found for repo '{repo_name}'.")
    
    return full_chart_name, versions, repo_url

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

def update_cookiecutter_json(chart_name, chart_version, chart_repository):
    # Find the template root directory
    template_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cookiecutter_json_path = os.path.join(template_dir, "cookiecutter.json")
    
    # Read the current cookiecutter.json
    with open(cookiecutter_json_path, "r") as f:
        context = json.load(f)
    
    # Update the context with our values
    context["chart_name"] = chart_name
    context["chart_version"] = chart_version
    context["chart_repository"] = chart_repository
    
    # Write the updated context back
    with open(cookiecutter_json_path, "w") as f:
        json.dump(context, f, indent=2)
    
    return cookiecutter_json_path

def main():
    # Get chart name from user input
    chart_name = "{{ cookiecutter.chart_name }}"
    
    # If chart_name is null or the default, ask the user
    if chart_name == "null" or chart_name == "my-chart":
        chart_name = get_chart_name()
    
    # Find chart details (version and repo)
    full_chart_name, versions, chart_repo = find_chart_details(chart_name)
    
    # Let the user select a version
    selected_version = select_version(versions)
    
    print(f"\nSelected chart details:")
    print(f"  Chart Name: {full_chart_name}")
    print(f"  Chart Version: {selected_version}")
    print(f"  Chart Repository: {chart_repo}")
    
    # Update cookiecutter.json with the selected values
    update_cookiecutter_json(full_chart_name, selected_version, chart_repo)
    
    # Exit with a special code to signal cookiecutter to reload the context
    sys.exit(0)

if __name__ == "__main__":
    main()
