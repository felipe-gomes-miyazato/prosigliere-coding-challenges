import datetime

# Fake currency client that returns fixed rates for demo/testing
class CurrencyClient:
    def __init__(self, rates=None):
        # rates is a dict like {('EUR','USD'):{'2025-09-01':1.08}}
        self.rates = rates or {}

    def get_rate(self, date: datetime.date, currency_from: str, currency_to: str) -> float:
        key = (currency_from.upper(), currency_to.upper())
        date_key = date.isoformat()
        if key in self.rates and date_key in self.rates[key]:
            return self.rates[key][date_key]
        # fallback demo rates
        demo = {
            ('EUR','USD'): 1.08,
            ('GBP','USD'): 1.25,
            ('USD','USD'): 1.0
        }
        return demo.get(key, 1.0)
