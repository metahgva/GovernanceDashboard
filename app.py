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
            auth=(API_KEY, API_KEY),  # Updated for auth
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        st.error(f"Error fetching deliverables: {e}")
        return []

# Fetch deliverable details to get attachments
@st.cache_data
def fetch_deliverable_details(deliverable_id):
    try:
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables/{deliverable_id}",
            auth=(API_KEY, API_KEY),
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching details for deliverable {deliverable_id}: {e}")
        return None

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

    # Extract deliverable IDs for cross-referencing
    deliverable_ids = {d["id"] for d in deliverables}
    deliverable_attachments = {}

    # Fetch attachments for each deliverable
    for deliverable in deliverables:
        details = fetch_deliverable_details(deliverable["id"])
        if details:
            deliverable_attachments[deliverable["id"]] = details.get("attachments", [])

    # Categorize models based on governance status
    models_in_bundles = [m for m in models if m.get("id") in deliverable_ids]
    models_not_in_bundles = [m for m in models if m.get("id") not in deliverable_ids]

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
            attachments = deliverable_attachments.get(deliverable["id"], [])
            if attachments:
                st.write("**Attachments:**")
                for attachment in attachments:
                    st.write(f"- **Name:** {attachment['name']}, **Type:** {attachment['type']}")
            else:
                st.write("No attachments found for this deliverable.")

    # Models Not in Bundles
    st.markdown("---")
    st.header("Models Not in Bundles")
    if models_not_in_bundles:
        st.subheader("Models Not in Governed Bundles")
        for model in models_not_in_bundles:
            st.write(f"- **Name**: {model['name']}, **Project**: {model['project']['name']}, **Owner**: {model['ownerUsername']}")

else:
    st.warning("No deliverables or models found.")