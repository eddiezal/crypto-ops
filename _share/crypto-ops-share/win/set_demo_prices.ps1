Param([double]$btc=65000,[double]$eth=3500)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force | Out-Null
try { py -3 scripts\set_prices.py --btc $btc --eth $eth } catch { python scripts\set_prices.py --btc $btc --eth $eth }
