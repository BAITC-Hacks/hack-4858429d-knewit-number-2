param([int]$BackendPort = 8000)

$ErrorActionPreference = 'Stop'
$taskBackend = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend'
$taskPython = Join-Path $taskBackend '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw "Backend virtual environment is missing: $taskPython"
}

# Keep the variable present so load_dotenv cannot restore an OpenAI key.
# The provider selector strips whitespace and treats this value as disabled.
$env:OPENAI_API_KEY = ' '
$env:NVIDIA_API_KEY = 'local-brev'
$env:NVIDIA_BASE_URL = 'http://127.0.0.1:9000/v1'
$env:NVIDIA_MODEL = 'nvidia/NVIDIA-Nemotron-Nano-9B-v2'
$env:AI_MODE = 'auto'
$env:PYTHONIOENCODING = 'utf-8'

Push-Location $taskBackend
try {
    Write-Host 'Starting TaskReady with NVIDIA through the SSH tunnel on localhost:9000.'
    & $taskPython -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort
    $taskExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExitCode
