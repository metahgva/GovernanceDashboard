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

st.title("Bundles and Projects Dashboard")

# ----------------------------------------------------
#   SIDEBAR NAVIGATION
# ----------------------------------------------------
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Detailed Metrics](#detailed-metrics)", unsafe_allow_html=True)
st.sidebar.markdown("[Policies Adoption](#policies-adoption)", unsafe_allow_html=True)
st.sidebar.markdown("[Projects Without Bundles](#projects-without-bundles)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details-table)", unsafe_allow_html=True)
st.sidebar.markdown("[Registered Models](#registered-models)", unsafe_allow_html=True)

# Sidebar API Configuration (hide API key)
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
st.sidebar.write("API Key: Configured")
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

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
    """
    Constructs the full URL from API_HOST, sets the required header,
    and makes an API request.
    """
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
    """
    Centralized helper to build Domino links.
    Added 'policy' artifact to link directly to a policy details page.
    """
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
        # Link to a policy details page (assuming this route exists)
        return f"{base}/u/{enc_owner}/{enc_project}/governance/policy/{policy_id}"
    return f"{base}/u/{enc_owner}/{enc_project}/overview"

# ----------------------------------------------------
#   FETCH DATA
# ----------------------------------------------------
all_projects = fetch_all_projects()
bundles = fetch_bundles()
models = fetch_registered_models()

# ----------------------------------------------------
#   BUILD A PROJECT MAP & ANNOTATE BUNDLES
# ----------------------------------------------------
project_map = {}
for proj in all_projects:
    pid = proj.get("id")
    if pid:
        project_map[pid] = proj

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

# ----------------------------------------------------
#   PRE-COMPUTE SUMMARY DATA
# ----------------------------------------------------
# Build a dictionary mapping policy_id -> (policy_name, owner, project) from the first bundle that has it.
policy_info = {}
for b in bundles:
    pol_id = b.get("policyId")
    if pol_id and pol_id not in policy_info:
        policy_info[pol_id] = (b.get("policyName", "No Policy Name"), b.get("projectOwner", "unknown_user"), b.get("projectName", "UNKNOWN"))

policy_names = [b.get("policyName", "No Policy Name") for b in bundles]
total_policies = len(set(policy_names))
total_bundles = len(bundles)
governed_bundles = [bundle for bundle in bundles if bundle.get("policyName")]
total_governed_bundles = len(governed_bundles)

approval_tasks = []
for b in bundles:
    project_id = b.get("projectId")
    if not project_id or project_id == "unknown_project_id":
        continue
    tasks = fetch_tasks_for_project(project_id)
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

total_registered_models = len(models)

model_name_version_in_bundles = set()
for b in bundles:
    for att in b.get("attachments", []):
        if att.get("type") == "ModelVersion":
            identifier = att.get("identifier", {})
            m_name = identifier.get("name")
            m_ver = identifier.get("version")
            if m_name and m_ver:
                model_name_version_in_bundles.add((m_name, m_ver))
total_models_in_bundles = len(model_name_version_in_bundles)

total_projects = len(all_projects)
project_ids_with_bundles = set(b.get("projectId") for b in bundles if b.get("projectId"))
projects_with_a_bundle = len(project_ids_with_bundles)

# ----------------------------------------------------
#   SUMMARY SECTION (CLICKABLE)
# ----------------------------------------------------
st.markdown("---")
st.header("Summary")
st.markdown('<a id="summary"></a>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
# All policies now as clickable links: using the first bundle info
policy_links = []
for pol_id, (pol_name, owner, proj) in policy_info.items():
    link = build_domino_link(owner=owner, project_name=proj, artifact="policy", policy_id=pol_id)
    policy_links.append(f'<a href="{link}" target="_blank">{pol_name}</a>')
col1.metric("Total Policies", total_policies)
col1.markdown(" | ".join(policy_links), unsafe_allow_html=True)

col2.metric("Total Bundles", total_bundles)
col2.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

col3.metric("Pending Tasks", total_pending_tasks)
col3.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

colA, colB, colC, colD = st.columns(4)
colA.metric("Registered Models", total_registered_models)
colA.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
colB.metric("Models in a Bundle", total_models_in_bundles)
colB.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
colC.metric("Total Projects", total_projects)
colC.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)
colD.metric("Projects w/ Bundle", projects_with_a_bundle)
colD.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

# ----------------------------------------------------
#   DETAILED METRICS SECTION
# ----------------------------------------------------
st.markdown("---")
st.markdown("## Detailed Metrics")
st.markdown('<a id="detailed-metrics"></a>', unsafe_allow_html=True)

with st.expander("All Policies"):
    st.write(f"Found {total_policies} policy names:")
    # Each policy is shown as a link
    for pol_id, (pol_name, owner, proj) in sorted(policy_info.items(), key=lambda x: x[1][0]):
        link = build_domino_link(owner=owner, project_name=proj, artifact="policy", policy_id=pol_id)
        st.markdown(f"- <a href='{link}' target='_blank'>{pol_name}</a>", unsafe_allow_html=True)

with st.expander("All Bundles"):
    st.write(f"Found {total_bundles} total bundles:")
    for b in bundles:
        # Each bundle name as link to bundle evidence page
        owner = b.get("projectOwner", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        link = build_domino_link(owner=owner, project_name=proj, artifact="bundleEvidence", bundle_id=b.get("id", ""), policy_id=b.get("policyId", ""))
        st.markdown(f"- <a href='{link}' target='_blank'>{b.get('name', 'Unnamed')}</a>", unsafe_allow_html=True)

with st.expander("Pending Tasks"):
    st.write(f"Found {total_pending_tasks} pending tasks:")
    if approval_tasks:
        for t in approval_tasks:
            st.markdown(f"- <a href='{t['bundle_link']}' target='_blank'>{t['task_name']} (Stage: {t['stage']})</a>", unsafe_allow_html=True)
    else:
        st.write("None")

with st.expander("Registered Models"):
    st.write(f"Found {total_registered_models} registered models:")
    model_names = sorted(m.get("name", "Unnamed") for m in models)
    for mn in model_names:
        st.write(f"- {mn}")

with st.expander("Models in a Bundle"):
    st.write(f"Found {total_models_in_bundles} distinct (model, version) references:")
    group_map = defaultdict(list)
    for (m_name, m_ver) in model_name_version_in_bundles:
        group_map[m_name].append(m_ver)
    for mod_name, versions in group_map.items():
        st.write(f"- **{mod_name}** => Versions: {', '.join(str(v) for v in versions)}")

with st.expander("All Projects"):
    st.write(f"Found {total_projects} total projects:")
    for pid, p_obj in project_map.items():
        st.write(f"- {p_obj.get('name', 'Unnamed')} (id={pid})")

with st.expander("Projects w/ Bundle"):
    st.write(f"Found {projects_with_a_bundle} projects that have at least one bundle:")
    for pid in sorted(project_ids_with_bundles):
        if pid in project_map:
            p_obj = project_map[pid]
            st.write(f"- {p_obj.get('name', 'Unnamed')} (id={pid})")
        else:
            st.write(f"- Unknown project (id={pid})")

# ----------------------------------------------------
#  POLICIES ADOPTION SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Policies Adoption")
st.markdown('<a id="policies-adoption"></a>', unsafe_allow_html=True)

policies = { b.get("policyId"): b.get("policyName") for b in bundles if b.get("policyId") }
if policies:
    for policy_id, policy_name in policies.items():
        st.subheader(f"Policy: {policy_name}")
        policy_details = fetch_policy_details(policy_id)
        if policy_details:
            stages = policy_details.get("stages", [])
            if stages:
                bundle_data_per_stage = defaultdict(list)
                for bundle in bundles:
                    if bundle.get("policyId") == policy_id:
                        bundle_data_per_stage[bundle.get("stage", "Unknown Stage")].append(bundle)
                # For each stage, list bundles as clickable links.
                for stage_name, items in bundle_data_per_stage.items():
                    st.write(f"- **Stage: {stage_name}** ({len(items)})")
                    with st.expander(f"View Bundles in {stage_name}"):
                        for one_b in items:
                            owner = one_b.get("projectOwner", "unknown_user")
                            proj = one_b.get("projectName", "UNKNOWN")
                            link = build_domino_link(owner=owner, project_name=proj, artifact="bundleEvidence", bundle_id=one_b.get("id", ""), policy_id=one_b.get("policyId", ""))
                            st.markdown(f"- <a href='{link}' target='_blank'>{one_b.get('name', 'Unnamed Bundle')}</a> (Moved: {one_b.get('stageUpdateTime', 'N/A')})", unsafe_allow_html=True)
            else:
                st.warning(f"No stages found for policy {policy_name}")
        else:
            st.error(f"Could not fetch policy details for {policy_name}")
else:
    st.info("No policies found.")

# ----------------------------------------------------
#  GOVERNED BUNDLES DETAILS
# ----------------------------------------------------
st.markdown("---")
st.header("Governed Bundles Details (Table)")
st.markdown('<a id="governed-bundles-details-table"></a>', unsafe_allow_html=True)

sorted_bundles = sorted(
    governed_bundles,
    key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in approval_tasks),
    reverse=True
)

if show_debug:
    st.subheader("Bundles Debug Info")
    for i, bundle in enumerate(sorted_bundles, start=1):
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
for bundle in sorted_bundles:
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
    evidence_link = build_domino_link(owner=proj_owner, project_name=proj_name, artifact="bundleEvidence", bundle_id=b_id, policy_id=pol_id)
    bundle_html = f'<a href="{evidence_link}" target="_blank">{b_name}</a>'
    # Policy name as link:
    policy_link = build_domino_link(owner=proj_owner, project_name=proj_name, artifact="policy", policy_id=pol_id)
    policy_html = f'<a href="{policy_link}" target="_blank">{pol_name}</a>'
    rel_tasks = [t for t in approval_tasks if t["bundle_name"] == b_name]
    if rel_tasks:
        tasks_bullets = []
        for t in rel_tasks:
            tasks_bullets.append(f'<li><a href="{t["bundle_link"]}" target="_blank">{t["task_name"]}, Stage: {t["stage"]}</a></li>')
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
            mv_link = build_domino_link(owner=created_by, project_name=proj_name, artifact="model-card", model_name=m_name, version=m_ver)
            mv_links.append(f'<li>{m_name} (Version: {m_ver}) — <a href="{mv_link}" target="_blank">View Model Card</a></li>')
    mv_html = f"<ul>{''.join(mv_links)}</ul>" if mv_links else "No ModelVersion attachments found"
    table_rows.append({
        "Bundle": bundle_html,
        "Status": status,
        "Policy Name": policy_html,
        "Stage": stage,
        "Tasks": tasks_html,
        "Model Versions": mv_html
    })

df_bundles = pd.DataFrame(table_rows)
st.write(df_bundles.to_html(escape=False), unsafe_allow_html=True)

# ----------------------------------------------------
#  REGISTERED MODELS TABLE
# ----------------------------------------------------
st.markdown("---")
st.header("Registered Models")
st.markdown('<a id="registered-models"></a>', unsafe_allow_html=True)

if models:
    st.write(f"Total Registered Models: {len(models)}")
    model_to_bundles = defaultdict(list)
    for b in governed_bundles:
        b_id = b.get("id", "")
        b_n = b.get("name", "Unnamed Bundle")
        p_owner = b.get("projectOwner", "unknown_user")
        p_name = b.get("projectName", "UNKNOWN")
        pol_id = b.get("policyId", "")
        link = build_domino_link(owner=p_owner, project_name=p_name, artifact="bundleEvidence", bundle_id=b_id, policy_id=pol_id)
        for att in b.get("attachments", []):
            if att.get("type") == "ModelVersion":
                ident = att.get("identifier", {})
                mod_name = ident.get("name")
                if mod_name:
                    model_to_bundles[mod_name].append((b_n, link))
    model_rows = []
    for m in models:
        mod_name = m.get("name", "Unnamed Model")
        p_name = m.get("project", {}).get("name", "Unknown Project")
        owner = m.get("ownerUsername", "Unknown Owner")
        model_registry_url = build_domino_link(owner=owner, project_name=p_name, artifact="model-registry", model_name=mod_name)
        model_name_html = f'<a href="{model_registry_url}" target="_blank">{mod_name}</a>'
        if mod_name in model_to_bundles:
            items = model_to_bundles[mod_name]
            bul = []
            for (bn, bn_link) in items:
                safe_bn = bn.replace("<", "&lt;").replace(">", "&gt;")
                bul.append(f'<li><a href="{bn_link}" target="_blank">{safe_bn}</a></li>')
            bundles_html = f"<ul>{''.join(bul)}</ul>"
        else:
            bundles_html = ""
        model_rows.append({
            "Name": model_name_html,
            "Project": p_name,
            "Owner": owner,
            "Bundles": bundles_html
        })
    df_models = pd.DataFrame(model_rows)
    st.write(df_models.to_html(escape=False), unsafe_allow_html=True)
else:
    st.warning("No registered models found.")