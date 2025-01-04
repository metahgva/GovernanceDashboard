import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Deliverables and Projects Dashboard")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Tasks with Approval Requests](#tasks-with-approval-requests)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details)", unsafe_allow_html=True)

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

# Function to fetch tasks for a project
@st.cache_data
def fetch_tasks_for_project(project_id):
    try:
        url = f"{API_HOST}/api/projects/v1/projects/{project_id}/goals"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching tasks for project {project_id}: {response.status_code}")
            return []
        tasks_data = response.json()
        if "goals" not in tasks_data:
            st.error(f"Unexpected tasks structure for project {project_id}: {tasks_data}")
            return []
        return tasks_data["goals"]
    except Exception as e:
        st.error(f"An error occurred while fetching tasks for project {project_id}: {e}")
        return []

# Function to fetch policy details
def fetch_policy_details(policy_id):
    try:
        url = f"{API_HOST}/guardrails/v1/policies/{policy_id}"
        response = requests.get(url, auth=(API_KEY, API_KEY))
        if response.status_code != 200:
            st.error(f"Error fetching policy details for {policy_id}: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An exception occurred while fetching policy details for {policy_id}: {e}")
        return None

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

# Function to visualize policies with stages
def plot_policy_stages(policy_name, stages, bundle_data):
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(stage_names, bundle_counts, color="skyblue", edgecolor="black")
    ax.set_title(f"Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    ax.yaxis.get_major_locator().set_params(integer=True)  # Force Y-axis to use whole numbers
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()

if deliverables:
    # Summary Section
    st.markdown("---")
    st.header("Summary")
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    non_quick_start_projects, quick_start_projects, projects_without_bundles = calculate_project_stats(
        all_projects, deliverables
    )
    total_projects_without_bundles = len(projects_without_bundles)

    cols = st.columns(2)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Projects Without Bundles", total_projects_without_bundles)

    # Policies Adoption Section
    st.markdown("---")
    st.header("Policies Adoption")
    policies = {bundle.get("policyId"): bundle.get("policyName") for bundle in deliverables if bundle.get("policyId")}

    if policies:
        for policy_id, policy_name in policies.items():
            st.subheader(f"Policy: {policy_name}")
            policy_details = fetch_policy_details(policy_id)

            if policy_details:
                stages = policy_details.get("stages", [])
                if stages:
                    # Collect bundle data per stage
                    bundle_data_per_stage = defaultdict(list)
                    for deliverable in deliverables:
                        if deliverable.get("policyId") == policy_id:
                            stage_name = deliverable.get("stage", "Unknown Stage")
                            bundle_data_per_stage[stage_name].append({
                                "name": deliverable.get("name", "Unnamed Bundle"),
                                "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A")
                            })

                    # Plot the stages and bundles
                    fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                    st.pyplot(fig)

                    # List bundles in each stage
                    for stage_name, bundles in bundle_data_per_stage.items():
                        st.write(f"- **Stage: {stage_name}** ({len(bundles)})")
                        with st.expander(f"View Bundles in {stage_name}"):
                            for bundle in bundles:
                                bundle_name = bundle['name']
                                moved_date = bundle['stageUpdateTime']
                                st.write(f"- {bundle_name} (Moved: {moved_date})")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")

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

    # Tasks with Approval Requests Section
    st.markdown("---")
    st.header("Tasks with Approval Requests")
    project_ids = {
        bundle.get("projectId", "unknown_project_id") for bundle in deliverables if bundle.get("projectId")
    }

    approval_tasks = []

    for project_id in project_ids:
        if project_id == "unknown_project_id":
            continue

        tasks = fetch_tasks_for_project(project_id)
        for task in tasks:
            if isinstance(task, dict):
                description = task.get("description", "")
                task_name = description if description else task.get("title", "Unnamed Task")
                if "Approval requested Stage" in description:
                    bundle_name, bundle_link = parse_task_description(description)
                    if bundle_name and bundle_link:
                        approval_tasks.append({
                            "task_name": task_name,
                            "stage": description.split("Stage")[1].split(":")[0].strip(),
                            "bundle_name": bundle_name,
                            "bundle_link": bundle_link,
                        })

    if approval_tasks:
        for task in approval_tasks:
            st.subheader(task["task_name"])
            st.write(f"**Stage:** {task['stage']}")
            st.write(f"**Bundle Name:** {task['bundle_name']}")
            st.markdown(f"[View Bundle]({task['bundle_link']})", unsafe_allow_html=True)
            st.write("---")
    else:
        st.write("No tasks with approval requests found.")

    # Governed Bundles Section
    st.markdown("---")
    st.header("Governed Bundles Details")
    for deliverable in deliverables:
        bundle_name = deliverable.get("name", "Unnamed Bundle")
        status = deliverable.get("state", "Unknown")
        policy_name = deliverable.get("policyName", "Unknown")
        stage = deliverable.get("stage", "Unknown")
        project_name = deliverable.get("projectName", "Unnamed Project")
        owner_username = deliverable.get("createdBy", {}).get("username", "unknown_user")
        bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"
        st.subheader(bundle_name)
        st.markdown(f"[View Bundle Details]({bundle_link})", unsafe_allow_html=True)
        st.write(f"**Status:** {status}")
        st.write(f"**Policy Name:** {policy_name}")
        st.write(f"**Stage:** {stage}")