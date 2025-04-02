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

    # Group charts by repository
    charts_by_repo = {}
    for chart in charts:
        repo_name = chart["name"].split('/')[0]
        if repo_name not in charts_by_repo:
            charts_by_repo[repo_name] = []
        charts_by_repo[repo_name].append(chart)
    
    # Sort each repo's charts by version and take the 5 latest
    selected_chart = None
    available_charts = []
    
    for repo_name, repo_charts in charts_by_repo.items():
        # Sort by version (assuming semantic versioning)
        repo_charts.sort(key=lambda c: c["version"], reverse=True)
        # Take 5 latest versions
        latest_five = repo_charts[:5]
        
        # Print available versions for this repo
        print(f"\nRepo: {repo_name}")
        for i, chart in enumerate(latest_five, 1):
            chart_name = chart["name"]
            version = chart["version"]
            print(f"{i}. {chart_name} - v{version}")
        
        available_charts.extend(latest_five)
    
    # Let user select a chart
    selected_index = 0
    if len(available_charts) > 1:
        choice = input(f"\nSelect chart [1-{len(available_charts)}] (default: 1): ").strip()
        if choice.isdigit():
            selected_index = int(choice) - 1
            if selected_index < 0 or selected_index >= len(available_charts):
                selected_index = 0
    
    selected_chart = available_charts[selected_index]
    chart_name_parts = selected_chart["name"].split('/')
    repo_name = chart_name_parts[0]
    
    # Get the repository URL
    chart_repo = run_helm_command("helm repo list -o json")
    chart_repo_list = json.loads(chart_repo)
    repo_url = next((repo["url"] for repo in chart_repo_list if repo["name"] == repo_name), None)
    
    if not repo_url:
        raise FailedHookException(f"Repository URL not found for repo '{repo_name}'.")
    
    return selected_chart["name"], selected_chart["version"], repo_url

# This function is no longer needed as version selection is now handled in find_chart_details
def select_version(versions):
    # Default to the latest version
    return versions[0]

def update_cookiecutter_json(chart_name, chart_version, chart_repository):
    # Use the environment variable that Cookiecutter sets
    template_dir = os.environ.get('COOKIECUTTER_TEMPLATE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cookiecutter_json_path = os.path.join(template_dir, "cookiecutter.json")
    
    # Make sure the path exists before trying to open it
    if not os.path.exists(cookiecutter_json_path):
        print(f"Warning: cookiecutter.json not found at {cookiecutter_json_path}")
        print(f"Using current directory instead")
        cookiecutter_json_path = os.path.join(os.getcwd(), "cookiecutter.json")
    
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
    full_chart_name, chart_version, chart_repo = find_chart_details(chart_name)
    
    print(f"\nSelected chart details:")
    print(f"  Chart Name: {full_chart_name}")
    print(f"  Chart Version: {chart_version}")
    print(f"  Chart Repository: {chart_repo}")
    
    # Store values in environment variables so post_gen can access them
    os.environ["COOKIECUTTER_CHART_NAME"] = full_chart_name
    os.environ["COOKIECUTTER_CHART_VERSION"] = chart_version
    os.environ["COOKIECUTTER_CHART_REPOSITORY"] = chart_repo
    
    # Try to update cookiecutter.json, but continue if it fails
    try:
        update_cookiecutter_json(full_chart_name, chart_version, chart_repo)
    except Exception as e:
        print(f"Warning: Could not update cookiecutter.json: {str(e)}")
        print("Continuing with generation...")
    
    # Exit with success code
    sys.exit(0)

if __name__ == "__main__":
    main()
