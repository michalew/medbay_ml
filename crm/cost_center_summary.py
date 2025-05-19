from crm.models import CostBreakdown


class CostCenterSummary:
    def __init__(self, invoice):
        self.invoice = invoice

    def compute_summary(self):
        cost_breakdowns = CostBreakdown.objects.filter(invoice=self.invoice)
        cost_center_summary = {}

        for cb in cost_breakdowns:
            cc_id = cb.cost_center_id

            if cc_id not in cost_center_summary:
                cost_center_summary[cc_id] = {
                    'cost_center_symbol': cb.cost_center_symbol,
                    'cost_center_name': cb.cost_center_name,
                    'cost_center_description': cb.cost_center_description,
                    'net_cost': 0,
                    'gross_cost': 0,
                }

            cost_center_summary[cc_id]['net_cost'] += cb.net_cost
            cost_center_summary[cc_id]['gross_cost'] += cb.gross_cost

        return cost_center_summary
