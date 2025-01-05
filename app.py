import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import urllib.parse
import pandas as pd

# ----------------------------------------------------
#   ENV CONFIG & CONSTANTS
# ----------------------------------------------------
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# ----------------------------------------------------
#   STREAMLIT TITLE & SIDEBAR
# ----------------------------------------------------
st.title("Deliverables and Projects Dashboard")

st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details)", unsafe_allow_html=True)

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Mask the key for security
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Optional: Debug checkbox to control JSON output
show_debug = st.sidebar.checkbox("Show Bundle Debug Info", value=False)

# ----------------------------------------------------
#   HELPER FUNCTIONS
# ----------------------------------------------------
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

def parse_task_description(description):
    try:
        start = description.find("[")
        end = description.find("]")
        bundle_name = description[start + 1 : end]
        link_start = description.find("(")
        link_end = description.find(")")
        bundle_link = description[link_start + 1 : link_end]
        bundle_link = f"{API_HOST}{bundle_link}"  # In case it needs a prefix
        return bundle_name, bundle_link
    except Exception:
        return None, None

# Optional: Debug function to show JSON data for a given bundle
def debug_deliverable(deliverable, bundle_name="Deliverable JSON"):
    with st.expander(f"Debug: {bundle_name}"):
        st.json(deliverable)

# ----------------------------------------------------
#   MAIN LOGIC
# ----------------------------------------------------
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
models = fetch_registered_models()

if deliverables:
    # ----------------------------------------
    #  SUMMARY SECTION
    # ----------------------------------------
    st.markdown("---")
    st.header("Summary")

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

    # 3) Total count of projects (from Domino API)
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

    # ----------------------------------------
    #  POLICIES ADOPTION SECTION
    # ----------------------------------------
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
                            bundle_data_per_stage[stage_name].append({
                                "name": deliverable.get("name", "Unnamed Bundle"),
                                "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A"),
                            })

                    # Plot the stages and bundles
                    fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                    st.pyplot(fig)

                    # List bundles in each stage
                    for stage_name, bundles_in_stage in bundle_data_per_stage.items():
                        st.write(f"- **Stage: {stage_name}** ({len(bundles_in_stage)})")
                        with st.expander(f"View Bundles in {stage_name}"):
                            for one_bundle in bundles_in_stage:
                                bundle_n = one_bundle["name"]
                                moved_date = one_bundle["stageUpdateTime"]
                                st.write(f"- {bundle_n} (Moved: {moved_date})")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")
    else:
        st.info("No policies found in deliverables.")

    # ----------------------------------------
    #  GOVERNED BUNDLES DETAILS
    # ----------------------------------------
    st.markdown("---")
    st.header("Governed Bundles Details")
    st.markdown('<div id="governed-bundles-details"></div>', unsafe_allow_html=True)

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
        project_name = bundle.get("projectName", "Unnamed Project")

        # "projectOwner" from your JSON can be used as the correct username
        owner_username = bundle.get("projectOwner", "unknown_user")

        # Construct the bundle overview link
        bundle_link = f"{API_HOST}/u/{owner_username}/{project_name}/overview"

        # Make the bundle name itself a link
        st.markdown(f"## [{bundle_name}]({bundle_link})", unsafe_allow_html=True)

        # Show debug JSON if user toggled in sidebar
        if show_debug:
            debug_deliverable(bundle, bundle_name)

        # Display key fields
        st.write(f"**Status:** {status}")
        st.write(f"**Policy Name:** {policy_name}")
        st.write(f"**Stage:** {stage}")

        # Display tasks related to this bundle
        related_tasks = [t for t in approval_tasks if t["bundle_name"] == bundle_name]
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
                m_name = identifier.get("name", "Unknown Model")
                m_version = identifier.get("version", "Unknown Version")
                created_by = target.get("createdBy", {}).get("userName", "unknown_user")

                # URL-encode in case project name or model name has spaces
                encoded_project_name = urllib.parse.quote(project_name, safe="")
                encoded_model_name = urllib.parse.quote(m_name, safe="")

                model_card_link = (
                    f"{API_HOST}/u/{created_by}/{encoded_project_name}/"
                    f"model-registry/{encoded_model_name}/model-card?version={m_version}"
                )
                model_links.append((m_name, m_version, model_card_link))

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

        st.write("---")

    # ----------------------------------------
    #  REGISTERED MODELS SECTION (TABLE)
    # ----------------------------------------
    if models:
        st.header("Registered Models")
        st.write(f"Total Registered Models: {len(models)}")

        # 1) Build a set of model names in governed bundles
        #    so we know which ones to show a "Bundles" link for.
        models_in_gov_bundles = set()
        for b in governed_bundles:
            for t in b.get("targets", []):
                if t.get("type") == "ModelVersion":
                    identifier = t.get("identifier", {})
                    model_name = identifier.get("name")
                    if model_name:
                        models_in_gov_bundles.add(model_name)

        # 2) Build rows for each registered model
        model_rows = []
        for model in models:
            model_name = model.get("name", "Unnamed Model")
            project_name = model.get("project", {}).get("name", "Unknown Project")
            owner_username = model.get("ownerUsername", "Unknown Owner")

            # Encode project name for safety
            encoded_project_name = urllib.parse.quote(project_name, safe="")

            # Model details link (HTML)
            model_overview_link = (
                f"{API_HOST}/u/{owner_username}/{encoded_project_name}/overview"
            )
            model_details_html = (
                f'<a href="{model_overview_link}" target="_blank">View Model Details</a>'
            )

            # Bundles link (only if in governed bundles)
            if model_name in models_in_gov_bundles:
                encoded_model_name = urllib.parse.quote(model_name, safe="")
                # Link to the governed bundles section, possibly with a query param
                bundles_anchor = f"#governed-bundles-details?model={encoded_model_name}"
                bundles_html = f'<a href="{bundles_anchor}">View Governed Bundles</a>'
            else:
                bundles_html = ""

            model_rows.append({
                "Name": model_name,
                "Project": project_name,
                "Owner": owner_username,
                "Model details (link)": model_details_html,
                "Bundles": bundles_html
            })

        # Convert to DataFrame
        df_models = pd.DataFrame(model_rows)

        # Render as HTML with unsafe_allow_html so links remain clickable
        st.write(df_models.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.warning("No registered models found.")

else:
    st.warning("No deliverables found or an error occurred.")