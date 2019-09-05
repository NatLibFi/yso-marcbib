import unittest
import os
from pymarc import Record, Field
from yso_converter import YsoConverter
from pymarc import MARCReader

class RecordReadTest(unittest.TestCase):

    #def setUp(self):
        
    @classmethod
    def setUpClass(cls):
        #cls.vocabulary = Vocabularies()
        cls.input_path = "test/test_records.mrc"
        cls.output_path = "test/tested_records.mrc"
        cls.yc = YsoConverter(
            input_file = cls.input_path,
            input_directory = None,
            output_file = cls.output_path,
            output_directory = None,
            file_format = "marc21",
            field_links = True,
            all_languages = True
        )

        cls.yc.initialize_vocabularies()
        return super(RecordReadTest, cls).setUpClass()

    def test_read_records(self):
        self.yc.read_records()
        output_reader = MARCReader(open(self.output_path, 'rb'), to_unicode=True)
        test_reader = MARCReader(open("test/converted_records.mrc", 'rb'), to_unicode=True)
        test_record = Record()
        while test_record:                
            output_record = next(output_reader, None)
            test_record = next(test_reader, None)
            if output_record:
                output_fields = []
                test_fields = []
                for field in output_record.get_fields():
                    output_fields.append(str(field))
                for field in test_record.get_fields():
                    test_fields.append(str(field))
                self.assertCountEqual(output_fields, test_fields)
                self.assertListEqual(output_fields, test_fields)
                  
        output_reader.close()
        test_reader.close()
    
    def tearDown(self):
        os.remove(self.output_path)

if __name__ == "__main__":
    unittest.main()
