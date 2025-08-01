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
st.set_page_config(page_title="Governance Dashboard", layout="wide")

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
API_HOST = os.getenv("API_HOST", "https://domino.domino.tech")
API_KEY = os.getenv("API_KEY", "")

st.title("Governance Dashboard")

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
    st.rerun()

# ----------------------------------------------------
#   CONSOLIDATED API CALL HELPER
# ----------------------------------------------------
def api_call(method, endpoint, params=None, json=None):
    headers = {"X-Domino-Api-Key": API_KEY}
    url = f"{API_HOST}{endpoint}"
    return requests.request(method, url, headers=headers, params=params, json=json)

# ----------------------------------------------------
#   HELPER FUNCTIONS (USING api_call)
# ----------------------------------------------------
@st.cache_data
def fetch_bundles():
    try:
        resp = api_call("GET", "/api/governance/v1/bundles")
        if resp.status_code != 200:
            st.error(f"Error fetching bundles: {resp.status_code} - {resp.text}")
            return []
        return resp.json().get("data", [])
    except Exception as e:
        st.error(f"Error while fetching bundles: {e}")
        return []

@st.cache_data
def fetch_all_projects():
    try:
        resp = api_call("GET", "/v4/projects")
        if resp.status_code != 200:
            st.error(f"Error fetching projects: {resp.status_code} - {resp.text}")
            return []
        return resp.json()
    except Exception as e:
        st.error(f"Error while fetching projects: {e}")
        return []

@st.cache_data
def fetch_tasks_for_project(project_id):
    try:
        resp = api_call("GET", f"/api/projects/v1/projects/{project_id}/goals")
        if resp.status_code == 403:
            # Silently handle permission errors
            return []
        if resp.status_code != 200:
            st.error(f"Error fetching tasks for project {project_id}: {resp.status_code}")
            return []
        data = resp.json()
        if "goals" not in data:
            st.error(f"Unexpected tasks structure for project {project_id}: {data}")
            return []
        return [g for g in data["goals"] if g.get("status") != "Completed"]
    except Exception as e:
        st.error(f"Error while fetching tasks for project {project_id}: {e}")
        return []

@st.cache_data
def fetch_policy_details(policy_id):
    try:
        resp = api_call("GET", f"/api/governance/v1/policies/{policy_id}")
        if resp.status_code != 200:
            st.error(f"Error fetching policy details for {policy_id}: {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        st.error(f"Error while fetching policy details for {policy_id}: {e}")
        return None

@st.cache_data
def fetch_registered_models():
    try:
        resp = api_call("GET", "/api/registeredmodels/v1")
        if resp.status_code != 200:
            st.error(f"Error fetching registered models: {resp.status_code} - {resp.text}")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        st.error(f"Error while fetching registered models: {e}")
        return []

@st.cache_data
def fetch_bundle_evidence(bundle_id, policy_id):
    try:
        # Try to get the bundle evidence which includes project info
        resp = api_call("GET", f"/api/governance/v1/bundles/{bundle_id}/evidence/{policy_id}")
        st.write(f"Bundle evidence response for {bundle_id}: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            st.write(f"Bundle evidence data: {data}")
            return data
        return None
    except Exception as e:
        st.error(f"Error fetching bundle evidence for {bundle_id}: {e}")
        return None

@st.cache_data
def fetch_project_details(project_id):
    try:
        # Try the governance API endpoint for project details
        resp = api_call("GET", f"/api/governance/v1/projects/{project_id}")
        st.write(f"Project {project_id} governance response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            st.write(f"Project data: {data}")
            return data
        return None
    except Exception as e:
        st.error(f"Error fetching project details for {project_id}: {e}")
        return None

@st.cache_data
def fetch_bundle_details(bundle_id):
    try:
        # Use the governance API bundle endpoint
        resp = api_call("GET", f"/api/governance/v1/bundles/{bundle_id}")
        st.write(f"Bundle {bundle_id} details response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            st.write(f"Bundle details: {data}")
            return data
        return None
    except Exception as e:
        st.error(f"Error fetching bundle details for {bundle_id}: {e}")
        return None

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
        return f"{base}/governance/policy/{policy_id}"
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

def plot_policy_stages_interactive(policy_name, stages, bundle_data):
    """Interactive horizontal bar chart with Plotly."""
    import plotly.express as px
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]
    df = pd.DataFrame({
        "Stage": stage_names,
        "Number of Bundles": bundle_counts
    })
    fig = px.bar(
        df,
        x="Number of Bundles",
        y="Stage",
        orientation="h",
        title=f"Policy Adoption: {policy_name}",
        labels={"Number of Bundles": "Count", "Stage": "Stage"},
    )
    fig.update_layout(title_font_size=14, xaxis_title_font_size=12, yaxis_title_font_size=12)
    return fig

def derive_project_name(bundle_name: str) -> str:
    """Derive project name from bundle name based on common patterns."""
    if not bundle_name:
        return "UNKNOWN"
    
    # If it starts with 'owl-', it's likely in the owl-scratch project
    if bundle_name.startswith('owl-'):
        return 'owl-scratch'
    
    # For other cases, take the first part before any special characters
    parts = bundle_name.split('-')
    if len(parts) > 0:
        base = parts[0]
        if base in ['test', 'rentpro']:
            # For test/rentpro bundles, use the first two parts
            if len(parts) > 1:
                return f"{base}-{parts[1]}"
            return base
        return base
    
    return "UNKNOWN"

# ----------------------------------------------------
#   DATA FETCHING AND PROCESSING
# ----------------------------------------------------
@st.cache_data
def fetch_data():
    """Fetch all required data and return as a tuple."""
    bundles = fetch_bundles()
    projects = fetch_all_projects()
    models = fetch_registered_models()
    return bundles, projects, models

def process_bundles(bundles):
    """Process bundles to add required information."""
    processed_bundles = []
    for b in bundles:
        # Add owner info
        created_by = b.get("createdBy", {})
        b["projectOwner"] = created_by.get("userName", "unknown_user")
        
        # Add project name
        project_name = b.get("projectName")
        b["projectName"] = project_name if project_name else "UNKNOWN"
        
        processed_bundles.append(b)
    return processed_bundles

def get_approval_tasks(bundles):
    """Get approval tasks for the given bundles."""
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
                if b_name and b_link and b_name == b.get("name"):
                    approval_tasks.append({
                        "task_name": t.get("title", "Unnamed Task"),
                        "stage": desc.split("Stage")[1].split(":")[0].strip(),
                        "bundle_name": b_name,
                        "bundle_link": b_link,
                    })
    return approval_tasks

def get_model_attachment_map(bundles):
    """Create map of model attachments from bundles."""
    model_map = {}
    for b in bundles:
        owner = b.get("projectOwner", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        for att in b.get("attachments", []):
            if att.get("type") == "ModelVersion":
                m_name = att.get("identifier", {}).get("name")
                m_ver = att.get("identifier", {}).get("version")
                if m_name and m_ver:
                    model_map[(m_name, m_ver)] = (owner, proj)
    return model_map

def get_filtered_bundles(bundles, selected_policy, selected_project, selected_status):
    """Filter bundles based on selection criteria."""
    filtered = []
    for b in bundles:
        # policy filter
        if selected_policy != "All" and b.get("policyName", "None") != selected_policy:
            continue
        # project filter
        if selected_project != "All" and b.get("projectName", "None") != selected_project:
            continue
        # status filter
        if selected_status != "All" and b.get("state", "Unknown") != selected_status:
            continue
        filtered.append(b)
    return filtered

# ----------------------------------------------------
#   MAIN APPLICATION LOGIC
# ----------------------------------------------------
def main():
    # Fetch all data
    bundles, all_projects, models = fetch_data()
    
    # Process bundles
    bundles = process_bundles(bundles)
    
    # Get additional data
    approval_tasks = get_approval_tasks(bundles)
    model_attachment_map = get_model_attachment_map(bundles)
    
    # Setup filters
    all_policy_options = sorted({b.get("policyName") for b in bundles if b.get("policyName")})
    all_project_options = sorted({b.get("projectName") for b in bundles if b.get("projectName")})
    all_status_options = sorted({b.get("state") for b in bundles if b.get("state")})
    
    if not all_policy_options:
        all_policy_options = ["(No Policies)"]
    if not all_project_options:
        all_project_options = ["(No Projects)"]
    if not all_status_options:
        all_status_options = ["(No Status)"]
    
    # Display filters
    selected_policy = st.sidebar.selectbox(
        "Select Policy",
        options=["All"] + all_policy_options,
        index=0
    )
    selected_project = st.sidebar.selectbox(
        "Select Project",
        options=["All"] + all_project_options,
        index=0
    )
    selected_status = st.sidebar.selectbox(
        "Select Bundle Status",
        options=["All"] + all_status_options,
        index=0
    )
    
    # Filter bundles
    filtered_bundles = get_filtered_bundles(bundles, selected_policy, selected_project, selected_status)
    
    # Build a project map
    project_map = {}
    for proj in all_projects:
        pid = proj.get("id")
        if pid:
            project_map[pid] = proj

    # Annotate bundles with project data
    for b in bundles:
        created_by = b.get("createdBy", {})
        owner = created_by.get("userName", "unknown_user")
        b["projectOwner"] = owner
        
        # Get project name directly from bundle data
        project_name = b.get("projectName")
        if project_name:
            b["projectName"] = project_name
        else:
            st.error(f"No project name found in bundle {b.get('name', 'unnamed')}")
            b["projectName"] = "UNKNOWN"

    # ----------------------------------------------------
    #   SUMMARY METRICS
    # ----------------------------------------------------
    filtered_policy_names = {b.get("policyName") for b in filtered_bundles if b.get("policyName")}
    num_policies = len(filtered_policy_names)
    num_bundles = len(filtered_bundles)
    num_pending_tasks = len(approval_tasks)

    # Count how many models appear in filtered bundles
    filtered_model_versions = set()
    for b in filtered_bundles:
        for att in b.get("attachments", []):
            if att.get("type") == "ModelVersion":
                identifier = att.get("identifier", {})
                m_name = identifier.get("name")
                m_ver = identifier.get("version")
                if m_name and m_ver:
                    filtered_model_versions.add((m_name, m_ver))
    num_models_in_bundles = len(filtered_model_versions)

    # Which projects appear in the filtered set
    filtered_project_names = {b.get("projectName") for b in filtered_bundles}
    num_projects_with_bundles = len(filtered_project_names)

    # For "total projects", we interpret as how many are currently in the selected project filter
    if selected_project == "All":
        # That means "All" is selected, so let's show how many unique projects are in the entire system
        # or we can show how many are in the entire system. We'll do entire system:
        all_proj_names = {b.get("projectName") for b in bundles}
        num_total_projects = len(all_proj_names)
    else:
        num_total_projects = 1

    # Filtered model names from the attachments
    filtered_model_names = set(mn for (mn, mv) in filtered_model_versions)

    # For completeness, if the user wants to also see if the model's own project property matches
    # the selected project. We'll skip that to keep it simpler.
    num_registered_models = 0
    for m in models:
        if m.get("name", "") in filtered_model_names:
            num_registered_models += 1

    # ----------------------------------------------------
    #   SUMMARY SECTION
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Summary")
    st.markdown('<a id="summary"></a>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    col1.metric("Total Policies", num_policies)
    col1.markdown('[View All Policies](#detailed-metrics)', unsafe_allow_html=True)

    col2.metric("Total Bundles", num_bundles)
    col2.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    col3.metric("Pending Tasks", num_pending_tasks)
    col3.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    col4.metric("Registered Models", num_registered_models)
    col4.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    col5.metric("Models in a Bundle", num_models_in_bundles)
    col5.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    col6.metric("Total Projects", num_total_projects)
    col6.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    col7.metric("Projects w/ Bundle", num_projects_with_bundles)
    col7.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

    if num_pending_tasks > 10:
        st.warning("There are more than 10 pending tasks. Please review!")

    # ----------------------------------------------------
    #   DETAILED METRICS
    # ----------------------------------------------------
    st.markdown("---")
    st.markdown("## Detailed Metrics")
    st.markdown('<a id="detailed-metrics"></a>', unsafe_allow_html=True)

    with st.expander("All Policies"):
        pol_ids = {b.get("policyId") for b in bundles if b.get("policyId")}
        unique_policies = {}
        for b in bundles:
            pid = b.get("policyId")
            if not pid:
                continue
            pol_name = b.get("policyName", "Unknown")
            owner = b.get("projectOwner", "unknown_user")
            proj = b.get("projectName", "UNKNOWN")
            if pid not in unique_policies:
                unique_policies[pid] = {
                    "name": pol_name,
                    "owner": owner,
                    "project": proj
                }
        
        st.write(f"Found {len(unique_policies)} unique policy IDs.")
        for pid, policy in unique_policies.items():
            link = build_domino_link(
                owner=policy["owner"],
                project_name=policy["project"],
                artifact="policy",
                policy_id=pid
            )
            st.markdown(f"- <a href='{link}' target='_blank'>{policy['name']}</a>", unsafe_allow_html=True)

    with st.expander("All Bundles"):
        st.write(f"Found {len(bundles)} total bundles (unfiltered).")
        for b in bundles:
            owner = b.get("projectOwner", "unknown_user")
            proj = b.get("projectName", "UNKNOWN")
            link = build_domino_link(owner=owner, project_name=proj,
                                     artifact="bundleEvidence",
                                     bundle_id=b.get("id", ""),
                                     policy_id=b.get("policyId", ""))
            name = b.get('name', 'Unnamed')
            st.markdown(f"- <a href='{link}' target='_blank'>{name}</a>", unsafe_allow_html=True)

    with st.expander("Pending Tasks"):
        st.write(f"Found {num_pending_tasks} pending tasks (filtered).")
        if approval_tasks:
            for t in approval_tasks:
                st.markdown(f"- <a href='{t['bundle_link']}' target='_blank'>{t['task_name']} (Stage: {t['stage']})</a>", unsafe_allow_html=True)
        else:
            st.write("None")

    with st.expander("Registered Models"):
        st.write(f"Found {num_registered_models} registered models (filtered).")
        if filtered_model_names:
            for mn in sorted(filtered_model_names):
                matched = [m for m in models if m.get("name") == mn]
                if matched:
                    first_match = matched[0]
                    p_name = first_match.get("project", {}).get("name", "")
                    owner = first_match.get("ownerUsername", "unknown_user")
                    link = build_domino_link(owner=owner, project_name=p_name,
                                             artifact="model-registry", model_name=mn)
                    st.markdown(f"- <a href='{link}' target='_blank'>{mn}</a> (Project: {p_name})", unsafe_allow_html=True)
                else:
                    st.write(f"- {mn}")
        else:
            st.write("None in this filter")

    # --- MODELS IN A BUNDLE (NOW WITH CLICKABLE VERSION LINKS) ---
    with st.expander("Models in a Bundle"):
        st.write(f"Found {num_models_in_bundles} distinct (model, version) references (filtered).")
        if num_models_in_bundles > 0:
            group_map = defaultdict(list)
            for (m_name, m_ver) in filtered_model_versions:
                group_map[m_name].append(m_ver)
            for mod_name, versions in sorted(group_map.items()):
                version_links = []
                for v in sorted(versions):
                    if (mod_name, v) in model_attachment_map:
                        (owner, proj) = model_attachment_map[(mod_name, v)]
                        link = build_domino_link(
                            owner=owner, project_name=proj,
                            artifact="model-card",
                            model_name=mod_name,
                            version=v
                        )
                        version_links.append(f'<a href="{link}" target="_blank">v{v}</a>')
                    else:
                        version_links.append(f'v{v}')
                joined_versions = ", ".join(version_links)
                st.markdown(f"- **{mod_name}** => Versions: {joined_versions}", unsafe_allow_html=True)
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
    #   POLICIES ADOPTION SECTION
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Policies Adoption")
    st.markdown('<a id="policies-adoption"></a>', unsafe_allow_html=True)

    policies_dict = {}
    for b in bundles:
        pid = b.get("policyId")
        pname = b.get("policyName")
        if pid and pname:
            policies_dict[pid] = pname

    if not policies_dict:
        st.info("No policies found.")
    else:
        for policy_id, policy_name in policies_dict.items():
            # If user selected a single policy and it's not this one, skip
            if selected_policy != "All" and policy_name != selected_policy:
                continue
            st.subheader(f"Policy: {policy_name}")
            details = fetch_policy_details(policy_id)
            if details:
                stages = details.get("stages", [])
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
                                link = build_domino_link(owner=owner, project_name=proj,
                                                         artifact="bundleEvidence",
                                                         bundle_id=one_b.get("id", ""),
                                                         policy_id=one_b.get("policyId", ""))
                                st.markdown(
                                    f"- <a href='{link}' target='_blank'>{one_b.get('name', 'Unnamed Bundle')}</a>",
                                    unsafe_allow_html=True
                                )
                else:
                    st.warning(f"No stages found for policy {policy_name}")
            else:
                st.error(f"Could not fetch policy details for {policy_name}")

    # ----------------------------------------------------
    #   GOVERNED BUNDLES DETAILS (Table)
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Governed Bundles Details (Table)")
    st.markdown('<a id="governed-bundles-details-table"></a>', unsafe_allow_html=True)

    governed_bundles = [b for b in filtered_bundles if b.get("policyName")]
    governed_bundles = sorted(
        governed_bundles,
        key=lambda b: any(t["bundle_name"] == b.get("name", "") for t in approval_tasks),
        reverse=True
    )

    if show_debug:
        st.subheader("Bundles Debug Info")
        for i, bundle in enumerate(governed_bundles, start=1):
            st.markdown(f"**Bundle #{i}:**")
            st.json(bundle)

    gov_table_rows = []
    for b in governed_bundles:
        owner = b.get("createdBy", {}).get("userName", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        b_name = b.get("name", "Unnamed")
        b_id = b.get("id", "")
        pol_id = b.get("policyId", "")
        pol_name = b.get("policyName", "Unknown")
        status = b.get("state", "Unknown")
        stage = b.get("stage", "Unknown")

        # Evidence link
        evidence_url = build_domino_link(owner=owner, project_name=proj,
                                         artifact="bundleEvidence",
                                         bundle_id=b_id, policy_id=pol_id)
        # Policy link
        policy_url = build_domino_link(owner=owner, project_name=proj,
                                       artifact="policy", policy_id=pol_id)

        b_html = f'<a href="{evidence_url}" target="_blank">{b_name}</a>'
        pol_html = f'<a href="{policy_url}" target="_blank">{pol_name}</a>'

        rel_tasks = [t for t in approval_tasks if t["bundle_name"] == b_name]
        if rel_tasks:
            tasks_list = []
            for t in rel_tasks:
                tasks_list.append(
                    f'<li><a href="{t["bundle_link"]}" target="_blank">{t["task_name"]} (Stage: {t["stage"]})</a></li>'
                )
            tasks_html = f"<ul>{''.join(tasks_list)}</ul>"
        else:
            tasks_html = "No tasks"

        gov_table_rows.append({
            "Project": proj,
            "Bundle": b_html,
            "Status": status,
            "Policy": pol_html,
            "Stage": stage,
            "Tasks": tasks_html
        })

    df_gov = pd.DataFrame(gov_table_rows)
    if len(df_gov) > 0:
        st.markdown(df_gov.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.write("No governed bundles match the current filters.")

    # ----------------------------------------------------
    #   REGISTERED MODELS (Table)
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Registered Models")
    st.markdown('<a id="registered-models"></a>', unsafe_allow_html=True)

    model_rows = []
    for m in models:
        m_name = m.get("name", "Unnamed Model")
        if m_name not in filtered_model_names:
            continue
        p_name = m.get("project", {}).get("name", "")
        owner = m.get("ownerUsername", "unknown_user")
        reg_link = build_domino_link(owner=owner, project_name=p_name,
                                     artifact="model-registry", model_name=m_name)
        m_html = f'<a href="{reg_link}" target="_blank">{m_name}</a>'
        model_rows.append({
            "Name": m_html,
            "Project": p_name,
            "Owner": owner
        })

    df_models = pd.DataFrame(model_rows)
    if len(df_models) > 0:
        st.markdown(df_models.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.write("No registered models match the current filters.")

    # ----------------------------------------------------
    #   BUNDLES BY PROJECT (Table)
    # ----------------------------------------------------
    st.markdown("---")
    st.header("Bundles by Project")
    st.markdown('<a id="bundles-by-project"></a>', unsafe_allow_html=True)

    bundle_rows = []
    for b in filtered_bundles:
        owner = b.get("createdBy", {}).get("userName", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        b_name = b.get("name", "Unnamed Bundle")
        state = b.get("state", "Unknown")
        pol_name = b.get("policyName", "None")
        stage = b.get("stage", "Unknown")
        url = build_domino_link(owner=owner, project_name=proj,
                                artifact="bundleEvidence",
                                bundle_id=b.get("id", ""),
                                policy_id=b.get("policyId", ""))
        link_html = f'<a href="{url}" target="_blank">View</a>'
        bundle_rows.append({
            "Project": proj,
            "Bundle Name": b_name,
            "State": state,
            "Policy": pol_name,
            "Stage": stage,
            "Link": link_html
        })

    df_bundles_project = pd.DataFrame(bundle_rows)
    if len(df_bundles_project) > 0:
        st.markdown(df_bundles_project.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.write("No bundles match the current filters.")

# ----------------------------------------------------
#   RUN MAIN APPLICATION
# ----------------------------------------------------
if __name__ == "__main__":
    main()
