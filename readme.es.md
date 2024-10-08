[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/maiktreya/rental-scrapers/blob/main/readme.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/maiktreya/rental-scrapers/blob/main/readme.es.md)

---

# 🏠 Scrapers de Alquiler para el Empoderamiento de Inquilinas

Este proyecto está diseñado para empoderar a los inquilinos y usuarios a pequeña escala proporcionando scrapers accesibles para listados de propiedades en Airbnb e Idealista. Con el aumento de los precios de la vivienda y prácticas de alquiler injustas, el acceso a los datos es crucial. Esta herramienta permite a los individuos recopilar datos sobre propiedades disponibles sin estar sujetos a los habituales listados multi-página opacos plagados de anuncios.

**Nota:** No está destinado para su uso a escala corporativa ni para explotar los datos de propiedades a gran escala. Los scrapers están diseñados para **uso personal**, centrándose en el derecho a la información para las inquilinas.

## ⚙️ Instalación

Para los no expertos, aquí tienes una forma sencilla de comenzar con un entorno virtual de Python con Ubuntu o usando WSL con Windows:

1. **Instalar Python:** Asegúrate de tener [Python 3.7+](https://www.python.org/downloads/) instalado en tu equipo.

2. **Crear un entorno virtual:**

   En el directorio raíz del proyecto (donde se encuentra este archivo README), ejecuta los siguientes comandos para crear y activar un entorno virtual llamado `env`:

   ```bash
   python -m venv env
   source env/bin/activate
   ```

3. **Instalar las dependencias requeridas:**

   Debes instalar Chrome junto a su webdriver y dependencias necesarias:

   ```bash
   sudo bash lib/installChromeDriver.sh
   ```

   Una vez activado el entorno virtual, instala los paquetes necesarios ejecutando:

   ```bash
   pip install -r lib/requirements.txt
   ```

   ¡Ahora tu entorno está listo para ejecutar los scrapers!

## 🎯 Objetivo del Proyecto

El objetivo de este proyecto es empoderar a las personas afectadas por el aumento de los costos de vivienda, ofreciéndoles una forma fácil de acceder a listados públicos de propiedades y hacer el mercado de alquiler más transparente. Simplifica el scraping sin las complejidades corporativas (como las solicitudes paralelas o proxies), manteniéndose enfocado en usos personales y a pequeña escala.

## 🛠️ Funcionalidades Clave

- Scrapea listados de Airbnb (corto, medio y largo plazo).
- Scrapea listados de propiedades de Idealista tanto de venta como de alquiler.
- Maneja la paginación y guarda los datos en formato CSV o JSON.
- Soporta retrasos personalizables para evitar bloqueos.
- Enfoque simple y minimalista adaptado a usuarios personales.

## 🚀 Uso

### Requisitos Previos

- Python 3.7+
- ChromeDriver para scraping de Airbnb (a través de Selenium, el script `lib/installChromeDriver.sh` automatiza la instalación)
- Entorno virtual con los paquetes requeridos (`httpx`, `selenium`, `parsel`, `argparse`, `pandas`, `beautifulsoup4`)

### Ejecutar el Scraper de Airbnb

Para scrapear listados de Airbnb:

```bash
python src/airbnb_scraper.py --url "AIRBNB_URL" --format csv
```

### Ejecutar el Scraper de Idealista

Para scrapear listados de Idealista:

```bash
python src/idealista_scraper.py --url "IDEALISTA_URL" --delay 2 --format csv
```

### Ejecutar Todos los Scrapers

Puedes ejecutar todos los scrapers usando el script Bash proporcionado:

```bash
bash src/run_scraper.sh # empty for default CSV
bash src/run_scraper.sh json # get JSON files instead
bash src/run_scrsper.sh both # get both file types as output files
```

### Resultados

Los datos scrapeados se guardarán en el directorio `out/` en formatos JSON o CSV.

### Programar un trabajo cron automatizado

Puede crear un trabajo cron en Ubuntu para ejecutar su scraper de Python diariamente a las 2:00 a. m. con los siguientes pasos:

1. **Abrir el archivo crontab para editarlo:**

   Abre la terminal y escribe:

   ```bash
   crontab -e
   ```

2. **Añadir el cron job:**

   En el editor que se abre, añade la siguiente línea (donde path es la ruta al directorio rental-scrapers):

   ```bash
   0 2 * * * $PATH/rental-scrapers/src/run_scraper.sh >> $PATH/rental-scrapers/out/scraper.log 2>&1
   ```

   - `0 2 * * *` establece el cron job para que se ejecute diariamente a las 2:00 AM.
   - `$PATH/rental-scrapers/src/run_scraper.sh` ruta del script principal.
   - `>> $PATH/rental-scrapers/out/scraper.log 2>&1` asegura que tanto la salida como cualquier error se registren en un archivo log.

3. **Guardar y salir:**

   Después de añadir la línea, guarda el archivo y sal del editor. Ahora tu cron job se ejecutará diariamente a las 2:00 AM.

Asegúrate de que tu script sea ejecutable y que todos los permisos necesarios estén correctamente configurados. También recuerda modificar la variable `$BASE_PATH` en el script `src/run_scraper.sh` por la ruta local adecuada.

---

## 💼 Aviso Legal

Esta herramienta se proporciona únicamente para uso personal y con fines informativos. Está destinada a dar acceso justo a los datos de vivienda a los usuarios a pequeña escala. Los desarrolladores no son responsables del mal uso de esta herramienta ni de las consecuencias legales que puedan surgir por realizar scraping a gran escala o con fines comerciales. Los usuarios deben asegurarse de cumplir con los términos de servicio de los sitios web que scrapean.

## 🔒 Licencia

Este proyecto está licenciado bajo la Licencia Pública General de GNU (GPL-3). Consulta la licencia completa [aquí](https://www.gnu.org/licenses/gpl-3.0.en.html).

---
