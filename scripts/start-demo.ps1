param(
    [switch]$LiveAgents,
    [string]$Model = "gpt-5.4-mini",
    [string]$ProjectModel = "",
    [string]$EvaluatorModel = "",
    [string]$AgentRoot = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$demoDir = Join-Path $repoRoot ".workbench\demo"
$dbPath = Join-Path $demoDir "review-workbench-demo.sqlite3"
$sessionPath = Join-Path $demoDir "workspace-session-demo.json"
$resolvedAgentRoot = if ($AgentRoot.Trim()) { (Resolve-Path $AgentRoot).Path } else { $repoRoot }
$resolvedProjectModel = if ($ProjectModel.Trim()) { $ProjectModel } else { $Model }
$resolvedEvaluatorModel = if ($EvaluatorModel.Trim()) { $EvaluatorModel } else { $Model }

Set-Location $repoRoot

$backendCommandLines = @(
    "Set-Location '$repoRoot'",
    "`$env:REVIEW_WORKBENCH_DB_PATH = '$dbPath'",
    "`$env:REVIEW_WORKBENCH_SESSION_PATH = '$sessionPath'"
)

if ($LiveAgents) {
    $backendCommandLines += @(
        "`$env:REVIEW_WORKBENCH_USE_LOCAL_PROJECT_AGENT = 'true'",
        "`$env:REVIEW_WORKBENCH_PROJECT_AGENT_ROOT = '$resolvedAgentRoot'",
        "`$env:REVIEW_WORKBENCH_PROJECT_AGENT_MODEL = '$resolvedProjectModel'",
        "`$env:REVIEW_WORKBENCH_USE_LOCAL_EVALUATOR_AGENT = 'true'",
        "`$env:REVIEW_WORKBENCH_EVALUATOR_AGENT_ROOT = '$resolvedAgentRoot'",
        "`$env:REVIEW_WORKBENCH_EVALUATOR_AGENT_MODEL = '$resolvedEvaluatorModel'"
    )
}

$backendCommandLines += "python -m uvicorn review_gate.http_api:app --host 127.0.0.1 --port 8000"
$backendCommand = $backendCommandLines -join [Environment]::NewLine

$frontendCommand = @(
    "Set-Location '$repoRoot'",
    "npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173"
) -join [Environment]::NewLine

if ($DryRun) {
    Write-Host "Backend command:"
    Write-Host $backendCommand
    Write-Host ""
    Write-Host "Frontend command:"
    Write-Host $frontendCommand
    exit 0
}

Write-Host "Seeding demo workspace..."
& python scripts/seed_demo_data.py --db-path $dbPath --session-path $sessionPath

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
if ($LiveAgents) {
    Write-Host "Live agents: enabled"
    Write-Host "  Agent root:      $resolvedAgentRoot"
    Write-Host "  Project model:   $resolvedProjectModel"
    Write-Host "  Evaluator model: $resolvedEvaluatorModel"
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null

Write-Host "Starting frontend on http://127.0.0.1:5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand | Out-Null

Write-Host ""
Write-Host "Demo URLs:"
Write-Host "  Frontend: http://127.0.0.1:5173"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "Demo DB:     $dbPath"
Write-Host "Demo Session:$sessionPath"
