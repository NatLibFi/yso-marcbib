import unittest
from vocabularies import Vocabularies
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from concept_converter import ConceptConverter

class FieldConversionTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls):
        #cls.vocabulary = Vocabularies()
        cls.cc = ConceptConverter()
        """
        cls.cc.vocabularies.parse_vocabulary('yso-skos-test.rdf', 'yso', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary('yso-paikat-skos-test.rdf', 'yso_paikat', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary('ysa-skos-test.rdf', 'ysa', ['fi'])
        cls.cc.vocabularies.parse_vocabulary('allars-skos-test.rdf', 'allars', ['sv'])
        cls.cc.vocabularies.parse_vocabulary('slm-skos-test.rdf', 'slm_fi', ['fi', 'sv'], 'fi')
        cls.cc.vocabularies.parse_vocabulary('slm-skos-test.rdf', 'slm_sv', ['fi', 'sv'], 'sv')
        cls.cc.vocabularies.parse_vocabulary('musa-skos.rdf', 'musa', ['fi'], 'fi', 'ysa-skos.rdf')
        """
        cls.vocabularies = Vocabularies()
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
        cls.cc.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        cls.cc.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        cls.cc.vocabularies.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        cls.cc.vocabularies.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        cls.cc.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.cc.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)

        cls.convertible_fields = [
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'tsekkoslovakia', '2', 'ysa'],
             "results": '=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'membraanit', '2', 'ysa']
             "results": '=653  \\4$amembraanit'},
            {"tag": "655", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'rāgat', '2', 'ysa'],
             "results": '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['g', 'jotain', '2', 'allars'],
             "results": '=653  \\\\$ajotain'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'Tjeckoslovakien', '2', 'ysa'],
             "results": '=651  \\7$aTjeckoslovakien$2yso/swe$0http://www.yso.fi/onto/yso/p105847'},
            {"tag": "385", 
             "indicators": [ ' ', ' ' ], 
             "subfields": ['a', 'RAGAT', '2', 'ysa'],
             "results": '=385  \\\\$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['v', 'rāgat', '2', 'ysa'],
             "results": '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'steel pan', '2', 'musa'],
             "results": '=650  \\7$asteel pan$2yso/fin$0http://www.yso.fi/onto/yso/p29959'},
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'ragat', '2', 'musa'],
             "results": '=650  \\7$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038'},
            {"tag": "655", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'rāgat', '2', 'ysa'],
             "results": '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786'}            
        ]
        cls.inconvertible_fields = [
            {"tag": "655", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['c', 'silleen jättäminen', '2', 'ysa'],
             "results": '=655  \\4$csilleen jättäminen'},
            {"tag": "655", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'membraanit', '2', 'ysa'],
             "results": '=653  \\6$amembraanit'}          
        ]     

        cls.deletable_fields = [
            {"tag": "651", 
            "indicators": [ ' ', '7' ], 
            "subfields": ['e', 'suhdetermi', '2', 'ysa']},
            {"tag": "650", 
            "indicators": [ ' ', '7' ], 
            "subfields": ['f', 'jotain', '2', 'ysa']},
            {"tag": "650", 
            "indicators": [ ' ', '7' ], 
            "subfields": ['v', 'fiktio', '2', 'ysa']}
        ]
        return super(FieldConversionTest, cls).setUpClass()

    def test_subfields_to_tuples(self):
        
        subfields = ['a', 'nimi', 'b', 'alaotsikko']
        expected_result = [('a', 'nimi'), ('b', 'alaotsikko')]
        self.assertEqual(self.cc.subfields_to_tuples(subfields), expected_result)
    
    def test_convert_subfield(self):
        for test_field in self.convertible_fields:
            tag = test_field['tag']
            subfield = (test_field['subfields'][0], test_field['subfields'][1])
            vocabulary_code = test_field['subfields'][3]
            field = self.convert_field(tag, [' ', '7'], subfield)
            result_field = str(self.cc.process_subfield("00000001", field, subfield, vocabulary_code))
            self.assertEqual(result_field,
            test_field['results'])     
    
    def test_convert_fiction(self):
        tag = "650"
        subfield = ('a', 'RAGAT')
        field = self.convert_field(tag, [' ', '7'], [subfield[0], subfield[1]])
        vocabulary_code = 'ysa'
        result_field = str(self.cc.process_subfield("00000001", field, subfield, vocabulary_code, fiction=True))
        self.assertEqual(result_field,
            '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786')
    
    def test_process_geographical_concepts(self):
        field = Field(
            tag = "650",
            indicators = [' ', ' '],
            subfields = [
                'a', 'Helsinki',
                'z', 'Töölö',
                '2', 'ysa'
            ]
        )
        results = [
            "=651  \\7$aTöölö (Helsinki)$2yso/fin$0http://www.yso.fi/onto/yso/p109631"
        ]
        result_fields = self.cc.process_field("00000001", field, "ysa")
        for r in results:
            self.assertTrue(any(r == str(rf) for rf in result_fields))
    
    def test_process_field_567(self):
        field = Field(
            tag = "567",
            indicators = [' ', ' '],
            subfields = [
                'b', 'ragat',
                'b', 'Tšekkoslovakia',
                'a', 'huomautus metodologiasta',
                '1', 'Reaalimaailman kohteen tunniste',
                '6', 'linkitys',
                '2', 'ysa',
                '8', 'järjestysnumero',
                '9', 'FENNI-KEEP'
            ]
        )
        results = [
            ("=567  \\\\$6linkitys$8järjestysnumero$ahuomautus metodologiasta$brāgat"
             "$1Reaalimaailman kohteen tunniste$2yso/fin$0http://www.yso.fi/onto/yso/p30038"
             "$9FENNI-KEEP"),
            ("=567  \\\\$6linkitys$8järjestysnumero$ahuomautus metodologiasta$bTšekkoslovakia"
             "$1Reaalimaailman kohteen tunniste$9FENNI-KEEP")
        ]
        result_fields = self.cc.process_field("00000001", field, "ysa")
        for r in results:
            self.assertTrue(any(r == str(rf) for rf in result_fields))
    
    def test_convert_field(self):
        for test_field in self.convertible_fields:
            tag = test_field['tag']
            field = Field(
                tag = test_field['tag'],
                indicators = test_field['indicators'],
                subfields = test_field['subfields']
            )
            if 'results' in test_field:
                result_tag = test_field['results'][1:4]
                vocabulary_code = test_field['subfields'][3]
                result_fields = self.cc.process_field("00000001", field, vocabulary_code)   
                result_field = str(result_fields[0])
                self.assertEqual(result_field,
                test_field['results'])  
        #testaa rivit, joita ei konvertoida    
        for test_field in self.inconvertible_fields:
            tag = test_field['tag']
            field = Field(
                tag = test_field['tag'],
                indicators = test_field['indicators'],
                subfields = test_field['subfields']
            )
            if 'results' in test_field:
                result_tag = test_field['results'][1:4]
                vocabulary_code = test_field['subfields'][3]
                result_fields = self.cc.process_field("00000001", field, vocabulary_code)
                result_field = str(result_fields[0])
                self.assertEqual(result_field,
                test_field['results'])  
        for test_field in self.deletable_fields: 
            tag = test_field['tag']
            field = Field(
                tag = test_field['tag'],
                indicators = test_field['indicators'],
                subfields = test_field['subfields']
            )       
            subfield = (field.subfields[0], field.subfields[1])
            vocabulary_code = test_field['subfields'][3]
            result_fields = str(self.cc.process_field("00000001", field, vocabulary_code))
    
            self.assertTrue(result_fields)


    
    def convert_field(self, tag, indicators, subfields): 
        return Field(
            tag = tag,
            indicators = indicators,
            subfields = subfields
        )   

    """
def suite():
    test_suite = unittest.makeSuite(FieldConversionTest, 'test')
    return test_suite
    """
if __name__ == "__main__":
    unittest.main()