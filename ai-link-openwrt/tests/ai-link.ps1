# AI-LINK 维护入口（Windows / PowerShell）
#
#   .\ai-link.ps1 check        发布环境自检（11 项门禁 + 仓库可达性）
#   .\ai-link.ps1 test         跑完整验证套件（门禁 / OTA / 密码 / 面板 / 自检）
#   .\ai-link.ps1 online       核对线上 Release、清单、Pages 部署
#   .\ai-link.ps1 build -Version 1.0.2     只打包，输出指纹
#   .\ai-link.ps1 publish -Version 1.0.2   完整发布（会真的推送）
#
# 说明：
#   * 默认操作 project\site 这份工作副本，不改动 F:\wkbdai 下的原仓库
#   * Windows 上必须用 Git 自带的 bash，PATH 里 WSL 的 bash 会让门禁卡死，脚本已处理
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('check', 'test', 'online', 'build', 'publish')]
    [string]$Task = 'check',

    [string]$Version,

    [switch]$Strict,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Site = Join-Path $ProjectRoot 'site'
$EnvFile = Join-Path $env:USERPROFILE '.workbuddy-ai\ai-link-release.env'
$Skill = Join-Path $env:USERPROFILE '.workbuddy-ai\skills\ai-link-release\scripts\release.py'

# 读取凭据文件里的解释器路径（不含任何令牌）
$cfg = @{}
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.TrimStart([char]0xFEFF).Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $k, $v = $line.Split('=', 2)
            $cfg[$k.Trim()] = $v.Trim().Trim('"').Trim("'")
        }
    }
}

$py = if ($cfg['PYTHON_BIN'] -and (Test-Path $cfg['PYTHON_BIN'])) { $cfg['PYTHON_BIN'] } else { (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw '找不到 Python：请在 ai-link-release.env 里设置 PYTHON_BIN' }

$nodeBin = $cfg['NODE_BIN']
$gitBin = 'C:\Program Files\Git\bin'
$gitUsrBin = 'C:\Program Files\Git\usr\bin'
if (-not (Test-Path $gitBin)) { throw "找不到 Git for Windows：$gitBin（门禁与自检都需要它提供的 bash / openssl）" }

$env:AI_LINK_SITE = $Site
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
if ($nodeBin) { $env:NODE_BIN = $nodeBin }
$env:PATH = "$gitUsrBin;$gitBin;" + $env:PATH

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

switch ($Task) {
    'check' {
        & $py -u $Skill check
    }
    'test' {
        $cliArgs = @((Join-Path $ProjectRoot 'tests\run_all.py'))
        if ($Strict) { $cliArgs += '--strict' }
        & $py -u @cliArgs
    }
    'online' {
        & $py -u (Join-Path $ProjectRoot 'tools\verify_online.py')
    }
    'build' {
        if (-not $Version) { throw 'build 需要 -Version，例如 -Version 1.0.2' }
        & $py -u $Skill build --version $Version
    }
    'publish' {
        if (-not $Version) { throw 'publish 需要 -Version，例如 -Version 1.0.2' }
        $cliArgs = @($Skill, 'publish', '--version', $Version)
        if ($DryRun) { $cliArgs += '--dry-run' }
        & $py -u @cliArgs
    }
}

exit $LASTEXITCODE
