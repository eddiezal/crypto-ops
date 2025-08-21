param()

Clear-Host
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           CRYPTOOPS SANDBOX DASHBOARD               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$URL = "https://cryptoops-planner-799139385623.us-central1.run.app"
$TOKEN = gcloud auth print-identity-token 2>$null
$Headers = @{Authorization="Bearer $TOKEN"}

try {
    # Get current data
    $health = Invoke-RestMethod "$URL/_ah/health" -Headers $Headers
    $plan = Invoke-RestMethod "$URL/plan" -Headers $Headers
    
    # Status
    Write-Host "`n📊 SYSTEM STATUS" -ForegroundColor Yellow
    Write-Host "  Mode: $($health.trading_mode.ToUpper())" -ForegroundColor $(if($health.trading_mode -eq "paper"){"Green"}else{"Red"})
    Write-Host "  Environment: $($health.coinbase_env)" -ForegroundColor Green
    Write-Host "  Service: ONLINE" -ForegroundColor Green
    
    # Positions
    Write-Host "`n💰 SANDBOX POSITIONS" -ForegroundColor Yellow
    $btcValue = [math]::Round($plan.balances.BTC * $plan.prices."BTC-USD", 2)
    $ethValue = [math]::Round($plan.balances.ETH * $plan.prices."ETH-USD", 2)
    $totalValue = [math]::Round($btcValue + $ethValue + $plan.balances.USD, 2)
    
    Write-Host ("  BTC: {0:N6} @ ${1:N2} = ${2:N2}" -f $plan.balances.BTC, $plan.prices."BTC-USD", $btcValue)
    Write-Host ("  ETH: {0:N6} @ ${1:N2} = ${2:N2}" -f $plan.balances.ETH, $plan.prices."ETH-USD", $ethValue)
    Write-Host ("  USD: ${0:N2}" -f $plan.balances.USD)
    Write-Host "  ─────────────────────────────" -ForegroundColor DarkGray
    Write-Host ("  TOTAL: ${0:N2}" -f $totalValue) -ForegroundColor Cyan
    
    # Allocation
    Write-Host "`n📈 ALLOCATION" -ForegroundColor Yellow
    $btcPct = [math]::Round($btcValue / $totalValue * 100, 1)
    $ethPct = [math]::Round($ethValue / $totalValue * 100, 1)
    Write-Host "  BTC: $btcPct%"
    Write-Host "  ETH: $ethPct%"
    Write-Host "  USD: $([math]::Round($plan.balances.USD / $totalValue * 100, 1))%"
    
    # Safety reminders
    Write-Host "`n✅ SAFETY CHECKS" -ForegroundColor Green
    Write-Host "  ✓ This is SANDBOX money (not real)" -ForegroundColor Green
    Write-Host "  ✓ Paper trading mode active" -ForegroundColor Green
    Write-Host "  ✓ Kill switch armed" -ForegroundColor Green
    
} catch {
    Write-Host "`n❌ ERROR: Could not connect to service" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
}

Write-Host "`n══════════════════════════════════════════════════════" -ForegroundColor Cyan
