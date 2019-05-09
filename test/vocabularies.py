import unittest
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from vocabulary import Vocabulary
from vocabularies import Vocabularies


class VocabulariesTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls): 
        cls.vocabularies = Vocabularies()
        yso_graph = Graph()
        yso_graph.parse('test/yso-skos-test.rdf')
        yso_paikat_graph = Graph()
        yso_paikat_graph.parse('test/yso-paikat-skos-test.rdf')
        ysa_graph = Graph()
        ysa_graph.parse('test/ysa-skos-test.rdf')
        allars_graph = Graph()
        allars_graph.parse('test/allars-skos-test.rdf')
        slm_graph = Graph()
        slm_graph.parse('test/slm-skos-test.rdf')
        musa_graph = Graph()
        musa_graph.parse('test/musa-skos-test.rdf')
        cls.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        cls.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        cls.vocabularies.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        cls.vocabularies.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        cls.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)
        return super(VocabulariesTest, cls).setUpClass()

    def test_search(self):
        result =  self.vocabularies.search('1900-luku', ['numeric', 'ysa', 'allars'], True)
        self.assertEqual(result['label'], "1900-luku")
        result =  self.vocabularies.search('1900', ['numeric', 'ysa', 'allars'], True)
        self.assertEqual(result['label'], "1900")
        result =  self.vocabularies.search('400 fKr.', ['numeric', 'allars', 'ysa', 'numeric'], True)
        self.assertEqual(result['label'], "400 fKr.")
        result =  self.vocabularies.search('ragat', ['ysa'], True)
        #Lopputuloksessa koostemerkki pitää olla kaksiosainen:
        self.assertEqual(result['label'], "rāgat")
        result =  self.vocabularies.search('ragat', ['slm_fi', 'ysa', 'allars'], True)
        self.assertEqual(result['code'], "slm/fin")
        result =  self.vocabularies.search('ragor', ['slm_fi', 'ysa', 'slm_sv', 'allars'], True)
        self.assertEqual(result['code'], "slm/swe")
        result =  self.vocabularies.search('ragat', ['slm_fi', 'ysa', 'slm_sv', 'allars'], True)
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result =  self.vocabularies.search('steel pan', ['musa'], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p29959' in result['uris'])
        result =  self.vocabularies.search('Helsinki -- Töölö', ['musa', 'ysa'], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p109631' in result['uris'])
    
    def test_search_label_not_found(self):        
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('jotain', ['slm', 'ysa', 'allars'], True)
        self.assertTrue("1" in str(e.exception))

    def test_search_label_with_multiple_matches(self):    
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('membraanit', ['ysa'], True)
        self.assertTrue("2" in str(e.exception)) 

    def test_search_label_not_in_yso(self):    
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('roudarit', ['ysa'], True)
        self.assertTrue("1" in str(e.exception))

    def test_search_label_without_specifier(self):   
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('tunnusmerkit', ['ysa'], True)
        self.assertTrue("5" in str(e.exception))
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('kuvaus', ['ysa'], True)
        self.assertTrue("3" in str(e.exception))
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('tuomarit', ['ysa'], True)
        self.assertTrue("4" in str(e.exception)) 

if __name__ == "__main__":
    unittest.main()