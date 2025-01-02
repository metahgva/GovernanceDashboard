import streamlit as st
import requests
import json
import os

# Load API Host and Key from environment variables
API_HOST = os.getenv("API_HOST", "")
API_KEY = os.getenv("API_KEY", "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJBaDg5WmhHQ0paN2d1X1N0TDM5M3NVcnVKNVFJMFV4NGF3MXpYMmU5LUJNIn0.eyJleHAiOjE3MzU4MzIwODUsImlhdCI6MTczNTgzMTc4NSwiYXV0aF90aW1lIjoxNzM1NzM4OTU3LCJqdGkiOiJkZTcxYTBmZi03NzY4LTRkNTItOTM1Yy01NzUwM2E4NmRhMDMiLCJpc3MiOiJodHRwczovL3NlLWRlbW8uZG9taW5vLnRlY2gvYXV0aC9yZWFsbXMvRG9taW5vUmVhbG0iLCJhdWQiOlsiZG9taW5vLXBsYXRmb3JtIiwiZmx5dGVhZG1pbiIsImFjY291bnQiXSwic3ViIjoiNjU0ZDUxZGFjODljYjkzYjBmN2E5YjFmIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiZG9taW5vLXBsYXkiLCJzaWQiOiI4YzAxNzMyNS1kNThlLTQ3NGYtYmZlNC0zZmIwMWY4Zjc0YjAiLCJhbGxvd2VkLW9yaWdpbnMiOlsiaHR0cHM6Ly9zZS1kZW1vLmRvbWluby50ZWNoIiwiaHR0cHM6Ly9hcHBzLnNlLWRlbW8uZG9taW5vLnRlY2giXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLWRvbWlub3JlYWxtIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgZG9taW5vLWp3dC1jbGFpbXMgZW1haWwgb2ZmbGluZV9hY2Nlc3MgcHJvZmlsZSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpZHBfaWQiOiJmMjA0ZGUwYS0wOWExLTQ4M2MtYmNkYi01N2JjYWFhMGVkMzMiLCJuYW1lIjoiQWhtZXQgR3lnZXIiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJhaG1ldF9neWdlciIsImdpdmVuX25hbWUiOiJBaG1ldCIsImZhbWlseV9uYW1lIjoiR3lnZXIiLCJlbWFpbCI6ImFobWV0Lmd5Z2VyQGRvbWlub2RhdGFsYWIuY29tIiwidXNlcl9ncm91cHMiOlsiL3JvbGVzL0Nsb3VkQWRtaW4iLCIvcm9sZXMvUHJhY3RpdGlvbmVyIl19.C5Ng0e2Bf1laj2HlKuk3yB3d47_TezUSaByjT04WXgKKvQrHEYlc7jrrj-3FZZ4OdhPx26Bv-zQ5F74L_gJRaca-8p_CmImjHqUcp5WjqUDibLOJkGW0VYt2GIzM7w7CRV9Wz1v-3uy58r-vDiY7mWZvByw4iqYI7wkqCv3gh1iSGzGk1oxTEWpeCgVm42XWfhVxvJLjD6fSdnz9c60bc6y9h7L6dH-8Hr_CFkmD2lcHnvi08TZ1HCImE1g41tZw4J7exUrLMp48JppQOEb8_yBaPqHVaRifbJ_VDoxP7w6cfjSVecngY4v9k60ewZBYgnntpnWQl0m8qP8jESDuAg")

# Streamlit app title
st.title("Deliverables Dashboard")

# Sidebar information (no manual input needed)
st.sidebar.header("API Configuration")
st.sidebar.write(f"API Host: {API_HOST}")
if not API_KEY:
    st.sidebar.error("API Key is not set. Please configure the environment variable.")

# Button to fetch deliverables
fetch_data = st.sidebar.button("Fetch Deliverables")

# Function to fetch deliverables from the API
def fetch_deliverables():
    try:
        # API request
        response = requests.get(
            f"{API_HOST}/guardrails/v1/deliverables",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
        return response.json()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None

# Fetch and display deliverables
if fetch_data:
    if not API_KEY:
        st.error("API Key is missing. Set the environment variable and restart the app.")
    else:
        st.write("Fetching deliverables...")
        data = fetch_deliverables()
        if data:
            deliverables = data.get("data", [])
            # Display deliverables (same as before)
            for deliverable in deliverables:
                # Extract details and display
                bundle_name = deliverable.get("name", "Unnamed Bundle")
                status = deliverable.get("state", "Unknown")
                policy_name = deliverable.get("policyName", "Unknown")
                stage = deliverable.get("stage", "Unknown")
                project_name = deliverable.get("projectName", "Unnamed Project")
                project_owner = deliverable.get("projectOwner", "Unknown Project Owner")
                bundle_owner = f"{deliverable.get('createdBy', {}).get('firstName', 'Unknown')} {deliverable.get('createdBy', {}).get('lastName', 'Unknown')}"
                targets = deliverable.get("targets", [])
                # Group attachments by type and list details
                attachment_details = {}
                for target in targets:
                    attachment_type = target.get("type", "Unknown")
                    if attachment_type == "ModelVersion":
                        model_name = target.get("identifier", {}).get("name", "Unnamed Model")
                        model_version = target.get("identifier", {}).get("version", "Unknown Version")
                        attachment_name = f"{model_name} (Version: {model_version})"
                    else:
                        attachment_name = target.get("identifier", {}).get("filename", "Unnamed Attachment")
                    if attachment_type not in attachment_details:
                        attachment_details[attachment_type] = []
                    attachment_details[attachment_type].append(attachment_name)
                # Display bundle details
                st.subheader(f"Bundle: {bundle_name}")
                st.write(f"**Status:** {status}")
                st.write(f"**Policy Name:** {policy_name}")
                st.write(f"**Stage:** {stage}")
                st.write(f"**Project Name:** {project_name}")
                st.write(f"**Project Owner:** {project_owner}")
                st.write(f"**Bundle Owner:** {bundle_owner}")
                # Attachments
                st.write("**Attachments by Type:**")
                for attachment_type, names in attachment_details.items():
                    st.write(f"- **{attachment_type}:**")
                    for name in names:
                        st.write(f"  - {name}")
                st.write("---")