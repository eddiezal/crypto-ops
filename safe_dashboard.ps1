Clear-Host
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          CRYPTOOPS SANDBOX DASHBOARD                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan

$URL = "https://cryptoops-planner-799139385623.us-central1.run.app"
$TOKEN = gcloud auth print-identity-token 2>$null
$Headers = @{Authorization="Bearer $TOKEN"}

# Health check
try {
    $health = Invoke-RestMethod "$URL/_ah/health" -Headers $Headers
    Write-Host "`n📊 SYSTEM STATUS" -ForegroundColor Yellow
    Write-Host "  ✅ Service: ONLINE" -ForegroundColor Green
    Write-Host "  ✅ Mode: $($health.trading_mode)" -ForegroundColor Green
    Write-Host "  ✅ Environment: $($health.coinbase_env)" -ForegroundColor Green
    Write-Host "  ✅ Revision: $($health.revision)" -ForegroundColor Gray
} catch {
    Write-Host "  ❌ Health check failed" -ForegroundColor Red
}

# Try plan endpoint
try {
    $plan = Invoke-RestMethod "$URL/plan" -Headers $Headers -ErrorAction Stop
    
    if ($plan.balances) {
        Write-Host "`n💰 POSITIONS" -ForegroundColor Yellow
        Write-Host "  BTC: $($plan.balances.BTC)"
        Write-Host "  ETH: $($plan.balances.ETH)"
        Write-Host "  USD: $($plan.balances.USD)"
    }
    
    if ($plan.total_value) {
        Write-Host "  Total: `$$($plan.total_value)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "`n⚠️ Plan endpoint unavailable" -ForegroundColor Yellow
    Write-Host "  Using hardcoded sandbox values:" -ForegroundColor Gray
    Write-Host "  BTC: 1.703532" -ForegroundColor White
    Write-Host "  ETH: 19.972826" -ForegroundColor White
    Write-Host "  USD: 2,683.02" -ForegroundColor White
    Write-Host "  Total: `$281,925 (SANDBOX)" -ForegroundColor Cyan
}

Write-Host "`n══════════════════════════════════════════════════════" -ForegroundColor Cyan
