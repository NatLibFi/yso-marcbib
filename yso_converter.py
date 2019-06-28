#!/usr/bin/env python3
from rdflib import Graph, URIRef, Namespace, RDF
import pymarc
from pymarc import XmlHandler
from xml import sax
from pymarc import MARCReader, MARCWriter, XMLWriter, Record, Field
from pymarc.exceptions import (BaseAddressInvalid, 
                               RecordLeaderInvalid, 
                               BaseAddressNotFound, 
                               RecordDirectoryInvalid,
                               NoFieldsFound, 
                               FieldNotFound, 
                               RecordLengthInvalid) 
from xml.sax import SAXParseException
from vocabularies import Vocabularies
import urllib.request
import shutil
import argparse
import datetime
import pickle
import copy
import os
import logging
import sys
import re
import csv

class YsoConverter():

    def __init__(self, input_file, input_directory, output_file, output_directory, file_format, all_languages):      
        self.log_directory = "logs"
        if not os.path.isdir(self.log_directory):
            os.mkdir(self.log_directory)
        if input_file:
            if not os.path.isfile(input_file):
                logging.warning("Lähdetiedostoa ei ole olemassa.")
                sys.exit(2)
        if input_directory:
            if not os.path.isdir(input_directory):
                logging.warning("Lähdehakemistoa ei ole olemassa.")
                sys.exit(2)
        if input_file or output_file:
            if input_file == output_file:
                logging.warning("Lähdetiedoston ja kohdetiedoston nimi on sama.")
                sys.exit(2)
        if input_directory or output_directory:
            if input_directory == output_directory:
                logging.warning("Lähdetiedoston ja kohdetiedoston tiedostopolku on sama.")
                sys.exit(2)
        if output_file:
            if os.path.isfile(output_file):
                while True:
                    answer = input("Kirjoitettava tiedosto on olemassa. Kirjoitetaanko päälle (K/E)?")
                    if answer.lower() == "k":
                        break
                    if answer.lower() == "e":
                        sys.exit(2)
        if output_directory:
            if os.path.isdir(output_directory):
                while True:
                    answer = input("Kirjoitettava tiedostopolku on olemassa. Kirjoitetaanko päälle (K/E)?")
                    if answer.lower() == "k":
                        break
                    if answer.lower() == "e":
                        sys.exit(2)
        self.input_file = input_file
        self.input_directory = input_directory
        self.output_file = output_file
        self.output_directory = output_directory
        self.vocabularies = Vocabularies()
        self.file_format = file_format.lower()
        self.all_languages = False
        self.delimiter = "|"
        if all_languages == "yes":
            self.all_languages = True
        self.conversion_time = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.marcdate = str(datetime.date.today()).replace("-","")
        self.conversion_name = "yso-konversio"
        
        #self.error_logger = logging.getLogger()
        #korvataan kaksoispisteet Windows-tiedostonimeä varten:
        time = self.conversion_time.replace(":", "")
        

        self.error_log = self.conversion_name + "_error-log_" + time + ".log"

        

        self.removed_fields_log = self.conversion_name + "_removed-fields-log_" + time + ".log"
        self.new_fields_log = self.conversion_name + "_new-fields-log_" + time + ".log"
        self.results_log = self.conversion_name + "_results-log_" + time + ".log"
        self.error_log = os.path.join(self.log_directory, self.error_log)
        self.removed_fields_log = os.path.join(self.log_directory, self.removed_fields_log)
        self.new_fields_log = os.path.join(self.log_directory, self.new_fields_log)
        self.results_log = os.path.join(self.log_directory, self.results_log)

        """
        error_handler = logging.FileHandler(self.error_log, 'w', 'utf-8')
        error_handler.setLevel(logging.ERROR)
        self.error_logger.addHandler(error_handler)
        """
        self.linking_number = None #käytetään musiikkiaineiston hajotettujen ketjujen yhdistämiseen 8-osakentällä
        self.statistics = {}
        self.statistics.update({"konvertoituja tietueita": 0})
        self.statistics.update({"käsiteltyjä tietueita": 0})
        self.statistics.update({"käsiteltyjä kenttiä": 0})
        self.statistics.update({"kaikki tarkistetut kentät": 0})
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
            open(self.new_fields_log, 'w', encoding = 'utf-8-sig') as self.nf_handler, \
            open(self.error_log, 'w', newline='', encoding='utf-8-sig') as csvfile:
            
            self.csvriter = csv.writer(csvfile , delimiter=self.delimiter, quotechar='"', quoting=csv.QUOTE_MINIMAL)

            error_logger = logging.getLogger("error logger")
            error_handler = logging.FileHandler(self.error_log)
            error_logger.setLevel(logging.ERROR)

            input_files = []
            o_directory = ""
            i_directory = ""
            if self.input_directory:
                input_files = os.listdir(self.input_directory)          
            elif self.input_file:
                input_files.append(self.input_file)    
           
            if self.file_format == "marcxml":
                if not self.output_directory and self.input_directory:
                    self.writer = XMLWriter(open(self.output_file, 'wb'))
                for i_file in input_files:
                    if self.output_directory:
                        self.output_file = i_file
                        output_path = os.path.join(self.output_directory, self.output_file)
                    else:
                        output_path = self.output_file
                    if self.input_directory:
                        input_path = os.path.join(self.input_directory, i_file)
                    else:
                        input_path = i_file
                    if not self.output_directory and self.input_directory:
                        pass
                    else:
                        self.writer = XMLWriter(open(output_path, 'wb'))
                    try:
                        pymarc.map_xml(self.read_and_write_record, input_path)
                    except SAXParseException as e:
                        logging.warning("XML-rakenne viallinen, suoritus keskeytetään")
                        logging.warning(e)
                        sys.exit(2)
                    if not self.output_directory and self.input_directory:
                        continue
                    self.writer.close()
                if not self.output_directory and self.input_directory:
                    self.writer.close()
            if self.file_format == "marc21":
                if not self.output_directory and self.input_directory:
                    self.writer = MARCWriter(open(self.output_file,'wb'))
                for i_file in input_files:
                    if self.output_directory:
                        self.output_file = i_file
                        output_path = os.path.join(self.output_directory, self.output_file)
                    else:
                        output_path = self.output_file
                    if self.input_directory:
                        input_path = os.path.join(self.input_directory, i_file)
                    else:
                        input_path = i_file
                    #with open(input_path, 'rb') as fh, \
                    #open(self.output_file,'wb') as output:
                    if not self.output_directory and self.input_directory:
                        pass
                    else:
                        self.writer = MARCWriter(open(output_path,'wb'))
                    try:
                        reader = MARCReader(open(input_path, 'rb'), force_utf8=True, to_unicode=True)
                        record = Record()
                        while record:                
                            try:
                                record = next(reader, None)
                        
                                if record:
                                    self.read_and_write_record(record)
                            except (BaseAddressInvalid, 
                                    RecordLeaderInvalid, 
                                    BaseAddressNotFound, 
                                    RecordDirectoryInvalid,
                                    NoFieldsFound, 
                                    UnicodeDecodeError,
                                    ValueError,
                                    RecordLengthInvalid) as e:
                                if e.__class__.__name__ in self.statistics["virheluokkia"]:
                                    self.statistics["virheluokkia"][e.__class__.__name__] += 1
                                else:
                                    self.statistics["virheluokkia"].update({e.__class__.__name__: 1})
                                self.statistics['virheitä'] += 1
                    except TypeError:
                        logging.error("Tiedosto %s ei ole MARC21-muodossa"%input_path)
                        sys.exit(2)
                    if not self.output_directory and self.input_directory:
                        continue
                    self.writer.close()
                if not self.output_directory and self.input_directory:
                    self.writer.close()
              
        self.rf_handler.close()
        self.nf_handler.close()
        #error_handler.close()
        csvfile.close()
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
            new_record = None
            try:
                raw = record.as_marc()
                new_record = Record(data=raw)
            except ValueError as e:
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

    def similar_fields(self, ignored_codes, *fields):
        """
        apufunktio, joka vertailee parametreinä annettuja MARC21-kenttiä ja testaa, ovatko ne kaikki identtisiä
        ignored_codes: osakenttäkoodit, joita ei huomioida vertailussa
        fields: vertailtavat MARC21-kentät
        """
        field_subfields = []
        for field in fields:
            trimmed_subfields = []
            for subfield in self.subfields_to_dict(field.subfields):
                if subfield['code'] not in ignored_codes:
                    trimmed_subfields.append({"code": subfield['code'], "value": subfield['value']})
            field_subfields.append(trimmed_subfields)      
        for m in range(len(field_subfields) - 1):
            for n in range(m + 1, len(field_subfields)):
                if field_subfields[m] != field_subfields[n]:
                    return False
        return True

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
                            non_fiction = False
                            for field in record.get_fields('084'):
                                for subfield in field.get_subfields('a'):
                                    if subfield.startswith("78"):
                                        record_type = "music"
            if not record_type:
                record_type = "text"

            for tag in tags_of_fields_to_convert:
                for field in record.get_fields(tag):
                    self.statistics["kaikki tarkistetut kentät"] += 1
                    if any (sf in ['musa', 'cilla', 'ysa', 'allars'] for sf in field.get_subfields("2")):
                        convertible_record = True

            #jos $8-osakenttiä elokuva- tai musiikkitietueessa ennestään, otetaan uusien $8-osakenttien 1. numeroksi viimeistä seuraava numero:
            if convertible_record:
                if record_type in ['music', 'movie']:
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
                                self.rf_handler.write(record_id + self.delimiter + str(field) + "\n")
                                self.statistics['poistettuja kenttiä'] += 1
                                if converted_fields:
                                    altered_fields.add(tag)
                                    for cf in converted_fields:
                                        #self.statistics['uusia kenttiä'] += 1
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
                        if sorted_fields[m]['2']:
                            if sorted_fields[m]['2'] in ['yso/fin', 'yso/swe', 'slm/fin', 'slm/swe']:
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
                    
                    #poistetaan identtiset $8-osakentät ja yhdistellään $8-osakentät samaan kenttään:
                    
                    for m in range(len(sorted_fields)):
                        linking_numbers_list = [] #tallentaan erilaiset $8-osakentät, jos on useampia muuten identtisiä kenttiä
                        if sorted_fields[m]['2']:
                            if sorted_fields[m]['2'] in ['yso/fin', 'yso/swe', 'slm/fin', 'slm/swe'] and m not in removable_fields:
                                for n in range(m + 1, len(sorted_fields)):
                                    if m not in removable_fields and n not in removable_fields:
                                        m_subfields = self.subfields_to_dict(sorted_fields[m].subfields)
                                        n_subfields = self.subfields_to_dict(sorted_fields[n].subfields)
                                        if self.similar_fields(['8'], sorted_fields[m], sorted_fields[n]):
                                            for subfield in m_subfields:
                                                if subfield['code'] == "8":
                                                    if subfield['value'] not in linking_numbers_list:
                                                        linking_numbers_list.append(subfield['value'])
                                            for subfield in n_subfields:
                                                if subfield['code'] == "8":
                                                    if subfield['value'] not in linking_numbers_list:
                                                        linking_numbers_list.append(subfield['value'])        
                                            removable_fields.add(n)
                        if linking_numbers_list:
                            while (sorted_fields[m]['8']):
                                sorted_fields[m].delete_subfield('8')
                        for ln in linking_numbers_list:
                            sorted_fields[m].add_subfield('8', ln)
                              
                        new_subfields = self.sort_subfields(self.subfields_to_dict(sorted_fields[m].subfields))
                        subfield_list = []
                        for ns in new_subfields:
                            subfield_list.extend([ns['code'], ns['value']])
                        new_field = Field(
                            tag = tag,
                            indicators = sorted_fields[m].indicators,
                            subfields = subfield_list
                        )
                        sorted_fields[m] = new_field

                    for idx in range(len(sorted_fields)):
                        if idx not in removable_fields:
                            if not any(str(sorted_fields[idx]) == str(field) for field in record.get_fields(tag)):
                                self.nf_handler.write(record_id + self.delimiter + str(sorted_fields[idx]) + "\n")
                                self.statistics['uusia kenttiä'] += 1
                            record.add_ordered_field(sorted_fields[idx])  
                            
                        #TODO: älä tilastoi tässä kohtaa poistettavia rivejä: poista uusien rivien tilastosta nyt poistettava rivi? 
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
        #$6-osakentälliset kentät jätetään käsittelemättä, mutta poistetaan $2- ja $0-osakentät:
        for subfield in field.get_subfields('6'):
            new_field = self.strip_vocabulary_codes(field)
            new_field.indicators[1] = "4"
            #logging.error("%s;%s;%s;%s;%s"%("9", record_id, subfield, field, new_field))
            self.csvriter.writerow(["9", record_id, subfield, field, new_field])
            return [new_field]
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
                        if subfields[0]['code'] in ['a', 'b', 'c', 'd', 'v', 'x', 'y', 'z']: 
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
            #logging.error("%s;%s;%s;%s"%("8", record_id, subfield['value'], field))
            self.csvriter.writerow(["8", record_id, subfield['value'], field])
            return [field]      

        if tag in ['650'] and record_type == "movie":
            has_topics = True #alkuoletuksena on, että elokuvatietueen kentät tulkitaan aiheiksi
            has_genre_terms = False #kentän loput termeistä tulkitaan tämän perusteella luomiseen liittyviksi
            for subfield in subfields:
                if subfield['code'] in ['a', 'x']:
                    if subfield['code'] == "a" and "elokuvat" in subfield['value']:
                        has_genre_terms = True
                        has_topics = False
                    if subfield['value'] == "aiheet":
                        has_topics = True
                        #logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], field))
                        self.csvriter.writerow(["6", record_id, subfield['value'], field])
                    else:
                        responses = []  
                        converted_fields = self.process_subfield(record_id, field, subfield, vocabulary_code, non_fiction, record_type, has_topics)  
                        if converted_fields:
                            for cf in converted_fields:
                                cf = self.add_control_subfields(cf, control_subfields)
                                new_fields.append(cf) 
                elif not subfield['code'].isdigit():
                    converted_fields = self.process_subfield(record_id, field, subfield, vocabulary_code, non_fiction, record_type, has_topics)
                    if converted_fields:
                        for cf in converted_fields:
                            cf = self.add_control_subfields(cf, control_subfields)
                            new_fields.append(cf) 
            return new_fields
                
        #poikkeuksellisesti käsiteltävät kentät: 
        #385, 567 ja 648, jossa 1. indikaattori on "1", 650/655, jos musiikkiaineistoa:
        #musiikki- ja elokuva-eineisto, jos $a- tai $x-osakentässä on asiasanana aiheet
        #musiikkiaineisto, jossa SEKO-asiasanoja
        if tag in ['650', '655'] and record_type == "music":
            #kerätään SEKO-termejä sisältävät osakentät 382-kenttään siirrettäväksi:
            instrument_lists = []
            instrument_list = []
            
            has_topics = False #kentän loput termeistä tulkitaan tämän perusteella aiheiksi
            has_genre_terms = False #kentän loput termeistä tulkitaan tämän perusteella luomiseen liittyviksi
            for subfield in subfields:
                if subfield['code'] in ['a', 'x']:
                    if subfield['value'] == "kokoelmat":
                        subfield['value'] = "kokoomateokset"
                    if subfield['value'] == "sovitukset":
                        if instrument_list:
                            instrument_list = []
                    if subfield['value'] == "aiheet" and tag == "650":
                        has_topics = True
                        #logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], field))
                        self.csvriter.writerow(["6", record_id, subfield['value'], field])
                    elif subfield['value'] == "musiikki":
                        #logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], field))
                        self.csvriter.writerow(["6", record_id, subfield['value'], field])
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
                            if converted_fields:
                                for cf in converted_fields:
                                    if cf['2'] and tag == "650":
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
                    if converted_fields:
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
                new_field = self.strip_vocabulary_codes(field)
                new_field.indicators = [' ', ' ']
                #logging.error("%s;%s;%s;%s"%("8", record_id, "", field, new_field))
                self.csvriter.writerow(["8", record_id, "", field, new_field])
                return [new_field]
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
                new_field = self.strip_vocabulary_codes(field)
                new_field.indicators = [' ', ' ']
                #logging.error("%s;%s;%s;%s;%s"%("8", record_id, "", field, new_field))
                self.csvriter.writerow(["8", record_id, "", field, new_field])
                return [field]
        for subfield in subfields:
            if not subfield['code'].isdigit():
                #or tag == "385" or tag == "567":
                if tag == "385":
                    if subfield['code'] != "a":
                        continue
                if tag == "567":
                    if subfield['code'] != "b":
                        continue         
                if tag == "655" and record_type == "music":
                    if subfield['code'] in ['a', 'x', 'v']:
                        if subfield['value'] == "kokoelmat":
                            subfield['value'] = "kokoomateokset"

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
            #logging.error("%s;%s;%s;%s"%("1", record_id, subfield['value'], original_field))
            self.csvriter.writerow(["1", record_id, subfield['value'], original_field])
            return
        #alustetaan ensin hakuparametrien oletusarvot
        vocabulary_order = [] #hakujärjestys, jos sanaa haetaan useammasta sanastosta 
        language = None
        
        #sanastohakujärjestykseen liittyvät muuttujat:
        has_music = False
        yso = True
        slm = False
        
        if vocabulary_code == "ysa":
            language = "fi"
        if vocabulary_code == "allars":
            language = "sv"    
        if vocabulary_code == "musa":
            language = "fi"    
            has_music = True
        if vocabulary_code == "cilla":
            language = "sv"   
            has_music = True  
        
        #vocabulary_order = self.set_vocabulary_order(language, yso=True, music=has_music)

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
            '655': ['a', 'v', 'x', 'z']
        }

        #käsitellään ensin poikkeustapaukset ja/tai annetaan sanastohaulle erityisjärjestys:
        if tag == "385" or tag == "567":
            search_geographical_concepts = False
        if tag == "655":
            if not subfield['code'] == "z":
                yso = False #vain 655 kentän z-osakentässä katsotaan myös Ysa- ja Allärs-termejä
                has_music = False #ei katsotaan myöskään Musasta eikä Cillasta
            if subfield['code'] in ['a', 'v', 'x']:
                search_geographical_concepts = False
                slm = True
            if subfield['code'] == "y":                          
                field = self.field_without_voc_code("388", [' ', ' '], subfield)
                if vocabulary_code in ['ysa', 'musa']:
                    field.add_subfield('2', 'yso/fin')
                if vocabulary_code in ['allars', 'cilla']:
                    field.add_subfield('2', 'yso/swe')
                return [field]
        if tag in ['648', '650', '651']:
            if subfield['code'] == "v":
                slm = True
                if vocabulary_code in ['musa', 'cilla']:
                    has_music = True
                if tag == '650' or tag == '651':
                    if subfield['value'].lower() == "fiktio":
                        #logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], original_field))
                        self.csvriter.writerow(["6", record_id, subfield['value'], original_field])
                        return
            if tag == "650" and subfield['code'] == "a":
                if not non_fiction:
                    slm = True
                    if vocabulary_code in ['musa', 'cilla']:
                        has_music = True
        if tag in ['650', '651']:
            if subfield['code'] == "e":
                #logging.error("%s;%s;%s;%s"%("6", record_id, subfield['value'], original_field))
                self.csvriter.writerow(["6", record_id, subfield['value'], original_field])
                return 
            elif subfield['code'] == "g":
                field = self.field_without_voc_code("653", [' ', ' '], subfield)   
                #logging.error("%s;%s;%s;%s;%s"%("7", record_id, subfield['value'], original_field, field))
                self.csvriter.writerow(["7", record_id, subfield['value'], original_field, field])
                return [field]    
        if record_type == "music":
            if tag in ['650', '655']:
                if subfield['code'] == "a" and tag == "650":
                    slm = True
                if subfield['code'] in ['x', 'y', 'z']:
                    if not has_topics:
                        slm = True

        vocabulary_order = self.set_vocabulary_order(language, yso, slm, has_music)
        
        #hakujärjestykseen lisäys niille osakentille, josta haetaan aikatermejä:
        #Huom! 655 y käsitelty jo edellä
        if subfield['code'] == "y" and tag in ['648', '650', '651']:
            vocabulary_order = [('numeric', language)] + vocabulary_order
        if tag == "648":
            if subfield['code'] in ['a', 'x', 'z']:
                vocabulary_order = [('numeric', language)] + vocabulary_order
        if tag == "650":
            if subfield['code'] in ['a', 'b', 'c', 'x', 'z']:
                vocabulary_order = vocabulary_order + [('numeric', language)]
            if subfield['code'] == "d":
                vocabulary_order = [('numeric', language)] + vocabulary_order
        if tag == "651":
            if subfield['code'] in ['a', 'x', 'z']:
                vocabulary_order = vocabulary_order + [('numeric', language)]

        #käsitellään perustapaukset
        if subfield['code'] in valid_subfield_codes[tag]:
        #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja 
            try:
                responses = self.vocabularies.search(subfield['value'], vocabulary_order, search_geographical_concepts, self.all_languages)
                if tag == "650" and not non_fiction and subfield['code'] == "a":
                    tag == "655"
                if tag == "655" and subfield['code'] in ['z', 'c']:
                    if record_type == "movie":
                        tag = "257"
                    else:
                        tag = "370"
                if tag == "650" and record_type in ['music', 'movie'] and not has_topics: 
                    if subfield['code'] in ['z', 'c']:
                        if record_type == "movie":
                            tag = "257"
                        else:
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
                    if tag in ['650', '651'] and subfield['code'] == "v":
                        tag = 655
                    field = self.field_without_voc_code(tag, [' ', '4'], subfield)
                    converted_fields.append(field)
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
                            field = self.field_without_voc_code("653", [' ', '5'], subfield)    
                        elif subfield['code'] in ['v']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                    elif tag == '655':
                        if subfield['code'] in ['a', 'v', 'x']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                        elif subfield['code'] in ['z', 'c']:
                            field = self.field_without_voc_code("370", [' ', ' '], subfield)      
                    converted_fields.append(field)
                else:
                    logging.info("Tuntematon virhekoodi %s tietueessa %s virheilmoituksessa: %s"%(e, record_id, original_field))
                #logging.error("%s;%s;%s;%s;%s"%(e, record_id, subfield['value'], original_field, field))
                self.csvriter.writerow([e, record_id, subfield['value'], original_field, field])
        else:
            #logging.error("%s;%s;%s;%s"%("8", record_id, subfield['value'], original_field))
            self.csvriter.writerow(["8", record_id, subfield['value'], original_field])
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
            if tag in ['257', '388']:
                new_indicators = [' ', ' ']
            else:
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

    def set_vocabulary_order(self, language_code, yso=False, slm=False, music=False):
        """
        palauttaa listan sanastoista ja kielikoodeista sanastohakua varten
        esim. [('musa', 'fi'), ('slm', 'fi'), ('ysa', 'fi'), ('cilla', 'sv'), ('slm', 'sv'), ('allars', 'sv')],
        jos kielikoodi on "fi" ja kaikki muiden parametrien arvo True
        language_code: ensisijainen hakukieli kielikoodina
        slm: haetaan SLM-sanastosta
        music: haetaam Musa- ja Cilla-sanastoista 
        """
        vocabulary_order = []
        if yso:
            vocabulary_order += [('ysa', 'fi'), ('allars', 'sv')]
        if slm:
            vocabulary_order += [('slm', 'fi'), ('slm', 'sv')]    
        if music:
            vocabulary_order += [('musa', 'fi'), ('cilla', 'sv')] 
        vocabulary_order = sorted(vocabulary_order, key=lambda tup: (  
            tup[1] != language_code,
            tup[0] == "ysa",
            tup[0] == "allars",
            tup[0] == "slm",
            tup[0] == "musa",
            tup[0] == "cilla"
        ))
        return vocabulary_order

def main():
    parser = argparse.ArgumentParser(description="YSO-konversio-ohjelma.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", 
        help="Input file path")
    input_group.add_argument("-id", "--inputDirectory",
        help="Directory for input files",)

    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument("-o", "--output",
        help="Output file path")
    output_group.add_argument("-od", "--outputDirectory",
        help="Directory for output files")

    parser.add_argument("-f", "--format",
        help="File format", choices=['marc21', 'marcxml'], required=True)
    parser.add_argument("-al", "--all_languages",
        help="All languages", choices=['yes', 'no'], required=True)

    args = parser.parse_args()

    yc = YsoConverter(args.input, args.inputDirectory, args.output, args.outputDirectory, args.format, args.all_languages)
    yc.initialize_vocabularies()
    yc.read_records()
    
if __name__ == "__main__":
    main()