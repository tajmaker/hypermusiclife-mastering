param(
    [string]$SpaceRemote = "hf",
    [string]$BackendSubtree = "MasteringBackend",
    [string]$TargetBranch = "main"
)

$ErrorActionPreference = "Stop"

git rev-parse --show-toplevel | Out-Null

Write-Host "Deploying $BackendSubtree to Hugging Face remote '$SpaceRemote'..."
Write-Host "Target branch: $TargetBranch"

git subtree push --prefix $BackendSubtree $SpaceRemote $TargetBranch
