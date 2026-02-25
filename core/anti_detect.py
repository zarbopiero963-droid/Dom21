"""
🔥 MODULO ANTI-DETECT V5 (FPScanner & DataDome Bypass)
Sovrascrive a basso livello le API del browser per falsificare l'hardware
e nascondere le firme CDP (Chrome DevTools Protocol).
"""

STEALTH_INJECTION_V5 = """
(function() {
    // 1. DISTRUZIONE DEL MARKER WEBDRIVER (Cross-Context)
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 2. SIMULAZIONE OGGETTO CHROME (Assente in Chromium Headless)
    if (!window.chrome) {
        window.chrome = {
            runtime: {},
            app: {},
            csi: () => {},
            loadTimes: () => {}
        };
    }

    // 3. FIX DEI PERMESSI (FPScanner cerca incongruenze nelle notifiche)
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // 4. MOCK PLUGINS & MIME TYPES (I bot di solito li hanno vuoti)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3], // Finto array con lunghezza > 0
    });
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => [1, 2], // Finto array
    });

    // 5. SPOOFING HARDWARE GPU / WEBGL (Il colpo di grazia per FPScanner)
    // Nascondiamo il driver "SwiftShader" o "Google" dei server VPS
    const getParameterProxyHandler = {
        apply: function(target, ctx, args) {
            const param = args[0];
            if (param === 37445) { // UNMASKED_VENDOR_WEBGL
                return 'Intel Inc.';
            }
            if (param === 37446) { // UNMASKED_RENDERER_WEBGL
                return 'Intel Iris OpenGL Engine';
            }
            return Reflect.apply(target, ctx, args);
        }
    };
    const proxyWebGL = () => {
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function() {
            const context = getContext.apply(this, arguments);
            if (context && (arguments[0] === 'webgl' || arguments[0] === 'webgl2')) {
                context.getParameter = new Proxy(context.getParameter, getParameterProxyHandler);
            }
            return context;
        };
    };
    proxyWebGL();

    // 6. RIMOZIONE TRACCE DI AUTOMAZIONE (Pulizia Variabili Globali)
    delete window.__playwright;
    delete window.__pw_manual;
    delete window.__PW_outOfContext;
    delete window.domAutomation;
    delete window.domAutomationController;
})();
"""

class AntiDetect:
    @staticmethod
    def get_browser_args():
        """
        Argomenti a livello di motore Chromium per spegnere le flag di automazione.
        Da passare a playwright.chromium.launch(args=...)
        """
        return [
            "--disable-blink-features=AutomationControlled", # Nasconde l'uso del CDP
            "--disable-infobars",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--ignore-certificate-errors",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--window-position=0,0",
            "--window-size=1920,1080"
        ]

    @staticmethod
    async def apply_stealth(context):
        """
        Inietta lo script V5 in ogni nuova pagina e iframe aperto dal contesto.
        """
        await context.add_init_script(STEALTH_INJECTION_V5)
