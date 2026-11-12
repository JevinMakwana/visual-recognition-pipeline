<#
.SYNOPSIS
    Strip outputs and execution counts from a Jupyter notebook (nbstripout replacement).

.DESCRIPTION
    Used as a git filter so committed notebooks contain only code and markdown.
    Reads the notebook from a file path (if given) or from stdin, and writes the
    stripped notebook as UTF-8 to stdout. The working-copy notebook is never modified.

    - clean filter:  git pipes the notebook on stdin
    - diff textconv: git passes a temp file path as the first argument

    Pure PowerShell 5.1, no Python required.
#>
param([string]$Path)

$ErrorActionPreference = 'Stop'

# PS 5.1 quirk: the ETS 'Count' property on System.Array makes ConvertTo-Json emit
# {"value":[...],"Count":n} instead of [...]. Removing the type data fixes it.
Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue

$utf8 = New-Object System.Text.UTF8Encoding($false)

if ($Path) {
    $text = [System.IO.File]::ReadAllText($Path, $utf8)
} else {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), $utf8)
    $text = $reader.ReadToEnd()
}

$nb = $text | ConvertFrom-Json

foreach ($cell in $nb.cells) {
    if ($cell.cell_type -eq 'code') {
        $cell.outputs = @()
        $cell.execution_count = $null
    }
    # Per-cell execution timing/run metadata changes on every run; drop it.
    if ($cell.metadata) {
        foreach ($key in 'execution', 'collapsed', 'scrolled', 'ExecuteTime') {
            if ($cell.metadata.PSObject.Properties[$key]) {
                $cell.metadata.PSObject.Properties.Remove($key)
            }
        }
    }
}

# Widget state is output, not source.
if ($nb.metadata -and $nb.metadata.PSObject.Properties['widgets']) {
    $nb.metadata.PSObject.Properties.Remove('widgets')
}

$json = ($nb | ConvertTo-Json -Depth 100) -replace "`r`n", "`n"

$bytes = $utf8.GetBytes($json + "`n")
$out = [Console]::OpenStandardOutput()
$out.Write($bytes, 0, $bytes.Length)
$out.Flush()
