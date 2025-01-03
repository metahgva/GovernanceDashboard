import streamlit as st
import requests
import os
from collections import defaultdict

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables Dashboard")

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
        return response.json()  # The API response is a list of projects
    except Exception as e:
        st.error(f"An error occurred while fetching projects: {e}")
        return []

# Function to fetch deliverables from the API
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Main dashboard logic
if not API_KEY:
    st.error("API Key is missing. Set the environment variable and restart the app.")
else:
    # Fetch all projects
    all_projects = fetch_all_projects()
    if not all_projects:
        st.error("No projects retrieved from the API.")
    else:
        all_project_names = {project["id"]: project for project in all_projects}

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

        # Fetch deliverables
        data = fetch_deliverables()
        if data:
            deliverables = data.get("data", [])
            if not deliverables:
                st.warning("No deliverables found.")
            else:
                # Get the list of projects with bundles
                projects_with_bundles_ids = {
                    bundle.get("projectId") for bundle in deliverables if bundle.get("projectId")
                }

                # Find projects without bundles
                projects_without_bundles_ids = non_quick_start_project_ids - projects_with_bundles_ids
                projects_without_bundles = [
                    all_project_names[project_id]["name"]
                    for project_id in projects_without_bundles_ids
                    if project_id in all_project_names
                ]

                # Summary Section
                total_projects = len(non_quick_start_project_ids)
                projects_with_bundles_count = len(projects_with_bundles_ids)
                projects_without_bundles_count = len(projects_without_bundles)
                total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
                total_bundles = len(deliverables)

                # Summary Section with Metrics
                st.markdown("---")
                st.header("Summary")
                cols = st.columns(4)
                cols[0].metric("Total Policies", total_policies)
                cols[1].metric("Total Bundles", total_bundles)
                cols[2].metric("Projects With Bundles", projects_with_bundles_count)
                cols[3].metric("Projects Without Bundles", projects_without_bundles_count)

                # Projects Without Bundles Section
                st.markdown("---")
                st.header("Projects Without Bundles")
                with st.expander("View Projects Without Bundles"):
                    for project_id in projects_without_bundles_ids:
                        project_details = all_project_names.get(project_id, {})
                        project_owner = project_details.get("ownerName", "unknown_user")
                        project_name = project_details.get("name", "unknown_project")
                        project_link = f"{API_HOST}/u/{project_owner}/{project_name}/overview"
                        st.markdown(f"- [{project_name}]({project_link})", unsafe_allow_html=True)

                # Display bundles by policy and stage
                st.markdown("---")
                st.header("Bundles by Policy and Stage")
                bundles_per_policy_stage = defaultdict(lambda: defaultdict(list))
                for bundle in deliverables:
                    policy_name = bundle.get("policyName", "No Policy Name")
                    bundle_stage = bundle.get("stage", "No Stage")
                    bundles_per_policy_stage[policy_name][bundle_stage].append(bundle)

                for policy_name, stages in bundles_per_policy_stage.items():
                    policy_id = next(
                        (bundle.get("policyId") for bundle in deliverables if bundle.get("policyName") == policy_name),
                        "unknown",
                    )
                    # Corrected policy deep link
                    policy_link = f"{API_HOST}/governance/policy/{policy_id}/editor"
                    st.subheader(f"Policy: {policy_name}")
                    st.markdown(f"[View Policy]({policy_link})", unsafe_allow_html=True)

                    for stage, bundles in stages.items():
                        with st.expander(f"{stage} ({len(bundles)})"):
                            for bundle in bundles:
                                bundle_name = bundle.get("name", "Unnamed Bundle")
                                bundle_id = bundle.get("id", "")
                                project_owner = bundle.get("projectOwner", "unknown_user")
                                project_name = bundle.get("projectName", "unknown_project")
                                bundle_link = (
                                    f"{API_HOST}/u/{project_owner}/{project_name}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
                                )
                                st.markdown(f"- [{bundle_name}]({bundle_link})", unsafe_allow_html=True)

                # Detailed Deliverables Section
                st.write("---")
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