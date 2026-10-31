# pull_pw_backup.ps1 - copies the newest staged PW backup from the VM to this PC and checks its sha256.
# Keeps the newest $Keep (8 = about 2 months of weekly copies). Log: <Dest>\pull.log
# Usage: powershell -ExecutionPolicy Bypass -File pull_pw_backup.ps1 -Vm user@192.168.56.x -Dest D:\PWBackups
param(
    [Parameter(Mandatory = $true)][string]$Vm,          # user@address of the server VM (the user set in pw_offsite_stage.sh)
    [Parameter(Mandatory = $true)][string]$Dest,        # folder on this PC; use a different drive than the VM if you can
    [string]$Key = "$env:USERPROFILE\.ssh\pw_backup",   # SSH key used only for this job
    [int]$Keep = 8
)
$ErrorActionPreference = 'Stop'
$fallbackLog = Join-Path $PSScriptRoot 'pull.log'
$root = [System.IO.Path]::GetPathRoot($Dest)
if ($root -and -not (Test-Path $root)) {
    Add-Content -Path $fallbackLog -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm') + " drive $root not found, backup not pulled")
    exit 1
}
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
function Log($m) { Add-Content -Path "$Dest\pull.log" -Value ("{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'), $m) }
try {
    $remote = "$(ssh -i $Key -o BatchMode=yes -o ConnectTimeout=15 $Vm 'ls -1t ~/offsite/pw_backup_*.tar 2>/dev/null | head -1')".Trim()
    if (-not $remote) { Log 'no staged backup on the VM (or the VM did not answer)'; exit 1 }
    $name = Split-Path $remote -Leaf
    if (Test-Path "$Dest\$name") { Log "$name already here, nothing to do"; exit 0 }
    scp -i $Key -o BatchMode=yes "${Vm}:$remote" "$Dest\$name.part"
    $want = ((ssh -i $Key -o BatchMode=yes $Vm "cat $remote.sha256") -split '\s+')[0]
    $got  = (Get-FileHash "$Dest\$name.part" -Algorithm SHA256).Hash.ToLower()
    if ($want -ne $got) { Remove-Item "$Dest\$name.part"; Log "$name CHECKSUM MISMATCH, deleted"; exit 1 }
    Rename-Item "$Dest\$name.part" $name
    Log ("pulled {0} ({1:N0} MB), checksum OK" -f $name, ((Get-Item "$Dest\$name").Length / 1MB))
    Get-ChildItem $Dest -Filter 'pw_backup_*.tar' | Sort-Object LastWriteTime -Descending | Select-Object -Skip $Keep | Remove-Item
} catch { Log ("FAILED: " + $_.Exception.Message); exit 1 }
