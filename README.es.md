<p align="center">
  <img src="docs/logo-readme.svg#svgView(viewBox(0,0,64,47.5))" alt="Critique" width="72" />
</p>

<h1 align="center">Critique</h1>

<p align="center">
  <strong>Haz una pregunta. Recibe respuestas reales.</strong>
</p>

<p align="center">
  Critique es una plataforma de código abierto para recibir comentarios humanos,
  enfocados y estructurados, sobre tu proyecto. Comparte lo que estás construyendo,
  haz una sola pregunta concreta y recibe respuestas de personas que realmente
  ven tu proyecto.
</p>

<p align="center">
  <a href="https://github.com/BistaDinesh03/critique/actions/workflows/tests.yml"><img src="https://github.com/BistaDinesh03/critique/actions/workflows/tests.yml/badge.svg" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/BistaDinesh03/critique" alt="License: MIT" /></a>
</p>

<p align="center">
  <a href="https://critique.page/">Probar Critique</a> ·
  <a href="https://critique.page/discover">Explorar proyectos</a> ·
  <a href="https://github.com/BistaDinesh03/critique">Código fuente</a> ·
  <a href="https://github.com/BistaDinesh03/critique/issues">Issues</a> ·
  <a href="CONTRIBUTING.es.md">Contribuir</a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <strong>Español</strong>
</p>

> Este documento es la traducción al español de Critique. **La versión en inglés
> [README.md](README.md) es la fuente canónica**; si hay alguna discrepancia,
> prevalece la versión inglesa.

## Mira Critique en acción

Un recorrido de 62 segundos por el producto real: la página de inicio, el feed
de Discover, una página de proyecto y los comentarios que recibe el creador.

![GIF animado del recorrido de Critique: el titular de la página de inicio "Stop getting 'Looks good.'" sobre los botones Get feedback on my project y Give feedback to a builder, seguido de las tarjetas de proyecto del feed Discover](docs/videos/critique-overview-preview.gif)

**¿Quieres el recorrido completo? [Mira el video de 62 segundos.](https://dineshbista.com.np/critique/watch.html)**

El GIF de arriba es una vista previa de 12 segundos; el recorrido completo dura
62 segundos sin audio, y el reproductor de la página de visionado solo se inicia
cuando pulsas Play. ¿Prefieres el archivo original? Usa el [enlace MP4 directo](https://dineshbista.com.np/critique/videos/critique-overview.mp4)
(46.8 MB).<br />
Archivo original: [docs/videos/critique-overview.mp4](docs/videos/critique-overview.mp4)
— 1854×902, 30 fps, 62 s, H.264 MP4, 46.8 MB, incluido en este repositorio
para que forme parte de cada clonación, y reproducido desde la página de
visionado de GitHub Pages.

## El problema

Puedes pasar horas construyendo algo y aun así no saber si otra persona entiende
qué es, qué hace o por qué importa. Publicar «¿qué te parece?» suele merecer un
rápido «¡se ve bien!», cortés pero no accionable.

Quien construye se queda adivinando: ¿los usuarios entendieron el proyecto?
¿Lo usarían de verdad? ¿Qué debería mejorarse? Un comentario vago no responde
a ninguna de esas preguntas.

## La solución

Critique sustituye la adivinación por una señal clara. Comparte tu proyecto, haz
**una sola pregunta enfocada** — por ejemplo, *«¿Entenderías qué hace esto en
10 segundos?»* — y recibe comentarios estructurados de personas reales.

Una sola pregunta mantiene las respuestas comparables, y cada respuesta es una
señal sobre la que puedes actuar. Todos los comentarios provienen de personas
usando el sitio; Critique no contiene respuestas generadas por IA.

> Un proyecto. Una pregunta enfocada. Comentarios humanos reales.

## Cómo funciona

<table>
  <tr>
    <td align="center"><strong>1. Crea un proyecto</strong><br>Añade lo que construiste y para qué sirve.</td>
    <td align="center"><strong>2. Haz una sola pregunta enfocada</strong><br>Lo único que más quieres saber.</td>
    <td align="center"><strong>3. Compártelo con la gente</strong><br>Envía el enlace donde esté tu audiencia.</td>
    <td align="center"><strong>4. Aprende de comentarios estructurados</strong><br>Valoraciones en cada respuesta, más sugerencias escritas opcionales.</td>
  </tr>
</table>

## Características

- **Discover** — un feed público de proyectos que piden comentarios, ordenado de
  forma determinista (necesidad, frescura, calidad de la pregunta y más)
- **My Projects** — gestiona tus envíos y revisa resultados
- **Panel de resultados** — totales, barras de distribución y comentarios
  escritos de cada proyecto
- **Una sola pregunta enfocada** — cada proyecto hace una única pregunta, y dos
  preguntas de valoración fijas hacen que las respuestas sean fáciles de leer y comparar
- **Sugerencias escritas privadas** — asociadas al proyecto, visibles solo para su dueño
- **Compartir sencillo** — publica en X o Reddit, o copia el enlace, justo después
  de enviar o desde My Projects
- **Insignia dinámica** — un contador de respuestas en SVG, vivo, para tu README (abajo)
- **Opciones de inicio de sesión** — GitHub OAuth o un enlace mágico por correo sin contraseña
- **Consciente de la privacidad** — no se guardan direcciones IP en bruto, sin scripts
  de terceros, datos analíticos mínimos
- **Código abierto** — la implementación completa es pública bajo la licencia MIT,
  y la app funciona en local sin más pasos
- **Soporte SEO** — `robots.txt`, un `sitemap.xml` dinámico y metadatos de vista
  previa social en la página de inicio

## Modelo de comentarios

Cada respuesta responde a dos preguntas centrales.

<table>
  <tr>
    <th align="center">¿El proyecto es claro?</th>
    <th align="center">¿Lo usarías?</th>
  </tr>
  <tr>
    <td align="center">Muy claro<br>Bastante claro<br>Confuso</td>
    <td align="center">Sí<br>Tal vez<br>No</td>
  </tr>
</table>

> Los dueños del proyecto también pueden recibir sugerencias escritas opcionales,
> visibles solo para el dueño.

## Insignia de comentarios

Cada proyecto tiene una insignia SVG incrustable con su contador de respuestas vivo:

- **Endpoint de la insignia:** `GET /badge/{project_id}.svg` —
  `https://critique.page/badge/PROJECT_ID.svg`
- **Enlaza a:** la página del proyecto — `https://critique.page/project/PROJECT_ID`

```markdown
[![Critique](https://critique.page/badge/PROJECT_ID.svg)](https://critique.page/project/PROJECT_ID)
```

Sustituye `PROJECT_ID` por el ID de tu proyecto — el número de su URL en Critique.
El contador se genera desde la base de datos en cada petición, y más de 1000
se muestra como `1k+`.

## Prueba Critique

> ¿Tienes un proyecto del que no estás seguro? Haz una pregunta enfocada y mira
> qué opinan las personas reales.

<p align="center">
  <a href="https://critique.page/">
    <img src="static/og-image.png" alt='Stop getting "Looks good." — Ask one question. Get real answers. — critique.page' width="600" />
  </a>
</p>

[Abrir Critique](https://critique.page/) ·
[Explorar proyectos](https://critique.page/discover)

## Construido con

| Capa | Tecnología |
|---|---|
| Framework web | FastAPI (Python 3.11+) |
| Acceso a datos | SQLAlchemy 2.x |
| Almacenamiento | SQLite (desarrollo), PostgreSQL (producción) |
| Frontend | HTML/CSS/JavaScript puro — sin paso de compilación |
| Autenticación | GitHub OAuth y correo sin contraseña (Resend) |
| Despliegue | Render (`render.yaml`) |

## Arquitectura

```text
Browser — vanilla HTML/CSS/JavaScript
   │
   │  HTML pages + JSON API calls
   ▼
FastAPI — routes, auth, CSRF, rate limiting
   │
   │  SQLAlchemy ORM queries
   ▼
SQLAlchemy — models, validation, migrations
   │
   ▼
SQLite (development)  /  PostgreSQL (production)
```

El servidor sirve directamente las páginas de `frontend/` y expone una API JSON
bajo `/api/*`. No hay paso de compilación en el frontend ni capa de ORM más allá
de SQLAlchemy.

<details>
<summary>Estructura del repositorio</summary>

```text
backend/
  app/
    main.py                   App setup, page routes, /health, cache headers
    auth.py                   GitHub OAuth, email magic links, sessions
    csrf.py                   Double-submit-cookie CSRF protection
    config.py                 Environment-based settings
    database.py               Engine, table creation, additive migrations
    models.py                 SQLAlchemy models
    schemas.py                Pydantic request/response validation
    ranking.py                Deterministic Discover ranking
    rate_limit.py             In-memory per-endpoint rate limiting
    analytics.py              Event storage and visitor cookie
    email.py                  Magic-link email delivery (Resend)
    routes_projects.py        Project CRUD and Discover feed
    routes_responses.py       Feedback submission and listing
    routes_results.py         Aggregated results for owners
    stats.py                  Aggregate feedback statistics
    routes_badge.py           GET /badge/{id}.svg
    routes_stats.py           GET /api/stats
    routes_analytics.py       Event allowlist, /api/analytics/track
    routes_analytics_dashboard.py  Owner analytics endpoint
    routes_seo.py             robots.txt and sitemap.xml
  tests/                      pytest suite (API, security, frontend render)
frontend/                     HTML pages (vanilla JS, no build step)
static/                       CSS, JS, logos, favicon
docs/                         Setup guides and API reference
render.yaml                   Deployment config
```

</details>

## Primeros pasos

**Requisitos:** Python 3.11+, Git. Node.js (cualquier versión reciente) solo se
necesita para las pruebas de renderizado del frontend — se omiten si `node` no
está en tu PATH.

```bash
git clone https://github.com/BistaDinesh03/critique.git
cd critique
python -m venv .venv
```

Activa el entorno virtual:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instala las dependencias, crea tu archivo de entorno e inicia el servidor:

```bash
pip install -r requirements.txt
cp .env.example .env    # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000. Las tablas de SQLite se crean automáticamente al
arrancar — no hay un paso de migración aparte.

La autenticación es opcional para navegar en local; iniciar sesión solo es
necesario para enviar o gestionar proyectos. La configuración de GitHub OAuth y
de los enlaces mágicos por correo (incluidos los valores `RESEND_API_KEY` y
`EMAIL_FROM` que necesita el inicio de sesión por correo) está en
[docs/github-oauth-setup.md](docs/github-oauth-setup.md).

## Variables de entorno

Copia `.env.example` a `.env` y configura lo que necesites. `.env` está en
gitignore — nunca subas credenciales reales.

| Variable | Propósito | Por defecto / notas |
|---|---|---|
| `APP_ENV` | `development` o `production` | `development` |
| `APP_URL` | URL base pública | `http://127.0.0.1:8000` |
| `SECRET_KEY` | Firma los tokens de sesión y el estado OAuth | Sin valor por defecto — genera: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Cadena de conexión a la base de datos | `sqlite:///./critique.db`; usa PostgreSQL en producción |
| `GITHUB_CLIENT_ID` | ID de cliente de la app OAuth de GitHub | Opcional — habilita el inicio de sesión con GitHub |
| `GITHUB_CLIENT_SECRET` | Secreto de la app OAuth de GitHub | Opcional |
| `GITHUB_REDIRECT_URI` | URL de callback de OAuth | `http://127.0.0.1:8000/auth/callback` |
| `SESSION_COOKIE_SECURE` | Pon `true` detrás de HTTPS | `false` |
| `SESSION_COOKIE_MAX_AGE` | Duración de la sesión en segundos | Opcional; `604800` (7 días) |
| `RESEND_API_KEY` | Clave de API de Resend para los enlaces mágicos | Opcional — habilita el inicio de sesión por correo |
| `EMAIL_FROM` | Dirección de origen de los enlaces mágicos | Opcional; verificada en Resend |

## Base de datos

El desarrollo usa SQLite (`critique.db`, en gitignore) — el valor por defecto
cuando `DATABASE_URL` no está definido. Al arrancar la app ejecuta `init_db()`,
que crea las tablas y aplica migraciones ligeras y aditivas tanto para SQLite
como para PostgreSQL, así que no hay un paso de migración aparte. La producción
usa PostgreSQL, con `DATABASE_URL` proporcionado por el entorno de alojamiento y
fuera del repositorio.

## Pruebas

```bash
cd backend
python -m pytest tests/ -q
```

Actualmente pasan 501 pruebas. La suite cubre el comportamiento de la API, CSRF,
limitación de tasa, comprobaciones de propiedad, reglas de privacidad, ranking,
XSS, validación analítica, flujos de autenticación, endpoints de SEO y el
renderizado del frontend mediante un arnés DOM basado en Node (se omite si no
hay Node.js disponible).

## API

La API JSON está documentada en [docs/api.md](docs/api.md). Categorías principales:

- **Autenticación** — `/auth/*`: GitHub OAuth, enlaces mágicos por correo, comprobación de sesión, token CSRF
- **Proyectos** — `/api/projects/`: crear, feed de Discover, listado del dueño, detalles, borrar
- **Comentarios** — `/api/projects/{id}/responses`: enviar y leer respuestas
- **Resultados** — `/api/projects/{id}/results`: agregados para todos, sugerencias escritas para el dueño
- **Insignia** — `/badge/{id}.svg`: contador de respuestas vivo
- **Estadísticas y analítica** — `/api/stats`, `/api/analytics/track`
- **SEO** — `robots.txt`, `sitemap.xml`

Con la app en ejecución, la documentación interactiva se sirve en `/docs`
(Swagger UI) y `/redoc`, y hay una comprobación de salud en `GET /health`.

Ejemplo — listar los proyectos que buscan comentarios ahora (público, sin
autenticación):

```bash
curl -s https://critique.page/api/projects
```

La respuesta está paginada (`items`, `total`, `page`, `page_size`,
`total_pages`), y cada elemento incluye el `title` del proyecto, su
`question_text` y un `response_count` vivo.

## Seguridad y privacidad

Critique está diseñado pensando en la seguridad y la privacidad:

| Protección | Comportamiento |
|---|---|
| **Protección CSRF** | Cookie de doble envío con una cabecera `X-CSRF-Token` en todas las peticiones que cambian estado; las sesiones viven en una cookie `HttpOnly`, `SameSite=Lax`, con `Secure` cuando `SESSION_COOKIE_SECURE=true` (Render lo define) |
| **Limitación de tasa** | Autenticación y inicio de sesión por correo, creación y borrado de proyectos, envío de comentarios y analítica |
| **Validación de entrada** | Validación Pydantic en cada cuerpo de petición, con patrones estrictos para los valores de comentario |
| **Protección XSS** | La salida controlada por el usuario se escapa en el frontend y está cubierta por pruebas de regresión XSS |
| **Comprobaciones de autenticación y propiedad** | La propiedad del proyecto se verifica en el servidor a partir de la sesión en cada mutación, nunca desde cabeceras proporcionadas por el cliente |
| **Comentarios escritos privados** | Las sugerencias se devuelven solo al dueño del proyecto |
| **Manejo seguro de redirecciones** | Los valores `return_to` del inicio de sesión se validan contra una lista de rutas locales |
| **Secretos por entorno** | Las credenciales provienen de variables de entorno y nunca se guardan en el repositorio |
| **Analítica mínima** | Eventos validados contra una lista permitida en el servidor; sin scripts de terceros; sin direcciones IP en bruto (solo hashes SHA-256 para detectar duplicados) |

[SECURITY.md](SECURITY.md) enumera el comportamiento completo y explica cómo
reportar una vulnerabilidad.

## Despliegue

El despliegue está configurado en `render.yaml`: un servicio web de Render con una
base de datos PostgreSQL. `APP_ENV=production` y `SESSION_COOKIE_SECURE=true` se
definen allí; los secretos — `DATABASE_URL`, `SECRET_KEY`, credenciales OAuth y
claves de correo — están marcados como `sync: false` y se introducen manualmente
en el panel de Render, sin guardarse nunca en el repositorio. Consulta
`render.yaml` para la lista completa de variables esperadas.

## Analítica del producto

> **Instantánea de analítica** — totales de eventos en un momento dado. No se
> indicó el periodo de medición.

**Titular:** 1.443 páginas vistas · 263 visitantes únicos · 232 vistas de
proyecto · 20 envíos de comentarios.

**Embudo:** 232 vistas de proyecto → 92 inicios de comentarios → 65 intentos de
envío → 20 envíos correctos.

![Instantánea de analítica del producto de Critique](docs/analytics-snapshot.svg)

Estos totales son una instantánea registrada — **no son analítica en vivo**; la
cifra no se actualiza automáticamente. Todos los porcentajes son **ratas de
eventos** (un número de eventos dividido por otro), no tasas de conversión de
usuarios únicos, y un solo visitante puede generar varios eventos.

> **Existen dos instantáneas y difieren.** Esta cifre y el
> [informe de analítica en HTML](docs/analytics-snapshot.html) se proporcionaron
> en momentos distintos y no llevan los mismos totales (1.443 frente a 1.582
> páginas vistas). Ninguna indicó un periodo de medición, así que no puede
> fecharse ni conciliarse aquí. Ambos conjuntos de datos se dejan tal cual se
> recibieron — esto está registrado en el
> [issue #23](https://github.com/BistaDinesh03/critique/issues/23) para una
> resolución adecuada.

## Contribuir

Son bienvenidas las contribuciones, los informes de errores, las mejoras de
documentación y los comentarios de producto bien razonados. Un buen punto de
partida es un issue con la etiqueta
[`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue).

1. Haz un fork del repositorio
2. Crea una rama para tu cambio
3. Haz tus cambios y añade pruebas
4. Ejecuta la suite de pruebas
5. Abre una solicitud de incorporación

[CONTRIBUTING.es.md](CONTRIBUTING.es.md) tiene las pautas completas (la versión
canónica en inglés es [CONTRIBUTING.md](CONTRIBUTING.md)), y
[SECURITY.md](SECURITY.md) explica cómo reportar vulnerabilidades.

**¿Buscas algo en lo que trabajar?** Empieza por el plan curado en
[docs/issue-roadmap.md](docs/issue-roadmap.md) — 50 issues revisados con el
problema, el alcance, los criterios de aceptación, la dificultad y los archivos
relevantes detallados para cada uno. Los issues también están etiquetados por
área (`frontend`, `backend`, `tests`, `accessibility`, `security`,
`performance`), y las preguntas son bienvenidas en el
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) antes de empezar.

También se anima a los colaboradores a dedicar algo de tiempo a usar el propio
Critique — enviar un proyecto o dar comentarios — antes de su primera solicitud
de incorporación. [CONTRIBUTING.es.md](CONTRIBUTING.es.md) explica la pauta y sus
excepciones; es una forma de entender el producto, no una barrera para contribuir.

## Código abierto

Critique es código abierto bajo la licencia MIT. La implementación completa —
backend, frontend, pruebas y configuración de despliegue — está en
[github.com/BistaDinesh03/critique](https://github.com/BistaDinesh03/critique).
Issues y solicitudes de incorporación son bienvenidos.

## Licencia

MIT — consulta [LICENSE](LICENSE).
