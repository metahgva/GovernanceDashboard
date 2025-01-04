import streamlit as st
import requests
import os
from collections import defaultdict

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Tasks with Approval Requests Dashboard")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Approval Tasks](#tasks-with-approval-requests)", unsafe_allow_html=True)

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch deliverables
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        if response.status_code != 200:
            st.error(f"Error fetching deliverables: {response.status_code} - {response.text}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return []

# Function to fetch tasks for a project
@st.cache_data
def fetch_tasks_for_project(project_id):
    try:
        url = f"{API_HOST}/api/projects/v1/projects/{project_id}/goals"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching tasks for project {project_id}: {response.status_code}")
            return []
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching tasks for project {project_id}: {e}")
        return []

# Function to parse task description and extract bundle name and link
def parse_task_description(description):
    try:
        start = description.find("[")
        end = description.find("]")
        bundle_name = description[start + 1 : end]
        link_start = description.find("(")
        link_end = description.find(")")
        bundle_link = description[link_start + 1 : link_end]
        return bundle_name, bundle_link
    except Exception:
        return None, None

# Main App Logic
deliverables = fetch_deliverables()

if not deliverables:
    st.warning("No deliverables found.")
else:
    # Extract unique project IDs from deliverables
    project_ids = {
        bundle.get("projectId", "unknown_project_id") for bundle in deliverables if bundle.get("projectId")
    }
    st.write(f"Found {len(project_ids)} projects related to deliverables.")  # Debug: Log number of projects

    approval_tasks = []

    for project_id in project_ids:
        if project_id == "unknown_project_id":
            st.warning(f"Unknown project ID for a deliverable. Skipping...")
            continue

        # Fetch tasks for each project
        tasks = fetch_tasks_for_project(project_id)
        for task in tasks:
            description = task.get("description", "")
            task_name = description if description else "Unnamed Task"  # Use description as the task name
            if "Approval requested Stage" in description:
                bundle_name, bundle_link = parse_task_description(description)
                if bundle_name and bundle_link:
                    approval_tasks.append({
                        "task_name": task_name,
                        "stage": description.split("Stage")[1].split(":")[0].strip(),
                        "bundle_name": bundle_name,
                        "bundle_link": bundle_link,
                    })

    # Display Approval Tasks
    st.markdown("---")
    st.header("Tasks with Approval Requests")
    if approval_tasks:
        for task in approval_tasks:
            st.subheader(task["task_name"])
            st.write(f"**Stage:** {task['stage']}")
            st.write(f"**Bundle Name:** {task['bundle_name']}")
            st.markdown(f"[View Bundle]({task['bundle_link']})", unsafe_allow_html=True)
            st.write("---")
    else:
        st.write("No tasks with approval requests found.")