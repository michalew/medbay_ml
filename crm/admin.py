from django.contrib import admin
from crm.models import Location, CostCentre, Contractor


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    pass


@admin.register(CostCentre)
class CostCentreAdmin(admin.ModelAdmin):
    pass


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    # Możesz odkomentować i dostosować poniższe linie, jeśli chcesz dodać więcej funkcji do panelu admina
    # list_display = ['nick', 'video', 'published', 'body', 'status']
    # search_fields = ['nick', 'video__title', 'ip_address', 'body']
    pass
