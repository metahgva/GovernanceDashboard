import streamlit as st
import requests
import os
from collections import defaultdict
import matplotlib.pyplot as plt

# Load API Host and Key from environment variables or fallback values
API_HOST = os.getenv("API_HOST", "https://se-demo.domino.tech")
API_KEY = os.getenv("API_KEY", "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4")

# Streamlit app title
st.title("Policy Stages Visualization")

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
            return None
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"An exception occurred while fetching deliverables: {e}")
        return None

# Function to fetch policy details using the Guardrails `/policies/{id}` endpoint
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

# Function to plot stages and bundles
def plot_stages(policy_name, stages, bundle_data):
    stage_names = [stage["name"] for stage in stages]
    bundle_counts = [len(bundle_data.get(stage["name"], [])) for stage in stages]

    # Prepare the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(stage_names, bundle_counts, color="skyblue", edgecolor="black")

    # Add annotations for bundle movement dates (if available)
    for i, stage_name in enumerate(stage_names):
        bundles = bundle_data.get(stage_name, [])
        for bundle in bundles:
            moved_date = bundle.get("stageUpdateTime", "N/A")
            if moved_date != "N/A":
                ax.text(
                    i,
                    bundle_counts[i] + 0.2,
                    f"{moved_date}",
                    ha="center",
                    fontsize=8,
                    color="gray",
                )

    # Formatting the plot
    ax.set_title(f"Policy Stages Visualization for {policy_name}", fontsize=14)
    ax.set_xlabel("Stages", fontsize=12)
    ax.set_ylabel("Number of Bundles", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig

# Main App Logic
deliverables = fetch_deliverables()
if deliverables:
    st.header("Policy Visualization")

    # Extract policies from deliverables
    policies = {}
    for deliverable in deliverables:
        policy_id = deliverable.get("policyId", "unknown")
        policy_name = deliverable.get("policyName", "No Policy Name")
        if policy_id != "unknown":
            policies[policy_id] = policy_name

    if policies:
        st.subheader("Available Policies")
        for policy_id, policy_name in policies.items():
            st.write(f"- {policy_name} (ID: {policy_id})")

        # Select a policy to visualize
        selected_policy_id = st.selectbox("Select a Policy to Visualize", list(policies.keys()))
        selected_policy_name = policies[selected_policy_id]

        # Fetch policy details
        policy_details = fetch_policy_details(selected_policy_id)
        if policy_details:
            stages = policy_details.get("stages", [])
            if stages:
                # Collect bundle data per stage
                bundle_data_per_stage = defaultdict(list)
                for deliverable in deliverables:
                    if deliverable.get("policyId") == selected_policy_id:
                        stage_name = deliverable.get("stage", "Unknown Stage")
                        bundle_data_per_stage[stage_name].append({
                            "name": deliverable.get("name", "Unnamed Bundle"),
                            "stageUpdateTime": deliverable.get("stageUpdateTime", "N/A")
                        })

                # Plot the stages and bundles
                fig = plot_stages(selected_policy_name, stages, bundle_data_per_stage)
                st.pyplot(fig)
            else:
                st.warning(f"No stages found for the policy {selected_policy_name}.")
        else:
            st.error(f"Could not fetch details for policy {selected_policy_name}.")
    else:
        st.warning("No policies found in the deliverables.")
else:
    st.warning("No deliverables found or an error occurred.")