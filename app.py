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

# ----------------------------------------------------
#   FETCH DATA
# ----------------------------------------------------
all_projects = fetch_all_projects()
deliverables = fetch_deliverables()
models = fetch_registered_models()

# ----------------------------------------------------
#   BUILD A PROJECT MAP & ANNOTATE DELIVERABLES
# ----------------------------------------------------
project_map = {}
for proj in all_projects:
    pid = proj.get("id")
    if pid:
        project_map[pid] = proj

# Now annotate each deliverable with consistent "projectName" & "projectOwner"
for d in deliverables:
    pid = d.get("projectId")
    if pid in project_map:
        p_obj = project_map[pid]
        d["projectName"] = p_obj.get("name", "Unnamed Project")
        d["projectOwner"] = p_obj.get("ownerUsername", "unknown_user")
    else:
        d["projectName"] = "UNKNOWN"
        d["projectOwner"] = "unknown_user"

if not deliverables:
    st.warning("No deliverables found or an error occurred.")
    st.stop()

# ----------------------------------------------------
#   PRE-COMPUTE SUMMARY DATA
# ----------------------------------------------------
# 1) Total Policies
policy_names = [d.get("policyName", "No Policy Name") for d in deliverables]
total_policies = len(set(policy_names))

# 2) Total Bundles
total_bundles = len(deliverables)

# 3) Governed vs Non-Governed Bundles
governed_bundles = [bundle for bundle in deliverables if bundle.get("policyName")]
total_governed_bundles = len(governed_bundles)

# 4) Pending Tasks
approval_tasks = []
for d in deliverables:
    proj_id = d.get("projectId")
    if not proj_id or proj_id == "unknown_project_id":
        continue
    tasks = fetch_tasks_for_project(proj_id)
    for t in tasks:
        if isinstance(t, dict):
            desc = t.get("description", "")
            if "Approval requested Stage" in desc:
                b_name, b_link = parse_task_description(desc)
                if b_name and b_link:
                    approval_tasks.append({
                        "task_name": t.get("title", "Unnamed Task"),
                        "stage": desc.split("Stage")[1].split(":")[0].strip(),
                        "bundle_name": b_name,
                        "bundle_link": b_link,
                    })
total_pending_tasks = len(approval_tasks)

# 5) Registered Models
total_registered_models = len(models)

# 6) Models in a Bundle
model_name_version_in_bundles = set()
for d in deliverables:
    for tgt in d.get("targets", []):
        if tgt.get("type") == "ModelVersion":
            identifier = tgt.get("identifier", {})
            m_name = identifier.get("name")
            m_ver = identifier.get("version")
            if m_name and m_ver:
                model_name_version_in_bundles.add((m_name, m_ver))
total_models_in_bundles = len(model_name_version_in_bundles)

# 7) Projects
total_projects = len(all_projects)

# 8) Projects with at least one bundle
project_ids_with_bundles = set(d.get("projectId") for d in deliverables if d.get("projectId"))
projects_with_a_bundle = len(project_ids_with_bundles)

# ----------------------------------------------------
#   SUMMARY SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Total Policies", total_policies)
col2.metric("Total Bundles", total_bundles)
col3.metric("Pending Tasks", total_pending_tasks)

colA, colB, colC, colD = st.columns(4)
colA.metric("Registered Models", total_registered_models)
colB.metric("Models in a Bundle", total_models_in_bundles)
colC.metric("Total Projects", total_projects)
colD.metric("Projects w/ Bundle", projects_with_a_bundle)

# ----------------------------------------------------
#   OPTIONAL: Detailed Metrics Section, etc.
#   (As in the previous demonstration)
# ----------------------------------------------------
st.markdown("---")
st.markdown("## Detailed Metrics Section")

with st.expander("All Policies"):
    st.write(f"Found {total_policies} policy names:")
    for pol_name in sorted(set(policy_names)):
        st.write(f"- {pol_name}")

with st.expander("All Bundles"):
    st.write(f"Found {total_bundles} total bundles/deliverables:")
    for d in deliverables:
        st.write(f"- {d.get('name','Unnamed')}")

with st.expander("Pending Tasks"):
    st.write(f"Total Pending Tasks: {total_pending_tasks}")
    if approval_tasks:
        for t in approval_tasks:
            st.markdown(
                f"- [{t['task_name']} (Stage: {t['stage']})]({t['bundle_link']})",
                unsafe_allow_html=True
            )
    else:
        st.write("No pending tasks")

with st.expander("Registered Models"):
    st.write(f"Found {total_registered_models} registered models:")
    all_model_names = sorted(m.get("name","Unnamed Model") for m in models)
    for mn in all_model_names:
        st.write(f"- {mn}")

with st.expander("Models in a Bundle"):
    st.write(f"Found {total_models_in_bundles} distinct (model, version) references in bundles:")
    grouped = defaultdict(list)
    for (m_name, m_ver) in model_name_version_in_bundles:
        grouped[m_name].append(m_ver)
    for k, v in grouped.items():
        st.write(f"- **{k}** => Versions: {', '.join(str(x) for x in v)}")

with st.expander("All Projects"):
    st.write(f"Found {total_projects} total projects:")
    # We can just list project_map values
    for pid, p_obj in project_map.items():
        st.write(f"- {p_obj.get('name','Unnamed')} (id={pid})")

with st.expander("Projects w/ Bundle"):
    st.write(f"Found {projects_with_a_bundle} projects that contain at least one deliverable.")
    for pid in sorted(project_ids_with_bundles):
        if pid in project_map:
            p_obj = project_map[pid]
            st.write(f"- {p_obj.get('name','Unnamed')} (id={pid})")
        else:
            st.write(f"- Unknown project (id={pid})")

# ----------------------------------------------------
#  POLICIES ADOPTION SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Policies Adoption")
policies = {
    d.get("policyId"): d.get("policyName") for d in deliverables if d.get("policyId")
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

# ----------------------------------------------------
#  GOVERNED BUNDLES DETAILS (TABLE)
# ----------------------------------------------------
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
    b_name = bundle.get("name", "Unnamed Bundle")
    status = bundle.get("state", "Unknown")
    pol_name = bundle.get("policyName", "Unknown")
    stage = bundle.get("stage", "Unknown")
    project_name = bundle.get("projectName", "Unnamed Project")
    project_owner = bundle.get("projectOwner", "unknown_user")

    encoded_project_name = urllib.parse.quote(project_name, safe="")
    bundle_link = f"{API_HOST}/u/{project_owner}/{encoded_project_name}/overview"

    # Make the bundle name clickable
    bundle_html = f'<a href="{bundle_link}" target="_blank">{b_name}</a>'

    # Collect tasks
    related_tasks = [t for t in approval_tasks if t["bundle_name"] == b_name]
    if related_tasks:
        tasks_bullets = []
        for t in related_tasks:
            t_name = t["task_name"]
            t_stage = t["stage"]
            t_link = t["bundle_link"]
            tasks_bullets.append(f'<li><a href="{t_link}" target="_blank">{t_name}, Stage: {t_stage}</a></li>')
        tasks_html = f"<ul>{''.join(tasks_bullets)}</ul>"
    else:
        tasks_html = "No tasks"

    # ModelVersion targets
    model_versions = []
    for tgt in bundle.get("targets", []):
        if tgt.get("type") == "ModelVersion":
            identifier = tgt.get("identifier", {})
            m_name = identifier.get("name", "Unknown Model")
            m_version = identifier.get("version", "Unknown Version")
            created_by = tgt.get("createdBy", {}).get("userName", "unknown_user")

            enc_m_name = urllib.parse.quote(m_name, safe="")
            m_link = (
                f"{API_HOST}/u/{created_by}/{encoded_project_name}"
                f"/model-registry/{enc_m_name}/model-card?version={m_version}"
            )
            model_versions.append(
                f'<li>{m_name} (Version: {m_version}) '
                f'— <a href="{m_link}" target="_blank">View Model Card</a></li>'
            )

    if model_versions:
        model_versions_html = f"<ul>{''.join(model_versions)}</ul>"
    else:
        model_versions_html = "No ModelVersion targets found"

    table_rows.append({
        "Bundle": bundle_html,
        "Status": status,
        "Policy Name": pol_name,
        "Stage": stage,
        "Tasks": tasks_html,
        "Model Versions": model_versions_html
    })

df_bundles = pd.DataFrame(table_rows)
st.write(df_bundles.to_html(escape=False), unsafe_allow_html=True)

# ----------------------------------------------------
#  REGISTERED MODELS TABLE
# ----------------------------------------------------
if models:
    st.header("Registered Models")
    st.write(f"Total Registered Models: {len(models)}")

    # Build a dictionary: model_name -> list of (bundle_name, bundle_link)
    model_to_bundles = defaultdict(list)
    for bundle in governed_bundles:
        b_name = bundle.get("name", "Unnamed Bundle")
        p_owner = bundle.get("projectOwner", "unknown_user")
        p_name = bundle.get("projectName", "Unnamed Project")
        b_link = f"{API_HOST}/u/{p_owner}/{p_name}/overview"

        for tgt in bundle.get("targets", []):
            if tgt.get("type") == "ModelVersion":
                identifier = tgt.get("identifier", {})
                target_m_name = identifier.get("name")
                if target_m_name:
                    model_to_bundles[target_m_name].append((b_name, b_link))

    model_rows = []
    for model_item in models:
        m_name = model_item.get("name", "Unnamed Model")
        project_name = model_item.get("project", {}).get("name", "Unknown Project")
        owner_username = model_item.get("ownerUsername", "Unknown Owner")

        enc_project_name = urllib.parse.quote(project_name, safe="")
        enc_m_name = urllib.parse.quote(m_name, safe="")

        # Link to Domino Model Registry
        model_registry_url = (
            f"{API_HOST}/u/{owner_username}/{enc_project_name}"
            f"/model-registry/{enc_m_name}"
        )
        model_name_html = f'<a href="{model_registry_url}" target="_blank">{m_name}</a>'

        # Bundles bullet list
        if m_name in model_to_bundles:
            bullets = []
            for (bn, bn_link) in model_to_bundles[m_name]:
                safe_bn = bn.replace("<", "&lt;").replace(">", "&gt;")
                bullets.append(f'<li><a href="{bn_link}" target="_blank">{safe_bn}</a></li>')
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