# StudentOps | ENSP461 capstone
Local-first lab reference implementation. Use synthetic student data only. Commands assume macOS/Linux shell; Ansible installation playbooks target Ubuntu 24.04 AMD64. Install Python 3.12, Git, Docker, kubectl, Minikube, Helm, Terraform and Ansible as needed. Run heavy services separately on low-memory laptops.

## 1. Application and Git
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_env.py
python -m pytest
```
Create an empty GitHub repository, then:
```
git init -b main
git add . && git commit -m 'Initial StudentOps implementation'
git remote add origin https://github.com/YOUR_USER/studentops.git
git push -u origin main
git switch -c feature/dashboard
```
Edit README, commit, switch main and merge feature/dashboard. To demonstrate conflict, edit the same README line differently on two branches, commit both, merge, remove conflict markers, add and commit. Capture git log --graph --oneline --all.

## 2. Jenkins CI
Install Jenkins on a Linux agent with Python, Docker, Trivy, sonar-scanner and Git. Install GitHub, Pipeline, SonarQube Scanner and SSH Agent plugins. Configure SonarQube server named SonarQube and token in Jenkins credentials. Create Docker Hub repository, username/token credential `dockerhub`, and SSH credential `gitops-ssh` with write access to a separate GitOps repository. Set GITOPS_REPO to its SSH clone URL in Jenkins environment; configure known_hosts. Replace YOUR_DOCKERHUB_USER in Jenkinsfile. Create a multibranch pipeline for the source repo, configure GitHub webhook /github-webhook/ on reachable HTTPS Jenkins, and verify push triggers. Scanner failures block publication. Separate GitOps repository prevents CI loops. Jenkins publishes a candidate, not automatic traffic promotion.

## 3. Docker
```
docker compose up --build -d
docker compose ps
curl http://localhost:5000/health
```
Open http://localhost:5000 and log in as admin with the password chosen in setup_env.py. Add/edit/delete synthetic records. API GET /api/students and GET/PUT/DELETE /api/students/ID, POST /api/students. Authenticate using session cookie; send X-CSRFToken from a form page for writes. JSON fields: roll,name,email,course,semester. Stop with docker compose down (do not add -v unless you want to delete data).

## 4. Kubernetes
```
minikube start --driver=docker
terraform -chdir=terraform init
terraform -chdir=terraform apply
python scripts/kube-secret.py
docker build -t studentops:local .
minikube image load studentops:local
kubectl apply -k kubernetes -n studentops
kubectl -n studentops get pods,pvc,pv
kubectl -n studentops port-forward svc/studentops 8080:80
```
Visit localhost:8080. The PVC dynamically provisions a PV using Minikube default storage class. If startup races with MySQL, pods retry; inspect logs. Before enabling GitOps, demonstrate `kubectl -n studentops scale deployment/studentops-blue --replicas=3`, `kubectl -n studentops rollout restart deployment/studentops-blue`, `kubectl -n studentops rollout status deployment/studentops-blue`, `kubectl -n studentops rollout undo deployment/studentops-blue`. For a real image update build a new tag, load it, then use kubectl set image deployment/studentops-blue app=studentops:v2 -n studentops. Keep database schema compatible across versions.

## 5. Ansible
On Ubuntu AMD64, install Ansible and run `ansible-playbook -i ansible/inventory.ini ansible/install-docker.yml -K`. Ensure your user can run Docker (Docker group grants root-equivalent access; use a dedicated lab VM). Run install-kubernetes.yml, then the Terraform, secret and image setup above, followed by deploy-app.yml and configure.yml using the same inventory. On Mac install Docker Desktop and Minikube natively instead; deploy/configure playbooks still use kubectl.

## 6. Terraform
The commands above provision a Kubernetes namespace using a reusable module, variables and outputs. This is local Kubernetes infrastructure, not a cloud VM or cluster provisioning solution. Run `terraform -chdir=terraform output`. Do not destroy until demo is complete.

## 7. Monitoring
```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring/values.yaml
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
```
Get Grafana credentials from the chart-created secret (do not screenshot passwords). Use built-in Kubernetes dashboards and add panels with queries in monitoring/queries.md. Visit application to generate metrics.

## 8. Logging
`kubectl apply -f logging/fluentd.yaml -n studentops` then `kubectl logs -n studentops -l app=fluentd --tail=100`. Fluentd collects node container logs and outputs them to its own stdout for lab demonstration; this is not durable centralized storage. Add a remote sink for production or strict central-storage requirements. Do not collect real student data.

## 9. Security
Run SonarQube scan in Jenkins, Trivy image scan, inspect non-root container and demonstrate `kubectl auth can-i list pods --as=demo --as-group=studentops-viewers -n studentops`. Secrets are generated locally, not committed. Kubernetes Secrets are not encrypted at rest by default. Use TLS, secret encryption, restricted network access and stronger authentication for production.

## 10–11. Blue-Green and GitOps
Create separate GitOps repository containing kubernetes directory. Replace both local image references with accessible registry image tags before syncing (or load local tags for lab). Install ArgoCD: `kubectl create namespace argocd` then `kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml`. Replace repoURL in gitops/application.yaml; configure repo credentials if private. Apply application YAML. Port-forward argocd-server service 8443:443 in argocd namespace; use initial admin secret to log in and change password. Jenkins updates green image tag in GitOps repo. Wait for green deployment ready, port-forward deployment/studentops-green 8081:5000 and test candidate. Promote by changing color selector in service.yaml to green in GitOps repo, commit and push. ArgoCD sync switches traffic. Roll back by reverting promotion commit. Do not manually patch Git-managed resources after enabling self-heal. Verify endpoints and ArgoCD sync status.

## Evidence
See docs/evidence.md. No screenshots or live deployment results are fabricated. Configuration requires real accounts, credentials, tool installation and testing on your machine.
