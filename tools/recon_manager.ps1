param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("analyze", "sync", "check")]
    [string]$Action,
    
    [string]$AbsUSD = "100",
    [string]$Pct = "2.0",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

switch ($Action) {
    "analyze" {
        Write-Host "=== Analyzing Drift ===" -ForegroundColor Cyan
        
        # Run reconciliation
        python -c @"
from decimal import Decimal
from apps.recon.coinbase_recon import reconcile_once
import json
rec = reconcile_once(Decimal('$AbsUSD'), Decimal('$Pct'))
print(json.dumps(rec, indent=2))
with open('logs/recon/last_recon.json', 'w') as f:
    json.dump(rec, f)
"@
        
        # Analyze the drift
        python -c @"
import json
with open('logs/recon/last_recon.json') as f:
    rec = json.load(f)
    
print('\nDrift Summary:')
for asset in ['USD', 'BTC', 'ETH']:
    d = rec['drift'][asset]
    print(f"  {asset}: Exchange={d['exchange']}, State={d['state']}, Drift={d['drift_pct']}%")
    
if rec['ok']:
    print('\n✅ Within thresholds')
else:
    print('\n⚠️  Exceeds thresholds - consider sync')
"@
    }
    
    "sync" {
        if (-not $Force) {
            Write-Host "This will overwrite your state with exchange balances!" -ForegroundColor Yellow
            $confirm = Read-Host "Type 'SYNC-STATE' to proceed"
            if ($confirm -ne 'SYNC-STATE') {
                Write-Host "Aborted" -ForegroundColor Red
                exit 1
            }
        }
        
        # Backup, sync, and log
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Copy-Item .\state\balances.json ".\state\balances_backup_$timestamp.json"
        
        # Get and save new state
        python -c @"
from apps.exchange.coinbase_client import CoinbaseAdv
import json
client = CoinbaseAdv()
b = client.get_balances()
new_state = {
    'USD': float(b.get('USD', 0)),
    'BTC': float(b.get('BTC', 0)),
    'ETH': float(b.get('ETH', 0))
}
print(json.dumps(new_state, indent=2))
with open('state/balances.json', 'w') as f:
    json.dump(new_state, f, indent=2)
"@
        
        Write-Host "✅ State synced from exchange" -ForegroundColor Green
    }
    
    "check" {
        # Just run a check with current thresholds
        python -c @"
from decimal import Decimal
from apps.recon.coinbase_recon import reconcile_once
rec = reconcile_once(Decimal('$AbsUSD'), Decimal('$Pct'))
exit(0 if rec['ok'] else 1)
"@
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Reconciliation OK" -ForegroundColor Green
        } else {
            Write-Host "❌ Drift detected" -ForegroundColor Red
            exit 1
        }
    }
}
