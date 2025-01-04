import requests

# Define your Domino API URLs
registered_models_url = "https://se-demo.domino.tech/api/registeredmodels/v1"
deliverables_url = "https://se-demo.domino.tech/api/deliverables/v1"

# Fetch registered models
registered_models_response = requests.get(registered_models_url, headers={"Authorization": "Bearer <your_api_key>"})
models = registered_models_response.json().get("items", [])

# Fetch deliverables (bundles)
deliverables_response = requests.get(deliverables_url, headers={"Authorization": "Bearer <your_api_key>"})
deliverables = deliverables_response.json().get("items", [])

# Extract model IDs in deliverables
model_ids_in_bundles = set()
for deliverable in deliverables:
    model_versions = deliverable.get("modelVersions", [])
    for model_version in model_versions:
        model_id = model_version.get("modelId")
        if model_id:
            model_ids_in_bundles.add(model_id)

# Classify models
models_in_bundle = []
models_not_in_bundle = []

for model in models:
    model_id = model.get("project", {}).get("id")
    name = model.get("name", "N/A")
    project_name = model.get("project", {}).get("name", "N/A")
    owner = model.get("ownerUsername", "N/A")
    model_link = f"https://se-demo.domino.tech/models/{name}"  # Example link format

    if model_id in model_ids_in_bundles:
        models_in_bundle.append({"name": name, "project": project_name, "owner": owner, "link": model_link})
    else:
        models_not_in_bundle.append({"name": name, "project": project_name, "owner": owner, "link": model_link})

# Summary
print(f"Total Registered Models: {len(models)}")
print(f"Models in Governed Bundle: {len(models_in_bundle)}")
print(f"Models Not in Governed Bundle: {len(models_not_in_bundle)}")

# Display tables
print("\nModels in Governed Bundle:")
for model in models_in_bundle:
    print(f"Name: {model['name']}, Project: {model['project']}, Owner: {model['owner']}, Link: {model['link']}")

print("\nModels Not in Governed Bundle:")
for model in models_not_in_bundle:
    print(f"Name: {model['name']}, Project: {model['project']}, Owner: {model['owner']}, Link: {model['link']}")