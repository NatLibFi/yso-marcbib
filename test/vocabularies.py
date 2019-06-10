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
        seko_graph = Graph()
        seko_graph.parse('test/seko-skos-test.rdf')
        cls.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        cls.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        cls.vocabularies.parse_vocabulary(slm_graph, 'slm', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)
        cls.vocabularies.parse_vocabulary(seko_graph, 'seko', ['fi'])
        return super(VocabulariesTest, cls).setUpClass()
    
    def test_search(self):
        result =  self.vocabularies.search('1900-luku', [('numeric', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result['label'], "1900-luku")
        result =  self.vocabularies.search('1900', [('numeric', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result['label'], "1900")
        result =  self.vocabularies.search('400 fKr.', [('numeric', 'sv'), ('allars', 'sv'), ('ysa', 'fi'), ('numeric', 'fi')], True)

        self.assertEqual(result['label'], "400 fKr.")
        self.assertEqual(result['code'], "yso/swe")
        self.assertEqual(result['numeric'], True)
        result =  self.vocabularies.search('ragat', [('ysa', 'fi')], True)
        #Lopputuloksessa koostemerkki pitää olla kaksiosainen:
        self.assertEqual(result['label'], "rāgat")
        result =  self.vocabularies.search('ragat', [('slm', 'fi'), ('ysa', 'fi'), ('allars', 'sv')], True)
        self.assertEqual(result['code'], "slm/fin")
        result =  self.vocabularies.search('ragor', [('slm', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('allars', 'sv')], True)
        self.assertEqual(result['code'], "slm/swe")
        result =  self.vocabularies.search('ragat', [('slm', 'fi'), ('ysa', 'fi'), ('slm', 'sv'), ('allars', 'sv')], True)
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result =  self.vocabularies.search('steel pan', [('musa', 'fi')], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p29959' in result['uris'])
        result =  self.vocabularies.search('Helsinki -- Töölö',  [('musa', 'fi'), ('ysa', 'fi')], True)
        self.assertTrue('http://www.yso.fi/onto/yso/p109631' in result['uris'])
     
    def test_search_label_not_found(self):        
        with self.assertRaises(ValueError) as e:
            #result =  self.vocabularies.search('jotain', ['slm', 'ysa', 'allars'], True)
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
        self.assertTrue('http://www.yso.fi/onto/yso/p2014' in result['uris'])
        with self.assertRaises(ValueError) as e:
            result =  self.vocabularies.search('kuvaus', [('ysa', 'fi')], True)
        self.assertTrue("3" in str(e.exception))
        with self.assertRaises(ValueError) as e:
            result = self.vocabularies.search('tuomarit', [('ysa', 'fi')], True)
        self.assertTrue("4" in str(e.exception)) 

if __name__ == "__main__":
    unittest.main()