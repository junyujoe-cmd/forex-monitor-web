def calculate_bp(quote, cost):
    return round(abs(quote - cost) * 10000, 1)


def market_cost_price(market_bid, market_ask):
    if market_bid and market_ask:
        return round((market_bid + market_ask) / 2, 4)
    return market_bid or market_ask


def bank_cost_price(bank_bid, bank_ask):
    return round((bank_bid + bank_ask) / 2, 4)


def compute_entry_result(user_quote, direction, market_bid, market_ask, bank_bid, bank_ask):
    market_mid = market_cost_price(market_bid, market_ask)
    bank_mid = bank_cost_price(bank_bid, bank_ask)
    bp_vs_market = calculate_bp(user_quote, market_mid)
    bp_vs_bank = calculate_bp(user_quote, bank_mid)
    return {
        "market_cost": market_mid,
        "bank_cost": bank_mid,
        "bp_vs_market": bp_vs_market,
        "bp_vs_bank": bp_vs_bank,
    }
