import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Goals Related to Deliverables")

# Function to fetch deliverables
@st.cache_data
def fetch_deliverables():
    try:
        url = f"{API_HOST}/guardrails/v1/deliverables"
        response = requests.get(url, auth=(API_KEY, API_KEY))
        if response.status_code != 200:
            st.error(f"Error fetching deliverables: {response.status_code} - {response.text}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching deliverables: {e}")
        return []

# Function to fetch goals for a project
def fetch_goals_for_project(project_id):
    try:
        url = f"{API_HOST}/api/projects/v1/projects/{project_id}/goals"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching goals for project {project_id}: {response.status_code}")
            return []
        return response.json().get("goals", [])
    except Exception as e:
        st.error(f"An error occurred while fetching goals for project {project_id}: {e}")
        return []

# Main App Logic
deliverables = fetch_deliverables()

if not deliverables:
    st.warning("No deliverables found.")
else:
    # Extract unique project IDs from deliverables
    project_ids = {
        bundle.get("projectId", "unknown_project_id") for bundle in deliverables if bundle.get("projectId")
    }

    st.header("Goals Related to Deliverables")

    for project_id in project_ids:
        # Fetch goals for each project
        goals = fetch_goals_for_project(project_id)
        if not goals:
            continue

        # Filter goals related to deliverables
        related_goals = [
            goal for goal in goals if goal.get("relatedBundleId") in {bundle["id"] for bundle in deliverables}
        ]

        if related_goals:
            # Display project-specific goals
            project_name = next(
                (bundle.get("projectName", "Unnamed Project") for bundle in deliverables if bundle.get("projectId") == project_id),
                "Unnamed Project",
            )
            st.subheader(f"Project: {project_name}")
            for goal in related_goals:
                goal_name = goal.get("name", "Unnamed Goal")
                goal_status = goal.get("status", "Unknown Status")
                related_bundle_id = goal.get("relatedBundleId", "Unknown Bundle")
                st.write(f"- **{goal_name}** (Status: {goal_status}, Bundle ID: {related_bundle_id})")