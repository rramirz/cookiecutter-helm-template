import subprocess
import json
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
    
    # Get the latest version and repo URL
    latest_chart = charts[0]  # Assuming the first result is the latest
    chart_version = latest_chart["version"]
    chart_repo = run_helm_command("helm repo list -o json")
    chart_repo_list = json.loads(chart_repo)

    # Match the repository name with the Helm search result
    repo_name = latest_chart["name"].split('/')[0]
    repo_url = next((repo["url"] for repo in chart_repo_list if repo["name"] == repo_name), None)

    if not repo_url:
        raise FailedHookException(f"Repository URL not found for repo '{repo_name}'.")

    return chart_version, repo_url

def main():
    chart_name = "{{ cookiecutter.chart_name }}"
    if chart_name == "my-chart":
        raise FailedHookException("You must specify a chart name.")

    print(f"Searching Helm repositories for chart: {chart_name}")
    chart_version, chart_repo = find_chart_details(chart_name)

    # Update context for Cookiecutter
    with open("{{ cookiecutter._template }}", "r") as f:
        context = json.load(f)
    
    context["chart_version"] = chart_version
    context["chart_repo"] = chart_repo

    with open("{{ cookiecutter._template }}", "w") as f:
        json.dump(context, f, indent=2)

if __name__ == "__main__":
    main()

