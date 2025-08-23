import cbpro
import os
from dotenv import load_dotenv

load_dotenv(".env.exchange_sandbox")

class ExchangeSandboxClient:
    def __init__(self):
        self.client = cbpro.AuthenticatedClient(
            os.getenv("EXCHANGE_SANDBOX_KEY"),
            os.getenv("EXCHANGE_SANDBOX_SECRET"),
            os.getenv("EXCHANGE_SANDBOX_PASSPHRASE"),
            api_url="https://api-public.sandbox.exchange.coinbase.com"
        )
        print("Connected to Exchange sandbox")
    
    def get_accounts(self):
        return self.client.get_accounts()
