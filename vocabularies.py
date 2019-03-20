from vocabulary import Vocabulary
from rdflib import Graph, URIRef, Namespace, RDF
import unicodedata
import unicodedata

class Vocabularies:

    def __init__(self):
        
        self.vocabularies = {}

    def parse_vocabulary(self, graph, vocabulary_code, language_codes, language_code = None, secondary_graph = None):
        #secondary_vocabulary: tarvitaan luomaan musa -> ysa ja cilla -> ysa -vastaavuudet
        vocabulary = Vocabulary(language_codes)
        if vocabulary_code.startswith("yso"):
            vocabulary.parse_yso_vocabulary(graph)
        elif vocabulary_code == "ysa" or vocabulary_code == "allars":
            vocabulary.parse_origin_vocabulary(graph)
        elif vocabulary_code == "musa" or vocabulary_code == "cilla":
            vocabulary.parse_musa_vocabulary(graph, secondary_graph)    
        elif vocabulary_code.startswith("slm"):
            vocabulary.parse_slm_vocabulary(graph, language_code)
        self.vocabularies.update({vocabulary_code: vocabulary})

    def search(self, keyword, vocabulary_codes, search_geographical_concepts=False):
        keyword = unicodedata.normalize('NFKC', keyword)
        keyword = keyword.strip()
        response = {}
        geographical_concept = False
        for vc in vocabulary_codes:
            if vc == "ysa" or vc == "allars":
                if vc == "ysa":
                    language = "fi"
                if vc == "allars":
                    language = "sv"
                response = self.vocabularies[vc].get_uris_with_concept(keyword)
                if response:
                    
                    if "uris" in response:
                        if len(response['uris']) > 1:
                            raise ValueError("MULTIPLE_CONCEPTS")
                        if response["uris"][0] in self.vocabularies[vc].geographical_concepts:
                            if search_geographical_concepts:
                                response = self.vocabularies['yso_paikat'].get_concept_with_uri(response["uris"][0], language) 
                                geographical_concept = True
                            else:
                                response = None
                        else:
                            response = self.vocabularies['yso'].get_concept_with_uri(response["uris"][0], language)    
                #except ValueError as e:
                    #logging.warning
                    #print(e)
                    #return response          
            elif vc == "slm_fi" or vc == "slm_sv":
                if vc == "slm_fi":
                    language = "fi"
                if vc == "slm_sv":
                    language = "sv"
                response = self.vocabularies[vc].get_concept_with_label(keyword, language)               
            if response:
                if "uris" in response:
                    response.update({'geographical': geographical_concept})
                    #HUOM! Vocabularyn on palautettava vastauksessa sanastokoodi, esim. YSO-paikat
                    if len(response['uris']) > 1:
                        raise ValueError("MULTIPLE_CONCEPTS")
                    if len(response['uris']) == 1:
                        return response
        raise ValueError("NOT_FOUND")

        
    def decomposedÅÄÖtoUnicodeCharacters(self, string):
        return (string.replace("A\u030a", "Å").replace("a\u030a", "å").
            replace("A\u0308", "Ä").replace("a\u0308", "ä").
            replace("O\u0308", "Ö").replace("o\u0308", "ö"))