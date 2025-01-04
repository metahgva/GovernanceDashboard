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

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()

if deliverables:
    # Summary Section
    st.markdown("---")
    st.header("Summary")
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
    total_governed_bundles = len(governed_bundles)
    total_pending_tasks = 0

    # Fetch tasks and count pending ones
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
                if "Approval requested Stage" in description:
                    bundle_name, bundle_link = parse_task_description(description)
                    if bundle_name and bundle_link:
                        approval_tasks.append({
                            "task_name": task.get("title", "Unnamed Task"),
                            "stage": description.split("Stage")[1].split(":")[0].strip(),
                            "bundle_name": bundle_name,
                            "bundle_link": bundle_link,
                        })
                        total_pending_tasks += 1

    cols = st.columns(3)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Total Bundles", total_bundles)
    cols[2].metric("Pending Tasks", total_pending_tasks)

    # Policies Adoption Section
    st.markdown("---")
    st.header("Policies Adoption")
    policies = {bundle.get("policyId"): bundle.get("policyName") for bundle in deliverables if bundle.get("policyId")}

    if policies:
        for policy_id, policy_name in policies.items():
            st.subheader(f"Policy: {policy_name}")
            stages = {bundle.get("stage", "Unknown Stage") for bundle in deliverables if bundle.get("policyId") == policy_id}
            for stage in stages:
                st.write(f"- **Stage:** {stage}")

    # Governed Bundles Section
    st.markdown("---")
    st.header("Governed Bundles Details")

    # Sort governed bundles by whether they have tasks first
    sorted_bundles = sorted(governed_bundles, key=lambda b: any(
        t["bundle_name"] == b.get("name", "") for t in approval_tasks
    ), reverse=True)

    for bundle in sorted_bundles:
        bundle_name = bundle.get("name", "Unnamed Bundle")
        status = bundle.get("state", "Unknown")
        policy_name = bundle.get("policyName", "Unknown")
        stage = bundle.get("stage", "Unknown")
        project_name = bundle.get("projectName", "Unnamed Project")
        owner_username = bundle.get("createdBy", {}).get("username", "unknown_user")
        bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"

        st.subheader(bundle_name)
        st.markdown(f"[View Bundle Details]({bundle_link})", unsafe_allow_html=True)
        st.write(f"**Status:** {status}")
        st.write(f"**Policy Name:** {policy_name}")
        st.write(f"**Stage:** {stage}")

        # Display tasks related to this bundle
        related_tasks = [task for task in approval_tasks if task["bundle_name"] == bundle_name]
        if related_tasks:
            st.write("**Tasks for this Bundle:**")
            for task in related_tasks:
                st.write(f"- {task['task_name']} (Stage: {task['stage']})")
                st.markdown(f"[View Task Bundle]({task['bundle_link']})", unsafe_allow_html=True)
        st.write("---")
else:
    st.warning("No deliverables found or an error occurred.")