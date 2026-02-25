# 🤖 SuperAgent - Trading Automation OS (V8.5 Hedge-Grade)

SuperAgent non è un semplice script o un "bot Python", ma un Sistema Operativo di Automazione Finanziaria (Trading OS) progettato per operare in autonomia totale 24/7 su VPS/Server Dedicati e PC Locali.

È strutturato per intercettare segnali da Telegram, analizzarli tramite AI, mappare i selettori DOM e piazzare scommesse sportive in modo totalmente invisibile ai sistemi anti-frode (Datadome, Akamai), garantendo un uptime del 100% grazie al suo strato di supervisione OS e prevenendo qualsiasi perdita di dati.

### 🧠 Che cos'è il Risk Engine "Roserpina"?
A partire dalla versione 8.5, SuperAgent integra **Roserpina Hedge AI**, un motore quantitativo di gestione del capitale che trasforma il bot da semplice esecutore a un vero e proprio **Algorithmic Trading Desk**.
Il sistema non si limita a piazzare scommesse fisse, ma:
* **Gestisce il Bankroll:** Decide quanto capitale esporre in tempo reale in base al drawdown e alla volatilità.
* **Tavoli Paralleli:** Gestisce fino a 5 scommesse simultanee ("Tavoli") su flussi indipendenti ma con cassa condivisa.
* **Adattivo (AI-Driven):** Se l'equity sale, aumenta l'esposizione (Expansion Mode). Se c'è un drawdown, attiva i protocolli di difesa per proteggere il capitale (Defense Mode).
* **Anti-Duplicazione:** Impedisce matematicamente di scommettere due volte sullo stesso evento, azzerando il rischio di sovraesposizione tossica.

---

## 📖 Benvenuto in SUPERAGENT OS! (Guida Rapida)

Se è la prima volta che apri questo programma, non preoccuparti: anche se dietro le quinte c'è una tecnologia di livello finanziario (Hedge-Grade), l'interfaccia è stata studiata per essere semplice e intuitiva. 

Immagina questo programma come il tuo **ufficio virtuale**: qui assumi i tuoi "robot", gli dai le chiavi per accedere ai siti di scommesse, gli spieghi cosa fare e loro lavorano per te 24 ore su 24.

Ecco una guida passo-passo per navigare tra le 10 sezioni (Tab) che trovi in alto:

### 📊 1. Tab: Dashboard (Il Pannello di Controllo)
* **A cosa serve:** È la tua schermata di benvenuto e la cabina di pilotaggio principale.
* **Sistema di Sicurezza:** Ti avvisa che tutti i dati sono protetti nel "Vault" (una cassaforte digitale invisibile) e il sistema di backup è attivo.
* 🔴 **Pulsante "START/STOP MOTORE" (Toggle di Accensione Globale):**
  Un grande interruttore visivo che ti permette di accendere e spegnere il motore principale del bot direttamente dall'interfaccia.
  * **Stato OFF:** Rosso, con scritto "Avvia Sistema". Il bot è a riposo e non elabora segnali.
  * **Stato ON:** Verde, con scritto "Sistema Operativo: IN ASCOLTO". Il bot è connesso a Telegram ed è pronto ad agire.

### 💰 2. Tab: Bookmakers (La tua Cassaforte)
* **A cosa serve:** Qui è dove inserisci le tue credenziali (nome utente e password) dei vari siti di scommesse (es. Bet365, Sisal, ecc.).
* **È sicuro?** Assolutamente sì. Le password che inserisci non vengono mai salvate "in chiaro", ma vengono criptate a livello militare.
* **Come aggiungere un account:**
  1. Vai nel pannello di destra.
  2. Scrivi un **Nome** per ricordarti l'account (es. *Bet365_Mio*).
  3. Inserisci il tuo **Username** e la **Password**.
  4. Clicca sul pulsante **`➕ Salva Bookmaker`**. Vedrai l'account comparire nella lista a sinistra.
* **Come eliminare un account:** Clicca sul nome dell'account nella lista a sinistra e premi **`❌ Elimina Selezionato`**.

### 🧩 3. Tab: Selettori (Gli "Occhi" del Bot)
* **A cosa serve:** I siti web cambiano spesso. Qui è dove "insegni" al bot dove si trovano esattamente i pulsanti sui vari siti web (es. dove cliccare per scommettere).
* **Come si usa:**
  1. Scegli un **Nome** per l'istruzione (es. *pulsante_scommetti*).
  2. Seleziona a quale **Bookmaker** si riferisce.
  3. Incolla il codice "CSS" o "XPath" (è il "percorso" tecnico del pulsante sul sito web).
  4. Clicca su **`➕ Salva Selettore`**.

### 🤖 4. Tab: Robot & Strategie (Il Cervello)
* **A cosa serve:** Qui crei le tue strategie. Puoi creare quanti robot vuoi, assegnare a ciascuno un budget e dirgli a quali parole (inviate su Telegram) deve reagire.
* **Come creare una strategia:**
  1. Clicca sul pulsante in basso **`➕ Crea Nuovo Robot`**.
  2. Guardando il pannello di destra, dagli un **Nome**.
  3. Scegli dal menu a tendina quale **Account Bookmaker** (che hai salvato nella Tab 2) questo robot dovrà usare.
  4. Inserisci le **Trigger Words** (parole chiave separate da virgola, es: *calcio, over 2.5, serie a*). Quando il bot leggerà queste parole su Telegram, si attiverà.
  5. **Gestione Cassa (MM):** Scegli come il robot deve gestire i tuoi soldi dal menu a tendina:
     * **Stake Fisso:** Il robot scommetterà esattamente l'importo fisso in euro specificato sotto.
     * **Roserpina (Progressione):** Il robot non userà uno stake fisso, ma interrogherà l'Intelligenza Artificiale quantitativa per calcolare lo stake matematico in base a rischio, esposizione e drawdown attuali.
* 🔘 **Pulsante START/STOP Individuale:** Oltre al motore principale, puoi accendere o mettere in pausa ogni singolo robot! Se una strategia sta andando male, spegni solo quel robot ("⏸️ Robot IN PAUSA") senza fermare le altre strategie.
* 💡 **NOTA MAGICA:** Hai notato che non c'è il pulsante "Salva"? In questa schermata **il salvataggio è automatico e istantaneo**. Ogni lettera che digiti viene salvata in tempo reale. Se va via la corrente, non perdi nulla!
* **Come eliminare un robot:** Selezionalo a sinistra e clicca **`❌ Elimina Robot`**.

### 🕵️ 5. Tab: Anti-Detect Lab (Il Laboratorio di Sicurezza)
* **A cosa serve:** È il tuo campo di addestramento militare. Qui testi in diretta l'invisibilità del tuo bot (Firma CDP, Canvas, WebGL, Entropia) contro i sistemi anti-frode più potenti del mondo (SannySoft, Pixelscan, CreepJS, FPScanner, ecc.).
* **Come si usa:** Clicca sul grande pulsante verde **`🚀 AVVIA DECATHLON ANTI-FRODE`**. 
* **Cosa succede:** Vedrai aprirsi un vero browser sul tuo schermo. Il bot navigherà da solo sui vari siti di test, e nella tua interfaccia (in stile hacker) appariranno i log in tempo reale. 
* **Perché farlo dal PC e non su GitHub?** Testando da qui, il browser userà il tuo VERO indirizzo IP (residenziale) e la tua VERA scheda video. Questo spegne gli allarmi di "Datacenter IP" e "Headless VM" che invece scattano sempre sui server Cloud, permettendoti di ottenere un punteggio di invisibilità totale (Semafori Verdi 🟢).

### 🧠 6. Tab: God Certification (Il Giudice Supremo)
* **A cosa serve:** È il protocollo di validazione di livello Enterprise per l'intera architettura. Testa spietatamente la tenuta del Database, la resilienza ai crash (Chaos Mode), l'invisibilità Anti-Detect e l'integrità dell'Interfaccia.
* **Come si usa:** Clicca sul pulsante **`🏆 AVVIA GOD CERTIFICATION`**.
* **Cosa succede:** La console si riempirà con i risultati di decine di stress test. Se alla fine vedi la scritta **"🟢 BOT CERTIFICATO PRODUZIONE"**, significa che la macchina è letteralmente invincibile: non perde dati, sopravvive agli attacchi di rete, non va in crash ed è totalmente invisibile.

### 📈 7. Tab: Risk Desk (Storico & Tavoli)
* **A cosa serve:** È il tuo cruscotto finanziario in tempo reale (Hedge Fund Monitor). Qui controlli l'andamento del capitale e le decisioni dell'Intelligenza Artificiale.
* **Cosa puoi vedere:**
  1. **Statistiche Cassa:** Il tuo Bankroll attuale, il Picco Massimo raggiunto e il Drawdown (percentuale di perdita dal picco).
  2. **Stato dei 5 Tavoli:** Scopri subito se i tavoli Roserpina sono liberi (Verde), occupati in una bet (Blu) o in fase di recupero perdite (Arancione).
  3. **Cronologia:** Una tabella completa con lo storico di tutte le tue scommesse (data, tavolo usato, esito, stake e profitto netto).

### ⚙️ 8. Tab: Roserpina Config (Il Cervello AI)
* **A cosa serve:** È la plancia di comando dell'Hedge Fund. Qui decidi il "carattere" del bot e imposti i limiti matematici invalicabili che proteggeranno i tuoi soldi.
* **Come si usa:** Per proteggere il tuo capitale da click accidentali, i parametri nascono bloccati (sola lettura). Clicca su **✏️ Modifica Impostazioni** per cambiarli, poi su **💾 Salva e Applica al Motore** per confermare e rimettere in sicurezza.
* **Parametri Principali:**
  * **Target Profitto Ciclo (%):** L'obiettivo di guadagno **GLOBALE** dell'intero conto. Se imposti 3% su un bankroll di 100€, il sistema lavorerà con tutti i tavoli per generare +3€ netti. Al raggiungimento, il ciclo si resetta e riparte su un saldo maggiore.
  * **Max Stake Singola Bet (%):** La tua cintura di sicurezza. Protegge dalla bancarotta impedendo al sistema (anche durante un recupero difficile) di puntare oltre questa percentuale del tuo capitale totale.
  * **Max Capitale Esposto (%):** Definisce quanti soldi massimi possono essere "in gioco" contemporaneamente in scommesse aperte.
  * **Auto-Reset Recovery:** Il "paracadute". Se il drawdown supera una soglia critica (es. -15%), il sistema azzera la memoria delle perdite, accetta la sconfitta e riparte pulito per non bruciare la cassa.
  * **Aggiorna Bankroll:** Usalo per sincronizzare il bot dopo che hai fatto un prelievo o un deposito manuale sul sito del bookmaker.
  * **Forza Reset Recovery:** Un tasto d'emergenza rosso per piallare tutti i tavoli attivi e azzerare le perdite in memoria istantaneamente.

### ☁️ 9. Tab: Cloud & API (I Collegamenti Esterni)
* **A cosa serve:** Il tuo bot ha bisogno di "parlare" con Telegram (per leggere i pronostici) e con l'Intelligenza Artificiale (per capirli). Qui inserisci i codici segreti (API) per permettere questa comunicazione.
* **Come si usa:**
  1. Incolla i tuoi codici di Telegram (`API ID`, `API Hash` e la lunghissima `Session String`).
  2. Incolla la tua `API Key` di OpenRouter (il cervello dell'IA).
  3. Clicca su **`💾 Salva Chiavi API & Cloud`**.
* **Nota di Sicurezza:** Appena salvi, i codici si trasformeranno in pallini o asterischi per proteggere la tua privacy da chiunque guardi il tuo schermo.

### 📝 10. Tab: Logs (La Scatola Nera)
* **A cosa serve:** È il monitor in stile "hacker" (sfondo nero, scritte verdi). Ti mostra in diretta tutto quello che il bot sta facendo in quel preciso istante.
* **Come si usa:** Non devi fare assolutamente nulla. Siediti e guarda le scritte scorrere. Vedrai il bot che riceve i segnali, ragiona, si connette ai bookmaker e piazza le scommesse.

### 🚦 IN CHE ORDINE DEVO PROCEDERE LA PRIMA VOLTA?
Per non confonderti, segui questo ordine esatto per la prima configurazione:
1. Vai su **Cloud & API** e collega Telegram e l'Intelligenza artificiale.
2. Vai su **Bookmakers** e inserisci il tuo conto di gioco (es. Bet365).
3. Vai su **Selettori** (se hai codici da aggiornare per i siti).
4. Vai su **Robot & Strategie** e crea il tuo primo lavoratore virtuale. Scegli se usare "Stake Fisso" o il potente "Roserpina Hedge AI" come Gestore Cassa. Assicurati che il robot sia "🟢 Robot ATTIVO".
5. Vai su **Roserpina Config** e imposta i tuoi limiti di rischio e il tuo Bankroll iniziale.
6. (Opzionale) Vai in **Anti-Detect Lab** e fai un giro di test per verificare che la tua connessione sia anonima e sicura.
7. (Opzionale) Vai in **God Certification** per confermare che il bot sia perfettamente operativo sul tuo hardware.
8. Vai sulla **Dashboard** e clicca su "🔴 Avvia Sistema" per accendere il motore.
9. Vai su **Logs** o **Risk Desk**, rilassati e lascia che il bot faccia il lavoro sporco!

---

## 🔬 Dettagli Tecnici: Come Funziona il Motore Roserpina Hedge AI

Selezionando "Roserpina" nella tab Robot, si disattiva lo stake fisso e si accende il motore quantitativo basato su AI. Ecco cosa accade passo-passo quando arriva un segnale da Telegram:

**1. Analisi di Rischio in Tempo Reale**
L'Intelligenza Artificiale scansiona istantaneamente il database leggendo:
* Il **Bankroll attuale** e il picco storico (*High Water Mark*).
* Il **Drawdown corrente** (quanto capitale si è perso rispetto al massimo).
* L'**Esposizione totale** (quanto denaro è già impegnato in scommesse aperte).
* Quanti dei **5 Tavoli Paralleli** sono attualmente occupati.

**2. Assegnazione della Strategia Macro**
A seconda della salute finanziaria del sistema, l'AI ordina una direttiva:
* **🟢 EXPANSION:** (Equity ai massimi, Drawdown 0%). Permette l'utilizzo di tutti e 5 i tavoli simultaneamente, aumenta il tetto di esposizione massima e incrementa lo stake base.
* **🟡 NEUTRAL:** (Fase di stabilizzazione). Mantiene un massimo di 3 tavoli attivi per consolidare.
* **🔴 DEFENSE:** (Drawdown negativo oltre il 10%). Riduce immediatamente l'esposizione, blocca le nuove entrate oltre il secondo tavolo e diminuisce i moltiplicatori di scommessa.

**3. Calcolo Matematico e Anti-Duplicazione**
Se l'AI autorizza l'ingresso, il sistema:
* Verifica che l'evento (es. "Inter Milan Over 2.5") non sia già presente in un altro tavolo. In caso positivo, **blocca la scommessa per impedire doppie esposizioni tossiche**.
* Cerca il tavolo libero più idoneo, dando precedenza assoluta a quelli che si trovano in fase di recovery (perdita pregressa da recuperare).
* Calcola lo stake matematico combinando la quota reale dal bookmaker, l'esposizione residua disponibile, il target di profitto e il moltiplicatore dettato dall'IA.
* Prenota i fondi sul Database SQLite (*Transaction Memory*) e lancia l'Execution Engine.

**4. Verifica Crittografica Post-Bet (Hedge-Grade)**
Il sistema non si fida ciecamente dei siti di scommesse. Dopo aver cliccato per scommettere, confronta il saldo reale del conto prima e dopo l'operazione. Solo se il saldo decresce esattamente dell'importo dello stake (Delta = Stake), la transazione viene confermata sul DB. In caso contrario (es. bug visivo del bookmaker), il bot attua un **Rollback automatico** annullando la prenotazione dei fondi e mettendo il sistema in sicurezza.

---

## 🧪 Suite di Test Enterprise (QA Automatica & Chaos Engineering)

Il repository è equipaggiato con un sistema di Quality Assurance automatizzato che protegge l'architettura a livello di core e di interfaccia grafica, girando automaticamente su GitHub Actions ad ogni push (tramite Xvfb per il rendering headless dell'interfaccia).

* **Test UI End-to-End (`MASTER_UI_TEST.py`):** Un bot (PyTest-Qt) simula un utente reale inserendo dati nei campi, cliccando pulsanti e testando il caricamento automatico delle chiavi e dei robot. Verifica la non-congelabilità dell'interfaccia.
* **Chaos Engineering & Attacchi Reali (`REAL_ATTACK_TEST.py`):** Il sistema inietta guasti mirati (Crash di rete, Blocchi Cloudflare/Captcha, Panico sull'Event Bus) per garantire che il database non venga mai corrotto e che il meccanismo di rollback funzioni.
* **Telegram & AI Pipeline (`TELEGRAM_AI_PIPELINE_TEST.py`):** Un collaudo a 4 stadi sui "sensori" del bot. Testa l'iniezione chirurgica di un segnale, respinge bombardamenti di 1.000 messaggi spam al secondo, valida l'estrazione dati complessa via AI e simula un collasso dei server di Telegram verificando che il bot si ricolleghi senza andare in crash.
* **Soak Test 24H (`SOAK_24H_TEST.py`):** Mette sotto stress l'Execution Engine sparando cicli continui per verificare l'assenza assoluta di Memory Leaks e garantire che il bot possa girare su server per mesi senza riavvii.

---

## 🛡️ Modulo Anti-Detect e Security Audit (GitHub Actions)

### 📘 Spiegazione dei Test (Cosa controlliamo in CI/CD)
Oltre al test manuale nella UI, il codice esegue un controllo di integrità ogni volta che viene aggiornato su GitHub. Il test inietta il nostro script `STEALTH_INJECTION_V5` e legge silenziosamente la risposta dell'antifrode:

* **Classici (SannySoft, BrowserLeaks, AmIUnique, DeviceInfo):** Controlla se le difese di base smascherano il nostro bot. Verifica che la proprietà "WebDriver" sia stata cancellata con successo e che la nostra finta scheda video (WebGL Hardware Spoofing) sia attiva.
* **Rete e Coerenza (BrowserScan, IPHey, Whoer, Pixelscan):** Qui entra in gioco il Proxy. I server antifrode incrociano l'impronta hardware del tuo browser con l'indirizzo IP. Se l'IP è di un Datacenter americano (come quelli di GitHub), il test fallisce; se inserisci il tuo proxy residenziale, l'IP appare domestico, superando le euristiche WebRTC e TLS.
* **Hardcore (FPScanner, Detect.expert, CreepJS):** Analizza come facciamo i calcoli matematici, falsifica la firma della GPU contro i sistemi DataDome (FPScanner) e cerca le tracce remote del protocollo di automazione (CDP). *Nota: Su GitHub, a causa dell'assenza di un monitor fisico e di un vero mouse, questi test falliscono di proposito, confermando l'efficacia dei sistemi anti-bot moderni contro le macchine virtuali.*

### ⚙️ GUIDA: Come inserire in sicurezza l'API Key / URL del Proxy in GitHub
Affinché la seconda fase dei test passi (sui server GitHub), dobbiamo camuffare l'IP di Microsoft Azure.

1. Apri il tuo repository su **GitHub**.
2. Clicca sulla tab in alto a destra **Settings** (Impostazioni).
3. Nel menu verticale a sinistra, scendi e clicca su **Secrets and variables**, poi su **Actions**.
4. Clicca sul pulsante verde in alto **New repository secret**.
5. Nel campo **Name**, scrivi ESATTAMENTE questo:
   `PROXY_URL`
6. Nel campo **Secret**, incolla l'URL completo del tuo proxy. Il formato standard è:
   `http://iltuousername:latuapassword@192.168.1.100:8080`
   *(Se non hai una password, basta inserire `http://ip:porta`)*
7. Clicca su **Add secret**.

Da questo momento, ogni volta che GitHub eseguirà il workflow, scaricherà di nascosto questo indirizzo e lo aggancerà al browser, eludendo la sorveglianza di rete dei siti di test! Se non configuri il proxy, il test girerà comunque, ma le fasi 5-8 riporteranno fallimenti previsti (a causa dell'IP Datacenter), avvisandoti.

---

## 📂 Struttura del Repository

Ecco l'elenco completo di tutti i file attualmente caricati e disponibili nell'ambiente:

**Directory Principale / Root (`/`):**
* `.gitignore`, `AUDIT_REPORT.md`, `GOD_CERTIFICATION.py`, `README.md`, `hedge_super_tester.py`, `main.py`, `pyproject.toml`, `quant_ci_evaluator.py`, `repo_audit.py`, `requirements.txt`, `setup_vps_task.py`, `supervisor.py`, `tester_v4.py`

**Directory `.github/workflows/`:**
* `build.yml`, `openrouter_audit.yml`, `production_check.yml`, `v4_test_suite.yml`, `v7_quant_monitoring.yml`, `anti_detect_audit.yml`, `master_ui_audit.yml`

**Directory `config/`:**
* `config.yaml`, `robots.yaml`, `selectors.yaml`, `roserpina_settings.yaml`

**Directory `core/`:**
* `ai_parser.py`, `ai_selector_validator.py`, `ai_trainer.py`, `anti_detect.py`, `arch_v6.py`, `auto_mapper_worker.py`, `bet_worker.py`, `command_parser.py`, `config_loader.py`, `config_paths.py`, `controller.py`, `crypto_vault.py`, `database.py`, `dom_executor_playwright.py`, `dom_self_healing.py`, `event_bus.py`, `events.py`, `execution_engine.py`, `geometry.py`, `health.py`, `heartbeat.py`, `human_behavior.py`, `human_mouse.py`, `human_profile.py`, `lifecycle.py`, `logger.py`, `money_management.py`, `multi_site_scanner.py`, `os_human_interaction.py`, `playwright_worker.py`, `secure_storage.py`, `security.py`, `security_logger.py`, `signal_parser.py`, `state_machine.py`, `telegram_worker.py`, `utils.py`

**Directory `ui/`:**
* `anti_detect_tab.py`, `bookmaker_tab.py`, `desktop_app.py`, `god_certification_tab.py`, `history_tab.py`, `roserpina_tab.py`, `robots_tab.py`, `selectors_tab.py`

**Directory `tests/tests/` (QA Automatica):**
* `ui/MASTER_UI_TEST.py`, `system_integrity/REAL_ATTACK_TEST.py`, `system_integrity/SOAK_24H_TEST.py`, `system_integrity/ULTRA_SYSTEM_TEST.py`, `system_integrity/ENDURANCE_TEST.py`, `system_integrity/ANTI_DETECT_AUDIT.py`, `system_integrity/TELEGRAM_AI_PIPELINE_TEST.py`