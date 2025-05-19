from decimal import Decimal
from cmms.models import Service, Ticket, Device
from crm.models import CostBreakdown


class CostBreakdownCreator:
    def __init__(self, invoice):
        self.invoice = invoice

    def breakdown_costs(self):
        """Create cost breakdown for given invoice"""
        CostBreakdown.objects.filter(invoice=self.invoice).delete()

        unique_devices = {}

        services = self.invoice.get_services()
        tickets = [t for s in services for t in s.ticket.all()]
        devices = [d for t in tickets for d in t.device.all()]

        for device in devices:
            unique_devices[device.id] = device

        devices_number = len(unique_devices)
        signle_device_net_cost = round(self.invoice.net_value / devices_number, 2) if devices_number else 0
        single_device_gross_cost = round(self.invoice.gross_value / devices_number, 2) if devices_number else 0

        failed_for_devices = []

        for device in unique_devices.values():
            if device.cost_centre:
                cc_name = device.cost_centre.name
                cc_symbol = device.cost_centre.symbol
                cc_id = device.cost_centre.id
                cc_desc = device.cost_centre.description
            else:
                cc_name = cc_symbol = "brak"
                cc_id = -1
                cc_desc = "Urządzenie nie jest przypisane do żadnego centrum kosztowego"
                failed_for_devices.append(device.pk)

            CostBreakdown.objects.create(
                invoice=self.invoice,
                device_name=device.name,
                device_id=device.id,
                device_manufacturer=device.make.name,
                device_model=device.model,
                device_serial_number=device.serial_number,
                cost_center_name=cc_name,
                cost_center_symbol=cc_symbol,
                cost_center_id=cc_id,
                cost_center_description=cc_desc,
                device_inventory_number=device.inventory_number,
                net_cost=signle_device_net_cost,
                gross_cost=single_device_gross_cost
            )

        return failed_for_devices
