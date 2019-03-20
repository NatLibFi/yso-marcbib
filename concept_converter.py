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
        self.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        self.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        self.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        self.parse_vocabulary(allars_graph, 'allars', ['sv'])
        self.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        self.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        cls.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)

    def subfields_to_tuples(self, subfields):
        """
        muuntaa helpommin käsiteltäväksi pymarcin "osakenttälistan" eli listan, 
        jossa joka toinen alkio on osakenttäkoodi ja joka toinen osakenttä,
        listaksi, jossa on avainarvotupleja (osakenttäkoodi, osakenttä) 
        """
        tuple_subfields = []
        #Testattava, jos subfields-listassa pariton määrä alkioita! 
        for idx in range(0, len(subfields), 2):
            if idx + 1 < len(subfields):
                tuple_subfields.append((subfields[idx], subfields[idx+1]))
        return tuple_subfields         
    
    def process_record(self, record):
        if record['001']:
            tags_of_fields_to_convert = ['385', '567', '648', '650', '651', '655']
            tags_of_fields_to_process = ['370', '385', '388', '567', '648', '650', '651', '653', '655']
            original_fields = {}
            new_fields = {}
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
            if leader_type in ['a', 't']:
                record_type == "text"
                if record.leader[7] not in ['b', 'i', 's']:
                    if record['006']:
                        if record['006'].data[16] not in ['0', 'u', '|']:
                            fiction = True
                    elif record['008']:
                        if record['008'].data[33] not in ['0', 'u', '|']:
                            fiction = True
            elif leader_type in ['c', 'd', 'i', 'j']: 
                record_type == "music"
                if leader_type == "i":
                    if any (lf in record['008'].data[30:31] for lf in ['d', 'f', 'p']):
                        fiction = True
            elif leader_type == "g":
                record_type == "image"            
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

            if convertible_record:   
                subfields = []
                #TODO: vaihtoehto: säilytetään alkup. YSA-rivi, jos valittu optio
                for tag in tags_of_fields_to_process:
                    original_fields.update({tag: []})
                    if tag in tags_of_fields_to_convert:
                        vocabulary_code = None
                        for sf in field.get_subfields('2'):
                            if not vocabulary_code:
                                if sf == "ysa" or sf == "allars" or sf == "musa" or cf == "cilla":
                                    vocabulary_code = sf    
                        if vocabulary_code:
                            converted_fields = self.process_field(record_id, field, vocabulary_code, fiction)
                            if converted_fields:
                                for cf in converted_fields:
                                    if cf.tag in new_fields:
                                        new_fields[cf.tag] += converted_fields
                                    else:
                                        new_fields.update({cf.tag: converted_fields})
                            else:
                                original_fields.update({tag: [field]})              
                        else:
                            original_fields.update({tag: [field]})              
                    else:
                        original_fields.update({tag: [field]})        
                    #järjestetään rivit:
                    if tag in new_fields:
                        record.remove_fields(tag)
                        sorted_fields = self.sort_fields(tag, original_fields, new_fields)
                        for field in sorted_fields:
                            record.add(field)
                    #TODO:poista samanlaiset kentät!
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

            #record = next(reader, None)
            record = Record()
            while record:                
                try:
                    #TODO: kirjoittaminen MARCXML-formaattiin, jos valittu
                    #xml_writer.write(record)
                    record = next(reader, None)
                    new_record = self.process_record(record)
                    if new_record:
                        writer.write(new_record)
                    else:
                        writer.write(record)
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
        #tallennetaan $9-osakentät, jotka liitetään jokaiseen uuteen kenttään:
        #TODO: poista $2ysa-osakentät kaikista (paitsi 648?)
        control_subfield_codes = ['5', '9']
        control_subfields = {}
        for csc in control_subfield_codes:
            """
            HUOM! sanastokoodeja voi olla useampia, jos yksikin niistä ysa/allars,
            tulee valituksi niistä ensimmäiseksi kentässä esiintyvä sanastokoodi
            """
            if field[csc]:
                for sf in field.get_subfields(csc):
                    control_subfields.update({csc: sf})
     
        
        subfields = self.subfields_to_tuples(field.subfields)
        #etsitään paikkaketjut ja muodostetaan niistä yksiosainen käsite:
        if tag == "650" or tag == "651":
            combined_subfields = []
            while len(subfields) > 0:
                if len(subfields) > 1:
                    if subfields[0][0] == "a" or subfields[0][0] == "z":
                        first = subfields[0][1]
                        if subfields[1][0] == "z":
                            second = subfields[1][1]
                            combined_concept = first + " -- " + second
                            if combined_concept in \
                                self.vocabularies.vocabularies['ysa'].geographical_chained_labels | \
                                self.vocabularies.vocabularies['allars'].geographical_chained_labels:
                                combined_subfields.append((subfields[0][0], combined_concept))
                                del subfields[0]
                                del subfields[0]
                                continue
                combined_subfields.append((subfields[0][0], subfields[0][1]))
                del subfields[0]
            subfields = combined_subfields
        for subfield in subfields:
            new_field = None
            #new_field = self.process_numeric_subfield(subfield)    
            if new_field:
                if new_field.tag in new_fields:
                    new_fields[new_field.tag].append(new_field)
                else:
                    new_fields.update({new_field.tag: [new_field]})
            else:
                #TODO: vain kirjaimella alkavat käsitellään, entä jos pelkkiä numerollisia osakenttiä? 
                """
                if tag == "385":
                    if subfield[0] != "a":
                        continue
                    else:
                        new_field = self.process_subfield(record_id, field, subfield, vocabulary_code, fiction)
                elif tag == "567":
                    if subfield[0] != "b":
                        continue
                    else:
                        new_field = self.process_subfield(record_id, field, subfield, vocabulary_code, fiction)
                """
                if not subfield[0].isdigit() or tag == "385" or tag == "567":
                    if tag == "385":
                        if subfield[0] != "a":
                            continue
                    if tag == "567":
                        if subfield[0] != "b":
                            continue         
                    #358- ja 567-kentistä käsitellään vain a- ja b-osakentät:
                    new_field = self.process_subfield(record_id, field, subfield, vocabulary_code, fiction)
                    if tag not in ['385', '567']:
                        for csc in control_subfield_codes:
                            if csc in control_subfields:
                                for value in control_subfields[csc]:
                                    new_field.add_subfield(csc, value)
                    if new_field:
                        new_fields.append(new_field)
                        """
                        if new_field.tag in new_fields:
                            new_fields[new_field.tag].append(new_field)
                        else:
                            new_fields.update({new_field.tag: [new_field]})
                        """       
        return new_fields
        
    def process_subfield(self, record_id, original_field, subfield, vocabulary_code, fiction=False):
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
            '648': ['a', 'v', 'x', 'y', 'z'],
            '650': ['a', 'b', 'c', 'd', 'v', 'x', 'y', 'z'],
            '651': ['a', 'd', 'v', 'x', 'y', 'z'],
            '655': ['a', 'b', 'v', 'x', 'z']
        }

        #käsitellään ensin poikkeustapaukset ja/tai annetaan sanastohaulle erityisjärjestys:
        if tag == "385" or tag == "567":
            search_geographical_concepts = False
            """
            385- ja 567-kenttien erikoiskäsittely:  
            tulostetaan käsiteltävät osakentät jokainen omalle riville ja kaikkiin kenttiin muut osakentät sellaisenaan
            """
            subfield_code = None
            new_subfields = []
            if tag == "385" :
                subfield_code = "a"
                valid_subfield_codes = ['a', 'b', 'm', 'n', '0', '1', '2', '3', '5', '6', '8', '9']
            if tag == "567":
                subfield_code = "b"
                valid_subfield_codes = ['a', 'b', '0', '1', '2', '5', '6', '8', '9']
            try:
                response = self.vocabularies.search(subfield[1], vocabulary_order, search_geographical_concepts)
                original_subfields = self.subfields_to_tuples(original_field.subfields) 
                for subfield in original_subfields:
                    if subfield[0] not in valid_subfield_codes:        
                        #TODO: log error
                        continue
                    if subfield[0] == "0" or subfield[0] == "2" or subfield[0] == subfield_code:
                        continue
                    new_subfields.append((subfield[0], subfield[1]))
                new_subfields.append((subfield_code, response['label'])) 
                new_subfields.append(("0", response['uris'][0]))
                new_subfields.append(("2", response['code']))
                               
            except ValueError as e:
                if str(e) == "MULTIPLE_CONCEPTS":
                    field = self.field_without_voc_code("653", [' ', '4'], subfield)
                    #TODO: puuttuu konversiosäännöistä
                    return field
                elif str(e) == "NOT_FOUND":
                    original_subfields = self.subfields_to_tuples(original_field.subfields)
                    
                    for sf in original_subfields:
                        if sf[0] == "0" or sf[0] == "2" or sf[0] == subfield_code:
                            continue
                        else:
                            new_subfields.append(sf)
                    new_subfields.append((subfield_code, subfield[1]))
                    #TODO: log error
            #aakkkostetaan uudet ja vanhat osakenttäkoodit numerot viimeiseksi:
            new_subfields = new_subfields = sorted(new_subfields, key=lambda subfield: (  
                subfield[0] == "9", 
                subfield[0] == "0", 
                subfield[0] == "2", 
                subfield[0] != "6",
                subfield[0] != "8",
                subfield[0].isdigit(),
                subfield[0],
                subfield[0] == "6",
                subfield[0] == "8",))
            field = Field(
                tag = tag,
                indicators = [' ',' '],
            )
            for ns in new_subfields:
                field.add_subfield(ns[0], ns[1])            
            return field        
        if tag == "655":
            if subfield[0] in ['a', 'v', 'x']:
                search_geographical_concepts = False
                if language == "fi":
                    vocabulary_order = ['slm_fi', 'slm_sv']
                if language == "sv":
                    vocabulary_order = ['slm_sv', 'slm_fi']    
            if subfield[0] == "y":                            
                field = self.field_without_voc_code("388", [' ', ' '], subfield)
        if tag in ['648', '650', '651']:
            if subfield[0] == "v":
                vocabulary_order = slm_vocabulary_order[language]
                if tag == '650' or tag == '651':
                    if subfield[1].lower() == "fiktio":
                        return #TODO: log error REMOVED
            if tag == "650" and subfield[0] == "a" and fiction:
                vocabulary_order = slm_vocabulary_order[language]
        if tag == "650" or tag == "651": 
            if subfield[0] == "e":
                return #TODO: log error REMOVED
            elif subfield[0] == "g":
                field = self.field_without_voc_code("653", [' ', ' '], subfield)   
                return field

        #käsitellään perustapaukset
        if subfield[0] in valid_subfield_codes[tag]:
            if subfield[0] in valid_subfield_codes[tag]:
            #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja 
                try:
                    response = self.vocabularies.search(subfield[1], vocabulary_order, search_geographical_concepts)
                    if tag == "650" and fiction and subfield[0] == "a":
                        tag == "655"
                    field = self.field_with_voc_code(tag, response)
                except ValueError as e:
                    #TODO: määriteltävä tähän kentät ja osakentät, joista haetaan numeerisia arvoja
                    if str(e) == "MULTIPLE_CONCEPTS":
                        field = self.field_without_voc_code("653", [' ', '4'], subfield)
                    elif str(e) == "NOT_FOUND":
                        if tag == "385" or tag == "567":
                            field = self.field_without_voc_code(tag, [' ', ' '], subfield)      
                        if tag in ['648', '650', '651']:
                            if subfield[0] in ['a', 'b', 'd', 'x', 'y']:
                                field = self.field_without_voc_code("653", [' ', '0'], subfield)
                            if subfield[0] in ['d', 'y']:
                                field = self.field_without_voc_code("653", [' ', '4'], subfield)
                            if subfield[0] in ['c', 'z']:
                                field = self.field_without_voc_code("653", [' ', '5'], subfield)    
                            if subfield[0] in ['v']:
                                field = self.field_without_voc_code("653", [' ', '6'], subfield)
                        if tag == '655':
                            if subfield[0] in ['a', 'v', 'x']:
                                field = self.field_without_voc_code("653", [' ', '6'], subfield)
                            if subfield[0] in ['b']:
                                field = self.field_without_voc_code("653", [' ', '0'], subfield)   
                            if subfield[0] in ['z']:
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
        subfield_code = "a"
        if tag == "358":
            subfield_code = "b"
        if tag in ['648', '650', '651', '655']:
            if response['geographical']:
                tag = "651"
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
        if tag == "358":
            subfield_code = "b"
        if tag == "370":
            subfield_code = "g"    
        field = Field(
            tag = tag,
            indicators = indicators,
            subfields = [subfield_code, subfield[1]]
            )                      
        return field

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
        
        
        for nf in new_fields:
            field = {}
            field.update({"original": False})
            field.update({"index": idx})
            field.update({"indicator": nf.indicators[1]})
            vocabulary_code = ""
            if nf['2']:
                vocabulary_code = nf['2']
            field.update({"code": vocabulary_code})  
            fenni_keep = False
            for sf in field.get_subfields('9'):
                if sf == "<FENNI>KEEP":
                    fenni_keep = True 
            field.update({"fenni_keep": fenni_keep}) 
            idx += 1
            fields.append(field)
        fields = sorted(fields, key=lambda field:( 
            field['fenni_keep'] == False))


        for of in original_fields:
            field = {}
            field.update({"original": True})
            field.update({"index": idx})
            field.update({"indicator": of.indicators[1]})
            vocabulary_code = ""
            if of['2']:
                vocabulary_code = of['2']
            field.update({"code": vocabulary_code})  
            idx += 1
            fields.append(field)

        fields_with_indicator_7 = []
        fields_without_indicator_7 = []
        if tag == "650" or tag == "651":
            for field in fields:
                if field['indicator'] == "7":
                    fields_with_indicator_7.append(field)
                else:
                    fields_without_indicator_7.append(field)

            fields_with_indicator_7 = sorted(fields_with_indicator_7, key=lambda subfield: (  
                subfield['code'] != "yso/fin",
                subfield['code'] != "yso/swe",
                subfield['code'],
                subfield['code'] == "yso/swe",
                subfield['code'] == "yso/fin"
            ))
            fields_without_indicator_7 = sorted(fields_without_indicator_7, key=lambda subfield: (  
                subfield['code']
            ))

        if tag == "655":
            for field in fields:
                if field['indicator'] == "7":
                    fields_with_indicator_7.append(field)
                else:
                    fields_without_indicator_7.append(field)

            fields_with_indicator_7 = sorted(fields_with_indicator_7, key=lambda subfield: (  
                subfield['code'] != "slm/fin",
                subfield['code'] != "slm/swe",
                subfield['code'],
                subfield['code'] == "slm/swe",
                subfield['code'] == "slm/fin"
            ))
            fields_without_indicator_7 = sorted(fields_without_indicator_7, key=lambda subfield: (  
                subfield['code']
            ))

        fields = fields_with_indicator_7 + fields_without_indicator_7
        fields = sorted(listb, key=lambda subfield: (  
                subfield['indicator']
            ))
    return fields
        
    def process_numeric_subfield(self, subfield):
        is_numeric = False
        if subfield.isdigit() and 1 < len(subfield) < 5:
            is_numeric = True
        if subfield.endswith('-luku') or subfield.endswith('-talet'):
            if len(subfield) > 0:
                if subfield[0].isdigit():
                    is_numeric = True
        """
        TAL/TALET?
        Kongressin kirjasto on auktorisoinut aiheina käytettäviä ajanjaksoja LCSH sanastossa.  Esimerkkejä sivun lopun taulukossa.
        Esitettävän vuosiluvun sijainti ennen tai jälkeen vuoden 0 ilmaistaan liitteellä eaa. tai jaa.
        Tällöin konversiossa voidaan [^.*eKr.$|^.*e\.Kr.$|^.*jKr.$|^.*j\.Kr.$]  muuttaa muotoon  [^.*eaa.$|^.*jaa.$]
        """
        if is_numeric:
            return Field(
                tag = '648',
                indicators = [' ','4'],
                subfields = [
                    'a', subfield,
            ])