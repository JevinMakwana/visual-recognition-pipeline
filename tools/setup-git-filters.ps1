<#
.SYNOPSIS
    Register the notebook-stripping git filter for this repo. Run once after `git init`
    (and once on every fresh clone), from anywhere inside the repo:

        powershell -NoProfile -ExecutionPolicy Bypass -File tools\setup-git-filters.ps1
#>
$ErrorActionPreference = 'Stop'

$root = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'Not inside a git repository. Run git init first.' }
Set-Location $root

# Git runs filters from the repo root, so the relative script path resolves.
$cmd = 'powershell -NoProfile -ExecutionPolicy Bypass -File tools/strip-notebook.ps1'

git config filter.nbstrip.clean $cmd
git config filter.nbstrip.smudge cat
git config filter.nbstrip.required true   # fail the commit rather than commit outputs
git config diff.nbstrip.textconv $cmd

Write-Host 'Notebook output stripping enabled for this repo.'
Write-Host 'Run "git add --renormalize ." if notebooks were staged before this.'
