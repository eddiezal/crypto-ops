# Two Projects on the Same PC (Windows)

1) Copy this folder to two locations:
```
F:\CryptoOps\alpha\
F:\CryptoOps\beta\
```
2) In each copy:
- Run `.\win\setup.ps1`
- Open `.env` with `.\win\open_env.ps1` and set unique `PROJECT_NAME` and distinct Notion DB IDs.
3) Open two PowerShell tabs and run:
```
alpha> .\win\run_rebalancer.ps1
beta>  .\win\run_basis.ps1
```
