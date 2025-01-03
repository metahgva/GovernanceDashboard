import streamlit as st
import requests
import os

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Debugging Projects Without Bundles")

# Sidebar information
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Masked for security

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

# Fetch all projects
all_projects = fetch_all_projects()
if not all_projects:
    st.error("No projects retrieved from the API.")
else:
    # Display all projects for debugging
    st.write("### Debug: All Projects Data")
    for project in all_projects:
        st.write(project)  # Debug: Display full project details for analysis

    # Separate quick-start projects
    quick_start_projects = [
        project for project in all_projects if "quick-start" in project["name"].lower()
    ]
    quick_start_project_ids = {project["id"] for project in quick_start_projects}

    # Exclude quick-start projects
    non_quick_start_projects = [
        project for project in all_projects if project["id"] not in quick_start_project_ids
    ]
    non_quick_start_project_ids = {project["id"] for project in non_quick_start_projects}

    # Debug: Display quick-start projects
    st.write("### Debug: Quick-Start Projects")
    for project in quick_start_projects:
        st.write(project)

    # Debug: Display non-quick-start projects
    st.write("### Debug: Non-Quick-Start Projects")
    for project in non_quick_start_projects:
        st.write(project)

    # Attempt to construct deep links for non-quick-start projects
    st.markdown("---")
    st.header("Project Deep-Link Debugging")
    for project in non_quick_start_projects:
        project_name = project.get("name", "unknown_project")
        project_owner = project.get("ownerName", "unknown_user")  # Primary field for owner
        # Alternative fields for debugging
        owner_field_debug = {
            "ownerName": project.get("ownerName"),
            "createdByUserName": project.get("createdByUserName"),
            "creator": project.get("creator"),
        }
        project_link = f"{API_HOST}/u/{project_owner}/{project_name}/overview"

        # Debug: Display all potential owner fields
        st.write(f"Project Name: {project_name}")
        st.write(f"Owner Field Debug: {owner_field_debug}")
        st.markdown(f"Deep-Link: [{project_name}]({project_link})", unsafe_allow_html=True)