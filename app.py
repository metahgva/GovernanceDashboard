import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import urllib.parse
import pandas as pd
import re

# ----------------------------------------------------
#   ENV CONFIG & CONSTANTS
# ----------------------------------------------------
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

st.title("Deliverables and Projects Dashboard")

st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details)", unsafe_allow_html=True)

# Sidebar API Configuration
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write(f"API Key: {API_KEY[:5]}{'*' * (len(API_KEY) - 5)}")  # Mask the key
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Optional debug checkbox
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
    import matplotlib.pyplot as plt
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(stage_names, bundle_counts, color="skyblue", edgecolor="black")
    ax.set_title(f"Policy: {policy_name}")
    ax.set_xlabel("Stages")
    ax.set_ylabel("Number of Bundles")
    ax.yaxis.get_major_locator().set_params(integer=True)
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

def debug_deliverable(deliverable, bundle_name="Deliverable JSON"):
    with st.expander(f"Debug: {bundle_name}"):
        st.json(deliverable)

def normalize_model_name(name: str) -> str:
    """
    Convert a model name to lowercase, remove underscores
    and spaces so 'Credit_Approval' matches 'credit approval'.
    Adjust this logic as needed.
    """
    name = name.lower()
    name = re.sub(r"[\s_]+", "", name)  # remove spaces+underscores
    return name

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

    # Collect basic info
    total_policies = len(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    total_bundles = len(deliverables)
    governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
    total_governed_bundles = len(governed_bundles)
    total_pending_tasks = 0

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

    # Additional summary metrics
    total_registered_models = len(models)

    # Models in a bundle
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

    total_projects = len(all_projects)

    # Projects with at least one bundle
    project_ids_with_bundles = set()
    for d in deliverables:
        pid = d.get("projectId")
        if pid:
            project_ids_with_bundles.add(pid)
    projects_with_a_bundle = len(project_ids_with_bundles)

    # ------------------------------------------------
    # CREATE CLICKABLE METRICS + LINKS TO DETAILED SECTION
    # ------------------------------------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Policies", total_policies)
    col1.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    col2.metric("Total Bundles", total_bundles)
    col2.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    col3.metric("Pending Tasks", total_pending_tasks)
    col3.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    st.markdown("")

    colA, colB, colC, colD = st.columns(4)
    colA.metric("Registered Models", total_registered_models)
    colA.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    colB.metric("Models in a Bundle", total_models_in_bundles)
    colB.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    colC.metric("Total Projects", total_projects)
    colC.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    colD.metric("Projects w/ Bundle", projects_with_a_bundle)
    colD.markdown("[See list](#detailed-metrics-section)", unsafe_allow_html=True)

    # ----------------------------------------
    # DETAILED METRICS SECTION
    # ----------------------------------------
    st.markdown("---")
    st.markdown("## Detailed Metrics Section")
    st.markdown('<a id="detailed-metrics-section"></a>', unsafe_allow_html=True)

    # 1) Policies (Detailed List)
    all_policy_names = sorted(set(bundle.get("policyName", "No Policy Name") for bundle in deliverables))
    with st.expander("All Policies"):
        st.write(f"Found {len(all_policy_names)} policy names:")
        for pol in all_policy_names:
            st.write(f"- {pol}")

    # 2) Bundles (Detailed List)
    with st.expander("All Bundles"):
        st.write(f"Found {len(deliverables)} bundles (deliverables):")
        for d in deliverables:
            st.write(f"- {d.get('name', 'Unnamed')}")

    # 3) Pending Tasks (Detailed List)
    with st.expander("Pending Tasks"):
        st.write(f"Total Pending Tasks: {total_pending_tasks}")
        if approval_tasks:
            for t in approval_tasks:
                link = t["bundle_link"]
                st.markdown(f"- [{t['task_name']} (stage: {t['stage']})]({link})", unsafe_allow_html=True)
        else:
            st.write("No pending tasks")

    # 4) Registered Models
    all_model_names = sorted(m.get("name", "Unnamed Model") for m in models)
    with st.expander("All Registered Models"):
        st.write(f"Found {len(all_model_names)} registered models:")
        for mn in all_model_names:
            st.write(f"- {mn}")

    # 5) Models in a Bundle (Detailed List)
    #    We'll just list the unique (model_name) from model_name_version_in_bundles
    #    Or show model_name + version
    with st.expander("Models in a Bundle"):
        st.write(f"Found {len(model_name_version_in_bundles)} model+version references:")
        # We can group them by model name
        model_map = defaultdict(list)
        for (mname, mver) in model_name_version_in_bundles:
            model_map[mname].append(mver)

        for mname, versions in model_map.items():
            st.write(f"- **{mname}**: Versions {', '.join(str(v) for v in versions)}")

    # 6) Projects (Detailed List)
    all_project_names = sorted(set(p.get("name", "Unnamed Project") for p in all_projects))
    with st.expander("All Projects"):
        st.write(f"Found {len(all_project_names)} total projects:")
        for pn in all_project_names:
            st.write(f"- {pn}")

    # 7) Projects w/ a Bundle
    #    We have project_ids_with_bundles, but let's also show their names if possible
    with st.expander("Projects w/ Bundle"):
        st.write(f"Found {projects_with_a_bundle} projects that have at least one deliverable/bundle.")
        # Build a map from projectId -> project
        pid_map = {}
        for p in all_projects:
            pid_val = p.get("id")
            if pid_val:
                pid_map[pid_val] = p

        for pid_val in project_ids_with_bundles:
            proj = pid_map.get(pid_val)
            if proj:
                st.write(f"- {proj.get('name', 'Unnamed Project')} (id={pid_val})")
            else:
                st.write(f"- (Unknown project name for id={pid_val})")

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
                                bname = one_bundle["name"]
                                moved_date = one_bundle["stageUpdateTime"]
                                st.write(f"- {bname} (Moved: {moved_date})")
                else:
                    st.warning(f"No stages found for policy {policy_name}.")
            else:
                st.error(f"Could not fetch details for policy {policy_name}.")
    else:
        st.info("No policies found in deliverables.")

    # ----------------------------------------
    #  GOVERNED BUNDLES DETAILS (TABLE)
    # ----------------------------------------
    st.markdown("---")
    st.header("Governed Bundles Details (Table)")

    # Sort governed bundles by whether they have tasks
    sorted_bundles = sorted(
        governed_bundles,
        key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in approval_tasks),
        reverse=True
    )

    table_rows = []
    for bundle in sorted_bundles:
        bundle_name = bundle.get("name", "Unnamed Bundle")
        status = bundle.get("state", "Unknown")
        policy_name = bundle.get("policyName", "Unknown")
        stage = bundle.get("stage", "Unknown")
        project_name = bundle.get("projectName", "Unnamed Project")
        project_owner = bundle.get("projectOwner", "unknown_user")

        # Domino project link for the bundle’s project
        encoded_project_name = urllib.parse.quote(project_name, safe="")
        bundle_link = f"{API_HOST}/u/{project_owner}/{encoded_project_name}/overview"

        # Make the bundle name clickable
        bundle_html = f'<a href="{bundle_link}" target="_blank">{bundle_name}</a>'

        # Collect tasks
        related_tasks = [t for t in approval_tasks if t["bundle_name"] == bundle_name]
        if related_tasks:
            tasks_bullets = []
            for task in related_tasks:
                task_name = task["task_name"]
                task_stage = task["stage"]
                task_link = task["bundle_link"]
                tasks_bullets.append(
                    f'<li><a href="{task_link}" target="_blank">{task_name}, Stage: {task_stage}</a></li>'
                )
            tasks_html = f"<ul>{''.join(tasks_bullets)}</ul>"
        else:
            tasks_html = "No tasks"

        # Collect ModelVersion targets
        model_versions = []
        for target in bundle.get("targets", []):
            if target.get("type") == "ModelVersion":
                identifier = target.get("identifier", {})
                m_name = identifier.get("name", "Unknown Model")
                m_version = identifier.get("version", "Unknown Version")
                created_by = target.get("createdBy", {}).get("userName", "unknown_user")

                encoded_m_name = urllib.parse.quote(m_name, safe="")
                model_card_link = (
                    f"{API_HOST}/u/{created_by}/{encoded_project_name}"
                    f"/model-registry/{encoded_m_name}/model-card?version={m_version}"
                )
                model_versions.append(
                    f'<li>{m_name} (Version: {m_version}) '
                    f'— <a href="{model_card_link}" target="_blank">View Model Card</a></li>'
                )

        if model_versions:
            model_versions_html = f"<ul>{''.join(model_versions)}</ul>"
        else:
            model_versions_html = "No ModelVersion targets found"

        # Construct a row dict for our table
        table_rows.append({
            "Bundle": bundle_html,
            "Status": status,
            "Policy Name": policy_name,
            "Stage": stage,
            "Tasks": tasks_html,
            "Model Versions": model_versions_html
        })

    df_bundles = pd.DataFrame(table_rows)
    st.write(df_bundles.to_html(escape=False), unsafe_allow_html=True)

    # ----------------------------------------
    #  REGISTERED MODELS TABLE
    # ----------------------------------------
    if models:
        st.header("Registered Models")
        st.write(f"Total Registered Models: {len(models)}")

        # 1) Build a dictionary: model_name -> list of (bundle_name, bundle_link)
        model_to_bundles = defaultdict(list)
        for bundle in governed_bundles:
            b_name = bundle.get("name", "Unnamed Bundle")
            p_owner = bundle.get("projectOwner", "unknown_user")
            p_name = bundle.get("projectName", "Unnamed Project")
            bundle_link = f"{API_HOST}/u/{p_owner}/{p_name}/overview"

            for target in bundle.get("targets", []):
                if target.get("type") == "ModelVersion":
                    identifier = target.get("identifier", {})
                    target_model_name = identifier.get("name")
                    if target_model_name:
                        model_to_bundles[target_model_name].append((b_name, bundle_link))

        # 2) Build rows for each registered model
        model_rows = []
        for model in models:
            m_name = model.get("name", "Unnamed Model")
            project_name = model.get("project", {}).get("name", "Unknown Project")
            owner_username = model.get("ownerUsername", "Unknown Owner")

            encoded_project_name = urllib.parse.quote(project_name, safe="")
            encoded_model_name = urllib.parse.quote(m_name, safe="")

            # Link directly to Domino Model Registry
            model_registry_url = (
                f"{API_HOST}/u/{owner_username}/{encoded_project_name}"
                f"/model-registry/{encoded_model_name}"
            )
            model_name_html = f'<a href="{model_registry_url}" target="_blank">{m_name}</a>'

            # Bundles bullet list
            if m_name in model_to_bundles:
                bundles_list = model_to_bundles[m_name]
                bullets = []
                for b_name, b_link in bundles_list:
                    safe_bundle_name = b_name.replace("<", "&lt;").replace(">", "&gt;")
                    bullets.append(
                        f'<li><a href="{b_link}" target="_blank">{safe_bundle_name}</a></li>'
                    )
                bundles_html = f"<ul>{''.join(bullets)}</ul>"
            else:
                bundles_html = ""

            model_rows.append({
                "Name": model_name_html,
                "Project": project_name,
                "Owner": owner_username,
                "Bundles": bundles_html
            })

        df_models = pd.DataFrame(model_rows)
        st.write(df_models.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.warning("No registered models found.")

else:
    st.warning("No deliverables found or an error occurred.")