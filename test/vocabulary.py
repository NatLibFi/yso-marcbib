import unittest
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from vocabulary import Vocabulary

class VocabularyTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls):
       
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
        cls.yso = Vocabulary("yso", ['fi', 'sv'])
        cls.yso.parse_yso_vocabulary(yso_graph)
        cls.yso_paikat = Vocabulary("yso", ['fi', 'sv'])
        cls.yso_paikat.parse_yso_vocabulary(yso_paikat_graph)
        cls.ysa = Vocabulary("ysa", ['fi'])
        cls.ysa.parse_origin_vocabulary(ysa_graph)
        cls.allars = Vocabulary("allars", ['fi'])
        cls.allars.parse_origin_vocabulary(allars_graph)
        cls.slm = Vocabulary("slm", ['fi', 'sv'])
        cls.slm.parse_label_vocabulary(slm_graph)
        cls.musa = Vocabulary("musa", ['fi'])
        cls.musa.parse_musa_vocabulary(musa_graph, ysa_graph)
        cls.seko = Vocabulary("seko", ['fi'])
        cls.seko.parse_label_vocabulary(seko_graph)
        return super(VocabularyTest, cls).setUpClass()

    def test_get_concept_with_uri(self):
        result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p10007', 'fi')
        self.assertEqual(result['label'], 'koristemaalaus')
        self.assertEqual(result['code'], 'yso/fin')
        result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p10007', 'sv')
        self.assertEqual(result['label'], 'dekorationsmålning')
        self.assertEqual(result['code'], 'yso/swe')
        
    def test_get_concept_with_wrong_uri(self):    
        result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p13y5y3007', 'sv')
        self.assertEqual(result, None)

    def test_get_concept_with_label(self):
        result = self.slm.get_concept_with_label('ragat', 'fi')
        self.assertEqual(result['label'], 'rāgat')
        self.assertEqual(result['code'], 'slm/fin')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result = self.slm.get_concept_with_label('ragor', 'fi')
        self.assertEqual(result, None)
        result = self.slm.get_concept_with_label('ragat', 'sv')
        self.assertEqual(result, None)
        result = self.slm.get_concept_with_label('ragor', 'sv')
        self.assertEqual(result['label'], 'ragor')
        self.assertEqual(result['code'], 'slm/swe')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result = self.seko.get_concept_with_label('kurttu', 'fi')  
        self.assertEqual(result['label'], '1-rivinen harmonikka')
        self.assertEqual(result['code'], 'seko/fin')
        self.assertTrue('http://urn.fi/urn:nbn:fi:au:seko:00001' in result['uris'])
        
    def test_get_concept_with_wrong_label(self):    
        result = self.slm.get_concept_with_label('ragor', 'fi')
        self.assertEqual(result, None)

    def test_get_uris_with_concept(self):
        result = self.musa.get_uris_with_concept('steel pan')
        self.assertTrue('http://www.yso.fi/onto/yso/p29959' in result['uris'])
        result = self.ysa.get_uris_with_concept('tsekkoslovakia')
        self.assertTrue('http://www.yso.fi/onto/yso/p105847' in result['uris'])

    def test_search_label_with_multiple_replacers(self):
        with self.assertRaises(ValueError) as e:
            result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p113', 'fi')
        self.assertTrue("9" in str(e.exception)) 

    def test_get_uris_with_concept_without_replacedby(self):
        result = self.ysa.get_uris_with_concept('roudarit')
        self.assertEqual(result, None)    

    def test_get_uris_with_wrong_concept(self):    
        result = self.slm.get_concept_with_label('olematon käsite', 'fi')
        self.assertEqual(result, None)
    
    def test_get_concept_with_wrong_uri(self):    
        result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p13y5y3007', 'sv')
        self.assertEqual(result, None) 
    
    def test_translate_label(self):
        result = self.slm.translate_label("http://urn.fi/URN:NBN:fi:au:slm:s786", "fi")
        self.assertEqual(result['label'], 'ragor')
        self.assertEqual(result['code'], 'slm/swe')

if __name__ == "__main__":
    unittest.main()