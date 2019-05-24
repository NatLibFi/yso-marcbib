Ohjelma konvertoi bibliografiset MARC21-tietueiden Ysa-, Allärs-, Musa- ja Cilla-asiasanat vastaaviin YSO- ja SLM-käsitteisiin.

**Ohjelman kuvaus**

Ohjelma käsittelee bibliografisia tietueita MARCXML- tai MARC21-muodossa. MARC21-tietueet luetaan yhtenä tiedostona. MARCXML-tietueet voivat olla yhdessä tiedostossa tai tietueet erillisinä tiedostona. Jälkimmäisessä tapauksessa konvertoidut tietueet tuotetaan samannimisinä tietueina käyttäjän käynnistysparametrissä ilmoittamaan kansioon. 
    
Jos tietueet ovat erillisissä tiedostoissa, ne on laitettava samaan kansioon, joka ei sisällä muita tiedostoja.
    
Konvertoidaan vain seuraavat tietueiden kentät 385, 567, 648, 650, 651, 655
Konversiossa tuotetaan ja päivitetään seuraaavia kenttiä: 370, 382, 385, 388, 567, 648, 650, 651, 653, 655
Muunnosprosessi on kuvattu Kiwissä: https://www.kiwi.fi/display/ysall2yso
- Konversiosäännöt on kuvaillaan erillisessä sääntödokumentissa, musiikki- ja elokuva-aineistolle on oma erillinen säännöstönsä
- Konversio kohdistuu kaikkiin aineistotyyppeihin
- Asiasanakenttiä järjestetään uudelleen mm. sanaston ja kielen mukaan
Ohjelma käyttää Musa (sisältää Cillan), Ysa-, Allärs-, Yso-, SEKO- ja SLM-sanastoja, jotka testiversiossa on ladattava ohjelman pääkansioon rdf-muodossa Finton sivulta: https://finto.fi/
Ohjelma käyttää Python-kirjastoja pymarc, rdflib, unidecode, jotka on asennettava ennen käyttöä, esim. `pip install <kirjaston nimi>`.
    
**Ohjelman käynnistysparametrit**

Annetaan komentorivillä `python yso_converter.py -i="input-tiedostopolku" -o="output-tiedostopolku" -f="formaatti ("marc21" tai "marcxml")` 

Ohjelma tuottaa automaattisesti lokitiedostot logs-kansion työhakemistoon aikaleimoilla.
          
**Ohjelman tuottamat tulosteet ja raportit**

Ohjelma tallentaa 1. ajokerralla sanastot väliaikaiseen tiedostoon vocabularies.pkl, josta sanastot on nopeampi ladata käyttöön uudelleen samana päivänä. Tämän jälkeen ohjelma lataa ja käsittelee sanastot päivän 1. ajokerralla uudelleen ja tallentaa väliaikaisen tiedoston uudestaan.

Ohjelman lokitiedostot tuotetaan logs-nimiseen alikansioon. 
Jokaiseen lokitiedoston nimeen lisätään ohjelman suorittamisen päivä ja aloitusaika:
- tarkistettavat kentät: finto-yso-konversio_check-log
    
- tilastot: 
    
Tarkistettavat kentät: 
    
Loki sisältää asiasanat, joita ei ole konvertoitu, mutta on siirretty toiseen kenttään.
    
Tarkistettaviin kenttiin kirjataan a) virhekoodi, b) sanastokoodi, c) virheen aiheuttanut termi, c) tietue-id, d) alkuperäinen kenttä e) uusi kenttä
Tällaiset kentät vaativat manuaalisen käsittelyn konversion jälkeen. 
          
Tarkistuskoodit:
1 = termille ei löytynyt vastinetta sanastoista
2 = termille useampi mahdollinen vastine (termille on useampi samanlainen normalisoitu käytettävä termi tai ohjaustermi) 
3 = termillä ei vastinetta, mutta termillä on täsmälleen yksi sulkutarkenteellinen muoto
4 = termillä ei vastinetta, mutta termillä on sulkutarkenteellinen muoto kahdessa tai useammassa käsitteessä
5 = termille löytyy vastine, mutta sille on olemassa myös sulkutarkenteellinen muoto eri käsitteessä
6 = ketjun osakentän termi poistettu tarpeettomana (fiktio, aiheet, musiikki ja ketjun $e-osakenttä sekä tyhjä osakenttä)
7 = kentän 650/651 osakentän $g "muut tiedot" on viety kenttään 653
8 = Kenttä sisältää MARC-formaattiin kuulumattomia osakenttäkoodeja tai ei sisällä asiasanaosakenttiä
 
Tilastot:
    
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
