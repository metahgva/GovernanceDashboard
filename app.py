import streamlit as st
import requests
import os
import plotly.express as px
import urllib.parse
import pandas as pd
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
API_HOST = os.getenv("API_HOST", "https://dev.qbe.domino.tech")
API_KEY = os.getenv("API_KEY", "63e426d6d476f2b2798e6d66c2221bcbf53edcd95988cb18d67e4cf7c8b06043")

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
    st.experimental_rerun()

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
        data = resp.json()
        # Unwrap potential wrappers
        if isinstance(data, dict):
            return data.get("items") or data.get("data") or data.get("projects") or []
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        st.error(f"Error while fetching projects: {e}")
        return []

@st.cache_data
def fetch_tasks_for_project(project_id):
    try:
        resp = api_call("GET", f"/api/projects/v1/projects/{project_id}/goals")
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

# ----------------------------------------------------
#   LINK BUILDING HELPER
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
        # direct link to the policy endpoint
        return f"{base}/governance/policy/{policy_id}"
    return f"{base}/u/{enc_owner}/{enc_project}/overview"

# ----------------------------------------------------
#   PARSE TASK DESCRIPTION
# ----------------------------------------------------
def parse_task_description(description):
    try:
        start, end = description.find('['), description.find(']')
        bundle_name = description[start+1:end]
        ls, le = description.find('('), description.find(')')
        bundle_link = f"{API_HOST}{description[ls+1:le]}"
        return bundle_name, bundle_link
    except:
        return None, None

# ----------------------------------------------------
#   PLOT HELPER
# ----------------------------------------------------
def plot_policy_stages_interactive(policy_name, stages, bundle_data):
    df = pd.DataFrame({
        'Stage': [s['name'] for s in stages],
        'Number of Bundles': [len(bundle_data.get(s['name'], [])) for s in stages]
    })
    fig = px.bar(df, x='Number of Bundles', y='Stage', orientation='h',
                 title=f"Policy Adoption: {policy_name}",
                 labels={'Number of Bundles':'Count','Stage':'Stage'})
    fig.update_layout(title_font_size=14, xaxis_title_font_size=12, yaxis_title_font_size=12)
    return fig

# ----------------------------------------------------
#   FETCH & PREP DATA
# ----------------------------------------------------
all_projects = fetch_all_projects()
bundles = fetch_bundles()
models = fetch_registered_models()

# Build project map (string IDs)
project_map = {str(p.get('id')): p for p in all_projects if p.get('id') is not None}

# Annotate bundles
for b in bundles:
    pid = str(b.get('projectId'))
    if pid in project_map:
        proj = project_map[pid]
        b['projectName']  = proj.get('name','Unnamed Project')
        b['projectOwner'] = proj.get('ownerUsername','unknown_user')
    else:
        b['projectName']  = 'UNKNOWN'
        b['projectOwner'] = 'unknown_user'

# Filters
all_policy_opts  = sorted({b.get('policyName') for b in bundles if b.get('policyName')})
all_project_opts = sorted({b.get('projectName') for b in bundles if b.get('projectName')})
all_status_opts  = sorted({b.get('state') for b in bundles if b.get('state')})
if not all_policy_opts:  all_policy_opts  = ['(No Policies)']
if not all_project_opts: all_project_opts = ['(No Projects)']
if not all_status_opts:  all_status_opts  = ['(No Status)']
selected_policy  = st.sidebar.selectbox('Select Policy',        ['All'] + all_policy_opts)
selected_project = st.sidebar.selectbox('Select Project',       ['All'] + all_project_opts)
selected_status  = st.sidebar.selectbox('Select Bundle Status', ['All'] + all_status_opts)

def get_filtered_bundles():
    return [
        b for b in bundles
        if (selected_policy=='All'  or b.get('policyName')==selected_policy)
        and (selected_project=='All' or b.get('projectName')==selected_project)
        and (selected_status=='All' or b.get('state')==selected_status)
    ]
filtered_bundles = get_filtered_bundles()

# Approval tasks
approval_tasks = []
for b in filtered_bundles:
    for t in fetch_tasks_for_project(b.get('projectId')):
        desc = t.get('description','')
        if 'Approval requested Stage' in desc:
            name, link = parse_task_description(desc)
            if name == b.get('name'):
                approval_tasks.append({
                    'task_name': t.get('title'),
                    'stage': desc.split('Stage')[1].split(':')[0].strip(),
                    'bundle_name': name,
                    'bundle_link': link
                })

# Model attachments
model_attachment_map = {}
for b in filtered_bundles:
    o, p = b.get('projectOwner'), b.get('projectName')
    for att in b.get('attachments', []):
        if att.get('type') == 'ModelVersion':
            nm  = att['identifier']['name']
            ver = att['identifier']['version']
            model_attachment_map[(nm, ver)] = (o, p)

# Metrics
filtered_model_versions = {
    (att['identifier']['name'], att['identifier']['version'])
    for b in filtered_bundles
    for att in b.get('attachments', [])
    if att.get('type') == 'ModelVersion'
}

num_policies    = len({b.get('policyName') for b in filtered_bundles if b.get('policyName')})
num_bundles     = len(filtered_bundles)
num_tasks       = len(approval_tasks)
num_models      = len(filtered_model_versions)
projects_all    = len({b.get('projectName') for b in bundles})
projects_wb     = len({b.get('projectName') for b in filtered_bundles})
num_reg_mods    = sum(1 for m in models if m.get('name') in {mn for mn,_ in filtered_model_versions})

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

col3.metric("Pending Tasks", num_tasks)
col3.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

col4.metric("Registered Models", num_reg_mods)
col4.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

col5.metric("Models in a Bundle", num_models)
col5.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

col6.metric("Total Projects", projects_all)
col6.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

col7.metric("Projects w/ Bundle", projects_wb)
col7.markdown("[See list](#detailed-metrics)", unsafe_allow_html=True)

if num_tasks > 10:
    st.warning("There are more than 10 pending tasks. Please review!")

# ----------------------------------------------------
#   DETAILED METRICS
# ----------------------------------------------------
st.markdown("---")
st.markdown("## Detailed Metrics")
st.markdown('<a id="detailed-metrics"></a>', unsafe_allow_html=True)

with st.expander("All Policies"):
    pol_ids = {b.get("policyId") for b in bundles if b.get("policyId")}
    st.write(f"Found {len(pol_ids)} unique policy IDs (unfiltered).")
    for b in bundles:
        pid = b.get("policyId")
        if not pid:
            continue
        pol_name = b.get("policyName", "Unknown")
        owner = b.get("projectOwner", "unknown_user")
        proj = b.get("projectName", "UNKNOWN")
        link = build_domino_link(owner=owner, project_name=proj, artifact="policy", policy_id=pid)
        st.markdown(f"- <a href='{link}' target='_blank'>{pol_name}</a>", unsafe_allow_html=True)

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
    st.write(f"Found {num_tasks} pending tasks (filtered).")
    if approval_tasks:
        for t in approval_tasks:
            st.markdown(f"- <a href='{t['bundle_link']}' target='_blank'>{t['task_name']} (Stage: {t['stage']})</a>", unsafe_allow_html=True)
    else:
        st.write("None")

with st.expander("Registered Models"):
    st.write(f"Found {num_reg_mods} registered models (filtered).")
    if filtered_model_versions:
        for mn in sorted({mn for mn,_ in filtered_model_versions}):
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

with st.expander("Models in a Bundle"):
    st.write(f"Found {num_models} distinct (model, version) references (filtered).")
    if num_models > 0:
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
    for pid, p_obj in enumerate(all_projects):
        proj_name = p_obj.get('name', 'Unnamed')
        owner     = p_obj.get('ownerUsername', 'unknown_user')
        link      = build_domino_link(owner=owner, project_name=proj_name, artifact="overview")
        st.markdown(f"- <a href='{link}' target='_blank'>{proj_name}</a>", unsafe_allow_html=True)

# ----------------------------------------------------
#   POLICIES ADOPTION SECTION
# ----------------------------------------------------
st.markdown("---")
st.header("Policies Adoption")
st.markdown('<a id="policies-adoption"></a>', unsafe_allow_html=True)

policies_dict = {b["policyId"]: b["policyName"] for b in bundles if b.get("policyId") and b.get("policyName")}
if not policies_dict:
    st.info("No policies found.")
else:
    for policy_id, policy_name in policies_dict.items():
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
                            proj  = one_b.get("projectName", "UNKNOWN")
                            link  = build_domino_link(owner=owner, project_name=proj,
                                                       artifact="bundleEvidence",
                                                       bundle_id=one_b.get("id", ""),
                                                       policy_id=policy_id)
                            st.markdown(f"- <a href='{link}' target='_blank'>{one_b.get('name')}</a>", unsafe_allow_html=True)
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

governed_bundles = sorted(
    [b for b in filtered_bundles if b.get("policyName")],
    key=lambda b: any(t["bundle_name"] == b.get("name") for t in approval_tasks),
    reverse=True
)

if show_debug:
    st.subheader("Bundles Debug Info")
    for i, bundle in enumerate(governed_bundles, start=1):
        st.markdown(f"**Bundle #{i}:**")
        st.json(bundle)

gov_table_rows = []
for b in governed_bundles:
    owner    = b.get("projectOwner", "unknown_user")
    proj     = b.get("projectName", "UNKNOWN")
    b_name   = b.get("name", "")
    b_id     = b.get("id", "")
    pol_id   = b.get("policyId", "")
    pol_name = b.get("policyName", "")
    status   = b.get("state", "")
    stage    = b.get("stage", "")

    evidence_url = build_domino_link(owner=owner, project_name=proj,
                                     artifact="bundleEvidence",
                                     bundle_id=b_id, policy_id=pol_id)
    policy_url   = build_domino_link(owner=owner, project_name=proj,
                                     artifact="policy", policy_id=pol_id)

    tasks_list = [
        f'<li><a href="{t["bundle_link"]}" target="_blank">{t["task_name"]} (Stage: {t["stage"]})</a></li>'
        for t in approval_tasks if t["bundle_name"] == b_name
    ]
    tasks_html = f"<ul>{''.join(tasks_list)}</ul>" if tasks_list else "No tasks"

    gov_table_rows.append({
        "Project": proj,
        "Bundle": f'<a href="{evidence_url}" target="_blank">{b_name}</a>',
        "Status": status,
        "Policy": f'<a href="{policy_url}" target="_blank">{pol_name}</a>',
        "Stage": stage,
        "Tasks": tasks_html
    })

df_gov = pd.DataFrame(gov_table_rows)
if not df_gov.empty:
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
    m_name = m.get("name", "")
    if m_name not in {mn for mn,_ in filtered_model_versions}:
        continue
    p_name = m.get("project", {}).get("name", "")
    owner  = m.get("ownerUsername", "unknown_user")
    link   = build_domino_link(owner=owner, project_name=p_name,
                               artifact="model-registry", model_name=m_name)
    model_rows.append({
        "Name": f'<a href="{link}" target="_blank">{m_name}</a>',
        "Project": p_name,
        "Owner": owner
    })

df_models = pd.DataFrame(model_rows)
if not df_models.empty:
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
    proj    = b.get("projectName", "")
    b_name  = b.get("name", "")
    state   = b.get("state", "")
    pol     = b.get("policyName", "")
    stage   = b.get("stage", "")
    owner   = b.get("projectOwner", "unknown_user")
    url     = build_domino_link(owner=owner, project_name=proj,
                                artifact="bundleEvidence",
                                bundle_id=b.get("id", ""), policy_id=b.get("policyId", ""))
    bundle_rows.append({
        "Project": proj,
        "Bundle Name": b_name,
        "State": state,
        "Policy": pol,
        "Stage": stage,
        "Link": f'<a href="{url}" target="_blank">View</a>'
    })

df_bundles_project = pd.DataFrame(bundle_rows)
if not df_bundles_project.empty:
    st.markdown(df_bundles_project.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.write("No bundles match the current filters.")