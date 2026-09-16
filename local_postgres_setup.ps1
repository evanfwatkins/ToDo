$ErrorActionPreference = 'Stop'

$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
$pgData = 'C:\Program Files\PostgreSQL\18\data'
$serviceName = 'postgresql-x64-18'
$dbName = 'todo_app'
$dbUser = 'todo_app_user'
$dbPassword = 'todo_password'

if (-not (Test-Path (Join-Path $pgBin 'psql.exe'))) {
    Write-Error "PostgreSQL does not appear to be installed at $pgBin. Download it from: https://www.postgresql.org/download/windows/"
    exit 1
}

$env:PATH += ';' + $pgBin

if (-not (Get-Service -Name $serviceName -ErrorAction SilentlyContinue)) {
    Write-Host 'Initializing PostgreSQL data directory...'
    & (Join-Path $pgBin 'initdb.exe') -D $pgData --username=postgres --auth=trust
}

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($null -ne $service -and $service.Status -ne 'Running') {
    Start-Service -Name $serviceName
}

$existingDb = psql -U postgres -h localhost -d postgres -At -c "SELECT 1 FROM pg_database WHERE datname = '$dbName';"
if (-not $existingDb) {
    Write-Host "Creating database: $dbName"
    createdb -U postgres -h localhost $dbName
}

$existingUser = psql -U postgres -h localhost -d postgres -At -c "SELECT 1 FROM pg_roles WHERE rolname = '$dbUser';"
if (-not $existingUser) {
    Write-Host "Creating user: $dbUser"
    psql -U postgres -h localhost -d postgres -c "CREATE USER $dbUser WITH PASSWORD '$dbPassword';"
}

psql -U postgres -h localhost -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;"

Write-Host "Done."
Write-Host "Connect with:"
Write-Host "  psql -U $dbUser -h localhost -d $dbName"
Write-Host "Password: $dbPassword"
