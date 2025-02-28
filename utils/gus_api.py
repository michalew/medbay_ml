import xml.etree.ElementTree as ET
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session


def xml_to_dict(element):
    data_dict = {}
    for child in element:
        data_dict[child.tag] = child.text
    return data_dict


# URL do WSDL
wsdl = 'https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/wsdl/UslugaBIRzewnPubl-ver11-test.wsdl'

# Klucz API
api_key = 'abcde12345abcde12345'

# Utwórz sesję i klienta Zeep
session = Session()
transport = Transport(session=session)
settings = Settings(strict=False, xml_huge_tree=True)
client = Client(wsdl=wsdl, transport=transport, settings=settings)


# Funkcja logowania
def login(api_key):
    try:
        response = client.service.Zaloguj(pKluczUzytkownika=api_key)
        # Sprawdź, czy odpowiedź jest poprawna
        if response is None:
            raise ValueError("Błędna odpowiedź serwera")
        return response
    except Exception as e:
        return None


# Funkcja wyszukiwania danych firmy
def get_company_data(nip):
    session_token = login(api_key)
    if session_token is None:
        return None
    else:
        client.transport.session.headers.update({'sid': session_token})
        params = {
            'Nip': nip
        }
        try:
            response = client.service.DaneSzukajPodmioty(pParametryWyszukiwania=params)
            # Sprawdź, czy odpowiedź jest poprawna
            if response is None:
                return None
            # Przetwarzaj odpowiedź
        except Exception as e:
            return None
    response_xml = ET.fromstring(response)
    response_dict = xml_to_dict(response_xml.find('.//dane'))
    if not response_dict:
        return None
    if response_dict.get('NrLokalu'):
        response_dict['NrNieruchomosci'] = response_dict['NrNieruchomosci'] + '/' + response_dict['NrLokalu']
    regon = response_dict.get('Regon')
    raport = 'PublDaneRaportPrawna'  # Typ raportu
    try:
        full_report = client.service.DanePobierzPelnyRaport(pRegon=regon, pNazwaRaportu=raport)
        # Sprawdź, czy odpowiedź jest poprawna
        if full_report is None:
            return None
        # Przetwarzaj pełny raport
    except Exception as e:
        return None
    full_report_xml = ET.fromstring(full_report)
    full_report_dict = xml_to_dict(full_report_xml.find('.//dane'))
    if not full_report_dict:
        return None
    response_dict['Krs'] = full_report_dict['praw_numerWrejestrzeEwidencji']
    return response_dict

#print(get_company_data('5270103391'))
