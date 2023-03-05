# QBGest

Demo disponibile qui [QBGest](https://ctfossolo.centu.it/qbdemo/registri) user demo password demo

QBGest è un software open source pensato per la gestione della contabilità di una piccola azienda, prende spunto dai software Odoo ed Esatto coniugando quelli che sono a mio avviso i loro punti di forza. Come dice il suo stesso nome QB="Quanto Basta" il software è di impronta minimalista ed essenziale, ma fa comunque tutto quello che serve. Viene utilizzato ormai da due anni per gestire la contabilità di una piccola azienda e ha raggiunto un buon grado di maturità. Ho ritenuto quindi opportuno condividere con la comunità open source sia il software, che le nozioni che ho appreso/sviluppato nella speranza che possa essere di aiuto per qualcuno.

QBGest è di tipo web based quindi utilizzabile con un normale browser web, è scritto in Python e utilizza il framework Flask e il database PostgreSQL.

QBGest gestisce tutte le funzionalità basilari che ci si può aspettare da un software per la contabilità italiana, offre inoltre una gestione documentale, permette l'importazione automatica dell'estratto conto bancario, gestisce la riconciliazione dei movimenti bancari con i relativi documenti di competenza, gestisce la ricezione e l'invio delle fatture elettroniche con il sistema di interscambio mediante pec.

L'impostazione non è classica ma a oggetti, non esistono quindi le Causali ma esistono le Registrazioni e viene sfruttata l'ipertestualità per la navigazione nel database. La contabilità viene quindi tenuta mediante l'utilizzo di opportuni registri che contengono le registrazioni che a loro volta, se validate, generano in automatico le scritture contabili. Le registrazioni possono essere riconciliate e sul meccanismo della riconciliazone si base tutta la logica di funzionamento, rendendo superfluo l'utilizzo delle scritture di prima nota, se non per casi particolari. Un esempio classico di riconciliazione si ha quando una fattura emessa viene segnata come pagata riconciliandola con il relativo movimento risultante dall'importazione dell'estratto conto dalla banca.

Le registrazioni possono essere annullate, e tornare quindi in fase di bozza per essere editate, o possono essere eliminate definitivamente (per esempio se si è fatto un errore). In ogni caso il database rimane sempre autoconsistente essendo il software in grado di gestire in automatico l'annullamento di tutte le registrazioni correlate.

Altra caratteristica è la capacità di gestire in automatico e con semplicità la numerazione delle registrazioni, senza vincoli troppo rigidi, ma garantendo comunque la corretta numerazione.

Altre informazioni si possono trovare nella pagina web di [QBGest](https://www.centu.it/qbgest)
