from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
import xml.etree.ElementTree as ET


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
    response = client.service.Zaloguj(pKluczUzytkownika=api_key)
    return response


# Funkcja wyszukiwania danych firmy
def get_company_data(nip):
    session_token = login(api_key)
    client.transport.session.headers.update({'sid': session_token})
    params = {
        'Nip': nip
    }
    response = client.service.DaneSzukajPodmioty(pParametryWyszukiwania=params)
    response_xml = ET.fromstring(response)
    response_dict = xml_to_dict(response_xml.find('.//dane'))
    if response_dict.get('NrLokalu'):
        response_dict['NrNieruchomosci'] = response_dict['NrNieruchomosci'] + '/' + response_dict['NrLokalu']
    regon = response_dict.get('Regon')
    raport = 'PublDaneRaportPrawna'  # Typ raportu
    full_report = client.service.DanePobierzPelnyRaport(pRegon=regon, pNazwaRaportu=raport)
    full_report_xml = ET.fromstring(full_report)
    full_report_dict = xml_to_dict(full_report_xml.find('.//dane'))
    response_dict['Krs'] = full_report_dict['praw_numerWrejestrzeEwidencji']
    return response_dict


#print(get_company_data('5270103391'))
