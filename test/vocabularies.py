import unittest
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from vocabulary import Vocabulary
from vocabularies import Vocabularies


class VocabulariesTest(unittest.TestCase):
        
    @classmethod
    def setUpClass(cls): 
        cls.vocabularies = Vocabularies()
        vocabulary_files = {
            'allars': 'test/allars-skos-test.rdf',
            'musa': 'test/musa-skos-test.rdf',
            'seko': 'test/seko-skos-test.rdf',
            'slm': 'test/slm-skos-test.rdf',
            'ysa': 'test/ysa-skos-test.rdf',
            'yso-paikat': 'test/yso-paikat-skos-test.rdf',
            'yso': 'test/yso-skos-test.rdf'
        }
        graphs = {}      
        vocabulary_names = ['ysa', 'yso', 'yso-paikat', 'allars', 'slm', 'musa', 'cilla', 'seko']
        
        for vf in vocabulary_files:
            g = Graph()
            graphs.update({vf: g})
            g.parse(vocabulary_files[vf])
    
        for vocabulary_name in vocabulary_names:
            cls.vocabularies.parse_vocabulary(vocabulary_name, graphs)
        return super(VocabulariesTest, cls).setUpClass()

    def test_search(self):
        result =  self.vocabularies.search('1900-luku', [('numeric', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result[0]['label'], "1900-luku")
        result =  self.vocabularies.search('1900', [('numeric', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result[0]['label'], "1900")
        result =  self.vocabularies.search('400 fKr.', [('numeric', 'sv'), ('allars', 'sv'), ('ysa', 'fi'), ('numeric', 'fi')], True)

        self.assertEqual(result[0]['label'], "400 fKr.")
        self.assertEqual(result[0]['code'], "yso/swe")
        self.assertEqual(result[0]['numeric'], True)
        result =  self.vocabularies.search('ragat', [('ysa', 'fi')], True)
        #Lopputuloksessa koostemerkki pitää olla kaksiosainen:
        self.assertEqual(result[0]['label'], "rāgat")
        result =  self.vocabularies.search('ragat', [('slm', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result[0]['code'], "slm/fin")
        result =  self.vocabularies.search('ragor', [('slm', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('allars', 'sv')], True)
        self.assertEqual(result[0]['code'], "slm/swe")
        result =  self.vocabularies.search('ragat', [('slm', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('allars', 'sv')], True)
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result[0]['uris'])
        result =  self.vocabularies.search('steel pan', [('musa', 'fi')], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p29959' in result[0]['uris'])
        result =  self.vocabularies.search('Helsinki -- Töölö',  [('musa', 'fi'), ('ysa', 'fi')], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p109631' in result[0]['uris'])
     
    def test_search_label_not_found(self):        
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('jotain', [('slm', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertTrue("1" in str(e.exception))

    def test_search_label_with_multiple_matches(self):    
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('membraanit', [('ysa', 'fi')], True)
        self.assertTrue("2" in str(e.exception)) 

    def test_search_label_not_in_yso(self):    
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('roudarit', [('ysa', 'fi')], True)
        self.assertTrue("1" in str(e.exception))
    
    def test_search_label_without_specifier(self):   
        result =  self.vocabularies.search('tunnusmerkit', [('ysa', 'fi')], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p2014' in result[0]['uris'])
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('kuvaus', [('ysa', 'fi')], True)
        self.assertTrue("3" in str(e.exception))
        with self.assertRaises(ValueError) as e:
            result = self.vocabularies.search('tuomarit', [('ysa', 'fi')], True)
        self.assertTrue("4" in str(e.exception)) 
    """
    def test_get_missing_relations(self):
        #testi-YSAa, jonka kaikille käsitteille on vastine testi-YSOssa:
        
        mini_ysa_graph = Graph()
        mini_ysa_graph.parse('test/mini-ysa-skos-test.rdf')
        mini_yso_graph = Graph()
        mini_yso_graph.parse('test/mini-yso-skos-test.rdf')
        for vf in vocabulary_files:
            g = Graph()
            graphs.update({vf: g})
        missing_relations = self.vocabularies.get_missing_relations(['mini_ysa'], ['mini_yso'])
        self.assertFalse(missing_relations)
        missing_relations = self.vocabularies.get_missing_relations(['ysa', 'allars', 'musa', 'cilla'], ['yso', 'yso_paikat'])
        self.assertTrue(missing_relations)
    """
if __name__ == "__main__":
    unittest.main()