/**
 * GitHub-API-basierter Sync für Leseliste und Später-lesen.
 * Token wird einmalig pro Gerät in localStorage gespeichert.
 */
const GH_SYNC = (function() {
    const REPO = 'gqwx6dwkyy-tech/zeitschriften-briefing';
    const DATEI = 'docs/leseliste.json';
    const TOKEN_KEY = 'briefing_gh_token';

    let _cache = null;
    let _sha = null;
    let _busy = false;

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token.trim());
    }

    function tokenEingabe() {
        return new Promise((resolve) => {
            // Overlay erstellen
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center;';
            overlay.innerHTML = `
                <div style="background:#faf7f2;border-radius:8px;padding:28px;max-width:400px;width:90%;border:2px solid #1a6b6a;">
                    <h3 style="margin:0 0 12px;color:#1a6b6a;font-size:16px;">GitHub-Token einrichten</h3>
                    <p style="margin:0 0 16px;font-size:13px;color:#2c3e50;line-height:1.5;">
                        Für die geräteübergreifende Leseliste wird ein GitHub Personal Access Token benötigt
                        (Scope: <code>repo</code>). Einmalige Eingabe pro Gerät.
                    </p>
                    <input type="password" id="gh-token-input" placeholder="ghp_..."
                        style="width:100%;padding:10px;border:1px solid #e8dcc8;border-radius:4px;font-size:14px;box-sizing:border-box;background:#fff;">
                    <div style="display:flex;gap:8px;margin-top:14px;justify-content:flex-end;">
                        <button id="gh-token-cancel" style="padding:8px 16px;border:1px solid #e8dcc8;background:#faf7f2;border-radius:4px;cursor:pointer;color:#7f8c8d;font-size:13px;">Abbrechen</button>
                        <button id="gh-token-save" style="padding:8px 16px;border:none;background:#1a6b6a;color:#fff;border-radius:4px;cursor:pointer;font-size:13px;">Speichern</button>
                    </div>
                </div>`;
            document.body.appendChild(overlay);

            const input = document.getElementById('gh-token-input');
            input.focus();

            document.getElementById('gh-token-save').onclick = () => {
                const val = input.value.trim();
                if (val) {
                    setToken(val);
                    overlay.remove();
                    resolve(val);
                }
            };
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const val = input.value.trim();
                    if (val) {
                        setToken(val);
                        overlay.remove();
                        resolve(val);
                    }
                }
            });
            document.getElementById('gh-token-cancel').onclick = () => {
                overlay.remove();
                resolve(null);
            };
        });
    }

    async function sicherToken() {
        let token = getToken();
        if (!token) {
            token = await tokenEingabe();
        }
        return token;
    }

    async function laden() {
        const token = await sicherToken();
        if (!token) return { spaeter_lesen: [], leseliste: [] };

        const resp = await fetch(`https://api.github.com/repos/${REPO}/contents/${DATEI}?ref=master`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github.v3+json'
            }
        });

        if (resp.status === 401 || resp.status === 403) {
            localStorage.removeItem(TOKEN_KEY);
            throw new Error('Token ungültig — bitte neu eingeben.');
        }

        if (!resp.ok) {
            // Datei existiert noch nicht
            if (resp.status === 404) {
                _sha = null;
                _cache = { spaeter_lesen: [], leseliste: [] };
                return _cache;
            }
            throw new Error('GitHub-API-Fehler: ' + resp.status);
        }

        const data = await resp.json();
        _sha = data.sha;
        const inhalt = JSON.parse(atob(data.content));
        _cache = inhalt;
        return inhalt;
    }

    async function speichern(daten) {
        if (_busy) return;
        _busy = true;

        try {
            const token = await sicherToken();
            if (!token) return;

            const body = {
                message: 'Leseliste aktualisiert',
                content: btoa(unescape(encodeURIComponent(JSON.stringify(daten, null, 2)))),
                branch: 'master'
            };
            if (_sha) body.sha = _sha;

            const resp = await fetch(`https://api.github.com/repos/${REPO}/contents/${DATEI}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            });

            if (resp.status === 401 || resp.status === 403) {
                localStorage.removeItem(TOKEN_KEY);
                throw new Error('Token ungültig');
            }
            if (resp.status === 409) {
                // Conflict — neu laden und erneut versuchen
                await laden();
                throw new Error('Konflikt — bitte erneut versuchen');
            }
            if (!resp.ok) {
                throw new Error('Speichern fehlgeschlagen: ' + resp.status);
            }

            const result = await resp.json();
            _sha = result.content.sha;
            _cache = daten;
        } finally {
            _busy = false;
        }
    }

    return {
        laden,
        speichern,
        sicherToken,
        getToken,
        setToken,
        get cache() { return _cache; }
    };
})();
