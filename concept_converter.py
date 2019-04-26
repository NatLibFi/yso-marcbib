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
import datetime
import copy
import os.path

class ConceptConverter():

    def __init__(self, input_file=None, output_file=None):      

        self.input_file = input_file
        self.output_file = output_file
        self.vocabularies = Vocabularies()
        self.conversion_time = datetime.datetime.now().replace(microsecond=0).isoformat()
        self.marcdate = str(datetime.date.today()).replace("-","")
        self.conversion_name = "yso-konversio"
        self.isil_identifier = "FI-NL"
        self.conversion_url = "http://kiwi.fi/display/ysall2yso"
        
        """
        self.input_file = input('Input file name? ')
        if not os.path.isfile(self.input_file):
            while (True):
                answer = input('File %s, overwrite (y/n)? '%input_file)
                    if nb == "n":
                        continue
                    if nb == "y":
                        break  
        self.output_file = input('Output file name? ')            
        if os.path.isfile(output_file):
            while (True):
                nb = input('%s exists, overwrite (y/n)? '%output_file)
                if nb == "n":
                    continue
                if nb == "y":
                    break
        """                    
        #self.xml_writer = pymarc.XMLWriter(open(self.output_file,'wb'))

    def initialize_vocabularies():
        yso_graph = Graph()
        yso_graph.parse('yso-skos.rdf')

        print("parsitaan YSO-paikkoja")
        yso_paikat_graph = Graph()
        yso_paikat_graph.parse('yso-paikat-skos.rdf')

        print("parsitaan YSaa")
        ysa_graph = Graph()
        ysa_graph.parse('ysa-skos.rdf')

        print("parsitaan Allärsia")
        allars_graph = Graph()
        allars_graph.parse('allars-skos.rdf')

        print("parsitaan SLM_ää")
        slm_graph = Graph()
        slm_graph.parse('slm-skos.rdf')

        print("parsitaan Musaa")
        musa_graph = Graph()
        musa_graph.parse('musa-skos.rdf')

        print("sanastot parsittu")
        self.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        self.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        self.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        self.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        self.vocabularies.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        self.vocabularies.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        self.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        self.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)

    def subfields_to_dict(self, subfields):
        """
        muuntaa helpommin käsiteltäväksi pymarcin "osakenttälistan" eli listan, 
        jossa joka toinen alkio on osakenttäkoodi ja joka toinen osakenttä,
        listaksi, jossa on avainarvopareja (osakenttäkoodi, osakenttä) 
        """
        subfields_list = []
        #Testattava, jos subfields-listassa pariton määrä alkioita! 
        for idx in range(0, len(subfields), 2):
            if idx + 1 < len(subfields):
                subfields_list.append({"code": subfields[idx], "value": subfields[idx+1]})
        return subfields_list         
    
    def remove_field_link_and_code(self, subfields):
        trimmed_subfields = []
        for subfield in self.subfields_to_dict(subfields):
            if subfield['code'] not in ['0', '2']:
                trimmed_subfields.append({"code": subfield['code'], "value": subfield['value']})
        return trimmed_subfields
    
    def is_equal_field(self, first_subfields, second_subfields):
        return self.sort_subfields(self.subfields_to_dict(first_subfields)) == \
               self.sort_subfields(self.subfields_to_dict(second_subfields))

    def process_record(self, record):
        if record['001']:
            tags_of_fields_to_convert = ['385', '567', '648', '650', '651', '655']
            tags_of_fields_to_process = ['370', '385', '388', '567', '648', '650', '651', '653', '655']
            original_fields = {}
            new_fields = {}
            altered_fields = set()
            record_status = record.leader[5]
            record_id = record['001'].data
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
            fiction = False
            convertible_record = False
            if leader_type in ['a', 't']:
                record_type = "text"
                if record.leader[7] not in ['b', 'i', 's']:
                    if record['006']:
                        if len(record['006'].data) > 16:
                            if record['006'].data[16] not in ['0', 'u', '|']:
                                fiction = True
                    elif record['008']:
                        if len(record['008'].data) > 33:
                            if record['008'].data[33] not in ['0', 'u', '|']:
                                fiction = True
            elif leader_type in ['c', 'd', 'i', 'j']: 
                record_type = "music"
                if leader_type == "i":
                    if record['008']:
                        if len(record['008'].data) > 31:
                            if any (lf in record['008'].data[30:31] for lf in ['d', 'f', 'p']):
                                fiction = True
            elif leader_type == "g":
                record_type = "image"            
            if record_type != "text":
                return
            for tag in tags_of_fields_to_convert:
                for field in record.get_fields(tag):
                    if any ("ysa" in sf for sf in field.get_subfields("2")) or \
                        any ("allars" in sf for sf in field.get_subfields("2")):
                        convertible_record = True
            #TODO: musiikkiaineistoa ei käsitellä vielä
            if record_type == "music":
                convertible_record = False

            if record_type == "text" and convertible_record:   
                subfields = []
                #TODO: vaihtoehto: säilytetään alkup. YSA-rivi, jos valittu optio
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
                                converted_fields = self.process_field(record_id, field, vocabulary_code, fiction)
                                if converted_fields:
                                    altered_fields.add(tag)
                                    for cf in converted_fields:
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
                                elif self.sort_subfields(self.remove_field_link_and_code(sorted_fields[m].subfields)) == \
                                    self.sort_subfields(self.remove_field_link_and_code(sorted_fields[n].subfields)):
                                    if sorted_fields[m]['2'] and sorted_fields[m]['0']:
                                        removable_fields.add(n)
                                    if sorted_fields[n]['2'] and sorted_fields[n]['0']:
                                        removable_fields.add(m)
                    for idx in range(len(sorted_fields)):
                        if idx not in removable_fields:
                            record.add_ordered_field(sorted_fields[idx])   
            else:
                return
            record.add_ordered_field(
                Field(
                    tag = '884',
                    indicators = [' ',' '],
                    subfields = [
                        'a', self.conversion_name,
                        'g', self.marcdate,
                        'q', self.isil_identifier,
                        'u', self.conversion_url
            ]))
            #TODO: tarkista ja tilastoi, onko tietue muuttunut
            return record
        
                 
                  
    def read_marcxml_file(self):
        #TODO: varaudu XML-epäsäännöllisyyksiin, esim. except xml.sax._exceptions.SAXParseException
        reader = XmlHandler(self.input_file)
        pymarc.map_xml(self.process_record, self.input_file)
        #reader = pymarc.parse_xml_to_array(self.input_file)

    def read_mrc_files(self):
        with open(self.input_file, 'rb') as in_file, \
            open(self.output_file, 'wb') as out_file:
            reader = MARCReader(in_file, force_utf8=True, to_unicode=True)
            writer = MARCWriter(out_file)
            record = Record()
            while record:                
                try:
                    #TODO: kirjoittaminen MARCXML-formaattiin, jos valittu
                    #xml_writer.write(record)
                    record = next(reader, None)
                    if record:
                        new_record = self.process_record(record)
                        if new_record:
                            writer.write(new_record)
                        #TODO: kirjoitetaanko konvertoimattomatkin tietueet?
                except BaseAddressInvalid:  
                    pass
                except RecordLengthInvalid:    
                    pass     
                except BaseAddressNotFound:
                    pass
                except RecordDirectoryInvalid:
                    pass
                except NoFieldsFound:
                    pass
                except FieldNotFound: 
                    pass
                except UnicodeDecodeError:
                    pass
                except AttributeError:
                    print(id)        
        in_file.close()
        out_file.close()

    def mrc_to_mrcx(self, input_file, output_file):
        print("converting %s" %input_file) 
        records = pymarc.parse_xml_to_array(input_file)
        mrc_writer = pymarc.MARCWriter(open(output_file, 'wb'))
        for r in records:
            mrc_writer.write(r)
        mrc_writer.close() 
        print("file written") 
        
    def process_field(self, record_id, field, vocabulary_code, fiction=False):
        #record_id: tietueen numero virheiden lokitusta varten
        #fiction: Tarvitaan ainakin
        new_fields = []
        tag = field.tag
        subfields = self.subfields_to_dict(field.subfields)
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
                        continue
                    if csc in control_subfields:
                        try:
                            control_subfields[csc].append(sf)
                        except TypeError:
                            print("type error "+str(sf))
                    else:
                        control_subfields.update({csc: [sf]})      
        #etsitään paikkaketjut ja muodostetaan niistä yksiosainen käsite:
        #TODO: katsotaan mahdollisest imyös muita kuin maantieteellisiä termejä
        if tag == "650" or tag == "651":
            combined_subfields = []
            while len(subfields) > 0:
                if len(subfields) > 1:
                    if subfields[0]['code'] == "a" or subfields[0]['code'] == "z":
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
            return [self.strip_vocabulary_codes(field)]
            #TODO: tulosta rivi virhelokiin
        
        #poikkeuksellisesti käsiteltävät kentät: 385, 567 ja 648:
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
                            subfield_list.append(ns['code'])
                            subfield_list.append(ns['value'])
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
                            response = self.vocabularies.search(subfield['value'], [vocabulary_code])
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
                new_field = self.process_subfield(record_id, field, subfield, vocabulary_code, fiction)
                #TODO: listaus koko 358- ja 567-kentästä virhelokiin
                #if tag not in ['385', '567']:
                if new_field:
                    new_subfields = self.subfields_to_dict(new_field.subfields)
                    for code in control_subfields:
                        for cs in control_subfields[code]:
                            new_subfields.append({"code": code, "value": cs})
                            new_subfields = self.sort_subfields(new_subfields)
                    new_field = Field(
                        tag = new_field.tag,
                        indicators = new_field.indicators,
                    )
                    for ns in new_subfields:
                        new_field.add_subfield(ns['code'], ns['value'])   
                    
                    new_fields.append(new_field)
                    """
                    if new_field.tag in new_fields:
                        new_fields[new_field.tag].append(new_field)
                    else:
                        new_fields.update({new_field.tag: [new_field]})
                    """
        return new_fields
        
    def process_subfield(self, record_id, original_field, subfield, vocabulary_code, fiction=False):
        #TODO: log error
        if not subfield['value']:
            return
        #alustetaan ensin hakuparametrien oletusarvot
        vocabulary_order = [] #hakujärjestys, jos sanaa haetaan useammasta sanastosta 
        language = None
        if vocabulary_code == "ysa":
            vocabulary_order = ['ysa', 'allars']
            language = "fi"
        if vocabulary_code == "allars":
            vocabulary_order = ['allars', 'ysa']
            language = "sv"    
        if vocabulary_code == "musa":
            vocabulary_order = ['musa', 'cilla', 'ysa', 'allars']
            language = "fi"    
        if vocabulary_code == "cilla":
            vocabulary_order = ['cilla', 'musa', 'allars', 'ysa']
            language = "sv"     
        slm_vocabulary_order = {}
        slm_vocabulary_order['fi'] = ['slm_fi', 'ysa', 'slm_sv', 'allars'] 
        slm_vocabulary_order['sv'] = ['slm_sv', 'allars', 'slm_fi', 'ysa']   
        search_geographical_concepts = True    

        tag = original_field.tag
        field = None
        #new_tag = None
        #new_indicators = None
        #new_subfields = None
        
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
        """    
            #385- ja 567-kenttien erikoiskäsittely:  
            #tulostetaan käsiteltävät osakentät jokainen omalle riville ja kaikkiin kenttiin muut osakentät sellaisenaan
            
            subfield_code = None
            new_subfields = []
            if tag == "385" :
                subfield_code = "a"
                valid_subfield_codes = ['a', 'b', 'm', 'n', '0', '1', '2', '3', '5', '6', '8', '9']
            if tag == "567":
                subfield_code = "b"
                valid_subfield_codes = ['a', 'b', '0', '1', '2', '5', '6', '8', '9']
            try:
                response = self.vocabularies.search(subfield['value'], vocabulary_order, search_geographical_concepts)
                original_subfields = self.subfields_to_dict(original_field.subfields) 
                for subfield in original_subfields:
                    if subfield['code'] not in valid_subfield_codes:        
                        #TODO: log error
                        continue
                    if subfield['code'] == "0" or subfield['code'] == "2" or subfield['code'] == subfield_code:
                        continue
                    new_subfields.append({'code': subfield['code'], 'value': subfield['value']})
                new_subfields.append({'code': subfield_code, 'value': response['label']}) 
                new_subfields.append({'code': "0", 'value': response['uris'][0]})
                new_subfields.append({'code': "2", 'value': response['code']})
                               
            except ValueError as e:
                if str(e) == "MULTIPLE_CONCEPTS":
                    field = self.field_without_voc_code("653", [' ', '4'], subfield)
                    #TODO: puuttuu konversiosäännöistä
                    return field
                elif str(e) == "NOT_FOUND":
                    original_subfields = self.subfields_to_dict(original_field.subfields)
                    
                    for sf in original_subfields:
                        if sf['code'] == "0" or sf['code'] == "2" or sf['code'] == subfield_code:
                            continue
                        else:
                            new_subfields.append(sf)
                    new_subfields.append({'code': subfield_code, 'value': subfield['value']})
                    #TODO: palautetaan virheellinen asiasana???
                    #TODO: log error
            #aakkkostetaan uudet ja vanhat osakenttäkoodit numerot viimeiseksi:
            #new_subfields = self.sort_subfields(new_subfields)
            field = Field(
                tag = tag,
                indicators = [' ',' '],
            )
            for ns in new_subfields:
                field.add_subfield(ns['code'], ns['value'])            
            return field    
        """    
        if tag == "655":
            if subfield['code'] in ['a', 'v', 'x']:
                search_geographical_concepts = False
                if language == "fi":
                    vocabulary_order = ['slm_fi', 'slm_sv']
                if language == "sv":
                    vocabulary_order = ['slm_sv', 'slm_fi']    
            if subfield['code'] == "y":                          
                field = self.field_without_voc_code("388", ['1', ' '], subfield)
                if vocabulary_code in ['ysa', 'musa']:
                    field.add_subfield('2', 'yso/fin')
                if vocabulary_code in ['musa', 'cilla']:
                    field.add_subfield('2', 'yso/swe')
                return(field)
        if tag in ['648', '650', '651']:
            if subfield['code'] == "v":
                vocabulary_order = slm_vocabulary_order[language]
                if tag == '650' or tag == '651':
                    if subfield['value'].lower() == "fiktio":
                        return #TODO: log error REMOVED
            if tag == "650" and subfield['code'] == "a" and fiction:
                vocabulary_order = slm_vocabulary_order[language]
        if tag == "650" or tag == "651": 
            if subfield['code'] == "e":
                return #TODO: log error REMOVED
            elif subfield['code'] == "g":
                field = self.field_without_voc_code("653", [' ', ' '], subfield)   
                print("täällä jotain")
                return field
            if subfield['code'] in ['a', 'b', 'c', 'x', 'z']:
                vocabulary_order.append('numeric')
            if subfield['code'] in ['d', 'y']:
                vocabulary_order = ['numeric'] + vocabulary_order
        if tag == "648" and subfield['code'] == "a":
            vocabulary_order = ['numeric'] + vocabulary_order
        #käsitellään perustapaukset
        if subfield['code'] in valid_subfield_codes[tag]:
        #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja 
            try:
                response = self.vocabularies.search(subfield['value'], vocabulary_order, search_geographical_concepts)
                
                if tag == "650" and fiction and subfield['code'] == "a":
                    tag == "655"
                field = self.field_with_voc_code(tag, response)
            except ValueError as e:
                #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja
                if str(e) == "MULTIPLE_CONCEPTS":
                    #TODO: korjattava tagi! Sulkutarkenteettomat monitulkintaiset myös tähän!
                    field = self.field_without_voc_code(tag, [' ', '4'], subfield)
                elif str(e) == "NOT_FOUND":
                    if tag == "385" or tag == "567":
                        field = self.field_without_voc_code(tag, [' ', ' '], subfield)      
                    if tag in ['648', '650', '651']:
                        if subfield['code'] in ['a', 'b', 'd', 'x', 'y']:
                            field = self.field_without_voc_code("653", [' ', '0'], subfield)
                        if subfield['code'] in ['d', 'y']:
                            field = self.field_without_voc_code("653", [' ', '4'], subfield)
                        if subfield['code'] in ['c', 'z']:
                            field = self.field_without_voc_code("653", [' ', '5'], subfield)    
                        if subfield['code'] in ['v']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                    if tag == '655':
                        if subfield['code'] in ['a', 'v', 'x']:
                            field = self.field_without_voc_code("653", [' ', '6'], subfield)
                        if subfield['code'] in ['b']:
                            field = self.field_without_voc_code("653", [' ', '0'], subfield)   
                        if subfield['code'] in ['z']:
                            field = self.field_without_voc_code("370", [' ', ' '], subfield)      
        else:
            #TODO: log error
            original_field.indicators[1] = "4"
            original_field.delete_subfield('2')
            
            return original_field
            #alkuperäinen ketju jätetään, 2. ind 4 ja poistetaan $2ysa osakenttä

        #else: alkuperäinen ketju jäteään, 2. ind 4 ja poistetaan $2ysa osakenttä????????????

        #MUISTA LIITTÄÄ NUMEROLLISET OSAKENTÄT UUTEEN KENTTÄÄN!!!
        #self.vocabularies.search("ragat", "fi", ['slm', 'allars', 'ysa']))
        return field
        

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
            tag = "648"
            new_indicators = [' ', '7']
            new_subfields = ["a", response['label'], '2', response['code']]
        else: 
            
            subfield_code = "a"
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
    """    
    def is_numeric_subfield(self, subfield):
        is_numeric = False
        if subfield:
            if subfield.isdigit() and 1 < len(subfield) < 5:
                is_numeric = True
            suffixes = ['-luku', '-talet', '-tal', 'ekr.', 'jkr.', 'fkr.', 'eaa.', 'jaa.']
            dashes = {"\u002D": "hyphen-minus",
                "\u007E": "tilde",
                "\u00AD": "soft hyphen",
                "\u058A": "armenian hyphen",
                "\u05BE": "hebrew punctuation maqaf",
                "\u1400": "canadian syllabics hyphen",
                "\u1806": "mongolian todo soft hyphen",
                "\u2010": "hyphen",
                "\u2011": "non-breaking hyphen",
                "\u2012": "figure dash",
                "\u2013": "en dash",
                "\u2014": "em dash",
                "\u2015": "horizontal bar",
                "\u2053": "swung dash",
                "\u207B": "superscript minus",
                "\u208B": "subscript minus",
                "\u2212": "minus sign",
                "\u2E17": "double oblique hyphen",
                "\u2E3A": "two-em dash",
                "\u2E3B": "three-em dash",
                "\u301C": "wave dash",
                "\u3030": "wavy dash",
                "\u30A0": "katakana-hiragana double hyphen",
                "\uFE31": "presentation form for vertical em dash",
                "\uFE32": "presentation form for vertical en dash",
                "\uFE58": "small em dash",
                "\uFE63": "small hyphen-minus",
                "\uFF0D": "fullwidth hyphen-minus"}
            for s in suffixes:
                if subfield.endswith(s):
                    is_numeric = True
            if not is_numeric:
                if not any (not char.isdigit() and not char in dashes for char in subfield):
                    is_numeric = True
            
            TAL/TALET?
            Kongressin kirjasto on auktorisoinut aiheina käytettäviä ajanjaksoja LCSH sanastossa.  Esimerkkejä sivun lopun taulukossa.
            Esitettävän vuosiluvun sijainti ennen tai jälkeen vuoden 0 ilmaistaan liitteellä eaa. tai jaa.
            Tällöin konversiossa voidaan [^.*eKr.$|^.*e\.Kr.$|^.*jKr.$|^.*j\.Kr.$]  muuttaa muotoon  [^.*eaa.$|^.*jaa.$]
            


            ???
            if is_numeric:
                return Field(
                    tag = '648',
                    indicators = [' ','4'],
                    subfields = [
                        'a', subfield,
                ])
            
            ???
            
        return is_numeric
    """