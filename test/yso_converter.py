import unittest
import re
from vocabularies import Vocabularies
from rdflib import Graph, URIRef, Namespace, RDF
from pymarc import Record, Field
from concept_converter import ConceptConverter

class YsoConversionTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls):
        #cls.vocabulary = Vocabularies()
        cls.cc = YsoConverter("test.mrc", "output.mrc", "marc21")
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
        cls.cc.vocabularies.parse_vocabulary(yso_graph, 'yso', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary(yso_paikat_graph, 'yso_paikat', ['fi', 'sv'])
        cls.cc.vocabularies.parse_vocabulary(ysa_graph, 'ysa', ['fi'])
        cls.cc.vocabularies.parse_vocabulary(allars_graph, 'allars', ['sv'])
        cls.cc.vocabularies.parse_vocabulary(slm_graph, 'slm_fi', ['fi', 'sv'], 'fi')
        cls.cc.vocabularies.parse_vocabulary(slm_graph, 'slm_sv', ['fi', 'sv'], 'sv')
        cls.cc.vocabularies.parse_vocabulary(musa_graph, 'musa', ['fi'], secondary_graph = ysa_graph)
        cls.cc.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)
        cls.cc.vocabularies.parse_vocabulary(musa_graph, 'cilla', ['sv'], secondary_graph = ysa_graph)
        cls.records = [
            {'original': ['=648  17$a1980-luku$0linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
                          '=648  \\7$a1900-luku$2yso',
                          '=648  \\7$a1900-luku$2ysa'
                         ],
             'converted': ['=388  1\$8järjestysnumero$a1980-luku$2yso/fin$9FENNI<KEEP>',
                           '=648  \\7$a1900-luku$2yso',
                           '=648  \\7$a1900-luku$2yso/fin'
                         ]
            },
            {'original': ['=648  17$a1980-luku$0linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
                          '=648  17$a1980-luku$vragat$0linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
                          '=650  \\7$a1900-luku$2yso',
                          '=650  \\7$a1900-luku$2ysa',
                          '=650  \\7$a1900$2allars',
                          '=650  \\7$a1800-1900-luku$bragat$2allars',
                          '=650  \\7$atsekkoslovakia$0linkitys$9FENNI<KEEP>$2ysa',
                          '=650  \\7$atsekkoslovakia$0linkitys$9FENNI<KEEP>$9FENNI<KEEP>$2ysa'
                         ],
             'converted': ['=388  1\$8järjestysnumero$a1980-luku$2yso/fin$9FENNI<KEEP>',
                            '=648  \\7$a1900-luku$2yso/fin',
                            '=648  \\7$a1900$2yso/swe',
                            '=648  \\7$a1800-1900-luku$2yso/swe',
                            '=650  \\7$a1900-luku$2yso',
                            '=650  \\7$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038',
                            '=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847$9FENNI<KEEP>',
                            '=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847$9FENNI<KEEP>$9FENNI<KEEP>',
                            '=655  \\7$8järjestysnumero$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786$9FENNI<KEEP>'
                         ]
            },
            {'original': ['=650  \\7$a1800-1900-luku$bragat$2allars'
                         ],
             'converted': ['=648  \\7$a1800-1900-luku$2yso/swe',
                            '=650  \\7$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038'
                         ]
            },
            {'original': ['=650  \\8$amembraanit$2yso',
                          '=650  \\7$amembraanit$2ysa$9SAVON<KEEP>$9FENNI<DROP>'
                         ],
             'converted': ['=650  \\4$amembraanit$9SAVON<KEEP>$9FENNI<DROP>',
                            '=650  \\8$amembraanit$2yso'
                         ]
            },
            {'original': ['=650  \\8$amembraanit$2yso',
                          '=650  \\7$amembraanit$bjotain$2ysa$9SAVON<KEEP>$9FENNI<DROP>'
                         ],
             'converted': ['=650  \\4$amembraanit$9SAVON<KEEP>',
                            '=650  \\8$amembraanit$2yso',
                            '=653  \\0$ajotain$9SAVON<KEEP>'
                         ]
            },
            {'original': ['=650  \\7$a1800-1900-luku$bragat$2allars',
                          '=650  \\7$arāgat$2yso/fin'
                         ],
             'converted': ['=648  \\7$a1800-1900-luku$2yso/swe',
                            '=650  \\7$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038'
                        ]
            },
            {'original': ['=650  \\7$aHelsinki$zTöölö$bpolkka (tanssit)$2ysa',
                          '=245  00$aSkogsradion och genom kaminröret :$bmidsommar 1942.',
                          '=648  \\7$a1900-talet$2allars',
                          '=338  \\\\$anide$bnc$2rdacarrier'
                         ],
             'converted': ['=245  00$aSkogsradion och genom kaminröret :$bmidsommar 1942.',
                           '=338  \\\\$anide$bnc$2rdacarrier',
                           '=648  \\7$a1900-talet$2yso/swe',
                           '=650  \\7$apolkka (tanssit)$2yso/fin$0http://www.yso.fi/onto/yso/p5647',
                           '=651  \\7$aTöölö (Helsinki)$2yso/fin$0http://www.yso.fi/onto/yso/p109631'
                        ]
            }
        ]

        cls.exceptional_fields = [
            {'original': '=650  \\7$a1900-luku$2ysa',
             'results': ['=648  \\7$a1900-luku$2yso/fin']
            },
            {'original': '=650  \\7$a$2allars',
             'results': ['=648  \\7$a1900$2yso/swe']
            },
            {'original': '=650  \\7$a1900$2allars',
             'results': ['=648  \\7$a1900$2yso/swe']
            },
            {'original': '=650  \\7$a1800-1900-luku$bragat$2allars',
             'results': ['=648  \\7$a1800-1900-luku$2yso/swe',
                 '=650  \\7$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038']
            },
            {'original': '=650  \\7$atsekkoslovakia$0linkitys$9FENNI<KEEP>$2ysa',
             'results': ['=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847$9FENNI<KEEP>']
            },
            {'original': '=650  \\7$atsekkoslovakia$0linkitys$9FENNI<KEEP>$9FENNI<KEEP>$2ysa',
             'results': ['=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847$9FENNI<KEEP>$9FENNI<KEEP>']
            },
            {'original': '=648  17$a1980-luku$0linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
             'results': ['=388  1\$8järjestysnumero$a1980-luku$2yso/fin$9FENNI<KEEP>']
            },
            {'original': '=648  17$a1980-luku$vragat$0linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
             'results': ['=388  1\$8järjestysnumero$a1980-luku$2yso/fin$9FENNI<KEEP>',
             '=655  \\7$8järjestysnumero$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786$9FENNI<KEEP>']
            },
            {'original': '=567  \\7$bragat$bTšekkoslovakia$ahuomautus metodologiasta' \
             '$1Reaalimaailman kohteen tunniste$6linkitys$2ysa$8järjestysnumero$9FENNI<KEEP>',
             "results": [
            ("=567  \\\\$6linkitys$8järjestysnumero$ahuomautus metodologiasta$brāgat" \
             "$1Reaalimaailman kohteen tunniste$2yso/fin$0http://www.yso.fi/onto/yso/p30038" \
             "$9FENNI<KEEP>"),
            ("=567  \\\\$6linkitys$8järjestysnumero$ahuomautus metodologiasta$bTšekkoslovakia" \
             "$1Reaalimaailman kohteen tunniste$9FENNI<KEEP>")
            ]},
            {'original':  '=567  \\7$bragat$2ysa',
             "results": ['=567  \\\\$brāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038']
            },
            {'original':  '=567  \\7$bjotain$2ysa$9FENNI<KEEP>',
             "results": ["=567  \\\\$bjotain$9FENNI<KEEP>"]
            },
            {'original':  '=567  \\7$cragat$2ysa$9FENNI<KEEP>',
             "results": ['=567  \\\\$cragat$9FENNI<KEEP>']
            },
            {'original':  '=567  \\7$aragat$2ysa$9FENNI<KEEP>',
             "results": ['=567  \\\\$brāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038$9FENNI<KEEP>']
            }
        ]
        #HUOM! sanastokoodi viimeiseksi osakentäksi
        cls.convertible_subfields = [
            {'original': '=650  \\7$aTšekkoslovakia$2ysa',
                'results': ['=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847']
            },
            {'original': '=650  \\7$amembraanit$2ysa',
                'results': ['=650  \\4$amembraanit']
            },
            {'original': '=650  \\7$amembraanit$9FENNI<KEEP>$2ysa',
                'results': ['=650  \\4$amembraanit$9FENNI<KEEP>']
            },
            {'original': '=655  \\7$aragat$2ysa',
                'results': ['=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786']
            },
            {'original': '=650  \\7$ajotain$2allars',
                'results': ['=653  \\0$ajotain']
            },
            {'original': '=650  \\7$aTjeckoslovakien$2ysa',
                'results': ['=651  \\7$aTjeckoslovakien$2yso/swe$0http://www.yso.fi/onto/yso/p105847']
            },
            {'original': '=385  \\7$aRAGAT$2ysa',
                'results': ['=385  \\\\$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038']
            },
            {'original': '=650  \\7$vrāgat$2ysa',
                'results': ['=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786']
            },
            {'original': '=385  \\7$aRAGAT$2ysa',
                'results': ['=385  \\\\$arāgat$2yso/fin$0http://www.yso.fi/onto/yso/p30038']
            },
            {'original': '=650  \\7$asteel pan$2musa',
                'results': ['=650  \\7$asteel pan$2yso/fin$0http://www.yso.fi/onto/yso/p29959']
            },
            {'original': '=655  \\7$aragat$2ysa',
                'results': ['=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786']
            },
            #haetaan yksiosaisella diakriitillisellä merkillä:
            {'original': '=650  \\7$aTšekkoslovakia$2ysa',
                'results': ['=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847']
            },
            {'original': '=650  \\7$aTsekkoslovakia$2ysa',
                'results': ['=651  \\7$aTšekkoslovakia$2yso/fin$0http://www.yso.fi/onto/yso/p105847']
            },
            {'original': '=655  \\7$csilleen jättäminen$2ysa',
                'results': ['=655  \\4$csilleen jättäminen']
            },
            {'original': '=655  \\7$amembraanit$2ysa',
                'results': ['=653  \\6$amembraanit']
            }
        ]

        cls.inconvertible_subfields = [
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
            "subfields": ['v', 'fiktio', '2', 'ysa']}
        ]

        
        cls.numeric_fields = [
            {"tag": "650", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', '1900-luku', '2', 'ysa'],
             "results": ['=648  \\7$a1900-luku$2yso/fin']},
            {"tag": "651", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['y', '1900', '2', 'allars'],
             "results": ['=648  \\7$a1900$2yso/swe']},
            {"tag": "655", 
             "indicators": [ ' ', '7' ], 
             "subfields": ['a', 'ragat', 'y', '1800-1900-luku', '2', 'allars'],
             "results": 
                ['=388  1\\$a1800-1900-luku',
                 '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786']
            }
        
        ]
        
        return super(FieldConversionTest, cls).setUpClass()

    def test_subfields_to_dict(self):
        
        subfields = ['a', 'nimi', 'b', 'alaotsikko']
        expected_result = [{'code': 'a', 'value': 'nimi'}, {'code': 'b', 'value': 'alaotsikko'}]
        self.assertEqual(self.cc.subfields_to_dict(subfields), expected_result)
    
    """
    def test_convert_subfield(self):
        for test_field in self.convertible_subfields:
            tag = test_field['tag']
            subfield = {'code': test_field['subfields'][0], 'value': test_field['subfields'][1]}
            vocabulary_code = test_field['subfields'][3]
            field = self.new_field(tag, [' ', '7'], subfield)
            result_field = str(self.cc.process_subfield("00000001", field, subfield, vocabulary_code))
            self.assertEqual(result_field,
            test_field['results'])     
    """

    #TESTAA OSAKENTTIEN LAJITTELUA!
    
    def test_convert_fiction(self):
        tag = "650"
        subfield = {'code': 'a', 'value': 'RAGAT'}
        field = self.new_field(tag, [' ', '7'], [subfield['code'], subfield['value']])
        vocabulary_code = 'ysa'
        result_field = str(self.cc.process_subfield("00000001", field, subfield, vocabulary_code, fiction=True))
        self.assertEqual(result_field,
            '=655  \\7$arāgat$2slm/fin$0http://urn.fi/URN:NBN:fi:au:slm:s786')
    
    def test_process_geographical_concepts(self):
        field = self.new_field("650", [' ', ' '], ['a', 'Helsinki', 'z', 'Töölö', '2', 'ysa'])
        test_result = "=651  \\7$aTöölö (Helsinki)$2yso/fin$0http://www.yso.fi/onto/yso/p109631"
        
        result_fields = self.cc.process_field("00000001", field, "ysa")
        self.assertEqual(str(result_fields[0]), test_result)
    """ 
    def test_convert_field(self):
        #testataan useampia asiasanaosakenttiä sisältävien kenttien konvertoimista:
        for test_field in self.convertible_subfields:
            field = self.str_to_marc(test_field['original'])
            vocabulary_code = field['2']
            result_fields = self.cc.process_field("00000001", field, vocabulary_code)
            self.assertTrue(len(test_field['results']) == len(result_fields))
            for r in test_field['results']:
                self.assertTrue(any(r == str(rf) for rf in result_fields))
        for test_field in self.exceptional_fields:
            field = self.str_to_marc(test_field['original'])
            vocabulary_code = field['2']
            result_fields = self.cc.process_field("00000001", field, vocabulary_code)
            self.assertTrue(len(test_field['results']) == len(result_fields))
            for r in test_field['results']:
                self.assertTrue(any(r == str(rf) for rf in result_fields))

        #testaa rivit, joita ei konvertoida    
        for test_field in self.deletable_fields: 
            field = self.new_field(test_field['tag'], test_field['indicators'], test_field['subfields'])  
            vocabulary_code = test_field['subfields'][-1]
            result_fields = self.cc.process_field("00000001", field, vocabulary_code)
            self.assertEqual(result_fields, [])
          
    """
    def test_convert_numeric_fields(self):
        valid_time_fields = {
            '648': ['a', 'z', 'y', 'v'],
            '650': ['a', 'b', 'x', 'y', 'd', 'z', 'c'],
            '651': ['a', 'x', 'y', 'z']
        }
        tags = ['648', '650', '651', '655']
        for tag in tags:
            #a-z-osakenttäkoodien läpikäynti:
            for letter in range(97,123):
                code = str(letter)
                field = self.new_field(tag, [' ', '7'], [code, '1900-luku', '2', 'ysa']) 
                result_fields = self.cc.process_field("00000001", field, 'ysa')
                if tag in valid_time_fields and code in valid_time_fields[tag]:
                    self.assertEqual(str(result_fields[0]), '=648  \\7$a1900-luku$2yso/fin')
                else:
                    self.assertNotEqual(str(result_fields[0]), '=648  \\7$a1900-luku$2yso/fin')
    
        for test_field in self.numeric_fields:
            field = self.new_field(test_field['tag'], test_field['indicators'], test_field['subfields']) 
            vocabulary_code = test_field['subfields'][-1]
            result_fields = self.cc.process_field("00000001", field, vocabulary_code)
            result_field = str(result_fields[0])
            self.assertTrue(len(test_field['results']) == len(result_fields))
            for r in test_field['results']:
                self.assertTrue(any(r == str(rf) for rf in result_fields))
    
    def test_process_record(self):
        for r in self.records:
            record = Record()
            record.add_field( Field(tag='001', data='00000001'))
            original_fields = []
            for field in r['original']:
                original_fields.append(field)
                record.add_field(self.str_to_marc(field))
            #nimiön 6. paikasta katsotaan tietuetyyppi:
            record.leader = "wefweeawfewfewfwefwg"
            new_record = self.cc.process_record(record)
            new_fields = []
            result_fields = []
            for field in new_record.get_fields():
                new_fields.append(str(field))
            result_fields.append(str(Field(tag='001', data='00000001')))
            for field in r['converted']:
                result_fields.append(field)   
            self.assertEqual(result_fields, new_fields)
            
    def new_field(self, tag, indicators, subfields): 
        return Field(
            tag = tag,
            indicators = indicators,
            subfields = subfields
        )   

    def str_to_marc(self, string):
        tag = string[1:4]
        indicator_1 = string[6]
        indicator_2 = string[7]
        if indicator_1 == "\\":
            indicator_1 = " "
        if indicator_2 == "\\":
            indicator_2 = " "
        fields = re.split('\$', string)
        subfields = []
        for f in fields[1:]:
            subfields.append(f[0])
            subfields.append(f[1:])
        return Field(
            tag = tag,
            indicators = [indicator_1, indicator_2],
            subfields = subfields
        )  

    """
def suite():
    test_suite = unittest.makeSuite(FieldConversionTest, 'test')
    return test_suite
    """
if __name__ == "__main__":
    unittest.main()