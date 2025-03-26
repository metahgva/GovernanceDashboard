import streamlit as st
import requests
import os
import matplotlib.pyplot as plt
import urllib.parse
import pandas as pd
import re
from collections import defaultdict

# ----------------------------------------------------
#   PAGE CONFIGURATION & CUSTOM CSS
# ----------------------------------------------------
st.set_page_config(page_title="Bundles and Projects Dashboard", layout="wide")

st.markdown(
    """
    <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background-color: #f5f5f5;
    }
    .reportview-container .main .block-container {
      padding-top: 2rem;
      padding-bottom: 2rem;
    }
    .stMetric {
      font-size: 1.5rem;
      font-weight: bold;
    }
    .css-1d391kg, .css-18e3th9 {
      background-color: #fff;
      border-radius: 10px;
      box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
      padding: 1rem;
    }
    h1, h2, h3 {
      color: #333;
    }
    a {
      color: #1a73e8;
      text-decoration: none;
      font-weight: 500;
    }
    a:hover {
      text-decoration: underline;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
#   ENV CONFIG & CONSTANTS
# ----------------------------------------------------
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

st.title("Bundles and Projects Dashboard")

# ----------------------------------------------------
#   SIDEBAR NAVIGATION
# ----------------------------------------------------
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Detailed Metrics](#detailed-metrics)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details-table)", unsafe_allow_html=True)
st.sidebar.markdown("[Registered Models](#registered-models)", unsafe_allow_html=True)
st.sidebar.markdown("[Bundles by Project](#bundles-by-project)", unsafe_allow_html=True)

# Optional debug checkbox
show_debug = st.sidebar.checkbox("Show Bundle Debug Info", value=False)

# ----------------------------------------------------
#   REFRESH BUTTON TO CLEAR CACHE
# ----------------------------------------------------
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# ----------------------------------------------------
#   API CALL HELPER
# ----------------------------------------------------
def api_call(method, endpoint, params=None, json=None):
    headers = {"X-Domino-Api-Key": API_KEY}
    url = f"{API_HOST}{endpoint}"
    response = requests.request(method, url, headers=headers, params=params, json=json)
    return response

# ----------------------------------------------------
#   FETCH FUNCTIONS
# ----------------------------------------------------
@st.cache_data
def fetch_bundles():
    try:
        response = api_call("GET", "/api/governance/v1/bundles")
        if response.status_code != 200:
            st.error(f"Error fetching bundles: {response.status_code} - {response.text}")
            return []
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An error occurred while fetching bundles: {e}")
        return []

@st.cache_data
def fetch_all_projects():
    try:
        response = api_call("GET", "/v4/projects")
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
        response = api_call("GET", f"/api/projects/v1/projects/{project_id}/goals")
        if response.status_code != 200:
            return []
        tasks_data = response.json()
        if "goals" not in tasks_data:
            return []
        all_goals = tasks_data["goals"]
        active_goals = [g for g in all_goals if g.get("status") != "Completed"]
        return active_goals
    except Exception as e:
        return []

@st.cache_data
def fetch_policy_details(policy_id):
    try:
        response = api_call("GET", f"/api/governance/v1/policies/{policy_id}")
        if response.status_code != 200:
            return None
        return response.json()
    except Exception as e:
        return None

@st.cache_data
def fetch_registered_models():
    try:
        response = api_call("GET", "/api/registeredmodels/v1")
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# ----------------------------------------------------
#   UTILITY FUNCTIONS
# ----------------------------------------------------
def build_domino_link(owner: str, project_name: str, artifact: str = "overview",
                      model_name: str = "", version: str = "",
                      bundle_id: str = "", policy_id: str = "") -> str:
    base = API_HOST.rstrip("/")
    enc_owner = owner
    enc_project = urllib.parse.quote(project_name, safe="")
    if artifact == "overview":
        return f"{base}/u/{enc_owner}/{enc_project}/overview"
    elif artifact == "model-registry":
        enc_model = urllib.parse.quote(model_name, safe="")
        return f"{base}/u/{enc_owner}/{enc_project}/model-registry/{enc_model}"
    elif artifact == "model-card":
        enc_model = urllib.parse.quote(model_name, safe="")
        return f"{base}/u/{enc_owner}/{enc_project}/model-registry/{enc_model}/model-card?version={version}"
    elif artifact == "bundleEvidence":
        return f"{base}/u/{enc_owner}/{enc_project}/governance/bundle/{bundle_id}/policy/{policy_id}/evidence"
    elif artifact == "policy":
        return f"{base}/u/{enc_owner}/{enc_project}/governance/policy/{policy_id}"
    return f"{base}/u/{enc_owner}/{enc_project}/overview"

def parse_task_description(description):
    try:
        start = description.find("[")
        end = description.find("]")
        bundle_name = description[start + 1 : end]
        link_start = description.find("(")
        link_end = description.find(")")
        bundle_link = description[link_start + 1 : link_end]
        bundle_link = f"{API_HOST}{bundle_link}"
        return bundle_name, bundle_link
    except Exception:
        return None, None

def plot_policy_stages(policy_name, stages, bundle_data):
    """
    Horizontal bar chart for policy stages.
    """
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    # Reverse so the first stage is at the top
    stage_names_rev = stage_names[::-1]
    bundle_counts_rev = bundle_counts[::-1]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(stage_names_rev, bundle_counts_rev, color="skyblue", edgecolor="black")
    ax.set_title(f"Policy: {policy_name}", fontsize=14)
    ax.set_xlabel("Number of Bundles", fontsize=12)
    ax.set_ylabel("Stages", fontsize=12)
    plt.tight_layout()
    return fig

def debug_bundle(bundle, bundle_name="Bundle JSON"):
    with st.expander(f"Debug: {bundle_name}"):
        st.json(bundle)

# ----------------------------------------------------
#   FETCH DATA
# ----------------------------------------------------
all_projects = fetch_all_projects()
bundles = fetch_bundles()
models = fetch_registered_models()

# Build a map of projectId -> project data
project_map = {}
for proj in all_projects:
    pid = proj.get("id")
    if pid:
        project_map[pid] = proj

# Annotate each bundle with project info
for b in bundles:
    pid = b.get("projectId")
    if pid in project_map:
        p_obj = project_map[pid]
        b["projectName"] = p_obj.get("name", "Unnamed Project")
        b["projectOwner"] = p_obj.get("ownerUsername", "unknown_user")
    else:
        b["projectName"] = "UNKNOWN"
        b["projectOwner"] = "unknown_user"

# If no bundles, stop
if not bundles:
    st.warning("No bundles found or an error occurred.")
    st.stop()

# ----------------------------------------------------
#   Derive Additional Data
# ----------------------------------------------------
policy_info = {}
for b in bundles:
    pol_id = b.get("policyId")
    if pol_id and pol_id not in policy_info:
        policy_info[pol_id] = (
            b.get("policyName", "No Policy Name"),
            b.get("projectOwner", "unknown_user"),
            b.get("projectName", "UNKNOWN"),
        )

# Gather tasks across all bundles
approval_tasks = []
for b in bundles:
    project_id = b.get("projectId")
    if not project_id:
        continue
    tasks = fetch_tasks_for_project(project_id)
    for t in tasks:
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

# ----------------------------------------------------
#   GLOBAL FILTERS
# ----------------------------------------------------
st.sidebar.header("Global Filters")
all_policy_names = sorted({p[0] for p in policy_info.values()})
selected_policy = st.sidebar.selectbox("Select Policy", options=["All"] + all_policy_names)

all_project_names = sorted({p.get("name", "Unnamed Project") for p in project_map.values()})
selected_project = st.sidebar.selectbox("Select Project", options=["All"] + all_project_names)

def filter_data(bundles, selected_policy, selected_project):
    """
    Return a subset of bundles matching the global filters (policy, project).
    """
    filtered = []
    for b in bundles:
        p_name = b.get("projectName", "UNKNOWN")
        pol_name = b.get("policyName", "None")
        if (selected_policy == "All" or pol_name == selected_policy) and \
           (selected_project == "All" or p_name == selected_project):
            filtered.append(b)
    return filtered

def filter_tasks(tasks, filtered_bundle_names):
    """
    Return only tasks that belong to the filtered bundle names.
    """
    return [t for t in tasks if t["bundle_name"] in filtered_bundle_names]

def filter_models(models, selected_project):
    """
    For now, we only filter by project if we know the model's project name.
    Some models might not have a 'project' field. We'll keep them if 'All' or if project matches.
    """
    if selected_project == "All":
        return models
    filtered = []
    for m in models:
        p_name = m.get("project", {}).get("name", "Unknown Project")
        if p_name == selected_project:
            filtered.append(m)
    return filtered

# ----------------------------------------------------
#   APPLY GLOBAL FILTERS
# ----------------------------------------------------
filtered_bundles = filter_data(bundles, selected_policy, selected_project)
filtered_bundle_names = {b.get("name", "") for b in filtered_bundles}
filtered_tasks = filter_tasks(approval_tasks, filtered_bundle_names)
filtered_models = filter_models(models, selected_project)

# Recalculate summary stats from filtered data
filtered_policies = {b.get("policyName") for b in filtered_bundles if b.get("policyName")}
total_policies = len(filtered_policies)
total_bundles = len(filtered_bundles)
total_pending_tasks = len(filtered_tasks)
total_registered_models = len(filtered_models)

# Models in filtered bundles
model_name_version_in_bundles = set()
for b in filtered_bundles:
    for att in b.get("attachments", []):
        if att.get("type") == "ModelVersion":
            identifier = att.get("identifier", {})
            m_name = identifier.get("name")
            m_ver = identifier.get("version")
            if m_name and m_ver:
                model_name_version_in_bundles.add((m_name, m_ver))
total_models_in_a_bundle = len(model_name_version_in_bundles)

# Filtered projects
filtered_project_ids = {b.get("projectId") for b in filtered_bundles if b.get("projectId")}
total_projects = len(filtered_project_ids)
# Projects w/ a bundle (in the filtered set)
projects_with_a_bundle = len(filtered_project_ids)

# ----------------------------------------------------
#   SUMMARY SECTION (Filtered)
# ----------------------------------------------------
st.markdown("---")
st.header("Summary")
st.markdown('<a id="summary"></a>', unsafe_allow_html=True)

# We'll do two rows of 4 columns each for a cleaner layout
colA1, colA2, colA3, colA4 = st.columns(4)
colA1.metric("Policies", total_policies)
colA2.metric("Bundles", total_bundles)
colA3.metric("Pending Tasks", total_pending_tasks)
colA4.metric("Registered Models", total_registered_models)

colB1, colB2, colB3, colB4 = st.columns(4)
colB1.metric("Models in a Bundle", total_models_in_a_bundle)
colB2.metric("Projects (Filtered)", total_projects)
colB3.metric("Projects w/ Bundle", projects_with_a_bundle)
colB4.markdown("")  # empty space

# ----------------------------------------------------
#   DETAILED METRICS SECTION
# ----------------------------------------------------
st.markdown("---")
st.markdown("## Detailed Metrics")
st.markdown('<a id="detailed-metrics"></a>', unsafe_allow_html=True)

with st.expander("All Policies"):
    # We won't re-filter them here because user might want to see all policies
    all_policy_ids = sorted(policy_info.keys(), key=lambda pid: policy_info[pid][0])
    st.write(f"Found {len(all_policy_ids)} policy names (unfiltered):")
    for pol_id in all_policy_ids:
        pol_name, owner, proj = policy_info[pol_id]
        link = build_domino_link(owner=owner, project_name=proj, artifact="policy", policy_id=pol_id)
        st.markdown(f"- <a href='{link}' target='_blank'>{pol_name}</a>", unsafe_allow_html=True)

with st.expander("All Bundles"):
    # Show only filtered bundles here
    st.write(f"Found {len(filtered_bundles)} bundles (filtered):")
    for b in filtered_bundles:
        owner = b.get("projectOwner", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        link = build_domino_link(owner=owner, project_name=proj, artifact="bundleEvidence",
                                 bundle_id=b.get("id", ""), policy_id=b.get("policyId", ""))
        b_name = b.get('name', 'Unnamed')
        st.markdown(f"- <a href='{link}' target='_blank'>{b_name}</a>", unsafe_allow_html=True)

with st.expander("Pending Tasks"):
    st.write(f"Found {len(filtered_tasks)} pending tasks (filtered):")
    if filtered_tasks:
        for t in filtered_tasks:
            st.markdown(
                f"- <a href='{t['bundle_link']}' target='_blank'>{t['task_name']} (Stage: {t['stage']})</a>",
                unsafe_allow_html=True
            )
    else:
        st.write("None")

with st.expander("Registered Models"):
    # We'll show only the filtered models
    st.write(f"Found {len(filtered_models)} registered models (filtered by project):")
    for m in filtered_models:
        mod_name = m.get("name", "Unnamed Model")
        p_name = m.get("project", {}).get("name", "Unknown Project")
        owner = m.get("ownerUsername", "Unknown Owner")
        model_registry_url = build_domino_link(
            owner=owner, project_name=p_name, artifact="model-registry", model_name=mod_name
        )
        st.markdown(f"- <a href='{model_registry_url}' target='_blank'>{mod_name}</a>", unsafe_allow_html=True)

with st.expander("Models in a Bundle"):
    st.write(f"Found {total_models_in_a_bundle} distinct (model, version) references (filtered):")
    group_map = defaultdict(list)
    for (m_name, m_ver) in model_name_version_in_bundles:
        group_map[m_name].append(m_ver)
    for mod_name, versions in group_map.items():
        st.write(f"- **{mod_name}** => Versions: {', '.join(str(v) for v in versions)}")

with st.expander("All Projects"):
    # Show all or filtered? We'll show them all, but let's add links.
    st.write(f"Found {len(all_projects)} total projects (unfiltered list):")
    for pid, p_obj in project_map.items():
        p_name = p_obj.get("name", "Unnamed Project")
        owner = p_obj.get("ownerUsername", "unknown_user")
        link = build_domino_link(owner=owner, project_name=p_name, artifact="overview")
        st.markdown(f"- <a href='{link}' target='_blank'>{p_name} (id={pid})</a>", unsafe_allow_html=True)

# ----------------------------------------------------
#  POLICIES ADOPTION SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Policies Adoption")
st.markdown('<a id="policies-adoption"></a>', unsafe_allow_html=True)

# We'll gather the distinct policy IDs from *all* bundles (unfiltered)
policies_dict = {b.get("policyId"): b.get("policyName") for b in bundles if b.get("policyId")}

if policies_dict:
    # We'll iterate over them, but skip if they don't match the selected policy (unless 'All')
    for policy_id, policy_name in policies_dict.items():
        if selected_policy != "All" and policy_name != selected_policy:
            continue

        # Build a subset of bundles for this policy that also respect the project filter
        policy_bundles = [b for b in filtered_bundles if b.get("policyId") == policy_id]
        if not policy_bundles:
            # If no bundles for this policy after filtering, skip
            continue

        st.subheader(f"Policy: {policy_name}")
        policy_details = fetch_policy_details(policy_id)
        if policy_details:
            stages = policy_details.get("stages", [])
            if stages:
                # Build stage->list_of_bundles map
                bundle_data_per_stage = defaultdict(list)
                for b in policy_bundles:
                    stage_name = b.get("stage", "Unknown Stage")
                    bundle_data_per_stage[stage_name].append(b)

                fig = plot_policy_stages(policy_name, stages, bundle_data_per_stage)
                st.pyplot(fig)

                # List out each stage's bundles
                for stage_name, items in bundle_data_per_stage.items():
                    st.write(f"- **Stage: {stage_name}** ({len(items)})")
                    with st.expander(f"View Bundles in {stage_name}"):
                        for one_b in items:
                            owner = one_b.get("projectOwner", "unknown_user")
                            proj = one_b.get("projectName", "UNKNOWN")
                            link = build_domino_link(
                                owner=owner, project_name=proj, artifact="bundleEvidence",
                                bundle_id=one_b.get("id", ""), policy_id=one_b.get("policyId", "")
                            )
                            b_name = one_b.get('name', 'Unnamed Bundle')
                            moved_time = one_b.get('stageUpdateTime', 'N/A')
                            st.markdown(
                                f"- <a href='{link}' target='_blank'>{b_name}</a> (Moved: {moved_time})",
                                unsafe_allow_html=True
                            )
            else:
                st.warning(f"No stages found for policy {policy_name}")
        else:
            st.error(f"Could not fetch policy details for {policy_name}")
else:
    st.info("No policies found.")

# ----------------------------------------------------
#  GOVERNED BUNDLES DETAILS SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Governed Bundles Details (Table)")
st.markdown('<a id="governed-bundles-details-table"></a>', unsafe_allow_html=True)

governed_bundles_filtered = [b for b in filtered_bundles if b.get("policyName")]

# Sort them so that those with pending tasks are on top
governed_bundles_filtered.sort(
    key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in filtered_tasks),
    reverse=True
)

if show_debug:
    st.subheader("Bundles Debug Info")
    for i, bundle in enumerate(governed_bundles_filtered, start=1):
        st.markdown(f"**Bundle #{i}:**")
        st.write(f"- **ID:** {bundle.get('id')}")
        st.write(f"- **Name:** {bundle.get('name')}")
        st.write(f"- **Project Name:** {bundle.get('projectName')}")
        st.write(f"- **Project Owner:** {bundle.get('projectOwner')}")
        st.write(f"- **Policy ID:** {bundle.get('policyId')}")
        st.write(f"- **Policy Name:** {bundle.get('policyName')}")
        st.write(f"- **Stage:** {bundle.get('stage')}")
        st.write(f"- **State:** {bundle.get('state')}")
        st.json(bundle)

rows = []
for b in governed_bundles_filtered:
    b_name = b.get("name", "Unnamed Bundle")
    b_id = b.get("id", "")
    pol_id = b.get("policyId", "")
    pol_name = b.get("policyName", "Unknown")
    status = b.get("state", "Unknown")
    stage = b.get("stage", "Unknown")
    proj_name = b.get("projectName", "UNKNOWN")
    proj_owner = b.get("projectOwner", "unknown_user")
    if not proj_owner or proj_owner.lower() == "unknown_user":
        proj_owner = b.get("createdBy", {}).get("userName", "unknown_user")

    # Build links
    evidence_link = build_domino_link(
        owner=proj_owner, project_name=proj_name, artifact="bundleEvidence",
        bundle_id=b_id, policy_id=pol_id
    )
    bundle_html = f'<a href="{evidence_link}" target="_blank">{b_name}</a>'

    policy_link = build_domino_link(
        owner=proj_owner, project_name=proj_name, artifact="policy", policy_id=pol_id
    )
    policy_html = f'<a href="{policy_link}" target="_blank">{pol_name}</a>'

    rel_tasks = [t for t in filtered_tasks if t["bundle_name"] == b_name]
    if rel_tasks:
        tasks_bullets = [
            f'<li><a href="{t["bundle_link"]}" target="_blank">'
            f'{t["task_name"]}, Stage: {t["stage"]}</a></li>'
            for t in rel_tasks
        ]
        tasks_html = f"<ul>{''.join(tasks_bullets)}</ul>"
    else:
        tasks_html = "No tasks"

    # Gather model attachments
    mv_links = []
    for att in b.get("attachments", []):
        if att.get("type") == "ModelVersion":
            ident = att.get("identifier", {})
            m_name = ident.get("name", "Unknown Model")
            m_ver = ident.get("version", "Unknown Version")
            created_by = att.get("createdBy", {}).get("userName", "unknown_user")
            mv_link = build_domino_link(
                owner=created_by, project_name=proj_name,
                artifact="model-card", model_name=m_name, version=m_ver
            )
            mv_links.append(
                f'<li>{m_name} (Version: {m_ver}) '
                f'— <a href="{mv_link}" target="_blank">View Model Card</a></li>'
            )
    mv_html = f"<ul>{''.join(mv_links)}</ul>" if mv_links else "No ModelVersion attachments found"

    rows.append({
        "Project": proj_name,
        "Bundle": bundle_html,
        "Status": status,
        "Policy": policy_html,
        "Stage": stage,
        "Tasks": tasks_html,
        "Model Versions": mv_html
    })

df_governed = pd.DataFrame(rows)
st.write(df_governed.to_html(escape=False), unsafe_allow_html=True)

# ----------------------------------------------------
#  REGISTERED MODELS SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Registered Models")
st.markdown('<a id="registered-models"></a>', unsafe_allow_html=True)

model_rows = []
for m in filtered_models:
    mod_name = m.get("name", "Unnamed Model")
    p_name = m.get("project", {}).get("name", "Unknown Project")
    owner = m.get("ownerUsername", "Unknown Owner")
    model_registry_url = build_domino_link(owner=owner, project_name=p_name, artifact="model-registry", model_name=mod_name)
    model_name_html = f'<a href="{model_registry_url}" target="_blank">{mod_name}</a>'
    model_rows.append({
        "Name": model_name_html,
        "Project": p_name,
        "Owner": owner
    })

df_models = pd.DataFrame(model_rows)
st.write(df_models.to_html(escape=False, index=False), unsafe_allow_html=True)

# ----------------------------------------------------
#  BUNDLES BY PROJECT SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Bundles by Project")
st.markdown('<a id="bundles-by-project"></a>', unsafe_allow_html=True)

bundle_rows = []
for b in filtered_bundles:
    proj = b.get("projectName", "UNKNOWN")
    bundle_name = b.get("name", "Unnamed Bundle")
    state = b.get("state", "Unknown")
    policy = b.get("policyName", "None")
    stage = b.get("stage", "Unknown")
    owner = b.get("projectOwner", "unknown_user")
    link = build_domino_link(owner=owner, project_name=proj, artifact="bundleEvidence", 
                             bundle_id=b.get("id", ""), policy_id=b.get("policyId", ""))
    link_html = f'<a href="{link}" target="_blank">View</a>'
    bundle_rows.append({
         "Project": proj,
         "Bundle Name": bundle_name,
         "State": state,
         "Policy": policy,
         "Stage": stage,
         "Link": link_html
    })

df_bundles_project = pd.DataFrame(bundle_rows)
st.write(df_bundles_project.to_html(escape=False, index=False), unsafe_allow_html=True)