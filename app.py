import streamlit as st
import requests
import os
import plotly.express as px
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
#   SIDEBAR NAVIGATION & GLOBAL FILTERS
# ----------------------------------------------------
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Detailed Metrics](#detailed-metrics)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details-table)", unsafe_allow_html=True)
st.sidebar.markdown("[Registered Models](#registered-models)", unsafe_allow_html=True)
st.sidebar.markdown("[Bundles by Project](#bundles-by-project)", unsafe_allow_html=True)

# Section visibility options
st.sidebar.header("Show/Hide Sections")
show_summary = st.sidebar.checkbox("Show Summary", value=True)
show_detailed = st.sidebar.checkbox("Show Detailed Metrics", value=True)
show_policies_adoption = st.sidebar.checkbox("Show Policies Adoption", value=True)
show_governed = st.sidebar.checkbox("Show Governed Bundles Details", value=True)
show_models = st.sidebar.checkbox("Show Registered Models", value=True)
show_bundles_proj = st.sidebar.checkbox("Show Bundles by Project", value=True)

# Global Filters (multi-select)
st.sidebar.header("Global Filters")
# We'll fill the options later once data is fetched
selected_policies = st.sidebar.multiselect("Select Policy", options=[], default=[])
selected_projects = st.sidebar.multiselect("Select Project", options=[], default=[])
selected_status = st.sidebar.multiselect("Select Bundle Status", options=[], default=[])

# Optional debug checkbox
show_debug = st.sidebar.checkbox("Show Bundle Debug Info", value=False)

# ----------------------------------------------------
#   REFRESH BUTTON TO CLEAR CACHE
# ----------------------------------------------------
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# ----------------------------------------------------
#   CONSOLIDATED API CALL HELPER
# ----------------------------------------------------
def api_call(method, endpoint, params=None, json=None):
    headers = {"X-Domino-Api-Key": API_KEY}
    url = f"{API_HOST}{endpoint}"
    response = requests.request(method, url, headers=headers, params=params, json=json)
    return response

# ----------------------------------------------------
#   HELPER FUNCTIONS (USING api_call)
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
            st.error(f"Error fetching tasks for project {project_id}: {response.status_code}")
            return []
        tasks_data = response.json()
        if "goals" not in tasks_data:
            st.error(f"Unexpected tasks structure for project {project_id}: {tasks_data}")
            return []
        all_goals = tasks_data["goals"]
        active_goals = [g for g in all_goals if g.get("status") != "Completed"]
        return active_goals
    except Exception as e:
        st.error(f"An error occurred while fetching tasks for project {project_id}: {e}")
        return []

@st.cache_data
def fetch_policy_details(policy_id):
    try:
        response = api_call("GET", f"/api/governance/v1/policies/{policy_id}")
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
        response = api_call("GET", "/api/registeredmodels/v1")
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

def plot_policy_stages_interactive(policy_name, stages, bundle_data):
    """Create a horizontal bar chart using Plotly for interactive exploration."""
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]
    df = pd.DataFrame({
        "Stage": stage_names,
        "Number of Bundles": bundle_counts
    })
    fig = px.bar(df, x="Number of Bundles", y="Stage", orientation="h", 
                 title=f"Policy Adoption: {policy_name}",
                 labels={"Number of Bundles": "Count", "Stage": "Stage"})
    fig.update_layout(title_font_size=14, xaxis_title_font_size=12, yaxis_title_font_size=12)
    return fig

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

def debug_bundle(bundle, bundle_name="Bundle JSON"):
    with st.expander(f"Debug: {bundle_name}"):
        st.json(bundle)

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

# ----------------------------------------------------
#   FETCH DATA & BUILD MAPPINGS
# ----------------------------------------------------
all_projects = fetch_all_projects()
bundles = fetch_bundles()
models = fetch_registered_models()

# Build a project map
project_map = {}
for proj in all_projects:
    pid = proj.get("id")
    if pid:
        project_map[pid] = proj

# Annotate bundles with project data
for b in bundles:
    pid = b.get("projectId")
    if pid in project_map:
        p_obj = project_map[pid]
        b["projectName"] = p_obj.get("name", "Unnamed Project")
        b["projectOwner"] = p_obj.get("ownerUsername", "unknown_user")
    else:
        b["projectName"] = "UNKNOWN"
        b["projectOwner"] = "unknown_user"

if not bundles:
    st.warning("No bundles found or an error occurred.")
    st.stop()

# Build policy info mapping
policy_info = {}
for b in bundles:
    pol_id = b.get("policyId")
    if pol_id and pol_id not in policy_info:
        policy_info[pol_id] = (b.get("policyName", "No Policy Name"), b.get("projectOwner", "unknown_user"), b.get("projectName", "UNKNOWN"))

# Build global options for filters
all_policy_options = sorted({b.get("policyName") for b in bundles if b.get("policyName")})
all_project_options = sorted({b.get("projectName") for b in bundles if b.get("projectName")})
all_status_options = sorted({b.get("state", "Unknown") for b in bundles})

# Update sidebar filter options if they are empty
if not selected_policies:
    selected_policies = all_policy_options.copy()
if not selected_projects:
    selected_projects = all_project_options.copy()
if not selected_status:
    selected_status = all_status_options.copy()

# Helper: Filter bundles based on global filters
def get_filtered_bundles():
    filtered = []
    for b in bundles:
        if b.get("policyName") not in selected_policies:
            continue
        if b.get("projectName") not in selected_projects:
            continue
        if b.get("state", "Unknown") not in selected_status:
            continue
        filtered.append(b)
    return filtered

filtered_bundles = get_filtered_bundles()

# ----------------------------------------------------
#   COMPUTE FILTERED METRICS (for Summary)
# ----------------------------------------------------
filtered_policy_names = {b.get("policyName") for b in filtered_bundles if b.get("policyName")}
filtered_total_policies = len(filtered_policy_names)
filtered_total_bundles = len(filtered_bundles)

filtered_bundle_names = {b["name"] for b in filtered_bundles}
filtered_approval_tasks = []
for b in filtered_bundles:
    project_id = b.get("projectId")
    if not project_id or project_id == "unknown_project_id":
        continue
    tasks = fetch_tasks_for_project(project_id)
    for t in tasks:
        if isinstance(t, dict):
            desc = t.get("description", "")
            if "Approval requested Stage" in desc:
                b_name, b_link = parse_task_description(desc)
                if b_name and b_link and b_name in filtered_bundle_names:
                    filtered_approval_tasks.append({
                        "task_name": t.get("title", "Unnamed Task"),
                        "stage": desc.split("Stage")[1].split(":")[0].strip(),
                        "bundle_name": b_name,
                        "bundle_link": b_link,
                    })
filtered_pending_tasks = len(filtered_approval_tasks)

filtered_model_name_version = set()
for b in filtered_bundles:
    for att in b.get("attachments", []):
        if att.get("type") == "ModelVersion":
            identifier = att.get("identifier", {})
            m_name = identifier.get("name")
            m_ver = identifier.get("version")
            if m_name and m_ver:
                filtered_model_name_version.add((m_name, m_ver))
filtered_models_in_bundles_count = len(filtered_model_name_version)

filtered_project_names = {b.get("projectName") for b in filtered_bundles}
filtered_projects_with_bundles_count = len(filtered_project_names)

filtered_total_projects = len({p_obj.get("name", "Unnamed Project") for p_obj in project_map.values() if p_obj.get("name") in selected_projects})

# For registered models, filter by project using the filtered bundle attachments
filtered_model_names = set()
all_filtered_model_names = {x for x, _ in filtered_model_name_version}
for m in models:
    m_name = m.get("name", "")
    p_name = m.get("project", {}).get("name", "")
    if p_name in selected_projects and (selected_policies == all_policy_options or m_name in all_filtered_model_names):
        filtered_model_names.add(m_name)
filtered_registered_models_count = len(filtered_model_names)

# ----------------------------------------------------
#   SUMMARY SECTION (with Export Option)
# ----------------------------------------------------
if show_summary:
    st.markdown("---")
    st.header("Summary")
    st.markdown('<a id="summary"></a>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Total Policies", filtered_total_policies)
    col1.markdown('[View All Policies](#detailed-metrics)', unsafe_allow_html=True)
    
    col2.metric("Total Bundles", filtered_total_bundles)
    col2.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    col3.metric("Pending Tasks", filtered_pending_tasks)
    col3.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    col4.metric("Registered Models", filtered_registered_models_count)
    col4.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    col5.metric("Models in a Bundle", filtered_models_in_bundles_count)
    col5.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    col6.metric("Total Projects", filtered_total_projects)
    col6.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    col7.metric("Projects w/ Bundle", filtered_projects_with_bundles_count)
    col7.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
    
    # Alert if pending tasks are high (e.g., >5)
    if filtered_pending_tasks > 5:
        st.warning("High number of pending tasks!")

    # Export filtered summary as CSV (example: exporting filtered bundles)
    csv_summary = pd.DataFrame({
        "Metric": ["Total Policies", "Total Bundles", "Pending Tasks", "Registered Models", "Models in a Bundle", "Total Projects", "Projects w/ Bundle"],
        "Value": [filtered_total_policies, filtered_total_bundles, filtered_pending_tasks, filtered_registered_models_count, filtered_models_in_bundles_count, filtered_total_projects, filtered_projects_with_bundles_count]
    })
    st.download_button("Download Summary CSV", csv_summary.to_csv(index=False), "summary.csv", "text/csv")

# ----------------------------------------------------
#   DETAILED METRICS SECTION (Interactive Tables)
# ----------------------------------------------------
if show_detailed:
    st.markdown("---")
    st.markdown("## Detailed Metrics")
    st.markdown('<a id="detailed-metrics"></a>', unsafe_allow_html=True)
    
    with st.expander("All Policies"):
        st.write(f"Found {len(policy_info)} policy IDs (unfiltered). Direct links:")
        for pol_id, (pol_name, owner, proj) in sorted(policy_info.items(), key=lambda x: x[1][0]):
            link = build_domino_link(owner=owner, project_name=proj, artifact="policy", policy_id=pol_id)
            st.markdown(f"- <a href='{link}' target='_blank'>{pol_name}</a>", unsafe_allow_html=True)
    
    with st.expander("All Bundles"):
        st.write(f"Found {len(bundles)} total bundles (unfiltered). Direct links:")
        for b in bundles:
            owner = b.get("projectOwner", "unknown_user")
            proj = b.get("projectName", "UNKNOWN")
            link = build_domino_link(owner=owner, project_name=proj, artifact="bundleEvidence", bundle_id=b.get("id", ""), policy_id=b.get("policyId", ""))
            name = b.get('name', 'Unnamed')
            st.markdown(f"- <a href='{link}' target='_blank'>{name}</a>", unsafe_allow_html=True)
    
    with st.expander("Pending Tasks"):
        st.write(f"Found {filtered_pending_tasks} pending tasks (filtered).")
        if filtered_approval_tasks:
            for t in filtered_approval_tasks:
                st.markdown(f"- <a href='{t['bundle_link']}' target='_blank'>{t['task_name']} (Stage: {t['stage']})</a>", unsafe_allow_html=True)
        else:
            st.write("None")
    
    with st.expander("Registered Models"):
        st.write(f"Found {filtered_registered_models_count} registered models (filtered).")
        if filtered_model_names:
            for mn in sorted(filtered_model_names):
                matched = [m for m in models if m.get("name") == mn]
                if matched:
                    first_match = matched[0]
                    p_name = first_match.get("project", {}).get("name", "")
                    owner = first_match.get("ownerUsername", "unknown_owner")
                    link = build_domino_link(owner=owner, project_name=p_name, artifact="model-registry", model_name=mn)
                    st.markdown(f"- <a href='{link}' target='_blank'>{mn}</a> (Project: {p_name})", unsafe_allow_html=True)
                else:
                    st.write(f"- {mn}")
        else:
            st.write("None in this filter")
    
    with st.expander("Models in a Bundle"):
        st.write(f"Found {filtered_models_in_bundles_count} distinct (model, version) references (filtered).")
        if filtered_models_in_bundles_count > 0:
            group_map = defaultdict(list)
            for (m_name, m_ver) in filtered_model_name_version:
                group_map[m_name].append(m_ver)
            for mod_name, versions in group_map.items():
                st.write(f"- **{mod_name}** => Versions: {', '.join(str(v) for v in versions)}")
        else:
            st.write("None")
    
    with st.expander("All Projects"):
        st.write(f"Found {len(all_projects)} total projects (unfiltered).")
        for pid, p_obj in project_map.items():
            proj_name = p_obj.get('name', 'Unnamed')
            owner = p_obj.get('ownerUsername', 'unknown_user')
            link = build_domino_link(owner=owner, project_name=proj_name, artifact="overview")
            st.markdown(f"- <a href='{link}' target='_blank'>{proj_name}</a>", unsafe_allow_html=True)

# ----------------------------------------------------
#   POLICIES ADOPTION SECTION (Interactive Plotly Chart)
# ----------------------------------------------------
if show_policies_adoption:
    st.markdown("---")
    st.header("Policies Adoption")
    st.markdown('<a id="policies-adoption"></a>', unsafe_allow_html=True)
    
    policies_dict = { b.get("policyId"): b.get("policyName") for b in bundles if b.get("policyId") }
    if policies_dict:
        for policy_id, policy_name in policies_dict.items():
            if policy_name not in selected_policies:
                continue
            st.subheader(f"Policy: {policy_name}")
            policy_details = fetch_policy_details(policy_id)
            if policy_details:
                stages = policy_details.get("stages", [])
                if stages:
                    stage_map = defaultdict(list)
                    for fb in filtered_bundles:
                        if fb.get("policyId") == policy_id:
                            stg = fb.get("stage", "Unknown Stage")
                            stage_map[stg].append(fb)
                    fig = plot_policy_stages_interactive(policy_name, stages, stage_map)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    for stage_name, items in stage_map.items():
                        st.write(f"- **Stage: {stage_name}** ({len(items)})")
                        with st.expander(f"View Bundles in {stage_name}"):
                            for one_b in items:
                                owner = one_b.get("projectOwner", "unknown_user")
                                proj = one_b.get("projectName", "UNKNOWN")
                                link = build_domino_link(
                                    owner=owner,
                                    project_name=proj,
                                    artifact="bundleEvidence",
                                    bundle_id=one_b.get("id", ""),
                                    policy_id=one_b.get("policyId", "")
                                )
                                st.markdown(
                                    f"- <a href='{link}' target='_blank'>{one_b.get('name', 'Unnamed Bundle')}</a> (Moved: {one_b.get('stageUpdateTime', 'N/A')})",
                                    unsafe_allow_html=True
                                )
                else:
                    st.warning(f"No stages found for policy {policy_name}")
            else:
                st.error(f"Could not fetch policy details for {policy_name}")
    else:
        st.info("No policies found.")

# ----------------------------------------------------
#   GOVERNED BUNDLES DETAILS SECTION (Interactive DataFrame)
# ----------------------------------------------------
if show_governed:
    st.markdown("---")
    st.header("Governed Bundles Details (Table)")
    st.markdown('<a id="governed-bundles-details-table"></a>', unsafe_allow_html=True)
    
    governed_filtered_bundles = [
        b for b in filtered_bundles if b.get("policyName")
    ]
    governed_filtered_bundles = sorted(
        governed_filtered_bundles,
        key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in filtered_approval_tasks),
        reverse=True
    )
    
    if show_debug:
        st.subheader("Bundles Debug Info")
        for i, bundle in enumerate(governed_filtered_bundles, start=1):
            st.markdown(f"**Bundle #{i}:**")
            st.write(f"- **ID:** {bundle.get('id')}")
            st.write(f"- **Name:** {bundle.get('name')}")
            st.write(f"- **Project Name:** {bundle.get('projectName')}")
            st.write(f"- **Project Owner:** {bundle.get('projectOwner')}")
            st.write(f"- **Policy ID:** {bundle.get('policyId')}")
            st.write(f"- **Policy Name:** {bundle.get('policyName')}")
            st.write(f"- **Stage:** {bundle.get('stage')}")
            st.write(f"- **State:** {bundle.get('state')}")
            st.write("**Full JSON:**")
            st.json(bundle)
    
    table_rows = []
    for bundle in governed_filtered_bundles:
        b_name = bundle.get("name", "Unnamed Bundle")
        b_id = bundle.get("id", "")
        pol_id = bundle.get("policyId", "")
        status = bundle.get("state", "Unknown")
        pol_name = bundle.get("policyName", "Unknown")
        stage = bundle.get("stage", "Unknown")
        
        proj_name = bundle.get("projectName", "UNKNOWN")
        proj_owner = bundle.get("projectOwner", "unknown_user")
        if not proj_owner or proj_owner.lower() == "unknown_user":
            proj_owner = bundle.get("createdBy", {}).get("userName", "unknown_user")
        evidence_link = build_domino_link(owner=proj_owner, project_name=proj_name,
                                          artifact="bundleEvidence", bundle_id=b_id, policy_id=pol_id)
        bundle_html = f'<a href="{evidence_link}" target="_blank">{b_name}</a>'
        policy_link = build_domino_link(owner=proj_owner, project_name=proj_name, artifact="policy", policy_id=pol_id)
        policy_html = f'<a href="{policy_link}" target="_blank">{pol_name}</a>'
        
        rel_tasks = [t for t in filtered_approval_tasks if t["bundle_name"] == b_name]
        if rel_tasks:
            tasks_bullets = []
            for t in rel_tasks:
                tasks_bullets.append(
                    f'<li><a href="{t["bundle_link"]}" target="_blank">'
                    f'{t["task_name"]}, Stage: {t["stage"]}</a></li>'
                )
            tasks_html = f"<ul>{''.join(tasks_bullets)}</ul>"
        else:
            tasks_html = "No tasks"
        
        mv_links = []
        for att in bundle.get("attachments", []):
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
                    f'<li>{m_name} (Version: {m_ver}) — '
                    f'<a href="{mv_link}" target="_blank">View Model Card</a></li>'
                )
        mv_html = f"<ul>{''.join(mv_links)}</ul>" if mv_links else "No ModelVersion attachments found"
    
        table_rows.append({
            "Project": proj_name,
            "Bundle": bundle_html,
            "Status": status,
            "Policy": policy_html,
            "Stage": stage,
            "Tasks": tasks_html,
            "Model Versions": mv_html
        })
    
    df_bundles_table = pd.DataFrame(table_rows)
    st.dataframe(df_bundles_table, use_container_width=True)
    st.download_button("Download Governed Bundles CSV", df_bundles_table.to_csv(index=False), "governed_bundles.csv", "text/csv")

# ----------------------------------------------------
#   REGISTERED MODELS SECTION (Interactive DataFrame)
# ----------------------------------------------------
if show_models:
    st.markdown("---")
    st.header("Registered Models")
    st.markdown('<a id="registered-models"></a>', unsafe_allow_html=True)
    
    model_rows = []
    for m in models:
        mod_name = m.get("name", "Unnamed Model")
        if mod_name not in filtered_model_names:
            continue
        p_name = m.get("project", {}).get("name", "Unknown Project")
        owner = m.get("ownerUsername", "Unknown Owner")
        model_registry_url = build_domino_link(owner=owner, project_name=p_name,
                                               artifact="model-registry", model_name=mod_name)
        model_name_html = f'<a href="{model_registry_url}" target="_blank">{mod_name}</a>'
        model_rows.append({
            "Name": model_name_html,
            "Project": p_name,
            "Owner": owner
        })
    if model_rows:
        df_models = pd.DataFrame(model_rows)
        st.dataframe(df_models, use_container_width=True)
        st.download_button("Download Registered Models CSV", df_models.to_csv(index=False), "registered_models.csv", "text/csv")
    else:
        st.write("No registered models match the current filters.")

# ----------------------------------------------------
#   BUNDLES BY PROJECT SECTION (Interactive DataFrame)
# ----------------------------------------------------
if show_bundles_proj:
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
        link = build_domino_link(owner=owner, project_name=proj,
                                 artifact="bundleEvidence", bundle_id=b.get("id", ""),
                                 policy_id=b.get("policyId", ""))
        link_html = f'<a href="{link}" target="_blank">View</a>'
        bundle_rows.append({
             "Project": proj,
             "Bundle Name": bundle_name,
             "State": state,
             "Policy": policy,
             "Stage": stage,
             "Link": link_html
        })
    if bundle_rows:
        df_bundles_project = pd.DataFrame(bundle_rows)
        st.dataframe(df_bundles_project, use_container_width=True)
        st.download_button("Download Bundles by Project CSV", df_bundles_project.to_csv(index=False), "bundles_by_project.csv", "text/csv")
    else:
        st.write("No bundles match the current filters.")