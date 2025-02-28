let activeForm = null;

document.addEventListener('focusin', function(event) {
    const activeElement = document.activeElement;
    const forms = document.forms;

    // Przejdź przez wszystkie formularze na stronie
    for (let i = 0; i < forms.length; i++) {
        const form = forms[i];
        // Sprawdź, czy aktywny element jest częścią formularza
        if (form.contains(activeElement)) {
            activeForm = form;
            break;
        }
    }

    if (activeForm) {
        console.log("Aktywny formularz:", activeForm);
    } else {
        console.log("Brak aktywnego formularza.");
    }
});

function validateNIP(nip) {
    // Usuń wszelkie znaki inne niż cyfry
    nip = nip.replace(/[\s-]/g, '');

    // Sprawdź, czy NIP ma dokładnie 10 cyfr
    if (nip.length !== 10) {
        console.log('Błędny numer NIP');
        return false;
    }

    // Tablica wag dla poszczególnych cyfr NIP
    const weights = [6, 5, 7, 2, 3, 4, 5, 6, 7];
    let sum = 0;

    // Oblicz sumę kontrolną
    for (let i = 0; i < 9; i++) {
        sum += parseInt(nip[i]) * weights[i];
    }

    // Oblicz cyfrę kontrolną
    const controlDigit = sum % 11;

    // Porównaj cyfrę kontrolną z ostatnią cyfrą NIP
    return controlDigit === parseInt(nip[9]);
}

document.addEventListener('DOMContentLoaded', function() {
    const nipField = document.getElementById('id_NIP');
    nipField.addEventListener('change', function() {
        const nip = nipField.value;
        if (validateNIP(nip)) {
            fetch(`/crm/fetch-company-data/?nip=${nip}`)
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        document.getElementById('id_REGON').value = data.Regon;
                        document.getElementById('id_name').value = data.Nazwa;
                        document.getElementById('id_city').value = data.Miejscowosc;
                        document.getElementById('id_street').value = data.Ulica;
                        document.getElementById('id_postal_code').value = data.KodPocztowy;
                        document.getElementById('id_KRS').value=data.Krs;
                        document.getElementById('id_street_number').value=data.NrNieruchomosci;
                        // Wypełnij inne pola według potrzeb
                    } else {
                        alert(data.error);
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        else {
            if (activeForm) {
                activeForm.reset();
            }
            console.log('Błędny numer NIP');
        }
    });
});