$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw '未找到 Python 3.10+，请先安装 Python。' }
python -m gui
