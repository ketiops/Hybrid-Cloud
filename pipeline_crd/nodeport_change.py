import yaml
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--port",type=int,default=30100)

args = parser.parse_args()
with open("./argo_install.yaml") as f:
    argo_yaml = list(yaml.safe_load_all(f))

for doc in argo_yaml:
    if doc['kind']=="Service":
        if doc['metadata']['name'] == 'argo-server':
            doc['spec']['ports'][0]['nodePort']=args.port
            print("Change Service:argo-server's ")
            print(doc)
with open("./argo_install.yaml", 'w') as f:
    yaml.dump_all(argo_yaml, f)