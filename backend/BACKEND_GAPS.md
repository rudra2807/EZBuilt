# Backend workflow – file-by-file gap analysis

This document lists gaps, inconsistencies, and suggested fixes for the EZBuilt backend. Items marked **FIXED** were addressed in code; the rest are for future work.

---

## 1. `main.py`

| Item | Status | Notes |
|------|--------|--------|
| Firebase init | OK | Lazily initialized in `firebase_client.get_firestore_client()`; no need to init in `main`. |
| CORS | Optional | `allow_origins=["http://localhost:3000"]` only. Consider env (e.g. `CORS_ORIGINS`) for production. |

---

## 2. `src/apis/routes_connection.py`

| Item | Status | Notes |
|------|--------|--------|
| Persist role after callback | **GAP** | `save_role_arn` is commented out. After CFN callback, role assumption succeeds but the role ARN is never stored, so `get_user(user_id)` has no `roleArn` and deploy will fail. |
| Persist pending connection | **GAP** | `save_pending_connection` is commented out. Optional for MVP if frontend only uses manual connect. |
| User lookup vs deploy | **GAP** | `get_user_by_external_id` reads from `users` (query by `external_id`). `get_user(user_id)` reads from `awsConnections` (document by `user_id`). Callback only receives `external_id` and `role_arn`; you need a consistent way to get `user_id` (e.g. from `users` doc) and then write to `awsConnections`. |
| Callback URL | Config | Hardcoded `https://yourplatform.com/api/cfn-callback`. Should come from config/env. |
| CFN template URL | Config | Hardcoded S3 URL. Consider env. |

---

## 3. `src/apis/routes_requirements.py`

| Item | Status | Notes |
|------|--------|--------|
| Persist update-terraform | **FIXED** | Update-terraform now calls `update_terraform_plan()` so code and validation are saved to Firestore. |
| Revalidate on update | **FIXED** | Update-terraform now calls `validate_terraform()` and persists the result. |
| Store deploymentId on plan | **FIXED** | After `create_deployment_record`, we call `update_terraform_plan(tf_id, deployment_id=deployment_id)` so the plan has `deploymentId` for the deploy flow. |

---

## 4. `src/apis/routes_terraform.py`

| Item | Status | Notes |
|------|--------|--------|
| Deploy response deployment_id | **FIXED** | Was returning `tf_record["deploymentId"]` (missing). Now returns `request.deployment_id`. |
| Destroy deployment record | **FIXED** | Destroy now creates a new deployment document, uses its id for the background task and for the response, so status polling works for destroy. |
| get_terraform_resources | **FIXED** | Firestore `stream()` returns DocumentSnapshots; code now converts to dicts and uses `snap.id` for deployment id. |
| Destroy request body | Optional | `DestroyRequest.deployment_id` is still present but destroy flow uses a new record id. Frontend should use the **returned** `deployment_id` for destroy status polling. |

---

## 5. `src/services/aws_conn.py`

| Item | Status | Notes |
|------|--------|--------|
| save_role_arn / save_pending_connection | **GAP** | Both commented out. Needed for CFN callback to persist connection so deploy can use `get_user()` and get `roleArn`. |
| get_user_by_external_id empty result | Minor | `.get()` returns a list; `if not doc` is correct for empty. Consider `if not doc or len(doc) == 0` for clarity. |
| Two stores | Design | `users` (by external_id) vs `awsConnections` (by user_id). Design decision: either unify or document that callback must resolve user_id from users and write to awsConnections. |

---

## 6. `src/services/terraform_exec.py`

| Item | Status | Notes |
|------|--------|--------|
| Destroy init | **GAP** | `terraform init` before destroy is commented out. If the deployment dir was never used for apply (e.g. only validation ran), or state was lost, destroy may fail. Consider re-enabling init before destroy, or ensuring the directory and state exist. |
| Encoding on write | Minor | `execute_terraform_apply` opens `tf_file` without `encoding="utf-8"`; `validate_terraform` uses `encoding="utf-8"`. Prefer utf-8 for consistency. |

---

## 7. `src/services/terraform_store.py`

| Item | Status | Notes |
|------|--------|--------|
| update_terraform_plan | **FIXED** | New helper to update code, requirements, deploymentId, validation. Used by requirements and update-terraform. |

---

## 8. `src/services/deployments.py`

| Item | Status | Notes |
|------|--------|--------|
| completed_at for destroy | **FIXED** | `update_deployment_status` now sets `completed_at` for `"destroyed"` and `"destroy_failed"` as well as `"success"` and `"failed"`. |
| get_user_deployments order | Optional | Uses `order_by("started_at")`. Firestore requires a composite index when combining `where` and `order_by`; ensure the index exists or add to `firestore.indexes.json` if used. |

---

## 9. `src/services/structure_requirements.py`

| Item | Status | Notes |
|------|--------|--------|
| Instruction file path | Minor | `_load_text_file("structure_requirements_instructions")` uses `os.path.join("model_instructions", file_name)` (cwd-relative). If the process is run from a different cwd (e.g. project root), it can break. Prefer path based on `__file__` (e.g. same as `_load_json_file`). |
| _load_json_file path | OK | Uses `os.path.dirname(__file__)` and `utilities`; robust across cwd. |

---

## 10. `src/utilities/schemas.py`

No gaps identified.

---

## 11. `src/utilities/firebase_client.py`

No gaps identified. Firebase is lazily initialized; credential path is relative to this file.

---

## Workflow summary

1. **Connection**: Generate CFN link → user runs stack → callback receives role ARN. **Gap**: role and link to user are not persisted; deploy will fail with “AWS account not connected”.
2. **Requirements**: Structure → generate Terraform → save plan → create deployment record → set deploymentId on plan → validate. **Fixed**: Plan has deploymentId; update-terraform persists and revalidates.
3. **Deploy**: Get user (roleArn), get plan, run apply in background. **Fixed**: Response returns correct deployment_id; plan has deploymentId for frontend.
4. **Destroy**: Create new deployment record, run destroy in background. **Fixed**: Uses new record id for task and response; terminal statuses set completed_at.
5. **Resources**: List deployments for terraform, return latest success. **Fixed**: Firestore snapshots converted to dicts with id.

---

## Suggested next steps

1. **Connection flow**: Implement `save_role_arn` (and optionally `save_pending_connection`) and wire callback so `awsConnections` (or equivalent) is updated after successful assumption; align `users` vs `awsConnections` and document how `user_id` is derived in the callback.
2. **terraform_exec**: Re-enable or replace `terraform init` before destroy so destroy works when state/dir is missing; consider idempotent init.
3. **Config**: Move callback URL, CFN template URL, and CORS origins to environment/config.
4. **structure_requirements**: Make instruction file path relative to `__file__` so it works regardless of cwd.
