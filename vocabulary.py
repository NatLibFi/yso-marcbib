from rdflib import Graph, URIRef, Namespace, RDF
from rdflib.namespace import SKOS, XSD, OWL, DC
import copy
import re
import unicodedata
import unidecode

class Container():
    #apuluokka get_replacers-funktiolle, joka etsii deprekoiduille käsitteille voimassaolevat korvaajat
    def __init__(self):
        self.nodes = []
    def delete_node(self, node):
        self.nodes.remove(node)
    def add_node(self, node):
        self.nodes.append(node)

class Vocabulary():

    def __init__(self, vocabulary_code, language_codes):
        if vocabulary_code.startswith('slm'):
            self.target_vocabulary_code = "slm" 
        elif vocabulary_code == 'seko':
            self.target_vocabulary_code = vocabulary_code
        else:
            self.target_vocabulary_code = "yso"
        self.language_codes = language_codes
        #tallennetaan deprekoitujen käsitteiden ja niiden voimassaolevien korvaajien URIt 
        self.geographical_concepts = set()
        #ketjutetut maantieteelliset termit:
        self.geographical_chained_labels = set()
        #sisältää deprekoidut käsitteet avaimina ja arvoina lista korvaajista
        self.deprecated_concepts = {}
        self.aggregate_concepts = set()
        #sisältää pref- ja altLabelit:
        self.labels = {}
        #labelit pienillä kirjaimilla case-insensitive-hakua varten
        self.labels_lowercase = {}
        #labelit ilman diakriittejä diakriitittömän hakua varten
        self.stripped_labels = {}
        #asiasanat, joilla tarkenteellisia ja tarkenteettomia muotoja:
        self.labels_with_and_without_specifiers = {}
        #asiasanat, joilla vain tarkenteellisia muotoja:
        self.labels_with_specifiers = {}
        #vastinsanat toisella kielellä (SLM-sanastoon):
        self.translations = {}
        self.dct = Namespace("http://purl.org/dc/terms/")
        self.namespace = 'http://www.yso.fi/onto/yso/'
        self.nodes = [] #for temporary use

    def parse_musa_vocabulary(self, g, secondary_graph):
        """
        g: käsiteltävän sanaston graafi
        secondary_graph: Ysa-sanaston graafi
        """
        #sisältää pelkät prefLabelit (tarvitaan poikkeustapauksiin, jossa voi olla sama termi pref- ja altLabelina):
        exact_matches = {}
        for conc in secondary_graph.subjects(RDF.type, SKOS.Concept):
            matches = secondary_graph.preferredLabel(conc, labelProperties=[SKOS.exactMatch]) 
            uris = set()
            for m in matches:
                #lisää YSO-linkit:
                if self.namespace in str(m[1]):
                    uris.add(str(m[1])) 
            if not uris:
                matches = secondary_graph.preferredLabel(conc, labelProperties=[SKOS.closeMatch]) 
                for m in matches:
                    if self.namespace in str(m[1]):
                        uris.add(str(m[1])) 
            exact_matches.update({str(conc): uris})        

        for conc in g.subjects(RDF.type, SKOS.Concept):
            replaced_by = g.preferredLabel(conc, labelProperties=[self.dct.isReplacedBy])
            replacer = None
            replacers = set()
            for rb in replaced_by:
                #HUOM! oletetaan, että musa-käsitteillä on vain yksi korvaaja:
                replacer = str(rb[1])
                if replacer in exact_matches:
                    for em in exact_matches[replacer]:
                        replacers.add(em)
            for lc in self.language_codes:
                alt_labels = g.preferredLabel(conc, lang=lc, labelProperties=[SKOS.altLabel])
                for al in alt_labels:
                    alt_label = str(al[1])
                    uris = copy.copy(replacers)
                    if alt_label in self.labels:
                        self.labels[alt_label].update(uris)
                    else:
                        self.labels.update({alt_label: uris})
                pref_label = g.preferredLabel(conc, lang=lc)
                if pref_label:
                    pref_label = str(pref_label[0][1])
                    uris = copy.copy(replacers)
                    if pref_label in self.labels:
                        self.labels[pref_label].update(uris)
                    else:
                        self.labels.update({pref_label: uris})     
        self.create_additional_dicts()

    def parse_yso_vocabulary(self, g):
        aggregateconceptscheme = URIRef("http://www.yso.fi/onto/yso/aggregateconceptscheme")
        deprecated_temp = {} #väliaikainen sanasto deprekoiduille käsitteille ja niiden seuraajille
        for conc in g.subjects(RDF.type, SKOS.Concept):
            uri = str(conc)
            in_scheme = g.preferredLabel(conc, labelProperties=[SKOS.inScheme]) 
            for scheme in in_scheme:
                if scheme[1] == aggregateconceptscheme:
                    self.aggregate_concepts.add(uri)
            #kerätään ensin deprekoitujen käsitteiden seuraajat
            deprecated = g.preferredLabel(conc, labelProperties=[OWL.deprecated])
            if deprecated:
                replaced_by = g.preferredLabel(conc, labelProperties=[self.dct.isReplacedBy])
                for rb in replaced_by:
                    replacer = str(rb[1])
                    if uri in deprecated_temp:
                        deprecated_temp[uri].append(replacer)
                    else:
                        deprecated_temp.update({uri: [replacer]})
            else:
                """
                value = g.value(conc, RDF.type)
                if value in aggregateconceptscheme:
                    aggregate_concepts.add(uri)
                """
                for lc in self.language_codes:
                    pref_label = g.preferredLabel(conc, lang=lc)
                    if pref_label:
                        pref_label = str(pref_label[0][1])
                        if uri in self.labels:
                            self.labels[uri].update({lc: pref_label})
                        else:
                            self.labels.update({uri: {lc: pref_label}})

        #selvitetään deprekoitujen käsitteiden korvaajat:
        for dc in deprecated_temp:
            c = Container()
            replaced_by = self.get_replacers(c, deprecated_temp, dc)
            replacers = []
            self.deprecated_concepts.update({dc: c.nodes})

    def get_replacers(self, container, replacers, key):
        if key in replacers:
            for r in replacers[key]:
                if key in container.nodes:
                    container.delete_node(key)
                container.add_node(r)
                self.get_replacers(container, replacers, r)
        else: 
            return

    def parse_origin_vocabulary(self, g):
        #sisältää pelkät prefLabelit (tarvitaan poikkeustapauksiin, jossa voi olla sama termi pref- ja altLabelina):
        geographical_namespaces = [URIRef("http://www.yso.fi/onto/ysa-meta/GeographicalConcept"),
        URIRef("http://www.yso.fi/onto/allars-meta/GeographicalConcept")]
        for conc in g.subjects(RDF.type, SKOS.Concept):
            is_geographical = False
            rdf_types = g.preferredLabel(conc, labelProperties=[RDF.type]) 
            for rdf_type in rdf_types:
                try:
                    if rdf_type[1] in geographical_namespaces:
                        is_geographical = True
                except IndexError:
                    logging.info("viallinen käsite: %s" %conc)
            for lc in self.language_codes:
                alt_labels = g.preferredLabel(conc, lang=lc, labelProperties=[SKOS.altLabel])
                matches = g.preferredLabel(conc, labelProperties=[SKOS.exactMatch]) 
                uris = set()
                for m in matches:
                    #lisätään YSO-vastineiden linkit:
                    if self.namespace in str(m[1]):
                        uris.add(str(m[1]))
                        if is_geographical:
                            self.geographical_concepts.add(str(m[1]))
                if not uris:
                    matches = g.preferredLabel(conc, labelProperties=[SKOS.closeMatch]) 
                    for m in matches:
                        if self.namespace in str(m[1]):
                            uris.add(str(m[1]))   
                            if is_geographical:
                                self.geographical_concepts.add(str(m[1]))          
                for al in alt_labels:
                    alt_label = str(al[1])
                    uris = copy.copy(uris)
                    if "--" in alt_label and is_geographical:
                        self.geographical_chained_labels.add(alt_label)     
                    if alt_label in self.labels:
                        self.labels[alt_label].update(uris)
                    else:
                        self.labels.update({alt_label: uris})
                pref_label = g.preferredLabel(conc, lang=lc)
                if pref_label:
                    pref_label = str(pref_label[0][1])
                    uris = copy.copy(uris)
                    if pref_label in self.labels:
                        self.labels[pref_label].update(uris)
                    else:
                        self.labels.update({pref_label: uris})
                    if "--" in pref_label and is_geographical:
                        self.geographical_chained_labels.add(pref_label)
                       
        self.create_additional_dicts()
 
    def parse_label_vocabulary(self, g):
        """
        muodostaa sanastolle, joka sisältää vain käsitteiden labelit ja niiden prefLabelit
        """
        temp_labels = {}
        for lc in self.language_codes:
            self.labels.update({lc: {}})
            self.labels_lowercase.update({lc: {}})
            self.stripped_labels.update({lc: {}})
            self.labels_with_and_without_specifiers.update({lc: {}})
            self.labels_with_specifiers.update({lc: {}})
            temp_labels.update({lc: {}})
        #SLM:n deprekoidut käsitteet laitetaan altLabeleihin 
        for conc in g.subjects(RDF.type, SKOS.Concept):
            uri = str(conc)
            for lc in self.language_codes:
                pref_label = g.preferredLabel(conc, lang=lc)
                if pref_label:
                    pref_label = str(pref_label[0][1])
                    if len(self.language_codes) > 1:
                        if uri in self.translations:
                            self.translations[uri].update({lc: pref_label})
                        else:
                            self.translations.update({uri: {lc: pref_label}})
                    if pref_label in self.labels[lc]:
                        self.labels[lc][pref_label]["pref_label"].add(pref_label)
                        self.labels[lc][pref_label]["uris"].add(uri)
                    else:
                        self.labels[lc].update({pref_label: {"pref_label": {pref_label}, "uris":{uri}}})
                alt_labels = g.preferredLabel(conc, lang=lc, labelProperties=[SKOS.altLabel])
                for al in alt_labels:
                    alt_label = str(al[1])
                    if alt_label in self.labels[lc]:
                        self.labels[lc][alt_label]["pref_label"].add(pref_label)
                        self.labels[lc][alt_label]["uris"].add(uri)
                    else:
                        self.labels[lc].update({alt_label: {"pref_label": {pref_label}, "uris":{uri}}})
        for lc in self.language_codes:
            for label in self.labels[lc]:
                label_info = self.labels[lc][label]
                ll = label.lower()
                pref_labels = label_info['pref_label'].copy()
                uris = label_info['uris'].copy()
                if ll in self.labels_lowercase[lc]:
                    self.labels_lowercase[lc][ll]["pref_label"].update(pref_labels)
                    self.labels_lowercase[lc][ll]["uris"].update(uris)
                else:
                    self.labels_lowercase[lc].update({ll: {"pref_label": pref_labels, "uris":uris}}) 
                
            for label in self.labels[lc]:
                label_info = self.labels[lc][label]
                ll = self.remove_diacritical_chars(label).lower()
                pref_labels = label_info['pref_label'].copy()
                uris = label_info['uris'].copy()
                if ll in self.stripped_labels[lc]:
                    self.stripped_labels[lc][ll]["pref_label"].update(pref_labels)  
                    self.stripped_labels[lc][ll]["uris"].update(uris)
                else:
                    self.stripped_labels[lc].update({ll: {"pref_label": pref_labels, "uris":uris}}) 
                
                #tehdään sanasto termeille, joilla on sulkutarkenteellinen ja sulkutarkenteeton muoto:
                stripped_label = re.sub("[\(].*?[\)]", "", ll)
                stripped_label = stripped_label.strip()
                pref_labels = label_info['pref_label'].copy()
                uris = label_info['uris'].copy()

                if stripped_label in temp_labels[lc]:
                    temp_labels[lc][stripped_label]["pref_label"].update(pref_labels)
                    temp_labels[lc][stripped_label]["uris"].update(uris)
                else:
                    temp_labels[lc].update({stripped_label: {"pref_label": pref_labels, "uris":uris}}) 
                
        for lc in self.language_codes:    
            for tl in temp_labels[lc]:
                if tl in self.stripped_labels[lc]:
                    if len(temp_labels[lc][tl]) > len(self.stripped_labels[lc][tl]):
                        self.labels_with_and_without_specifiers[lc].update({tl: temp_labels[lc][tl]})
                else:
                    self.labels_with_specifiers[lc].update({tl: temp_labels[lc][tl]}) 

    def create_additional_dicts(self):
        #luo sanahakuja varten 2 dictionaryä, joissa avaimet pienillä kirjaimilla ja ilman diakriittejä
        temp_labels = {}
        for label in self.labels:
            uris = copy.copy(self.labels[label])
            ll = label.lower()
            if ll in self.labels_lowercase:
                self.labels_lowercase[ll].update(uris)
            else:
                self.labels_lowercase.update({ll: uris})
            #sanasto ilman diakriittejä:
            uris = copy.copy(uris)
            stripped_label = self.remove_diacritical_chars(label).lower()
            if stripped_label in self.stripped_labels:
                self.stripped_labels[stripped_label].update(uris)
            else:
                self.stripped_labels.update({stripped_label: uris})     
            #sanasto ilman diakriittejä ja sulkutarkenteita:
            stripped_label = re.sub("[\(].*?[\)]", "", stripped_label)
            stripped_label = stripped_label.strip()
            uris = copy.copy(uris)
            
            if stripped_label in temp_labels:
                temp_labels[stripped_label].update(uris)
            else:
                temp_labels.update({stripped_label: uris})
        for tl in temp_labels:
            if tl in self.stripped_labels:
                if len(temp_labels[tl]) > len(self.stripped_labels[tl]):
                    self.labels_with_and_without_specifiers.update({tl: temp_labels[tl]})
            else:
                self.labels_with_specifiers.update({tl: temp_labels[tl]}) 
        
    def get_concept_with_uri(self, uri, language):
        #muutetaan kaksikirjaimiset kielikoodit kolmikirjaimiseksi sanastokoodia varten:
        concept = None
        response = {}
        if uri in self.deprecated_concepts:
            replacers = self.deprecated_concepts[uri]
            valid_uris = []
            if replacers:
                for r in replacers:
                    if not r in self.deprecated_concepts:
                        valid_uris.append(r)
                if len(valid_uris) == 0 or len(valid_uris) > 1:
                    raise ValueError("9")
            if valid_uris:
                label = self.labels[valid_uris[0]][language]
                return {"label": label, "uris": valid_uris, "code": self.target_vocabulary_code + "/" + self.convert_to_ISO_639_2(language)}  
            else:
                #raise ValueError("ei löydy YSO-vastinetta")
                return {"label": None, "uris": uris, "code": self.target_vocabulary_code + "/" + self.convert_to_ISO_639_2(language)}  
        elif uri in self.labels:
            if language in self.labels[uri]:
                label = self.labels[uri][language]
                return {"label": label, "uris": [uri], "code": self.target_vocabulary_code + "/" + self.convert_to_ISO_639_2(language)}      

    def get_concept_with_label(self, label, language):
        """
        label: haettavan käsiten pref- tai altLabel
        language: kieliversio, jota haetaan
        all_languages: jos True, niin tuotetaan kummatkin kieliversiot
        """
        concept = None
        uris = []
        valid_uris = []
        labels = {}
        pref_labels = []
        """
        Poistettu virhe 5: jos löytyy täsmälleen yksi sulkutarkenteeton muoto pref- tai altLabelina, niin konvertoidaan tähän labeliin
        if label.lower() in self.labels_with_and_without_specifiers:
            uris = self.labels_with_and_without_specifiers[label.lower()]["uris"]
            if len(uris) > 1:
                raise ValueError("5")
        """
        if label in self.labels[language]:
            uris = self.labels[language][label]["uris"]
            labels = self.labels[language][label]["pref_label"]
        elif label.lower() in self.labels_lowercase[language]:
            uris = self.labels_lowercase[language][label.lower()]["uris"]
            labels = self.labels_lowercase[language][label.lower()]["pref_label"]
        elif label.lower() in self.stripped_labels[language]:
            uris = self.stripped_labels[language][label.lower()]["uris"]
            labels = self.stripped_labels[language][label.lower()]["pref_label"]  
        elif label.lower() in self.labels_with_specifiers[language]:
            uris = self.labels_with_specifiers[language][label.lower()]["uris"]
            if len(uris) > 1:
                raise ValueError("4")
            elif len(uris) == 1:
                raise ValueError("3")
        for uri in uris:
            if uri not in self.deprecated_concepts:
                valid_uris.append(uri)     
        for l in labels:
            pref_labels.append(l)      
        if valid_uris:
            return {"label": pref_labels[0], "uris": valid_uris, "code": self.target_vocabulary_code + "/" + self.convert_to_ISO_639_2(language)}
                
    def get_uris_with_concept(self, concept):
        uris = []
        """
        Poistettu virhe 5: jos löytyy täsmälleen yksi sulkutarkenteeton muoto pref- tai altLabelina, niin konvertoidaan tähän labeliin
        if concept.lower() in self.labels_with_and_without_specifiers:
            uris = self.labels_with_and_without_specifiers[concept.lower()]
            if len(uris) > 1:
                raise ValueError("5")
        """
        if concept in self.labels:
            uris = self.labels[concept]
        elif concept.lower() in self.labels_lowercase:
            uris = self.labels_lowercase[concept.lower()]
        elif concept.lower() in self.stripped_labels:
            uris = self.stripped_labels[concept.lower()]
        elif concept.lower() in self.labels_with_specifiers:
            uris = self.labels_with_specifiers[concept.lower()]
            if len(uris) > 1:
                raise ValueError("4")
            elif len(uris) == 1:
                raise ValueError("3")
        valid_uris = []
        for uri in uris:
            if uri not in self.deprecated_concepts:
                valid_uris.append(uri)    
        if valid_uris:
            return {"uris": valid_uris}

    def translate_label(self, uri, language):
        translated_label = None
        if language == "fi":
            other_language = "sv"
        if language == "sv":
            other_language = "fi"
        if self.target_vocabulary_code == "slm":
            if other_language in self.translations[uri]:
                translated_label = self.translations[uri][other_language]
        if self.target_vocabulary_code == "yso":
            if other_language in self.labels[uri]:
                translated_label = self.labels[uri][other_language]
        if translated_label:
            return {"label": translated_label, "uris": [uri], "code": self.target_vocabulary_code + "/" + self.convert_to_ISO_639_2(other_language)}

    def remove_diacritical_chars(self, word):
        #poistaa tarkkeet kaikista muista merkeistä paitsi å, ä, ö
        result = ""
        for letter in word:
            match = re.match(r'.*([0-9a-zA-ZåäöÅÄÖ\- \'])', letter)
            if match:
                result += letter
            else:
                result += unidecode.unidecode(letter)
        return result  
    
    def convert_to_ISO_639_2(self, code):
        if code == "fi":
            code = "fin"
        if code == "sv":
            code = "swe"
        return code