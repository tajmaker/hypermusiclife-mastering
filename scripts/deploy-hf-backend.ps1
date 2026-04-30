param(
    [string]$SpaceRemote = "hf",
    [string]$BackendSubtree = "MasteringBackend",
    [string]$TargetBranch = "main",
    [switch]$ForceWithLease
)

$ErrorActionPreference = "Stop"

git rev-parse --show-toplevel | Out-Null

Write-Host "Deploying $BackendSubtree to Hugging Face remote '$SpaceRemote'..."
Write-Host "Target branch: $TargetBranch"
Write-Host "If Hugging Face asks for a password, use an access token with write permissions."
Write-Host "Token page: https://huggingface.co/settings/tokens"

$dirtyBackend = git status --porcelain -- $BackendSubtree
if ($dirtyBackend) {
    Write-Error "There are uncommitted changes in $BackendSubtree. Commit them before deploy; git subtree only deploys committed history."
    Write-Host $dirtyBackend
    exit 1
}

if (-not $ForceWithLease) {
    git subtree push --prefix $BackendSubtree $SpaceRemote $TargetBranch
    exit $LASTEXITCODE
}

$tempBranch = "deploy/hf-backend-temp"
Write-Host "Force-with-lease mode enabled."
Write-Host "Fetching remote branch before push..."
git fetch $SpaceRemote $TargetBranch

Write-Host "Preparing backend subtree branch: $tempBranch"
git show-ref --verify --quiet "refs/heads/$tempBranch"
if ($LASTEXITCODE -eq 0) {
    git branch -D $tempBranch | Out-Null
}
git subtree split --prefix $BackendSubtree -b $tempBranch

try {
    Write-Host "Pushing $BackendSubtree to $SpaceRemote/$TargetBranch with --force-with-lease..."
    git push $SpaceRemote "${tempBranch}:${TargetBranch}" --force-with-lease
}
finally {
    git show-ref --verify --quiet "refs/heads/$tempBranch"
    if ($LASTEXITCODE -eq 0) {
        git branch -D $tempBranch | Out-Null
    }
}
