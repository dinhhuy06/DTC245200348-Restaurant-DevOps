$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$composeArgs = @('compose','-f','compose.yaml','-f','compose.override.yaml','-f','compose.monitoring.yaml','-f','compose.logging.yaml','-f','compose.hardening.yaml')
function DockerCheck([string[]] $Arguments) {
    & docker @composeArgs @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker check failed: $($Arguments -join ' ')" }
}
DockerCheck @('config','--quiet')
DockerCheck @('ps','-a')
DockerCheck @('exec','-T','app','id')
DockerCheck @('exec','-T','app','sh','-c','test ! -w /app && echo app-filesystem-readonly')
foreach ($u in @('http://localhost:8080/health','http://localhost:5050','http://localhost:3000/api/health')) {
    $r = Invoke-WebRequest $u -TimeoutSec 15
    Write-Output "$u : $($r.StatusCode)"
}
$r = Invoke-WebRequest 'http://localhost:8080' -TimeoutSec 15
foreach($h in @('X-Content-Type-Options','X-Frame-Options','Referrer-Policy')) {
    if (-not $r.Headers[$h]) { throw "Missing security header: $h" }
    Write-Output "$h : $($r.Headers[$h])"
}
$t = Invoke-RestMethod 'http://localhost:9090/api/v1/targets' -TimeoutSec 15
foreach($j in @('prometheus','nginx','postgres','containers')) {
    $targets = @($t.data.activeTargets | Where-Object { $_.labels.job -eq $j })
    if ($targets.Count -eq 0 -or @($targets | Where-Object { $_.health -ne 'up' }).Count -gt 0) { throw "Target not UP: $j" }
    Write-Output "Prometheus target $j : UP"
}
DockerCheck @('exec','-T','postgres','psql','-U','restaurant_owner','-d','restaurant','-c',"SELECT rolname, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname IN ('restaurant_app','restaurant_monitor');")
DockerCheck @('exec','-T','app','python','-c',"import os,psycopg; c=psycopg.connect(host=os.environ['DB_HOST'],dbname=os.environ['DB_NAME'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD']); print('App DB role:',c.execute('select current_user').fetchone()[0]); print('Dishes:',c.execute('select count(*) from dishes').fetchone()[0]); c.close()")
Write-Output 'Runtime read-only checks completed. Perform the website workflow and LogQL demo in README manually.'
