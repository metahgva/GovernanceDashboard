import streamlit as st
import requests
import os
from collections import defaultdict

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables and Projects Dashboard")

# Sidebar information
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Function to fetch all projects
@st.cache_data
def fetch_all_projects():
    try:
        url = f"{API_HOST}/v4/projects"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching projects: {response.status_code} - {response.text}")
            return []
        return response.json()
    except Exception as e:
        st.error(f"An error occurred while fetching projects: {e}")
        return []

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
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Function to calculate project stats
def calculate_project_stats(all_projects, deliverables):
    quick_start_projects = [
        project for project in all_projects if "quick-start" in project["name"].lower()
    ]
    quick_start_project_ids = {project["id"] for project in quick_start_projects}

    # Non-quick-start projects
    non_quick_start_projects = [
        project for project in all_projects if project["id"] not in quick_start_project_ids
    ]

    # Projects without bundles
    bundled_projects = {bundle.get("projectName", "unknown_project") for bundle in deliverables}
    projects_without_bundles = [
        project for project in non_quick_start_projects if project["name"] not in bundled_projects
    ]

    return non_quick_start_projects, quick_start_projects, projects_without_bundles

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables_data = fetch_deliverables()

if not all_projects:
    st.error("No projects retrieved from the API.")
else:
    if deliverables_data:
        deliverables = deliverables_data.get("data", [])
        non_quick_start_projects, quick_start_projects, projects_without_bundles = calculate_project_stats(
            all_projects, deliverables
        )

        # Summary Section
        total_projects = len(non_quick_start_projects)
        total_bundled_projects = len(non_quick_start_projects) - len(projects_without_bundles)
        total_projects_without_bundles = len(projects_without_bundles)
        quick_start_count = len(quick_start_projects)

        st.markdown("---")
        st.header("Summary")
        cols = st.columns(4)
        cols[0].metric("Total Projects", total_projects)
        cols[1].metric("Projects with Bundles", total_bundled_projects)
        cols[2].metric("Projects without Bundles", total_projects_without_bundles)
        cols[3].metric("Quick-Start Projects", quick_start_count)

        # Projects Without Bundles Section
        st.markdown("---")
        st.header("Projects Without Bundles")
        if not projects_without_bundles:
            st.write("All projects have bundles.")
        else:
            with st.expander(f"Projects Without Bundles ({len(projects_without_bundles)})"):
                for project in projects_without_bundles:
                    project_name = project.get("name", "unknown_project")
                    owner_username = project.get("ownerUsername", "unknown_user")
                    project_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
                    st.markdown(f"- [{project_name}]({project_link})", unsafe_allow_html=True)

        # Governed Bundles Section
        st.markdown("---")
        st.header("Governed Bundles")
        for deliverable in deliverables:
            bundle_name = deliverable.get("name", "Unnamed Bundle")
            status = deliverable.get("state", "Unknown")
            policy_name = deliverable.get("policyName", "Unknown")
            stage = deliverable.get("stage", "Unknown")
            project_name = deliverable.get("projectName", "Unnamed Project")
            project_owner = deliverable.get("projectOwner", "Unknown Project Owner")
            bundle_owner = f"{deliverable.get('createdBy', {}).get('firstName', 'Unknown')} {deliverable.get('createdBy', {}).get('lastName', 'Unknown')}"
            bundle_id = deliverable.get("id", "")
            policy_id = deliverable.get("policyId", "")
            bundle_link = f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
            targets = deliverable.get("targets", [])

            # Group attachments by type
            attachment_details = defaultdict(list)
            for target in targets:
                attachment_type = target.get("type", "Unknown")
                if attachment_type == "ModelVersion":
                    model_name = target.get("identifier", {}).get("name", "Unnamed Model")
                    model_version = target.get("identifier", {}).get("version", "Unknown Version")
                    attachment_name = f"{model_name} (Version: {model_version})"
                else:
                    attachment_name = target.get("identifier", {}).get("filename", "Unnamed Attachment")
                attachment_details[attachment_type].append(attachment_name)

            # Display bundle details
            st.subheader(bundle_name)
            st.markdown(f"[View Bundle Details]({bundle_link})", unsafe_allow_html=True)
            st.write(f"**Status:** {status}")
            st.write(f"**Policy Name:** {policy_name}")
            st.write(f"**Stage:** {stage}")
            st.write(f"**Project Name:** {project_name}")
            st.write(f"**Project Owner:** {project_owner}")
            st.write(f"**Bundle Owner:** {bundle_owner}")

            # Attachments
            st.write("**Attachments by Type:**")
            for attachment_type, names in attachment_details.items():
                with st.expander(f"{attachment_type} ({len(names)})"):
                    for name in names:
                        st.write(f"- {name}")
            st.write("---")
