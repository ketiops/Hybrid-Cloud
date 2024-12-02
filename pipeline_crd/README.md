## Pipeline Deployment Installer
---

- Argo Workflow 설치/삭제 스크립트 & yaml 파일 저장소

### 파일 세부 설명
```
├── argo_install.sh : Argo Workflow 설치 스크립트 및 NodePort & Namespace 변경시 할당
├── argo_cluster_resource.yaml : Cluster Resource로 설치될 Argo workflow 구성요소, Global 설치 요소
├── argo_install.yaml : Namespace 별로 설치될 Argo workflow 구성요소
├── argo_delete.sh : Namespace 별 Argo workflow 구성요소 삭제 스크립트
├── argo_cluster_resource_remove.sh : Cluster Resource Argo workflow 구성요소 삭제
├── pipeline_runner : pipeline runner crd 관련 role, rolebinding, service account 설치 요소 폴더
```

- 설치 예시
```
# argo_install.sh [Port Num] [Namespace]
$ argo_install.sh 30190 argo_workflow

# argo_delete.sh [Namespace]
$ argo_delete.sh argo_workflow
```
