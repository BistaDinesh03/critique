# Contribuir a Critique

¡Gracias por tu interés en contribuir! Critique busca ser sencillo y mantenible.

> Este documento es la traducción al español de la guía de contribución de Critique.
> **La versión canónica en inglés es [CONTRIBUTING.md](CONTRIBUTING.md)**; si hay
> alguna discrepancia, prevalece la versión inglesa. Las secciones más profundas,
> como los scripts de mantenimiento (`scripts/review_pr.py`, `scripts/contributor.py`),
> están solo en la versión inglesa.

## Primeros pasos

1. Haz un fork del repositorio
2. Clona tu fork
3. Crea una rama para tu cambio
4. Haz tus cambios
5. Ejecuta las pruebas
6. Envía una solicitud de incorporación

### Configura un entorno de desarrollo

```bash
git clone https://github.com/YOUR_USERNAME/critique.git
cd critique
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
cd backend
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000. Los proveedores de autenticación son opcionales para
navegar en local — consulta [docs/github-oauth-setup.md](docs/github-oauth-setup.md)
si tu cambio afecta a flujos con sesión iniciada.

### Ejecuta las pruebas

```bash
cd backend
python -m pytest tests/ -q
```

Resultado esperado: **346 passed**. Instala primero [Node.js](https://nodejs.org) —
las pruebas de renderizado del frontend necesitan `node` en el PATH y se omiten
sin él.

Para un ciclo de retroalimentación más rápido, ejecuta un solo archivo de pruebas,
una función concreta, o las que coincidan con una palabra clave:

```bash
python -m pytest tests/test_main.py -q
python -m pytest tests/test_main.py::test_health_check -q
python -m pytest tests/ -q -k health_check
```

## Pautas de desarrollo

### Manténlo sencillo

Critique evita la complejidad a propósito. Antes de añadir algo, pregúntate:

- ¿Esto resuelve un problema real?
- ¿Puede hacerse con menos dependencias?
- ¿Necesita estar en la V1?

### Estilo de código

- Sigue los patrones existentes
- Usa nombres con significado
- Mantén las funciones pequeñas
- Comenta solo donde sea útil
- Sin código muerto

### Pruebas

- Ejecuta todas las pruebas antes de enviar
- Añade pruebas para la funcionalidad nueva
- Las pruebas deben pasar sin fallos

### Solicitudes de incorporación

- Mantén los PR enfocados y pequeños
- Describe qué cambiaste y por qué
- Enlaza cualquier issue relacionado
- Sé respetuoso y paciente

## Encuentra algo en lo que trabajar

Los issues abiertos con la etiqueta
[`good first issue`](https://github.com/BistaDinesh03/critique/labels/good%20first%20issue)
son un buen punto de partida. ¿Tienes una pregunta sobre el código o sobre un
enfoque? Pregunta en el [issue #1](https://github.com/BistaDinesh03/critique/issues/1)
antes de empezar — ninguna pregunta es demasiado pequeña.

Los issues también están etiquetados por área — `frontend`, `backend`, `tests`,
`accessibility`, `security`, `performance` — así que puedes filtrar hacia trabajo
que encaje con lo que ya sabes, o estirarte deliberadamente hacia algo nuevo.

Un plan curado y revisado de 50 issues vive en
[docs/issue-roadmap.md](docs/issue-roadmap.md). Cada entrada indica su dificultad,
el problema que resuelve y qué archivos toca. Si buscas algo concreto, empieza ahí.

## Cómo trabajamos juntos en Critique

Critique es un sitio donde quien construye hace una sola pregunta enfocada y otras
personas la responden. Se pide a los contribuyentes que usen el producto de la misma
manera en que pedirían a otros usar el suyo — es la forma más rápida de entender para
qué existe el proyecto.

Para una contribución de código típica:

1. **Reclama el issue.** Comenta en el issue para decir que vas a trabajar en él.
   Esto evita que dos personas hagan el mismo trabajo, y permite al mantenimiento
   orientarte pronto si el enfoque necesita replantearse.
2. **Usa Critique una vez.** Envía un proyecto con una pregunta enfocada, o da
   comentarios útiles en el proyecto de otra persona. No es una auditoría — es para
   que tu primera solicitud de incorporación nazca del producto y no solo del código.
3. **Haz fork y crea rama.** Haz un fork del repositorio, crea una rama e implementa
   el issue.
4. **Prueba, y usa el producto si aplica.** Ejecuta las pruebas pertinentes. Si tu
   cambio altera algo que un visitante vería, pruébalo en el propio Critique y pregunta
   a otros constructores si funciona.
5. **Abre la solicitud de incorporación.** Describe qué cambiaste, por qué, y las
   pruebas exactas que ejecutaste.

### Excepciones, dichas claro

Esta pauta es deliberadamente ligera, y **no** es una barrera. No se aplica a:

- **Correcciones de documentación, accesibilidad y seguridad** — ayudan a personas que
  no necesariamente pueden usar el sitio como los demás, y exigir participación previa
  en el producto sería una barrera justo en el lugar equivocado.
- **Tu primera contribución** — una contribución basta. Nadie es requerido a participar
  de forma repetida para seguir siendo bienvenido.
- **Informes de errores y triaje de issues** — son contribuciones en sí mismos.

No hay costo para participar, nunca se pide ningún pago, y no se necesita información
personal más allá de una cuenta de GitHub. Nada en GitHub puede verificar que hayas
usado el sitio, y no te pediremos que lo demuestres — ese paso existe para ayudarte,
no para vigilarte.

## Comunicación

- Sé amable y constructivo
- Asume buenas intenciones
- Céntrate en el trabajo, no en la persona

## Informar de un problema de seguridad

Por favor, no abras un issue público para una vulnerabilidad. Sigue el proceso privado
descrito en [SECURITY.md](SECURITY.md), que también documenta el comportamiento
relativo a la seguridad del proyecto. Para lo que no sea una vulnerabilidad, el
[issue #1](https://github.com/BistaDinesh03/critique/issues/1) es un buen lugar
para preguntar.

## Licencia

Al contribuir, aceptas que tu trabajo se licencie bajo la licencia MIT.
