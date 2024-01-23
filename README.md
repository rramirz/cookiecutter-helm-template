# Cookiecutter Helm Template

This Cookiecutter template is designed to make it easy to create Helm charts for Kubernetes applications. It provides a structured project layout and automates the process of fetching Helm chart values from a remote repository.

## Features

- Sets up a directory structure for your Helm chart project.
- Automatically populates the `values.yaml` file with values fetched from a Helm chart repository.

## Prerequisites

Before using this Cookiecutter template, make sure you have the following installed:

- Helm (for fetching chart values)
- Python (for running Cookiecutter)

## Usage

To create a new Helm chart project using this template, follow these steps:

1. Install Cookiecutter if you haven't already:

   ```bash
   pip install cookiecutter

