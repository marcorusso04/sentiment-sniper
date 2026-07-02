# Sentiment Sniper — Brand Kit

Fonte di verità: `landing.html`. Questo documento la formalizza e la estende alla dashboard (`streamlit_app.py`) e ai materiali di outreach.

> Nota: sostituisce la vecchia bozza "Design Bozza UI" su Notion (tema chiaro + accento arancione), mai implementata. Il brand reale in produzione è quello dark della landing.

## Vision

Un'app SaaS moderna, dark, minimal. Il merchant apre la dashboard e in 10 secondi capisce quali sono i problemi principali del suo store.

Tagline: *"Turn bad reviews into better products."*

## Colori

| Ruolo | Colore | Hex | Uso |
|---|---|---|---|
| Primary gradient | Viola → Blu | `#7C3AED` → `#3B82F6` | CTA, titoli brand, accenti, bordo card |
| Background | Nero quasi puro | `#0A0A0F` | Sfondo pagina |
| Surface | Grigio scurissimo | `#13131A` | Card, sidebar |
| Border | Bianco 8% | `rgba(255,255,255,0.08)` | Bordi card/nav |
| Text primario | Bianco caldo | `#F0F0F5` | Testo principale |
| Text muted | Grigio-viola | `#8888AA` | Sottotitoli, caption |
| Danger | Rosso corallo | `#EF4444` | Errori, badge Durability |

### Palette categorie (badge/grafici)

Colori fissi e coerenti ovunque compaiano le 8 categorie (dashboard, Excel export, futuri materiali):

| Categoria | Colore |
|---|---|
| Quality | `#7C3AED` |
| Shipping | `#3B82F6` |
| Packaging | `#F59E0B` |
| Usability | `#06B6D4` |
| Value | `#10B981` |
| Durability | `#EF4444` |
| Missing Accessories | `#EC4899` |
| Customer Service | `#A78BFA` |

Definiti in codice in `streamlit_app.py` (`CATEGORY_COLORS`) — unica fonte, non duplicare altrove.

## Tipografia

- **Titoli / logo:** Syne, 700–800 (Google Fonts)
- **Body / UI:** Inter, 400–600 (Google Fonts)
- **Numeri / KPI:** Syne 800 con gradient text-fill

Import: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@700;800&display=swap`

## Logo

- `assets/icon.svg` — mark (mirino/crosshair a gradient su plate scuro). Usato come favicon e app icon.
- `assets/wordmark.svg` — logotipo testuale "Sentiment" (regular, bianco) + "Sniper" (bold, gradient).
- `assets/logo-lockup.svg` — icona + wordmark affiancati, per header ed export.
- `assets/icon-512.png`, `assets/favicon-32.png`, `assets/apple-touch-icon.png` — raster per compatibilità (social share, iOS, fallback browser).

Uso: icona sempre su sfondo scuro (ha già il suo plate `#0A0A0F` incorporato). Wordmark richiede sfondo scuro per leggibilità (testo bianco).

## Componenti

- **Bottone primario:** gradient viola→blu, radius 8–10px, `box-shadow: 0 4px 20px rgba(124,58,237,0.3)`, hover = leggero fade opacità o lift `translateY(-2px)`.
- **Bottone secondario:** trasparente, bordo `rgba(255,255,255,0.08)`, hover bordo più chiaro.
- **Card:** `#13131A`, bordo 1px `rgba(255,255,255,0.08)`, radius 12–16px, hover lift + bordo viola.
- **KPI card:** come card, bordo sinistro 3px viola, valore in Syne 800 con gradient text-fill.
- **Badge/pill:** radius 100px (pillola), colore per categoria da tabella sopra.

## Spacing & Layout

- Border radius: 12px card, 8px bottone, 20px badge
- Padding card: 24px (landing) / 20px (dashboard, più denso)
- Max width contenuto: 1280px

## Dove è applicato oggi

- `landing.html` — riferimento originale, completo.
- `streamlit_app.py` — tema dark via `.streamlit/config.toml` (colori nativi Streamlit) + CSS custom per header, KPI card e bottoni; grafici Plotly ricolorati con `CATEGORY_COLORS`; Excel export con header viola.
- `.streamlit/config.toml` — tema nativo Streamlit (`base = "dark"`, `primaryColor = "#7C3AED"`, ecc.). Nota: esisteva già un `config.toml` con tema rosso in `Sniper/.streamlit/` (prototipo CLI vecchio, non collegato all'app attuale) — non toccato, ma da ripulire in futuro se quella cartella non serve più.

## Prossimi passi (non fatti oggi)

- Badge colorati per categoria dentro la tabella recensioni (oggi è testo semplice) — richiede sostituire `st.dataframe` con una tabella HTML custom.
- Dominio custom al posto di `*.up.railway.app` (impatta anche gli URL assoluti nei meta OG di `landing.html`, da aggiornare quando cambia).
- Eventuale icona App Store Shopify (richiede PNG 1200×1200 — `icon-512.png` può essere ri-esportato a risoluzione più alta dallo stesso `icon.svg`).
