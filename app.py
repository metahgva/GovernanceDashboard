import streamlit as st
import requests
import os

# Load API Host and Key from environment variables
API_HOST = "https://se-demo.domino.tech"
API_KEY = "2627b46253dfea3a329b8c5b84748b98d5b3c5ffe6eb02a55f7177231fc8c1c4"

# Streamlit app title
st.title("Deliverables and Models Dashboard")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("[Summary](#summary)", unsafe_allow_html=True)
st.sidebar.markdown("[Governed Bundles Details](#governed-bundles-details)", unsafe_allow_html=True)

# Fetch deliverables using Guardrails API
@st.cache_data
def fetch_deliverables():
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            auth=(API_KEY, API_KEY),
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"Error fetching deliverables: {e}")
        return []

# Fetch registered models
@st.cache_data
def fetch_registered_models():
    try:
        response = requests.get(
            f"{API_HOST}/api/registeredmodels/v1",
            headers={"X-Domino-Api-Key": API_KEY},
        )
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"Error fetching registered models: {e}")
        return []

# Main logic
deliverables = fetch_deliverables()
models = fetch_registered_models()

if deliverables and models:
    st.markdown("---")
    st.header("Summary")

    # Extract deliverable targets and cross-check with models
    deliverable_targets = {}
    for deliverable in deliverables:
        targets = deliverable.get("targets", [])
        deliverable_targets[deliverable["id"]] = targets

    models_in_bundles = [
        model for model in models if any(
            model.get("id") == target.get("targetId") for deliverable_targets_list in deliverable_targets.values() for target in deliverable_targets_list
        )
    ]
    models_not_in_bundles = [
        model for model in models if all(
            model.get("id") != target.get("targetId") for deliverable_targets_list in deliverable_targets.values() for target in deliverable_targets_list
        )
    ]

    # Metrics
    st.metric("Total Models", len(models))
    st.metric("Models in Governed Bundles", len(models_in_bundles))
    st.metric("Models Not in Bundles", len(models_not_in_bundles))

    # Governed Bundles Details
    st.markdown("---")
    st.header("Governed Bundles Details")
    if deliverables:
        for deliverable in deliverables:
            st.subheader(f"Deliverable: {deliverable['name']} (ID: {deliverable['id']})")
            targets = deliverable_targets.get(deliverable["id"], [])
            if targets:
                st.write("**Targets (Attachments):**")
                for target in targets:
                    st.write(f"- **Name:** {target['name']}, **Type:** {target['type']}, **Target ID:** {target['targetId']}")
            else:
                st.write("No targets found for this deliverable.")

    # Models Not in Bundles
    st.markdown("---")
    st.header("Models Not in Bundles")
    if models_not_in_bundles:
        st.subheader("Models Not in Governed Bundles")
        for model in models_not_in_bundles:
            st.write(f"- **Name**: {model['name']}, **Project**: {model['project']['name']}, **Owner**: {model['ownerUsername']}")

else:
    st.warning("No deliverables or models found.")