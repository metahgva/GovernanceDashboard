# Function to fetch registered models
@st.cache_data
def fetch_registered_models():
    try:
        url = f"{API_HOST}/api/registeredmodels/v1"
        response = requests.get(url, headers={"X-Domino-Api-Key": API_KEY})
        if response.status_code != 200:
            st.error(f"Error fetching registered models: {response.status_code} - {response.text}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        st.error(f"An error occurred while fetching registered models: {e}")
        return []

# Function to find models in and not in bundles
def categorize_models_by_bundles(models, bundles):
    models_in_bundles = []
    models_not_in_bundles = []

    # Collect model IDs in bundles
    model_ids_in_bundles = {
        model_version.get("modelId")
        for bundle in bundles
        for model_version in bundle.get("modelVersions", [])
    }

    for model in models:
        model_id = model.get("project", {}).get("id")
        if model_id in model_ids_in_bundles:
            models_in_bundles.append(model)
        else:
            models_not_in_bundles.append(model)

    return models_in_bundles, models_not_in_bundles

# Fetch data
registered_models = fetch_registered_models()
governed_bundles = fetch_deliverables()  # Already defined in your app

# Categorize models
models_in_bundles, models_not_in_bundles = categorize_models_by_bundles(registered_models, governed_bundles)

# Display results
st.markdown("---")
st.header("Registered Models and Bundles")

st.subheader("Summary")
st.write(f"Total Registered Models: {len(registered_models)}")
st.write(f"Models in Governed Bundles: {len(models_in_bundles)}")
st.write(f"Models Not in Governed Bundles: {len(models_not_in_bundles)}")

# Models in bundles
st.subheader("Models in Governed Bundles")
for model in models_in_bundles:
    name = model.get("name", "N/A")
    project_name = model.get("project", {}).get("name", "N/A")
    owner = model.get("ownerUsername", "N/A")
    link = f"{API_HOST}/models/{name}"  # Example link
    st.write(f"- **Name:** {name}, **Project:** {project_name}, **Owner:** {owner}")
    st.markdown(f"[View Model]({link})", unsafe_allow_html=True)

# Models not in bundles
st.subheader("Models Not in Governed Bundles")
for model in models_not_in_bundles:
    name = model.get("name", "N/A")
    project_name = model.get("project", {}).get("name", "N/A")
    owner = model.get("ownerUsername", "N/A")
    link = f"{API_HOST}/models/{name}"  # Example link
    st.write(f"- **Name:** {name}, **Project:** {project_name}, **Owner:** {owner}")
    st.markdown(f"[View Model]({link})", unsafe_allow_html=True)