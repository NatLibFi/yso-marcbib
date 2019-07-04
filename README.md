**YSO-MARCBIB konversio-ohjelma**

Ohjelma konvertoi bibliografisten MARC21-tietueiden Ysa-, Allärs-, Musa- ja Cilla-asiasanat vastaaviin YSO- ja SLM-käsitteisiin.

**Ohjelman kuvaus**

Ohjelma käsittelee bibliografisia tietueita MARCXML- tai MARC21-muodossa. MARC21-tietueet luetaan yhtenä tiedostona. MARCXML-tietueet voivat olla yhdessä tiedostossa tai tietueet erillisinä tiedostona. Jälkimmäisessä tapauksessa konvertoidut tietueet tuotetaan samannimisinä tietueina käyttäjän käynnistysparametrissä ilmoittamaan kansioon. 
    
Jos tietueet ovat erillisissä tiedostoissa, ne on laitettava samaan kansioon, joka ei sisällä muita tiedostoja.
    
Konvertoidaan vain seuraavat tietueiden kentät 385, 567, 648, 650, 651, 655
Konversiossa tuotetaan ja päivitetään seuraaavia kenttiä: 257, 370, 382, 385, 388, 567, 648, 650, 651, 653, 655
Muunnosprosessi on kuvattu Kiwissä: https://www.kiwi.fi/display/ysall2yso
- Konversiosäännöt on kuvailtu erillisessä sääntödokumentissa
- Konversio kohdistuu kaikkiin aineistotyyppeihin
- Asiasanakenttiä järjestetään uudelleen mm. sanaston ja kielen mukaan. 
- Termien alkuperäinen järjestys pyritään säästämään.

Ohjelma käyttää Musa (sisältää Cillan), Ysa-, Allärs-, Yso-, SEKO- ja SLM-sanastoja, jotka testiversiossa on ladattava ohjelman pääkansioon rdf-muodossa Finton sivulta: https://finto.fi/
Ohjelma käyttää Python-kirjastoja pymarc, rdflib, unidecode, jotka on asennettava ennen käyttöä, esim. `pip install <kirjaston nimi>`.
    
**Ohjelman käynnistysparametrit**

Annetaan komentorivillä `python yso_converter.py`

Komentoriviparametrit:
- -i="input-tiedostonimi" tai -id="input-hakemistopolku"
- -o="output-tiedostonimi" tai -od="output-hakemistopolku"
- -f="formaatti" ("marc21" tai "marcxml") 
- -al="yes" ("yes", jos halutaan asiasanat suomeksi ja ruotsiksi tai "no", jos halutaan vain alkuperäisellä kielellä) 

Jos valitaan input-hakemistopolku, ohjelma kopioi kaikki hakemiston tiedostot (varmista, että kaikki tiedostot ovat samassa formaatissa, joka valittu f-parametrillä)
Jos on valittu output-tiedostonimi, ohjelma kopioi kaikki uudet tietueet samaan tiedostoon valitulla output-tiedostonimellä
Jos on valittu output-hakemistopolku, ohjelma kopioi uudet tietueet alkuperäisillä tiedostonimillä output-hakemistopolulla määriteltyyn kansioon

Ohjelma tuottaa automaattisesti lokitiedostot logs-kansion työhakemistoon aikaleimoilla.
          
**Ohjelman tuottamat tulosteet ja raportit**

Ohjelma tallentaa 1. ajokerralla sanastot väliaikaiseen tiedostoon vocabularies.pkl, josta sanastot on nopeampi ladata käyttöön uudelleen samana päivänä. Tämän jälkeen ohjelma lataa ja käsittelee sanastot päivän 1. ajokerralla uudelleen ja tallentaa väliaikaisen tiedoston uudestaan.

Ohjelman lokitiedostot tuotetaan logs-nimiseen alikansioon. 
Jokaiseen lokitiedoston nimeen lisätään ohjelman suorittamisen päivä ja aloitusaika:
   
***Tarkistettavat kentät***

Tiedostonimi: finto-yso-konversio_check-log
    
Loki sisältää asiasanat, joita ei ole konvertoitu, mutta on siirretty toiseen kenttään.
    
Tarkistettaviin kenttiin kirjataan a) virhekoodi, b) sanastokoodi, c) virheen aiheuttanut termi, c) tietue-id, d) alkuperäinen kenttä e) uusi kenttä. Muuttujat eroteltu puolipisteellä.  Tällaiset kentät vaativat manuaalisen käsittelyn konversion jälkeen. 

Tarkistuskoodit:
- 1 = termille ei löytynyt vastinetta sanastoista
- 2 = termille useampi mahdollinen vastine (termille on useampi samanlainen normalisoitu käytettävä termi tai ohjaustermi) 
- 3 = termillä ei vastinetta, mutta termillä on täsmälleen yksi sulkutarkenteellinen muoto
- 4 = termillä ei vastinetta, mutta termillä on sulkutarkenteellinen muoto kahdessa tai useammassa käsitteessä
- 5 = termille löytyy vastine, mutta sille on olemassa myös sulkutarkenteellinen muoto eri käsitteessä
- 6 = ketjun osakentän termi poistettu tarpeettomana (fiktio, aiheet, musiikki ja ketjun $e-osakenttä sekä tyhjä osakenttä)
- 7 = kentän 650/651 osakentän $g "muut tiedot" on viety kenttään 653
- 8 = Kenttä sisältää MARC-formaattiin kuulumattomia osakenttäkoodeja tai ei sisällä asiasanaosakenttiä
- 9 = Kentässä on osakenttä 6 (tällaisia kenttiä ei voi konvertoida, sillä viitatussa 880-kentässä on vastaavat osakentät)
 
***Tilastot***
    
Tiedostonimi: finto-yso-konversio_stats-log_
    
Mittarit:
        
- käsiteltyjä tietueita: lähdetietueiden lukumäärä
- konvertoitujen tietueiden lukumäärä: kuinka moneen tietueeseen tehtiin muutoksia
- käsiteltyjä asiasanakenttiä
- poistettuja asiasanakenttiä
- uusia asiasanakenttiä
- viallisia tietueita:
- viallisten tietueiden selitykset, Pythonin ja pymarcin virheluokkien nimillä:
BaseAddressInvalid, 
RecordLeaderInvalid: tietueen nimiö on viallinen
BaseAddressNotFound, 
RecordDirectoryInvalid: tietueen hakemisto on viallinen
NoFieldsFound: tietueessa ei ole kenttiä
UnicodeDecodeError: tietueen nimiössä tai hakemistossa on ASCII-merkistön ulkopuolisia merkkejä
RecordLengthInvalid

***Julkaisutiedot***

Lisää tietoa julkaisuversioista, katso [julkaisutiedot](https://github.com/NatLibFi/yso-marcbib/releases)

**YSO-MARCBIB-converter**

The program takes bibliographic MARC21 records and converts subject headings from  the ysa allars, musa and cilla thesauri to the terms of matching concepts in the yso and slm ontologies.

**Description of the converter**
The program handles bibliographic records in either MARCXML or MARC21 format. The MARC21 records are read as one file. The MARCXML records can be input as one file or each record in a separate file. In the latter case the converted records are written with the same filenames to the subdirectory named in the starting parametres.

If the records are in separate files they need to be in the same directory which does not contain other files.

The program reads in only the following fields in the MARC records:  385, 567, 648, 650, 651, 655.
The conversion produces or modifies the following fields: 257, 370, 382, 385, 388, 567, 648, 650, 651, 653, 655.
The conversion process is described more thoroughly  (in Finnish) in a separate document available at https://www.kiwi.fi/display/ysall2yso
- The conversion rules are provided as a text document and as an Excel-table.
- Conversion handles all content types.
- The subject subfields are re-sorted according to the second indicator, source-id in subfield $2, and language
- sorting tries to keep the original order of the terms as much as possible
- multiple subfields are split to separate fields according to the subfield and content of the subfield

The conversion uses several thesauri which need to be loaded in RDF-format to the main folder with the program: Musa (containts Cilla), YSA, Allärs, YSO, SLM and Seko. These can be downloaded from the homepages of each thesaurus at the finto.fi service.
The program uses the following Python-libraries: pymarc, rdflib, unidecode, which need to be installed before running the program. e.g. 'pip install <library_name>'.

**Starting parametres**

Command line options `python yso_converter.py -i="input-path" -o="output-path" -f="format" (given as "marc21" or "marcxml") -al="yes/no" (choose "yes" if concept labels are wanted in Finnish and Swedish, "no" if only original language of concept is wanted) `

The converter produces automatically logfiles with timestamps to the logs subfolder working directory

**Outputs and reports**

During first run of the day, the converter stores the thesauri into a temporary file called vocabularies.pkl. It will be faster to load the thesauri from this file during possible consecutive runs in the same day. The converter reloads and stores the thesauri into the temporary file again, once each day it is run.

The logfiles are output into a subdirectory named logs.
A timestamp with date and starting time is added at the end of each of the logfiles produced.

***Fields to be checked***

Filename: "finto-yso-konversio_check-log"

The logfile contains those terms which were not converted. It has the following values separated by semicolons:
a) error_code, b) source-id, c) term in question, d) record identifier, e) original field, c) converted field.
These terms would need to be converted manually after the automatic conversion.

Error-codes:
- 1 = cannot find a matching label in the given thesauri
- 2 = several matching labels (label has more than one similar normalized label in the given thesauri)
- 3 = no exactly matching labels, but there is exactly one matching label with a following specifier in parentheses.
- 4 = no exactly matching labels, but a matching label with a specifier in two or more concepts
- 5 = one exactly matching label, but also a matching label with a specifier in another concept
- 6 = The label was removed as unnecessary (fiktio, aiheet, musiikki and $e-subfield as well as sufields with no values)
- 7 = The content fo subfield $g in fields 650 or 651 was moved to field 653##$a.
- 8 = Field contains subfield codes not registered in the MARC-format or has no concept labels.
- 9 = Field contains subfield $6 (not converted, as the corresponding 880-fields have the same subfields)

***Statistics***

Filename: finto-yso-konversio_stats-log_

The variables
- number of handled records : number of source records
- number of converted records: hom many records were changed
- number of fields handled
- number of removed fields
- number of new fields
- number of records with errors:
- explanations of record erros, Pythonin and pymarcin error_classes:
BaseAddressInvalid, 
RecordLeaderInvalid: 
BaseAddressNotFound, 
RecordDirectoryInvalid: 
NoFieldsFound: 
UnicodeDecodeError: 
RecordLengthInvalid

***Release notes***

For information about released versions, see [Release notes](https://github.com/NatLibFi/yso-marcbib/releases)
