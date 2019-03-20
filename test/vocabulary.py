import unittest
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from vocabulary import Vocabulary

class VocabularyTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls):
        {
        'sarjat (sävellykset)': {'http://www.yso.fi/onto/yso/p1513'},
        'ragat': {'http://www.yso.fi/onto/yso/p30038'},
        'rāgat': {'http://www.yso.fi/onto/yso/p30038'}, 
        'harlem-jazz': {'http://www.yso.fi/onto/yso/p29987'}
        }
              
        print("parsitaan YSOa")
        yso_graph = Graph()
        yso_graph.parse('test/yso-skos-test.rdf')

        print("parsitaan YSO-paikkoja")
        yso_paikat_graph = Graph()
        yso_paikat_graph.parse('test/yso-paikat-skos-test.rdf')

        print("parsitaan YSaa")
        ysa_graph = Graph()
        ysa_graph.parse('test/ysa-skos-test.rdf')

        print("parsitaan Allärsia")
        allars_graph = Graph()
        allars_graph.parse('test/allars-skos-test.rdf')

        print("parsitaan SLM_ää")
        slm_graph = Graph()
        slm_graph.parse('test/slm-skos-test.rdf')
       
        print("parsitaan Musaa")
        musa_graph = Graph()
        musa_graph.parse('test/musa-skos-test.rdf')
        """
        cls.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        cls.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        cls.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        cls.vocabularies.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        cls.vocabularies.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        cls.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)
        """
        
        cls.yso = Vocabulary(['fi', 'sv'])
        cls.yso.parse_yso_vocabulary(yso_graph)
        cls.yso_paikat = Vocabulary(['fi', 'sv'])
        cls.yso_paikat.parse_yso_vocabulary(yso_paikat_graph)
        cls.ysa = Vocabulary(['fi'])
        cls.ysa.parse_origin_vocabulary(ysa_graph)
        cls.allars = Vocabulary(['fi'])
        cls.allars.parse_origin_vocabulary(allars_graph)
        cls.slm_fi = Vocabulary(['fi', 'sv'])
        cls.slm_fi.parse_slm_vocabulary(slm_graph, 'fi')
        cls.slm_sv = Vocabulary(['fi', 'sv'])
        cls.slm_sv.parse_slm_vocabulary(slm_graph, 'sv')
        cls.musa = Vocabulary(['fi'])
        cls.musa.parse_musa_vocabulary(musa_graph, ysa_graph)
        
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

    def test_get_concept_with_concept_with_multiple_replacedby(self):    
        result = self.yso.get_concept_with_uri('http://www.yso.fi/onto/yso/p113','fi')
        self.assertTrue(len(result['uris']) > 1)    
        
    def test_get_concept_with_label(self):
        result = self.slm_fi.get_concept_with_label('ragat', 'fi')
        self.assertEqual(result['label'], 'rāgat')
        self.assertEqual(result['code'], 'slm/fin')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result = self.slm_sv.get_concept_with_label('ragor', 'fi')
        self.assertEqual(result['label'], 'ragor')
        self.assertEqual(result['code'], 'slm/fin')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result = self.slm_fi.get_concept_with_label('ragat', 'sv')
        self.assertEqual(result['label'], 'ragor')
        self.assertEqual(result['code'], 'slm/swe')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])
        result = self.slm_sv.get_concept_with_label('ragor', 'sv')
        self.assertEqual(result['label'], 'ragor')
        self.assertEqual(result['code'], 'slm/swe')
        self.assertTrue('http://urn.fi/URN:NBN:fi:au:slm:s786' in result['uris'])

    def test_get_concept_with_wrong_label(self):    
        result = self.slm_fi.get_concept_with_label('ragor', 'fi')
        self.assertEqual(result, None)

    def test_get_uris_with_concept(self):
        result = self.ysa.get_uris_with_concept('tsekkoslovakia')
        self.assertTrue('http://www.yso.fi/onto/yso/p105847' in result['uris'])
    
    def test_get_uris_with_concept_without_replacedby(self):
        #with self.assertRaises(ValueError) as e:
        result = self.ysa.get_uris_with_concept('roudarit')
        self.assertEqual(result, None)    
        #self.assertTrue("asiasanalla ei ole voimassaolevia YSO-vastineita" in str(e.exception))    

    def test_get_uris_with_wrong_concept(self):    
        result = self.slm_fi.get_concept_with_label('olematon käsite', 'fi')
        self.assertEqual(result, None)

    

if __name__ == "__main__":
    unittest.main()