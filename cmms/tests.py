from django.test import TestCase
from cmms.models import Device, Genre, Make

class GetDiffTest(TestCase):
    def setUp(self):
        # Tworzymy wymagane obiekty powiązane
        genre = Genre.objects.create(symbol="SYM", name="Test Genre")
        make = Make.objects.create(name="Test Make")

        # Tworzymy obiekt Device z wymaganymi polami
        self.device = Device.objects.create(
            name="Device 1",
            model="Model A",
            serial_number="12345",
            inventory_number="INV001",
            genre=genre,
            make=make,
            # jeśli są inne wymagane pola bez wartości domyślnych, dodaj je tutaj
        )
        # Zmieniamy obiekt, aby mieć historię zmian
        self.device.name = "Device 1 Updated"
        self.device.save()

    def test_get_diff(self):
        # Pobieramy najnowszą historię
        latest_history = self.device.history.latest('history_date')
        # Wywołujemy metodę diff
        diffs = latest_history.diff()
        print("Diffs:", diffs)
        # Sprawdzamy, czy lista różnic zawiera oczekiwaną zmianę
        self.assertTrue(any("name" in diff for diff in diffs))