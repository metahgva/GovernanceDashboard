pip install streamlit --user

mkdir ~/.streamlit
echo "[browser]" > ~/.streamlit/config.toml
echo "gatherUsageStats = true" >> ~/.streamlit/config.toml
echo "serverAddress = \"0.0.0.0\"" >> ~/.streamlit/config.toml
echo "serverPort = 8888" >> ~/.streamlit/config.toml
echo "[server]" >> ~/.streamlit/config.toml
echo "port = 8888" >> ~/.streamlit/config.toml
echo "enableCORS = false" >> ~/.streamlit/config.toml
echo "enableXsrfProtection = false" >> ~/.streamlit/config.toml
 
export PYTHONPATH=$(pwd):$PYTHONPATH
streamlit run app.py --server.port 8888