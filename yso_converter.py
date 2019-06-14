#!/usr/bin/env python3
from rdflib import Graph, URIRef, Namespace, RDF
import pymarc
from pymarc import XmlHandler
from pymarc import MARCReader, MARCWriter, Record, Field
from pymarc.exceptions import (BaseAddressInvalid, 
                               RecordLeaderInvalid, 
                               BaseAddressNotFound, 
                               RecordDirectoryInvalid,
                               NoFieldsFound, 
                               FieldNotFound, 
                               RecordLengthInvalid) 
from vocabularies import Vocabularies
import urllib.request
import shutil
import argparse
import datetime
import pickle
import copy
import os.path
import logging
import sys
import re

class YsoConverter():

    def __init__(self, input_file, output_file, file_format, all_languages):      
        
        self.input_file = input_file
        self.output_file = output_file
        #TODO: tiedoston nimeäminen aikaleimalla
        #TODO: tarkista ylikirjoitus!
        self.vocabularies = Vocabularies()
        self.file_format = file_format.lower()
        self.all_languages = False 
        if all_languages == "yes":
            self.all_languages = True
        self.conversion_time = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.marcdate = str(datetime.date.today()).replace("-","")
        self.conversion_name = "yso-konversio"
        self.error_logger = logging.getLogger()
        #korvataan kaksoispisteet Windows-tiedostonimeä varten:
        time = self.conversion_time.replace(":", "")
        self.error_log = self.conversion_name + "_error-log_" + time + ".log"
        self.removed_fields_log = self.conversion_name + "_removed-fields-log_" + time + ".log"
        self.new_fields_log = self.conversion_name + "_new-fields-log_" + time + ".log"
        self.results_log = self.conversion_name + "_results-log_" + time + ".log"
        error_handler = logging.FileHandler(self.error_log, 'w', 'utf-8')
        error_handler.setLevel(logging.ERROR)
        self.error_logger.addHandler(error_handler)
        self.linking_number = None #käytetään musiikkiaineiston hajotettujen ketjujen yhdistämiseen 8-osakentällä
        self.statistics = {}
        self.statistics.update({"konvertoituja tietueita": 0})
        self.statistics.update({"käsiteltyjä tietueita": 0})
        self.statistics.update({"käsiteltyjä kenttiä": 0})
        self.statistics.update({"poistettuja kenttiä": 0})
        self.statistics.update({"uusia kenttiä": 0})
        self.statistics.update({"virheitä": 0})
        self.statistics.update({"virheluokkia": {}})
        #ladattavien sanastojen sijainti:
        self.data_url = "http://api.finto.fi/download/"
        #ladattavien sanastojen kansio- ja tiedostonimi:
        self.vocabulary_files = {
            "yso": "yso-skos.ttl",
            "yso-paikat": "yso-paikat-skos.ttl",
            "ysa": "ysa-skos.ttl",
            "allars": "allars-skos.ttl",
            "slm": "slm-skos.ttl",
            "musa": "musa-skos.ttl",
            "seko": "seko-skos.ttl"
            }

    def initialize_vocabularies(self):
        vocabularies_dump_loaded = False
        if os.path.isfile('vocabularies.pkl'):
            timestamp = os.path.getmtime('vocabularies.pkl')
            file_date = datetime.date.fromtimestamp(timestamp)
            if file_date == datetime.date.today():
                with open('vocabularies.pkl', 'rb') as input_file: 
                    try:     
                        self.vocabularies = pickle.load(input_file)
                        vocabularies_dump_loaded = True
                    except EOFError:
                        vocabularies_dump_loaded = False    
                vocabulary_names = ['ysa', 'yso', 'yso_paikat', 'allars', 'slm', 'musa', 'cilla', 'seko']
                for vn in vocabulary_names:
                    if vn not in self.vocabularies.vocabularies:
                        #jos kaikki sanastot eivät löydy dumpista, sanastot on käsiteltävä uudelleen:
                        vocabularies_dump_loaded = False

        if not vocabularies_dump_loaded: 
            urllib_errors = False
            for vf in self.vocabulary_files:
                try:
                    with urllib.request.urlopen(self.data_url + "/" + vf + "/" + self.vocabulary_files[vf]) as turtle, \
                        open(self.vocabulary_files[vf], 'wb') as out_file:
                        shutil.copyfileobj(turtle, out_file)
                except urllib.error.URLError as e:
                    logging.warning("Ei onnistuttu lataamaan sanastoa %s")
                    urllib_errors = True
            if urllib_errors:
                while True:
                    answer = input("Kaikkia sanastoja ei onnistuttu lataamaan. Haluatko käyttää mahdollisesti vanhentuneita sanastoja paikalliselta levyltä (K/E)?")
                    if answer.lower() == "k":
                        break
                    if answer.lower() == "e":
                        sys.exit(2)
            graphs = {}
            
            for vf in self.vocabulary_files:
                g = Graph()
                graphs.update({vf: g})
                try:
                    logging.info("parsitaan sanastoa %s"%vf)
                    g.parse(self.vocabulary_files[vf], format='ttl')
                except FileNotFoundError:
                    logging.error("Tiedostoa %s ei löytynyt levyltä. "
                        "Tiedoston automaattinen lataaminen ei ole onnistunut tai tiedosto on poistettu. "
                        "Käy hakemassa kaikki tarvittavat sanastot 'ysa', 'yso', 'yso-paikat', 'allars', 'slm', 'musa', 'cilla', 'seko' "
                        "osoitteesta finto.fi ttl-tiedostomuodossa"%self.vocabulary_files[vf])
                    sys.exit(2)
            logging.info("valmistellaan sanastot konversiokäyttöä varten")
            
            self.vocabularies.parse_vocabulary(graphs['ysa'], 'ysa', ['fi'])
            self.vocabularies.parse_vocabulary(graphs['yso'], 'yso', ['fi', 'sv'])
            self.vocabularies.parse_vocabulary(graphs['yso-paikat'], 'yso_paikat', ['fi', 'sv'])
            self.vocabularies.parse_vocabulary(graphs['allars'], 'allars', ['sv'])
            self.vocabularies.parse_vocabulary(graphs['slm'], 'slm', ['fi', 'sv'])
            self.vocabularies.parse_vocabulary(graphs['musa'], 'musa', ['fi'], secondary_graph = graphs['ysa'])
            self.vocabularies.parse_vocabulary(graphs['musa'], 'cilla', ['sv'], secondary_graph = graphs['ysa'])
            self.vocabularies.parse_vocabulary(graphs['seko'], 'seko', ['fi'])

            with open('vocabularies.pkl', 'wb') as output:  # Overwrites any existing file.
                pickle.dump(self.vocabularies, output, pickle.HIGHEST_PROTOCOL)
            logging.info("sanastot tallennettu muistiin ja tiedostoon vocabularies.pkl")
            output.close()    

    def read_records(self):
        with open(self.error_log, 'w', encoding = 'utf-8-sig') as error_handler, \
            open(self.removed_fields_log, 'w', encoding = 'utf-8-sig') as self.rf_handler, \
            open(self.new_fields_log, 'w', encoding = 'utf-8-sig') as self.nf_handler:
            
            error_logger = logging.getLogger("error logger")
            error_handler = logging.FileHandler(self.error_log)
            error_logger.setLevel(logging.ERROR)
            if self.file_format == "marcxml":
                self.writer = XMLWriter(open(self.output_file,'wb'))
                try:
                    pymarc.map_xml(self.read_and_write_record, self.input_file)
                except SAXParseException as e:
                    logging.info(e)
                    #TODO: tarkempi virheilmoitus
                self.writer.close()
            if self.file_format == "marc21":
                with open(self.input_file, 'rb') as fh, \
                    open(self.output_file,'wb') as output:
                    self.writer = MARCWriter(output)
                    try:
                        reader = MARCReader(fh, force_utf8=True, to_unicode=True)
                    except TypeError:
                        logging.error("Tiedosto ei ole MARC21-muodossa")
                        sys.exit(2)
                    record = Record()
                    while record:                
                        try:
                            record = next(reader, None)
                            if record:
                                self.read_and_write_record(record)
                                    #TODO: kirjoitetaanko konvertoimattomatkin tietueet?
                        except (BaseAddressInvalid, 
                                RecordLeaderInvalid, 
                                BaseAddressNotFound, 
                                RecordDirectoryInvalid,
                                NoFieldsFound, 
                                UnicodeDecodeError,
                                RecordLengthInvalid) as e:
                            if e.__class__.__name__ in self.statistics["error classes"]:
                                self.statistics[e.__class__.__name__] += 1
                            else:
                                #self.statistics.update({e.__class__.__name__: 1})
                                self.statistics["error classes"][e.__class__.__name__] += 1
                            self.statistics['virheitä'] += 1
                output.close()
                fh.close()

        self.rf_handler.close()
        self.nf_handler.close()
        error_handler.close()
        with open(self.results_log, 'w', encoding = 'utf-8-sig') as result_handler:
            self.statistics["käsiteltyjä kenttiä"] = \
            self.statistics["poistettuja kenttiä"] + \
            self.statistics["uusia kenttiä"]
            for stat in self.statistics:
                if stat == "virheluokkia":
                    result_handler.write("Virhetilastot: \n")
                    for e in self.statistics[stat]:
                        result_handler.write("Virhetyyppi: %s, määrä: %s  \n"%(e, self.statistics[stat][e]))
                else:
                    result_handler.write("%s: %s \n"%(stat, self.statistics[stat]))
        result_handler.close()
        logging.info("konversio tehty")

    def read_and_write_record(self, record):
        #tarkistetaan, löytääkö pymarc XML-muotoisesta tietueesta MARC21-virheitä:
        if self.file_format == "marcxml":
            try:
                raw = record.as_marc()
                new_record = Record(data=raw)
            except ValueError:
                self.statistics['virheitä'] += 1
        #TODO: XML-tietueiden lukeminen yksittäisinä tiedostoina
        new_record = self.process_record(record)
        self.statistics['käsiteltyjä tietueita'] += 1
        if new_record:
            self.writer.write(new_record)
            self.statistics['konvertoituja tietueita'] += 1

    def subfields_to_dict(self, subfields):
        """
        muuntaa pymarc-kirjaston käyttämän osakenttälistan, jossa joka toinen alkio on osakenttäkoodi ja joka toinen osakenttä,
        konversio-ohjelmalle helpommin käsiteltävään muotoon listaksi, jossa on avainarvopareja {osakenttäkoodi, osakenttä} 
        """
        subfields_list = []
        #Testattava, jos subfields-listassa pariton määrä alkioita! 
        for idx in range(0, len(subfields), 2):
            if idx + 1 < len(subfields):
                subfields_list.append({"code": subfields[idx], "value": subfields[idx+1]})
        return subfields_list         
    
    def remove_subfields(self, codes, subfields):
        #apufunktio identtisten rivien poistamiseen, kun konvertoidut kentät ovat valmiina
        trimmed_subfields = []
        for subfield in self.subfields_to_dict(subfields):
            if subfield['code'] not in codes:
                trimmed_subfields.append({"code": subfield['code'], "value": subfield['value']})
        return trimmed_subfields
    
    def is_equal_field(self, first_subfields, second_subfields):
        #apufunktio identtisten rivien poistamiseen, kun konvertoidut kentät ovat valmiina
        return self.sort_subfields(self.subfields_to_dict(first_subfields)) == \
               self.sort_subfields(self.subfields_to_dict(second_subfields))

    def process_record(self, record):
        if record['001']:
            tags_of_fields_to_convert = ['385', '567', '648', '650', '651', '655']
            tags_of_fields_to_process = ['257', '370', '382', '385', '386', '388', '567', '648', '650', '651', '653', '655']
            original_fields = {}
            new_fields = {}
            altered_fields = set()
            record_status = record.leader[5]
            record_id = record['001'].data
            self.linking_number = None #käytetään musiikkiaineiston hajotettujen ketjujen yhdistämiseen 8-osakentällä
            linking_numbers = [] #merkitään 8-osakenttien numerot, joita tietueessa on jo ennestään
            if record_status == "d":
                return
            """
            KAUNOKIRJALLISUUS
            leader/06 on a tai t JA leader/07 ei ole b, i eikä s -> 
            008/33 - Kirjallisuuslaji ei ole 0 eikä u (painetut ja e-kirjat)
            leader/06 on i ->
            008/30-31 - Kirjallisuuslaji on d, f tai p (äänikirjat)
            """
            leader_type = record.leader[6]
            record_type = None
            non_fiction = True
            control_field_genres = []
            convertible_record = False
            if leader_type in ['a', 't']:
                record_type = "text"
                if record.leader[7] not in ['b', 'i', 's']:
                    """ 
                    008 (BK) merkkipaikka 34 arvo on erittäin oleellinen ja paljon käytetty 
                    a, niin 655 $a kenttään voidaan tallettaa muistelmat  http://urn.fi/URN:NBN:fi:au:slm:s286
                    b tai c niin 655 $a kenttään elämäkerrat http://urn.fi/URN:NBN:fi:au:slm:s1006
                    008 (BK) merkkipaikka 33 samaten
                    d -  näytelmät  http://urn.fi/URN:NBN:fi:au:slm:s929
                    f - romaanit http://urn.fi/URN:NBN:fi:au:slm:s518
                    h - huumori http://urn.fi/URN:NBN:fi:au:slm:s1128
                    j - novellit http://urn.fi/URN:NBN:fi:au:slm:s27
                    p - runot  http://urn.fi/URN:NBN:fi:au:slm:s1150
                    s - puheet http://urn.fi/URN:NBN:fi:au:slm:s775   tai esitelmät  http://urn.fi/URN:NBN:fi:au:slm:s313
                    """
                    if record['006']:
                        if len(record['006'].data) > 16:
                            if record['006'].data[16] not in ['0', 'u', '|']:
                                non_fiction = False
                    elif record['008']:
                        if len(record['008'].data) > 34:
                            if record['008'].data[33] not in ['0', 'u', '|']:
                                non_fiction = False
                            
            elif leader_type == "i":
                record_type = "text"
                if record['006']:
                    if len(record['008'].data) > 14:
                        for char in ['d', 'f', 'p']:
                            if char in record['008'].data[13:14]:
                                non_fiction = False
                elif record['008']:
                    if len(record['008'].data) > 31:
                        for char in ['d', 'f', 'p']:
                            if char in record['008'].data[30:31]:
                                non_fiction = False
            elif leader_type == "m":
                #Konsolipelien tunnistaminen 
                #Leader/06 on m JA kenttä 008/26 on g (eli peli)
                if record['008']:
                    if len(record['008'].data) > 33:
                        if record['008'].data[26] == "g":
                            non_fiction = False
            elif leader_type == "r":
                #Lautapelien tunnistaminen
                #leader/06 on r JA 008/33 on g
                if record['008']:
                    if len(record['008'].data) > 33:
                        if record['008'].data[33] == "g":
                            non_fiction = False

            elif leader_type in ['c', 'd', 'j']: 
                record_type = "music"
            elif leader_type == "g":
                if record['007']:
                    if len(record['007'].data) > 0:
                        if record['007'].data[0] == "v":
                            record_type = "movie"
                            for field in record.get_fields('084'):
                                for subfield in field.get_subfields('a'):
                                    if subfield.startswith("78"):
                                        record_type = "music"
            if not record_type:
                record_type = "text"

            for tag in tags_of_fields_to_convert:
                for field in record.get_fields(tag):
                    if any (sf in ['musa', 'cilla', 'ysa', 'allars'] for sf in field.get_subfields("2")):
                        convertible_record = True

            #jos $8-osakenttiä tietueessa ennestään, otetaan uusien $8-osakenttien 1. numeroksi viimeistä seuraava numero:
            if convertible_record:
                if record_type == "music":
                    for field in record.get_fields():
                        if hasattr(field, 'subfields'):
                            for subfield in self.subfields_to_dict(field.subfields):
                                if subfield['code'] == "8":
                                    value = subfield['value']
                                    if "\\" in value:
                                        value = value.split("\\")[0]
                                    if "." in value:
                                        value = value.split(".")[0] 
                                    if value.isdigit():
                                        linking_numbers.append(int(value))
                    linking_numbers = sorted(linking_numbers)
                    if linking_numbers:
                        self.linking_number = linking_numbers[len(linking_numbers) - 1]
                    else:
                        self.linking_number = 0
                subfields = []
                #TODO: vaihtoehto: säilytetään alkup. YSA-rivi, jos valittu optio?
                for tag in tags_of_fields_to_process:                    
                    for field in record.get_fields(tag):
                        converted_fields = []
                        if tag in tags_of_fields_to_convert:
                            vocabulary_code = None
                            for sf in field.get_subfields('2'):
                                #valitaan ensimmäinen vastaantuleva sanastokoodi:
                                if not vocabulary_code:
                                    if sf == "ysa" or sf == "allars" or sf == "musa" or sf == "cilla":
                                        vocabulary_code = sf    
                            #TODO: rekisteröi tässä onko tietuetta muutettu?
                            if vocabulary_code:
                                #TODO: vanha, konvertoitava kenttä lokiin!
                                converted_fields = self.process_field(record_id, field, vocabulary_code, non_fiction, record_type)
                                self.statistics['käsiteltyjä kenttiä'] += 1
                                if converted_fields:
                                    altered_fields.add(tag)
                                    for cf in converted_fields:
                                        self.statistics['uusia kenttiä'] += 1
                                        altered_fields.add(cf.tag)
                                        if cf.tag in new_fields:
                                            new_fields[cf.tag].append(cf)
                                        else:
                                            new_fields.update({cf.tag: [cf]})
                        if not converted_fields:
                            if tag in original_fields:
                                original_fields[tag].append(field)
                            else:
                                original_fields.update({tag: [field]})
                #järjestetään uudet ja alkuperäiset rivit:   
                altered_fields = sorted(altered_fields)
                for tag in altered_fields:
                    record.remove_fields(tag)
                for tag in altered_fields:
                    original_fields_with_tag = []
                    new_fields_with_tag = []
                    if tag in original_fields:
                        original_fields_with_tag = original_fields[tag]
                    if tag in new_fields:
                        new_fields_with_tag = new_fields[tag]
                    sorted_fields = self.sort_fields(tag, original_fields_with_tag, new_fields_with_tag)        
                    #poistetaan identtiset rivit:
                    removable_fields = set()
                    for m in range(len(sorted_fields)):
                        for n in range(m + 1, len(sorted_fields)):
                            if m not in removable_fields and n not in removable_fields:
                                if self.is_equal_field(sorted_fields[m].subfields, sorted_fields[n].subfields):
                                    if sorted_fields[m].indicators == sorted_fields[n].indicators:
                                        removable_fields.add(n)
                                    if sorted_fields[m].indicators[1] == " " and not sorted_fields[n].indicators[1] == " ":
                                        removable_fields.add(m)
                                    if sorted_fields[n].indicators[1] == " " and not sorted_fields[m].indicators[1] == " ":
                                        removable_fields.add(n)
                                elif self.sort_subfields(self.remove_subfields(['0'], sorted_fields[m].subfields)) == \
                                    self.sort_subfields(self.remove_subfields(['0'], sorted_fields[n].subfields)):
                                    if sorted_fields[m]['2'] and sorted_fields[m]['0']:
                                        removable_fields.add(n)
                                    elif sorted_fields[n]['2'] and sorted_fields[n]['0']:
                                        removable_fields.add(m)
                                elif self.sort_subfields(self.remove_subfields(['9'], sorted_fields[m].subfields)) == \
                                    self.sort_subfields(self.remove_subfields(['9'], sorted_fields[n].subfields)):
                                    if sorted_fields[m]['9'] and not sorted_fields[n]['9']:
                                        removable_fields.add(n)
                                    if sorted_fields[n]['9'] and not sorted_fields[m]['9']:
                                        removable_fields.add(m)
                    for idx in range(len(sorted_fields)):
                        if idx not in removable_fields:
                            record.add_ordered_field(sorted_fields[idx])   
                        #TODO: älä poista muiden sanastokoodien duplikaattirivejä
                        #TODO: älä tilastoi tässä kohtaa poistettavia rivejä: poista uusien rivien tilastosta nyt poistettava rivi?
                        #else:     
            else:
                return
            return record
        
    def process_field(self, record_id, field, vocabulary_code, non_fiction=True, record_type=None):
        """
        record_id -- 001-kentästä poimittu tietue-id
        field -- käsiteltävä kenttä MARC21-muodossa
        vocabulary_code -- alkuperäisen tietueen 2-osakentästä otettu sanastokoodi
        non_fiction -- määrittelee, onko tietueen aineisto tietokirjallisuutta
        record_type -- aineistotyyppi joidenkin kenttien erikoiskäsittelyä varten, käyvät arvot: "text", "music", "movie"
        """
        #record_id: tietueen numero virheiden lokitusta varten
        #fiction: Tarvitaan ainakin
        new_fields = []
        tag = field.tag
        subfields = self.subfields_to_dict(field.subfields)
        #jos ei-numeerisia arvoja on enemmän kuin yksi, kyseessä on asiasanaketju:
        non_digit_codes = []
        #$6-osakentälliset kentät jätetään käsittelemättä:
        for subfield in field.get_subfields('6'):
            field = self.strip_vocabulary_codes(field)
            field.indicators[1] = "4"
            logging.error("%s;%s;%s;%s"%("9", record_id, field['6'], field))
            return [field]
        for subfield in subfields:
            if not subfield['code'].isdigit():
                non_digit_codes.append(subfield['code'])   
        if len(non_digit_codes) > 1 and self.linking_number is not None:
            #musiikin  asiasanaketjuihin liitetään 8-osakenttä ja linkkinumero: 
            self.linking_number += 1
        #tallennetaan numeroilla koodatut osakentät, jotka liitetään jokaiseen uuteen kenttään, paitsi $0 ja $2:
        control_subfield_codes = ['1', '3', '4', '5', '6', '7', '8', '9']
        if tag == "567":
            if any(subfield['code'] == "b" for subfield in subfields):
                control_subfield_codes.append('a')
        control_subfields = {}
        for csc in control_subfield_codes:
            """
            HUOM! sanastokoodeja voi olla useampia, jos yksikin niistä ysa/allars,
            tulee valituksi niistä ensimmäiseksi kentässä esiintyvä sanastokoodi
            """
            if field[csc]:
                for sf in field.get_subfields(csc):
                    if "<DROP>" in sf and csc == "9":
                        #jos kyseessä on ketju, <DROP>-merkityt jätetään pois:
                        if len(non_digit_codes) > 1:
                            continue
                    if csc in control_subfields:
                        try:
                            control_subfields[csc].append(sf)
                        except TypeError:
                            logging.info("type error "+str(sf))
                    else:
                        control_subfields.update({csc: [sf]})      
        #etsitään paikkaketjut ja muodostetaan niistä yksiosainen käsite:
        #TODO: katsotaan mahdollisesti myös muita kuin maantieteellisiä termejä
        if len(non_digit_codes) > 1:
            if tag == "650" or tag == "651":
                combined_subfields = []
                while len(subfields) > 0:
                    if len(subfields) > 1:
                        if subfields[0]['code'] in ['a', 'b', 'c', 'd', 'v', 'x', 'y']: 
                            first = subfields[0]['value']
                            if subfields[1]['code'] == "z":
                                second = subfields[1]['value']
                                combined_concept = first + " -- " + second
                                if combined_concept in \
                                    self.vocabularies.vocabularies['ysa'].geographical_chained_labels | \
                                    self.vocabularies.vocabularies['allars'].geographical_chained_labels:
                                    combined_subfields.append({'code': subfields[0]['code'], 'value': combined_concept})
                                    del subfields[0]
                                    del subfields[0]
                                    continue
                    combined_subfields.append({'code': subfields[0]['code'], 'value': subfields[0]['value']})
                    del subfields[0]
                subfields = combined_subfields
        #jos kaikki osakenttäkoodit ovat numeroita, tulostetaan kenttä sellaisenaan ilman 0- ja 2-osakenttiä:
        if all(subfield['code'].isdigit() for subfield in subfields):
            field = self.strip_vocabulary_codes(field)
            field.indicators[1] = "4"
            logging.error("%s;%s;%s;%s"%("8", record_id, subfield['value'], field))
            return [field]
        
        #poikkeuksellisesti käsiteltävät kentät: 
        #385, 567 ja 648, jossa 1. indikaattori on "1", 650/655, jos musiikkiaineistoa:
        #musiikki- ja elokuva-eineisto, jos $a- tai $x-osakentässä on asiasanana aiheet
        #musiikkiaineisto, jossa SEKO-asiasanoja
        if tag in ['650', '655'] and record_type == "music":
            #kerätään SEKO-termejä sisältävät osakentät 382-kenttään siirrettäväksi:
            instrument_lists = []
            instrument_list = []
            
            has_topics = False #jkentän loput termeistä tulkitaan tämän perusteella aiheiksi
            has_genre_terms = False #kentän loput termeistä tulkitaan tämän perusteella luomiseen liittyviksi
            for subfield in subfields:
                if subfield['code'] in ['a', 'x']:
                    if subfield['value'] == "kokoelmat":
                        subfield['value'] = "kokoomateokset"
                    if subfield['value'] == "sovitukset":
                        if instrument_list:
                            #instrument_list = copy.deepcopy(instrument_list)
                            #instrument_lists.append(instrument_list)
                            instrument_list = []
                    if subfield['value'] in ['aiheet', 'musiikki']:
                        if subfield['value'] == 'aiheet':
                            has_topics = True
                        logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], field))
                    else:
                        responses = []  
                        n = None
                        matches = re.findall('\((.*?)\)', subfield['value'])
                        for m in matches:
                            if m.isdigit():
                                n = m
                                subfield['value'] = subfield['value'].replace("("+n+")", "")
                                subfield['value'] = subfield['value'].replace("  ", " ")
                                subfield['value'] = subfield['value'].strip()
                        try:
                            responses = self.vocabularies.search(subfield['value'], [('seko', 'fi')])
                        except ValueError:
                            pass    
                        if responses:
                            if not instrument_list: 
                                instrument_lists.append(instrument_list)
                            if n:
                                instrument_list.extend(["a", responses[0]['label'], "n", n])     
                            else: 
                                instrument_list.extend(["a", responses[0]['label']])
                        else:    
                            converted_fields = self.process_subfield(record_id, field, subfield, vocabulary_code, non_fiction, record_type, has_topics)  
                            for cf in converted_fields:
                                if cf['2']:
                                    if cf['2'].startswith('slm'):
                                        if not has_topics:
                                            has_genre_terms = True
                                    if cf['2'].startswith('yso'):
                                        if not has_genre_terms:
                                            has_topics = True
                                cf = self.add_control_subfields(cf, control_subfields)
                                new_fields.append(cf) 
                elif not subfield['code'].isdigit():
                    converted_fields = self.process_subfield(record_id, field, subfield, vocabulary_code, non_fiction, record_type, has_topics)
                    for cf in converted_fields:
                        cf = self.add_control_subfields(cf, control_subfields)
                        new_fields.append(cf) 
            if instrument_lists:
                for instrument_list in instrument_lists:
                  
                    new_field = Field(
                        tag = "382",
                        indicators = ['1', '1'],
                        subfields = instrument_list
                    )
                    new_field.add_subfield("2", "seko")  
                    new_field = self.add_control_subfields(new_field, control_subfields)
                    new_fields.append(new_field)
            return new_fields

        if tag == "648":
            if field.indicators[0] == "1":
                original_field = copy.deepcopy(field)
                edited_field = copy.deepcopy(field)
                a_subfield = True
                while (a_subfield):
                    a_subfield = edited_field.delete_subfield('a')
                    if self.vocabularies.is_numeric(a_subfield):
                        field.delete_subfield('a')
                        new_code = None
                        if vocabulary_code in ['ysa', 'musa']:
                            new_code = "yso/fin"
                        else:
                            new_code = "yso/swe"
                        new_subfields = []
                        for subfield in subfields:
                            if subfield['code'].isdigit() and subfield['code'] not in ['a', '0', '2']:
                                new_subfields.append({'code': subfield['code'], 'value': subfield['value']})
                        new_subfields.append({'code': 'a', 'value': a_subfield})
                        new_subfields.append({'code': '2', 'value': new_code})
                        new_subfields = self.sort_subfields(new_subfields)
                        subfield_list = []
                        for ns in new_subfields:
                            subfield_list.extend([ns['code'], ns['value']])
                        new_field = Field(
                            tag = '388',
                            indicators = ['1',' '],
                            subfields = subfield_list
                        )
                        new_fields.append(new_field)
                        """
                        if new_field.tag in new_fields:
                            new_fields[new_field.tag].append(new_field)
                        else:
                            new_fields.update({new_field.tag: [new_field]})
                        """    
                #testataan, onko muutoksia tullut eli onko a-osakentissä ollut numeerisia arvoja:
                """
                if original_field != field:
                    
                    field = new_field
                """
                subfields = self.subfields_to_dict(field.subfields)
                if not any (not subfield['code'].isdigit() for subfield in subfields):
                    return new_fields
        #TODO: tarkista, jos kentässä ei ole a-osakenttää

        if tag == "385":
            if not any(subfield['code'] == "a" for subfield in subfields):
                field = self.strip_vocabulary_codes(field)
                field.indicators = [' ', ' ']
                return [field]
                #TODO: tulosta rivi virhelokiin
        if tag == "567":
            if not any(subfield['code'] == "b" for subfield in subfields):
                """
                567-kenttä: Mikäli $b osakenttä puuttuu ja $a osakentässä on ysa/allars termi, 
                se siirretään $b osakenttään ja lisätään $2 ja $0 osakentät
                """
                for subfield in subfields:
                    if subfield['code'] == "a":
                        try:
                            response = self.vocabularies.search(subfield['value'], [('ysa', 'fi'), ('allars', 'sv')]) 
                            subfield['code'] = 'b'
                        except ValueError:
                            continue
                a_subfields = True
                while (a_subfields):
                    a_subfields = field.delete_subfield('a')
            if not any(subfield['code'] == "b" for subfield in subfields):
                field = self.strip_vocabulary_codes(field)
                field.indicators = [' ', ' ']
                return [field]
                #TODO: tulosta rivi virhelokiin
        for subfield in subfields:
            #new_field = None
            if not subfield['code'].isdigit():
                #or tag == "385" or tag == "567":
                if tag == "385":
                    if subfield['code'] != "a":
                        continue
                if tag == "567":
                    if subfield['code'] != "b":
                        continue         
                #358- ja 567-kentistä käsitellään vain a- ja b-osakentät:
                converted_fields = self.process_subfield(record_id, field, subfield, vocabulary_code, non_fiction)
                #TODO: listaus koko 358- ja 567-kentästä virhelokiin
                #if tag not in ['385', '567']:
                if converted_fields:
                    for cf in converted_fields:
                        cf = self.add_control_subfields(cf, control_subfields)
                        new_fields.append(cf)
                    
        return new_fields
        
    def process_subfield(self, record_id, original_field, subfield, vocabulary_code, non_fiction=True, record_type=None, has_topics=False):    
        """
        record_id -- 001-kentästä poimittu tietue-id
        original_field -- konvertoitava kenttä MARC21-muodossa
        subfield -- käsiteltävä osakenttä dict-muodossa {"code": "osakenttäkoodi", "value": "osakentän arvo"} 
        vocabulary_code -- alkuperäisen tietueen 2-osakentästä otettu sanastokoodi
        non_fiction -- määrittelee, onko tietueen aineisto tietokirjallisuutta
        """
        tag = original_field.tag
        converted_fields = []

        if not subfield['value']:
            logging.error("%s;%s;%s;%s"%("1", record_id, subfield['value'], original_field))
            return
        #alustetaan ensin hakuparametrien oletusarvot
        vocabulary_order = [] #hakujärjestys, jos sanaa haetaan useammasta sanastosta 
        language = None
        if vocabulary_code == "ysa":
            vocabulary_order = [('ysa', 'fi'), ('allars', 'sv')]
            language = "fi"
        if vocabulary_code == "allars":
            vocabulary_order = [('allars', 'sv'), ('ysa', 'fi')]
            language = "sv"    
        if vocabulary_code == "musa":
            vocabulary_order = [('musa', 'fi'), ('cilla', 'sv'), ('ysa', 'fi'), ('allars', 'sv')]
            language = "fi"    
        if vocabulary_code == "cilla":
            vocabulary_order = [('cilla', 'sv'), ('musa', 'fi'), ('allars', 'sv'), ('ysa', 'fi')]
            language = "sv"     
        slm_vocabulary_order = {}
        slm_vocabulary_order['fi'] = [('slm', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('allars', 'sv')]  
        slm_vocabulary_order['sv'] = [('slm', 'sv'), ('allars', 'sv'), ('slm', 'fi'), ('ysa', 'fi')]
        music_slm_vocabulary_order = {}
        music_slm_vocabulary_order['fi'] = [('slm', 'fi'), ('musa', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('cilla', 'sv'),  ('allars', 'sv')]
        music_slm_vocabulary_order['sv'] = [('slm', 'sv'), ('cilla', 'sv'),  ('allars', 'sv'), ('slm', 'fi'), ('musa', 'fi'), ('ysa', 'fi')]

        search_geographical_concepts = True    
        
        """
        normaalilla tavalla käsiteltävät osakentät, joista tässä ei ole:
        - osakentät 650 e ja g jätetään käsittelemättä
        - kentät 358 ja 567 käsitellään eri tavalla
        - osakenttä 655 y käsitellään eri tavalla
        """
        valid_subfield_codes = {
            '385': ['a', 'b', 'm', 'n', '0', '1', '2', '3', '5', '6', '8', '9'],
            '567': ['a', 'b', '0', '1', '2', '5', '6', '8', '9'],
            '648': ['a', 'v', 'x', 'y', 'z'],
            '650': ['a', 'b', 'c', 'd', 'v', 'x', 'y', 'z'],
            '651': ['a', 'd', 'v', 'x', 'y', 'z'],
            '655': ['a', 'b', 'v', 'x', 'z']
        }

        #käsitellään ensin poikkeustapaukset ja/tai annetaan sanastohaulle erityisjärjestys:
        if tag == "385" or tag == "567":
            search_geographical_concepts = False
        if tag == "648":
            vocabulary_order = [('numeric', language)] + vocabulary_order
        if tag == "655":
            if subfield['code'] in ['a', 'v', 'x']:
                search_geographical_concepts = False
                if language == "fi":
                    vocabulary_order = [('slm', 'fi'), ('slm', 'sv')]
                    #vocabulary_order = {'slm': 'fi', 'slm': 'sv'}
                if language == "sv":
                    vocabulary_order = [('slm', 'sv'), ('slm', 'fi')]
                    #vocabulary_order = {'slm': 'sv', 'slm': 'fi'}
            if subfield['code'] == "y":                          
                field = self.field_without_voc_code("388", [' ', ' '], subfield)
                if vocabulary_code in ['ysa', 'musa']:
                    field.add_subfield('2', 'yso/fin')
                if vocabulary_code in ['allars', 'cilla']:
                    field.add_subfield('2', 'yso/swe')
                return [field]
        if tag in ['648', '650', '651']:
            if subfield['code'] == "v":
                vocabulary_order = slm_vocabulary_order[language]
                if tag == '650' or tag == '651':
                    if subfield['value'].lower() == "fiktio":
                        logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], original_field))
                        return
            if tag == "650" and subfield['code'] == "a":
                if not non_fiction:
                    vocabulary_order = slm_vocabulary_order[language]
        if tag == "650" or tag == "651": 
            if subfield['code'] == "e":
                logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], original_field))
                return 
            elif subfield['code'] == "g":
                field = self.field_without_voc_code("653", [' ', ' '], subfield)   
                logging.error("%s;%s;%s;%s;%s"%("7", record_id, subfield['value'], original_field, field))
                return [field]
            if subfield['code'] in ['a', 'b', 'c', 'x', 'z']:
                vocabulary_order.append(('numeric', language))
            if subfield['code'] in ['d', 'y']:
                vocabulary_order = [('numeric', language)] + vocabulary_order
        if record_type == "music":
            if tag in ['650', '655']:
                if subfield['code'] == "a":
                    if vocabulary_code in ['musa', 'cilla']:
                            vocabulary_order = music_slm_vocabulary_order[language]
                    else:
                        vocabulary_order = slm_vocabulary_order[language]
                if subfield['code'] in ['x', 'y', 'z']:
                    if not has_topics:
                        if vocabulary_code in ['musa', 'cilla']:
                            vocabulary_order = music_slm_vocabulary_order[language]
                        else:
                            vocabulary_order = slm_vocabulary_order[language]
                    if subfield['code'] == "y":
                        vocabulary_order = [('numeric', language)] + vocabulary_order

        #käsitellään perustapaukset
        if subfield['code'] in valid_subfield_codes[tag]:
        #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja 
            try:
                responses = self.vocabularies.search(subfield['value'], vocabulary_order, search_geographical_concepts, self.all_languages)
                if tag == "650" and not non_fiction and subfield['code'] == "a":
                    tag == "655"
                if tag == "655" and subfield['code'] in ['z', 'c']:
                    if record_type == "movies":
                        tag = "257"
                    else:
                        tag = "370"
                if tag in ['650', '655'] and record_type == "music" and not has_topics: 
                    if subfield['code'] in ['z', 'c']:
                        tag = "370"
                    if subfield['code'] in ['y', 'd']:
                        tag = "388"
                for r in responses:
                    field = self.field_with_voc_code(tag, r)
                    converted_fields.append(field)
            except ValueError as e:
                #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja
                field = None
                if str(e) in ['2', '3', '4', '5']:
                    #TODO: korjattava tagi! Sulkutarkenteettomat monitulkintaiset myös tähän!
                    field = self.field_without_voc_code(tag, [' ', '4'], subfield)
                elif str(e) in ['1']:
                    if tag == "385" or tag == "567":
                        field = self.field_without_voc_code(tag, [' ', ' '], subfield)      
                    elif tag in ['648', '650', '651']:
                        if subfield['code'] in ['a', 'b', 'd', 'x', 'y']:
                            field = self.field_without_voc_code("653", [' ', '0'], subfield)
                        elif subfield['code'] in ['d', 'y']:
                            if tag == "650" and record_type == "music" and not has_topics:
                                field = self.field_without_voc_code("388", [' ', ' '], subfield)
                            else:
                                field = self.field_without_voc_code("653", [' ', '4'], subfield)
                        elif subfield['code'] in ['c', 'z']:
                            if tag == "655" or (tag == "650" and record_type == "music" and not has_topics):
                                field = self.field_without_voc_code("370", [' ', ' '], subfield)    
                            elif tag == "650" and record_type == "movie" and not has_topics:
                                field = self.field_without_voc_code("257", [' ', ' '], subfield)    
                            else:
                                field = self.field_without_voc_code("653", [' ', '5'], subfield)    
                        elif subfield['code'] in ['v']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                    elif tag == '655':
                        if subfield['code'] in ['a', 'v', 'x']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                        elif subfield['code'] in ['b']:
                            field = self.field_without_voc_code("653", [' ', '0'], subfield)   
                        elif subfield['code'] in ['z', 'c']:
                            field = self.field_without_voc_code("370", [' ', ' '], subfield)      
                else:
                    logging.info("Tuntematon virhekoodi %s tietueessa %s virheilmoituksessa: %s"%(e, record_id, original_field))
                logging.error("%s;%s;%s;%s;%s"%(e, record_id, subfield['value'], original_field, field))
        else:
            logging.error("%s;%s;%s;%s;%s"%("8", record_id, subfield['value'], original_field, field))
            original_field.indicators[1] = "4"
            original_field.delete_subfield('2')
            
            return [original_field]
            #alkuperäinen ketju jätetään, 2. ind 4 ja poistetaan $2ysa osakenttä

        #else: alkuperäinen ketju jäteään, 2. ind 4 ja poistetaan $2ysa osakenttä????????????

        #MUISTA LIITTÄÄ NUMEROLLISET OSAKENTÄT UUTEEN KENTTÄÄN!!!
        #self.vocabularies.search("ragat", "fi", ['slm', 'allars', 'ysa']))
        return converted_fields
        

    def field_with_voc_code(self, tag, response):
        """
        -   luo haun pohjalta YSO- tai SLM-asiasanasta uuden MARC-kentän
        -   jos kenttänumerona on 650 tai 651 kentän indikaattoreina on #7,
            muussa tapauksessa ##
        -   maantieteelliset termit kenttään 651
        """
        new_indicators = None
        subfields = []
        if "numeric" in response:
            if not tag == "388":
                tag = "648"
            new_indicators = [' ', '7']
            new_subfields = ["a", response['label'], '2', response['code']]
        else: 
            subfield_code = "a"
            if tag == "370":
                subfield_code = "g"
            if tag == "567":
                subfield_code = "b"
            if tag in ['648', '650', '651', '655']:
                if response['geographical']:
                    tag = "651"
                else:
                    tag = "650"
                new_indicators = [' ', '7']
            else:
                new_indicators = [' ', ' ']
            if response['code'].startswith('slm'):
                tag = "655"
            new_subfields = [subfield_code, response['label'], '2', response['code'], '0', response['uris'][0]]
        
        field = Field(
            tag = tag,
            indicators = new_indicators,
            subfields = new_subfields
            )                      
        return field

    def field_without_voc_code(self, tag, indicators, subfield):
        #luo uuden kentän ilman sanastokoodia
        subfield_code = "a"
        if tag == "567":
            subfield_code = "b"
        if tag == "370":
            subfield_code = "g"    
        field = Field(
            tag = tag,
            indicators = indicators,
            subfields = [subfield_code, subfield['value']]
            )         
        return field

    def add_control_subfields(self, field, control_subfields):
        #lisää konvertoituun kenttään numerolla koodatut osakentät
        new_subfields = self.subfields_to_dict(field.subfields)
        for code in control_subfields:
            for cs in control_subfields[code]:
                new_subfields.append({"code": code, "value": cs})
                new_subfields = self.sort_subfields(new_subfields)
        new_field = Field(
            tag = field.tag,
            indicators = field.indicators,
        )
        if self.linking_number:
        #and field.tag in ['650', '651', '655']:
            new_field.add_subfield("8", "%s\\u"%(self.linking_number))   
        for ns in new_subfields:
            new_field.add_subfield(ns['code'], ns['value'])   
        return new_field

    def strip_vocabulary_codes(self, field):
        #poistaa kentästä osakentät 0 ja 2
        subfields = self.subfields_to_dict(field.subfields)
        new_subfields = []
        for subfield in subfields:
            if subfield['code'] not in ['0', '2']:
                new_subfields.append(subfield['code'])
                new_subfields.append(subfield['value'])
        field = Field(
            tag = field.tag,
            indicators = field.indicators,
            subfields = new_subfields
            )                               
        return field

    def sort_field(self, field):
        new_subfields = self.sort_subfields(field.subfields)
        new_field = Field(
            tag = field.tag,
            indicators = field.indicators,
        )
        for ns in new_subfields:
            new_field.add_subfield(ns['code'], ns['value'])   
        return new_field

    def sort_subfields(self, subfields):
        #TODO: onko järjestys oikea?
        return sorted(subfields, key=lambda subfield: (  
            subfield['code'] == "9", 
            subfield['code'] == "5", 
            subfield['code'] == "0", 
            subfield['code'] == "2",
            subfield['code'] != "3",            
            subfield['code'] != "6",
            subfield['code'] != "8",
            subfield['code'].isdigit(),
            subfield['code'],
            subfield['code'] == "3",
            subfield['code'] == "6",
            subfield['code'] == "8"))

    def sort_fields(self, tag, original_fields, new_fields):
        """          
        Sanastojen järjestys kussakin kentässä
            2. indikaattorin koodin mukainen numerojärjestys: 0, 2, 4, 7. 
            TODO: muut indikaattorit?
            Kun indikaattori on sama, niin sanastot listataan sanastokoodin mukaan aakkosjärjestyksessä. 
            Poikkeuksena kentissä 650 ja 651, kun toinen indikaattori on 7, tulostetaan YSO kentät ensin. ja sitten muut sanastot aakkosjärjestyksessä.
            Kentässä 655 tulostetaan ensin SLM-kentät
        Termien järjestys kunkin sanaston sisällä 
            Vanhat kentät tulostetaan samassa järjestyksessä kuin ne ovat alunperinkin
            Vanhat YSO-termit listataan ensin
            Konvertoidut uudet YSO- ja SLM-termit tulostetaan siinä järjestyksessä kuin termejä käsitellään, 
            Uusista YSO-termeistä $9<FENNI>KEEP merktyt listataan käsittelyjärjestyksessä ensin, jos mahdollista
            Kunkin YSO:n ja SLM:n erikieliset termit listataan erikseen. Ensin suomenkieliset termit, sitten ruotsinkieliset termit. 
            Muiden sanastojen sisällä sanaston kentät listataan alkuperäisessä järjestyksessä ensimmäisen osakentän termin mukaan.
            Kentässä 653 käytetään 2. indikaattoria ilmaisemaan konversiossa lisättyjen termien tyyppi
        """
        fields = []
        idx = 0

        for of in original_fields:
            field = {}
            field.update({"field": of})
            field.update({"original": True})
            field.update({"index": idx})
            field.update({"indicator": of.indicators[1]})
            vocabulary_code = ""
            if of['2']:
                vocabulary_code = of['2']
            field.update({"code": vocabulary_code})  
            idx += 1
            fields.append(field)
        
        for nf in new_fields:
            field = {}
            field.update({"field": nf})
            field.update({"original": False})
            field.update({"index": idx})
            field.update({"indicator": nf.indicators[1]})
            vocabulary_code = ""
            if nf['2']:
                vocabulary_code = nf['2']
            field.update({"code": vocabulary_code})  
            idx += 1
            fields.append(field)
        
        fields_with_indicator_7 = []
        fields_without_indicator_7 = []

        if tag in ['650', '651', '655']:
            for field in fields:
                if field['indicator'] == "7":
                    fields_with_indicator_7.append(field)
                else:
                    fields_without_indicator_7.append(field)

        if tag == "650" or tag == "651":
            fields_with_indicator_7 = sorted(fields_with_indicator_7, key=lambda subfield: (  
                subfield['code'] != "yso",
                subfield['code'] != "yso/fin",
                subfield['code'] != "yso/swe",
                subfield['code'],
                subfield['code'] == "yso/swe",
                subfield['code'] == "yso/fin",
                subfield['code'] == "yso",
            ))
            fields_without_indicator_7 = sorted(fields_without_indicator_7, key=lambda subfield: (  
                subfield['code']
            ))
            fields = fields_with_indicator_7 + fields_without_indicator_7
        if tag == "655":
            fields_with_indicator_7 = sorted(fields_with_indicator_7, key=lambda subfield: (  
                subfield['code'] != "slm",
                subfield['code'] != "slm/fin",
                subfield['code'] != "slm/swe",
                subfield['code'],
                subfield['code'] == "slm/swe",
                subfield['code'] == "slm/fin",
                subfield['code'] == "slm",
            ))
            fields_without_indicator_7 = sorted(fields_without_indicator_7, key=lambda subfield: (  
                subfield['code']
            ))
            fields = fields_with_indicator_7 + fields_without_indicator_7

        fields = sorted(fields, key=lambda subfield: subfield['original'], reverse=True)
        fields = sorted(fields, key=lambda subfield: subfield['indicator'])
        sorted_fields = []
        for f in fields:
            sorted_fields.append(f['field'])
        return sorted_fields

def main():
    parser = argparse.ArgumentParser(description="YSO-konversio-ohjelma.")
    parser.add_argument("-i", "--input",
        help="Input file path", required=True)
    parser.add_argument("-o", "--output",
        help="Output file path", required=True)
    parser.add_argument("-f", "--format",
        help="File format", choices=['marc21', 'marcxml'], required=True)
    parser.add_argument("-al", "--all_languages",
        help="All languages", choices=['yes', 'no'], required=True)
    args = parser.parse_args()
    
    yc = YsoConverter(args.input, args.output, args.format, args.all_languages)
    yc.initialize_vocabularies()
    yc.read_records()
    
if __name__ == "__main__":
    main()