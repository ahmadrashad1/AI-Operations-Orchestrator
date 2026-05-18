# Smoke verification for Docker Compose stack (Windows PowerShell).
# Prerequisites: copy .env.example to .env and set APP_SLACK_WEBHOOK_URL + APP_JWT_SECRET_KEY.
# Usage (repo root): .\scripts\smoke_verify.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "== docker compose ps =="
docker compose ps

Write-Host "`n== GET /api/v1/healthz =="
try {
  $h = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/healthz" -Method Get
  Write-Host ($h | ConvertTo-Json -Compress)
  if ($h.status -ne "ok") { throw "healthz status not ok" }
} catch {
  Write-Host "FAIL: API not reachable at http://localhost:8000 — start stack with: docker compose up -d"
  exit 1
}

Write-Host "`n== worker logs (last 50 lines) =="
docker compose logs worker --tail 50 2>&1

Write-Host "`n== seed admin user (if api container running) =="
$seed = docker compose exec -T api python scripts/seed_admin.py --email admin@demo.local --password "ChangeMe123!" 2>&1
Write-Host $seed

Write-Host "`n== POST /api/v1/auth/login =="
$loginBody = @{ email = "admin@demo.local"; password = "ChangeMe123!" } | ConvertTo-Json
try {
  $tok = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
  Write-Host "access_token prefix:" $tok.access_token.Substring(0, [Math]::Min(20, $tok.access_token.Length)) "..."
} catch {
  Write-Host "Login failed (seed user / Postgres / JWT secret). Details:"
  Write-Host $_
  exit 1
}

$headers = @{ Authorization = "Bearer $($tok.access_token)" }

Write-Host "`n== POST /api/v1/workflow/create (triggers Slack dispatch job) =="
$wfBody = @{
  request_text = "Need 5 laptops for the engineering team — procurement approval test"
  tenant_id    = "demo-tenant"
} | ConvertTo-Json

try {
  $wf = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/workflow/create" -Method Post -Body $wfBody -ContentType "application/json" -Headers $headers
  Write-Host "workflow_id:" $wf.workflow.workflow_id "status:" $wf.workflow.status
} catch {
  Write-Host "Workflow create failed:" $_
  exit 1
}

Write-Host "`nDone. Check Slack channel for Incoming Webhook messages if APP_SLACK_WEBHOOK_URL is valid."
