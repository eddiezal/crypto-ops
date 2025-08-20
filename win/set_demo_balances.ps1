Param([double]$usd=100000,[double]$btc=1.0,[double]$eth=20.0,[string]$account="trading")
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
try { py -3 scripts\set_balances.py -a $account --usd $usd --btc $btc --eth $eth } catch { python scripts\set_balances.py -a $account --usd $usd --btc $btc --eth $eth }
