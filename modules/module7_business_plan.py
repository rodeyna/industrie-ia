import os
import json

def calculate_roi(revenue, cost):
    """Formula: (Earnings - Cost) / Cost"""
    if cost == 0: return 0
    return (revenue - cost) / cost
def calculate_van(initial_investment, cash_flow, rate=0.1):
    """VAN is how much the project is worth in 3 years"""
    # Simple 3-year projection
    van = -initial_investment
    for year in range(1, 4):
        van += cash_flow / ((1 + rate) ** year)
    return van


def run_module_7(shared_state=None):
    print("🚀 Module 7: Calculating Financials...")

    # MOCK DATA (Change these when your friends finish!)
    cost_of_200_valves = 45000.0  # From Module 6 (TCO)
    estimated_sales = 80000.0     # What we think we can sell them for
    yearly_profit = 15000.0       # Expected profit each year

    # DO THE MATH
    final_roi = calculate_roi(estimated_sales, cost_of_200_valves)
    final_van = calculate_van(cost_of_200_valves, yearly_profit)

    print(f"📊 Business Plan Results:")
    print(f"   -> ROI: {final_roi:.2%}")
    print(f"   -> VAN (3-Year): {final_van:,.2f} DZD")

    return {"roi": final_roi, "van": final_van}

if __name__ == "__main__":
    run_module_7()
