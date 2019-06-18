from vocabulary import Vocabulary
from rdflib import Graph, URIRef, Namespace, RDF
import unicodedata
import unicodedata

class Vocabularies:

    def __init__(self):
        
        self.vocabularies = {}
        """
        yso_graph = Graph()
        yso_graph.parse('yso-skos.rdf')

        logging.info("parsitaan YSO-paikkoja")
        yso_paikat_graph = Graph()
        yso_paikat_graph.parse('yso-paikat-skos.rdf')

        logging.info("parsitaan YSaa")
        ysa_graph = Graph()
        ysa_graph.parse('ysa-skos.rdf')

        logging.info("parsitaan Allärsia")
        allars_graph = Graph()
        allars_graph.parse('allars-skos.rdf')

        logging.info("parsitaan SLM_ää")
        slm_graph = Graph()
        slm_graph.parse('slm-skos.rdf')

        logging.info("parsitaan Musaa")
        musa_graph = Graph()
        musa_graph.parse('musa-skos.rdf')

        logging.info("sanastot parsittu")
        self.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        self.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        self.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        self.parse_vocabulary(allars_graph, 'allars', ['sv'])
        self.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        self.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        self.parse_vocabulary(musa_graph, 'musa', ['fi'], ysa_graph)
        self.parse_vocabulary(musa_graph, 'cilla', ['sv'], ysa_graph)
        """

    def parse_vocabulary(self, graph, vocabulary_code, language_codes, language_code = None, secondary_graph = None):
        #secondary_vocabulary: tarvitaan luomaan musa -> ysa ja cilla -> ysa -vastaavuudet
        vocabulary = Vocabulary(vocabulary_code, language_codes)
        if vocabulary_code.startswith("yso"):
            vocabulary.parse_yso_vocabulary(graph)
        elif vocabulary_code == "ysa" or vocabulary_code == "allars":
            vocabulary.parse_origin_vocabulary(graph)
        elif vocabulary_code == "musa" or vocabulary_code == "cilla":
            vocabulary.parse_musa_vocabulary(graph, secondary_graph)    
        elif vocabulary_code == "slm":
            vocabulary.parse_label_vocabulary(graph)
        elif vocabulary_code.startswith("seko"):
            vocabulary.parse_label_vocabulary(graph)
        self.vocabularies.update({vocabulary_code: vocabulary})

    def search(self, keyword, vocabulary_codes, search_geographical_concepts=False, all_languages=False):
        """
        kewword: hakusana
        vocabulary_codes: dictionary, joka muodostuu sanastokoodi, kielikoodi avainarvopareista
        search_geographical_concepts: Boolean-arvo sille, haetaanko käsitettä YSO-paikoista

        Virhekoodit:
        1: termille ei löytynyt vastinetta sanastoista
        2: termille useampi mahdollinen vastine (termille on useampi samanlainen normalisoitu käytettävä termi tai ohjaustermi) 
        3: termillä ei vastinetta, mutta termillä on täsmälleen yksi sulkutarkenteellinen muoto
        4: termillä ei vastinetta, mutta termillä on sulkutarkenteellinen muoto kahdessa tai useammassa käsitteessä
        5: termille löytyy vastine, mutta sille on olemassa myös sulkutarkenteellinen muoto eri käsitteessä
        6: ketjun osakentän termi poistettu tarpeettomana (fiktio, aiheet, musiikki ja ketjun $e-osakenttä)
        7: kentän 650/651 osakentän $g "muut tiedot" on viety kenttään 653
        8: Kenttä sisältää MARC-formaattiin kuulumattomia osakenttäkoodeja tai ei sisällä asiasanaosakenttiä
        9: tyhjä osakenttä
        """
        keyword = unicodedata.normalize('NFKC', keyword)
        keyword = keyword.strip()
        geographical_concept = False
        for vc in vocabulary_codes:
            response = {}
            if vc[0] == "numeric":
                if self.is_numeric(keyword):
                    response.update({'numeric': True})
                    response.update({'label': keyword})
                    if vc[1] == "fi":
                        response.update({'code': 'yso/fin'})
                    if vc[1] == "sv":
                        response.update({'code': 'yso/swe'})
            if vc[0] in ['ysa', 'allars', 'musa', 'cilla']:
                response = self.vocabularies[vc[0]].get_uris_with_concept(keyword)
                if response:
                    if "uris" in response:
                        if len(response['uris']) > 1:
                            raise ValueError("2")
                        if response["uris"][0] in self.vocabularies[vc[0]].geographical_concepts:
                            if search_geographical_concepts:
                                response = self.vocabularies['yso_paikat'].get_concept_with_uri(response["uris"][0], vc[1]) 
                                geographical_concept = True
                            else:
                                response = None
                        else:
                            response = self.vocabularies['yso'].get_concept_with_uri(response["uris"][0], vc[1])    
                #except ValueError as e:
                    #logging.warning
                    #logging.info(e)
                    #return response          
            elif vc[0] == "slm" or vc[0] == "seko":
                response = self.vocabularies[vc[0]].get_concept_with_label(keyword, vc[1])    
            if response:
                if "uris" in response:
                    responses = []
                    responses.append(response)
                    if all_languages:
                        vocabulary_code = None
                        if response['code'].startswith("slm"):
                            vocabulary_code = "slm"
                        if response['code'].startswith("yso"):
                            vocabulary_code = "yso"
                            if geographical_concept:
                                vocabulary_code = "yso_paikat"
                        translated_response = self.vocabularies[vocabulary_code].translate_label(response['uris'][0], vc[1])
                        if translated_response:
                            responses.append(self.vocabularies[vocabulary_code].translate_label(response['uris'][0], vc[1]))
                    for r in responses:
                        r.update({'geographical': geographical_concept})
                        r['label'] = self.normalize_characters(r['label'])
                    #HUOM! Vocabularyn on palautettava vastauksessa sanastokoodi, esim. YSO-paikat
                    if len(response['uris']) > 1:
                        raise ValueError("2")
                    if len(response['uris']) == 1:
                        return responses
                if "numeric" in response:
                    response.update({'geographical': geographical_concept})
                    return [response]
        raise ValueError("1")

    def is_numeric(self, keyword):
        numeric = False
        if keyword:
            if keyword.isdigit() and 1 < len(keyword) < 5:
                numeric = True
            suffixes = ['-luku', '-luvut', '-talet', '-tal', 'ekr.', 'jkr.', 'fkr.', 'eaa.', 'jaa.', 'ekr', 'jkr', 'fkr', 'eaa', 'jaa']
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
                      "\uFF0D": "fullwidth hyphen-minus",
                      "\u002E": "full stop"}
            for s in suffixes:
                if keyword.lower().endswith(s):
                    numeric = True
            if not numeric:
                if not any (not char.isdigit() and not char in dashes for char in keyword):
                    numeric = True
            """
            TAL/TALET?
            Kongressin kirjasto on auktorisoinut aiheina käytettäviä ajanjaksoja LCSH sanastossa.  Esimerkkejä sivun lopun taulukossa.
            Esitettävän vuosiluvun sijainti ennen tai jälkeen vuoden 0 ilmaistaan liitteellä eaa. tai jaa.
            Tällöin konversiossa voidaan [^.*eKr.$|^.*e\.Kr.$|^.*jKr.$|^.*j\.Kr.$]  muuttaa muotoon  [^.*eaa.$|^.*jaa.$]
            """
        return numeric

    def normalize_characters(self, string):
        #koodaa skandinaaviset merkit yksiosaisiksi ja muut kaksiosaisiksi: 
        string = unicodedata.normalize('NFD', string)
        return (string.replace("A\u030a", "Å").replace("a\u030a", "å").
            replace("A\u0308", "Ä").replace("a\u0308", "ä").
            replace("O\u0308", "Ö").replace("o\u0308", "ö"))