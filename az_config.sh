SUBSCRIPTION="worley-suscripcion-covid19"
RESOURCEGROUP="worley-resource-covid19"
LOCATION="eastus"
PLANNAME="ocorreave_asp_0020"
PLANSKU="B1"
SITENAME="worley-win-job-ofcv"
RUNTIME="PYTHON|3.12"

az webapp config set --resource-group "worley-resource-covid19" --name "worley-win-job-ofcv" startup-file "python app.py"