# Script para liberar Python no Firewall do Windows
# Execute como Administrador

Write-Host "Desabilitando regras de bloqueio do Python..." -ForegroundColor Yellow

# Desabilita todas as regras que bloqueiam Python
Get-NetFirewallRule | Where-Object { 
    $_.DisplayName -like "*Python*" -and $_.Action -eq "Block" 
} | ForEach-Object {
    Write-Host "Desabilitando regra: $($_.DisplayName)" -ForegroundColor Cyan
    Disable-NetFirewallRule -Name $_.Name
}

Write-Host "`nVerificando regra da porta 5000..." -ForegroundColor Yellow
$regra5000 = Get-NetFirewallRule -DisplayName "Flask Server - Porta 5000" -ErrorAction SilentlyContinue

if ($regra5000) {
    Write-Host "Regra da porta 5000 já existe e está ativa!" -ForegroundColor Green
} else {
    Write-Host "Criando regra para porta 5000..." -ForegroundColor Yellow
    New-NetFirewallRule -DisplayName "Flask Server - Porta 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
    Write-Host "Regra criada com sucesso!" -ForegroundColor Green
}

Write-Host "`nListando regras Python ativas:" -ForegroundColor Yellow
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*Python*" } | Select-Object DisplayName, Enabled, Direction, Action | Format-Table -AutoSize

Write-Host "`n✓ Firewall configurado! Tente acessar http://192.168.173.217:5000 do celular" -ForegroundColor Green
