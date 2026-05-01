# PostgreSQL 备份脚本 (Windows PowerShell)
# 使用方式：.\backup.ps1 [备份目录]
# 示例：.\backup.ps1 D:\backups

param(
    [string]$BackupDir = ".\backups"
)

$ErrorActionPreference = "Stop"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "sales_mgmt_$Timestamp.sql.gz"

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

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$Timestamp2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$Timestamp2] 开始备份数据库 $PgDb..."

$env:PGPASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "" }

# 使用 pg_dump 备份并压缩
$DumpArgs = @("-h", $PgHost, "-p", $PgPort, "-U", $PgUser, $PgDb)
$TempFile = Join-Path $BackupDir "sales_mgmt_$Timestamp.sql"

try {
    & pg_dump @DumpArgs | Out-File -Encoding utf8 $TempFile
    # 使用 gzip 如果可用，否则直接保留 .sql
    if (Get-Command gzip -ErrorAction SilentlyContinue) {
        & gzip -f $TempFile
        $FinalFile = "$TempFile.gz"
    } else {
        $FinalFile = $TempFile
        Compress-Archive -Path $TempFile -DestinationPath "$TempFile.zip" -Force
        Remove-Item $TempFile -Force
        $FinalFile = "$TempFile.zip"
    }

    $FileSize = (Get-Item $FinalFile).Length / 1MB
    Write-Host "[$Timestamp2] 备份完成: $FinalFile ($([math]::Round($FileSize, 2)) MB)"
} catch {
    Write-Host "[$Timestamp2] 备份失败: $_"
    exit 1
}

# 清理旧备份：保留最近 7 天每日备份 + 最近 4 周每周保留一份
$Cutoff7 = (Get-Date).AddDays(-7)
$Cutoff28 = (Get-Date).AddDays(-28)

Get-ChildItem -Path $BackupDir -Filter "sales_mgmt_*" | Where-Object {
    $_.LastWriteTime -lt $Cutoff7
} | ForEach-Object {
    # 保留周一备份 4 周
    if ($_.LastWriteTime.DayOfWeek -eq "Monday" -and $_.LastWriteTime -ge $Cutoff28) {
        return
    }
    if ($_.LastWriteTime.DayOfWeek -eq "Monday" -and $_.LastWriteTime -lt $Cutoff28) {
        Remove-Item $_.FullName -Force
        return
    }
    Remove-Item $_.FullName -Force
}

Write-Host "[$Timestamp2] 已清理旧备份（保留 7 天每日 + 4 周每周）"
