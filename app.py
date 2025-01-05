import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import urllib.parse  # For URL-encoding

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

# Function to fetch policy details
@st.cache_data
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

# Function to fetch registered models
@st.cache_data
def fetch_registered_models():
    try:
        response = requests.get(
            f"{API_HOST}/api/registeredmodels/v1",
            headers={"X-Domino-Api-Key": API_KEY},
        )
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

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

# Function to parse task description and extract bundle name and link
def parse_task_description(description):
    try:
        start = description.find("[")
        end = description.find("]")
        bundle_name = description[start + 1 : end]
        link_start = description.find("(")
        link_end = description.find(")")
        bundle_link = description[link_start + 1 : link_end]
        bundle_link = f"{API_HOST}{bundle_link}"  # Correct base URL
        return bundle_name, bundle_link
    except Exception:
        return None, None
    
def debug_deliverable(deliverable, label="Deliverable JSON"):
    """
    Displays the raw JSON of a deliverable inside an expander
    for debugging purposes.
    """
    with st.expander(label):
        st.json(deliverable)

# Main Dashboard Logic
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
models = fetch_registered_models()

if deliverables:
    # ----------------------------------------------------
    #  Summary Section
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Summary")

    # Existing summary metrics
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
    total_governed_bundles = len(governed_bundles)
    total_pending_tasks = 0

    # Collect tasks/pending approvals
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

    # Display original summary metrics
    cols = st.columns(3)
    cols[0].metric("Total Policies", total_policies)
    cols[1].metric("Total Bundles", total_bundles)
    cols[2].metric("Pending Tasks", total_pending_tasks)

    # Additional summary metrics
    # 1) Count of registered models
    total_registered_models = len(models)

    # 2) Count of registered models that are part of a bundle (do not double count)
    model_name_version_in_bundles = set()
    for deliverable in deliverables:
        for target in deliverable.get("targets", []):
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                model_name = identifier.get("name")
                model_version = identifier.get("version")
                if model_name and model_version:
                    model_name_version_in_bundles.add((model_name, model_version))
    total_models_in_bundles = len(model_name_version_in_bundles)

    # 3) Total count of projects (from the Domino API)
    total_projects = len(all_projects)

    # 4) Count of projects with at least one bundle
    project_ids_with_bundles = set()
    for d in deliverables:
        pid = d.get("projectId")
        if pid:
            project_ids_with_bundles.add(pid)
    projects_with_a_bundle = len(project_ids_with_bundles)

    # Display the new summary metrics
    st.markdown("#### Additional Metrics")
    cols2 = st.columns(4)
    cols2[0].metric("Registered Models", total_registered_models)
    cols2[1].metric("Models in a Bundle", total_models_in_bundles)
    cols2[2].metric("Total Projects", total_projects)
    cols2[3].metric("Projects w/ Bundle", projects_with_a_bundle)

    # ----------------------------------------------------
    #  Policies Adoption Section
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Policies Adoption")
    policies = {
        bundle.get("policyId"): bundle.get("policyName")
        for bundle in deliverables
        if bundle.get("policyId")
    }

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
                            bundle_data_per_stage[stage_name].append(
                                {
                                    "name": deliverable.get("name", "Unnamed Bundle"),
                                    "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A"),
                                }
                            )

                    # Plot the stages and bundles
                    fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                    st.pyplot(fig)

                    # List bundles in each stage
                    for stage_name, bundles_in_stage in bundle_data_per_stage.items():
                        st.write(f"- **Stage: {stage_name}** ({len(bundles_in_stage)})")
                        with st.expander(f"View Bundles in {stage_name}"):
                            for one_bundle in bundles_in_stage:
                                bundle_name = one_bundle["name"]
                                moved_date = one_bundle["stageUpdateTime"]
                                st.write(f"- {bundle_name} (Moved: {moved_date})")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")

    # ----------------------------------------------------
    # Governed Bundles Section (Now with improved layout)
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Governed Bundles Details")

    # Sort governed bundles by whether they have tasks first
    sorted_bundles = sorted(
        governed_bundles,
        key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in approval_tasks),
        reverse=True
    )

    for bundle in sorted_bundles:
        bundle_name = bundle.get("name", "Unnamed Bundle")
        status = bundle.get("state", "Unknown")
        policy_name = bundle.get("policyName", "Unknown")
        stage = bundle.get("stage", "Unknown")

        # Instead of "createdBy" or "project.ownerUsername",
        # you can now directly use the "projectOwner" field
        owner_username = bundle.get("projectOwner", "unknown_user")
        project_name = bundle.get("projectName", "Unnamed Project")

        # Construct the link using projectOwner and projectName
        bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"

        # Make the bundle name itself a link
        st.markdown(f"## [{bundle_name}]({bundle_link})", unsafe_allow_html=True)

        # Display key fields
        st.write(f"**Status:** {status}")
        st.write(f"**Policy Name:** {policy_name}")
        st.write(f"**Stage:** {stage}")

        # Display tasks related to this bundle
        related_tasks = [task for task in approval_tasks if task["bundle_name"] == bundle_name]
        if related_tasks:
            st.write("**Tasks for this Bundle:**")
            for task in related_tasks:
                task_name = task["task_name"]
                task_stage = task["stage"]
                task_link = task["bundle_link"]
                st.markdown(f"- [{task_name}, Stage: {task_stage}]({task_link})", unsafe_allow_html=True)
        else:
            st.write("No tasks for this bundle.")

        # Display associated ModelVersion links (if any)
        model_links = []
        for target in bundle.get("targets", []):
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                model_name = identifier.get("name", "Unknown Model")
                version = identifier.get("version", "Unknown Version")
                created_by = target.get("createdBy", {}).get("userName", "unknown_user")

                # (Optional) URL-encode if there may be spaces or special characters
                encoded_project_name = urllib.parse.quote(project_name, safe="")
                encoded_model_name = urllib.parse.quote(model_name, safe="")

                model_card_link = (
                    f"{API_HOST}/u/{created_by}/{encoded_project_name}"
                    f"/model-registry/{encoded_model_name}/model-card?version={version}"
                )
                model_links.append((model_name, version, model_card_link))

        if model_links:
            st.write("**Associated Model Versions:**")
            for m_name, m_version, m_link in model_links:
                st.markdown(
                    f"- **{m_name}** (Version: {m_version}) — "
                    f"[View Model Card]({m_link})",
                    unsafe_allow_html=True
                )
        else:
            st.write("No ModelVersion targets found for this bundle.")

        # Debug: See the raw JSON of the entire deliverable/bundle
        debug_deliverable(bundle, label=f"Raw JSON for {bundle_name}")
        
        # A horizontal rule after each bundle
        st.write("---")

    # ----------------------------------------------------
    # Models Section
    # ----------------------------------------------------
    if models:
        st.header("Registered Models")
        st.write(f"Total Registered Models: {len(models)}")

        st.write("Models List:")
        for model in models:
            model_name = model.get("name", "Unnamed Model")
            project_name = model.get("project", {}).get("name", "Unknown Project")
            owner_username = model.get("ownerUsername", "Unknown Owner")

            # URL-encode to avoid broken links
            encoded_project_name = urllib.parse.quote(project_name, safe="")

            model_link = f"{API_HOST}/u/{owner_username}/{encoded_project_name}/overview"
            st.write(f"- **Name:** {model_name}, **Project:** {project_name}, **Owner:** {owner_username}")
            st.markdown(f"[View Model Details]({model_link})", unsafe_allow_html=True)
    else:
        st.warning("No registered models found.")

else:
    st.warning("No deliverables found or an error occurred.")