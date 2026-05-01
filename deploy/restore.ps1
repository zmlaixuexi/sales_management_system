# PostgreSQL 恢复脚本 (Windows PowerShell)
# 使用方式：.\restore.ps1 <备份文件>
# 示例：.\restore.ps1 D:\backups\sales_mgmt_20260501_120000.sql.gz

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Host "错误: 文件 $BackupFile 不存在"
    exit 1
}

# 从 .env 读取配置
$EnvFile = Join-Path $PSScriptRoot ".." ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), "Process")
        }
    }
}

$PgHost = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$PgPort = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$PgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$PgDb = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "sales_management" }

$env:PGPASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "" }

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$Timestamp] 警告: 此操作将清空并恢复数据库 $PgDb！"
$Confirm = Read-Host "确认继续? (yes/no)"
if ($Confirm -ne "yes") {
    Write-Host "已取消"
    exit 0
}

Write-Host "[$Timestamp] 开始从 $BackupFile 恢复..."

# 解压备份文件
$SqlFile = $BackupFile
if ($BackupFile -match '\.gz$') {
    if (Get-Command gzip -ErrorAction SilentlyContinue) {
        $SqlFile = $BackupFile -replace '\.gz$', ''
        & gzip -dk $BackupFile
    } else {
        Write-Host "错误: 需要安装 gzip 工具来解压 .gz 文件"
        exit 1
    }
} elseif ($BackupFile -match '\.zip$') {
    $SqlFile = $BackupFile -replace '\.zip$', ''
    Expand-Archive -Path $BackupFile -DestinationPath (Split-Path $BackupFile) -Force
}

try {
    # 终止现有连接
    $PsqlArgs = @("-h", $PgHost, "-p", $PgPort, "-U", $PgUser, "-d", "postgres", "-c",
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$PgDb';")
    & psql @PsqlArgs 2>$null

    # 重建数据库
    $DropArgs = @("-h", $PgHost, "-p", $PgPort, "-U", $PgUser, "-e", $PgDb)
    & dropdb @DropArgs 2>$null

    $CreateArgs = @("-h", $PgHost, "-p", $PgPort, "-U", $PgUser, $PgDb)
    & createdb @CreateArgs

    # 恢复数据
    $RestoreArgs = @("-h", $PgHost, "-p", $PgPort, "-U", $PgUser, "-d", $PgDb, "-f", $SqlFile)
    & psql @RestoreArgs

    $Timestamp2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$Timestamp2] 恢复完成"
} catch {
    Write-Host "恢复失败: $_"
    exit 1
} finally {
    # 清理解压的临时文件
    if ($SqlFile -ne $BackupFile -and (Test-Path $SqlFile)) {
        Remove-Item $SqlFile -Force
    }
}
