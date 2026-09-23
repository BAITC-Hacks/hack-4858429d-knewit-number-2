param(
    [string]$ServerAddress = '64.247.196.218',
    [int]$SshPort = 22,
    [int]$LocalPort = 9000
)

$ErrorActionPreference = 'Stop'
$taskSshDirectory = Join-Path $env:USERPROFILE '.ssh'
$taskIdentity = Join-Path $taskSshDirectory 'taskready_brev_ed25519'
$taskKnownHosts = Join-Path $taskSshDirectory 'taskready_brev_known_hosts'

foreach ($taskRequiredFile in @($taskIdentity, $taskKnownHosts)) {
    if (-not (Test-Path -LiteralPath $taskRequiredFile)) {
        throw "Missing SSH file: $taskRequiredFile. Configure the key and verify the server fingerprint first."
    }
}

# Refuse to replace a running tunnel or an unrelated service on this port.
$taskListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $LocalPort)
try {
    $taskListener.Start()
} catch {
    throw "Local port $LocalPort is already in use. Check the existing tunnel before starting another."
} finally {
    $taskListener.Stop()
}

$taskSshArguments = @(
    '-F', 'NUL', '-N', '-T',
    '-i', $taskIdentity,
    '-o', ('UserKnownHostsFile="{0}"' -f $taskKnownHosts.Replace('\', '/')),
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'HostKeyAlgorithms=ssh-ed25519',
    '-o', 'IdentitiesOnly=yes',
    '-o', 'BatchMode=yes',
    '-o', 'ConnectTimeout=10',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-L', "127.0.0.1:${LocalPort}:127.0.0.1:8000",
    '-p', $SshPort.ToString(),
    "shadeform@$ServerAddress"
)

Write-Host "Forwarding localhost:$LocalPort to the model in Brev. Keep this window open; Ctrl+C closes the tunnel."
& ssh.exe @taskSshArguments
exit $LASTEXITCODE
