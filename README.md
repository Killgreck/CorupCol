# CorupCol: Sistema Anticorrupción Colombia 🔍🇨🇴

![Estado](https://img.shields.io/badge/Estado-Prototipo%20Activo-success)
![Datos Actualizados](https://img.shields.io/badge/Datos_Analizados-2026--03--05-blue)
![Registros](https://img.shields.io/badge/Registros-52M%2B-orange)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

Este proyecto rastrea, estructura y analiza más de **52 millones de contratos públicos** del Estado colombiano (SECOP I y II) convirtiéndolos en un enorme grafo paramétrico para detectar automáticamente patrones anómalos de contratación y posibles casos de corrupción.

Inspirado directamente en referentes globales de periodismo de datos y auditoría cívica asistida por IA (como el trabajo de [Bruno César en Brasil](https://www.dn.pt/economia/ia-contra-a-corrupo-programador-brasileiro-cria-algoritmo-que-expe-os-esquemas-invisveis-do-estado)).

---

## 📸 Dashboard de Alertas

El proyecto genera un dashboard público estático que muestra los casos más extremos detectados por los algoritmos:

*[Inserte screenshot del dashboard aquí]*
*(Ver carpeta `/dashboard` para la UI)*

---

## 🚨 Hallazgos Principales (Última corrida)

A través de consultas Cypher sobre Neo4j, el sistema aisló los siguientes patrones críticos:

* **Carruseles de Contratistas**: Entidades privadas que han creado enjambres contractuales logrando más de 100+ contratos simultáneos a través de decenas de agencias estatales distintas, diluyendo los radares de supervisión.
* **Repeticiones Sospechosas (Nepotismo/Monopolio)**: Cientos de casos donde un mismo Ordenador del Gasto (funcionario) le adjudicó repetidamente más de 50+ contratos al mismo individuo o empresa.
* **Sobrecostos de Tiempo Extremos**: Contratos que han acumulado más de **1.000 días (3 años)** en prórrogas adicionales (Otrosí) frente a lo que se planificó inicialmente, inmovilizando recursos públicos.

Para leer el informe detallado en lenguaje no técnico, visite: `reports/resumen_ejecutivo.md`.

---

## 🏗️ ¿Cómo funciona?

El pipeline de extracción y procesamiento se rige por la siguiente arquitectura:

```
FUENTES PÚBLICAS (datos.gov.co, SECOP)
        │
        ▼
  NORMALIZACIÓN MASIVA
  Limpieza de nombres, NITs, cédulas. Conversión de texto plano.
        │
        ▼
   GRAFO NEO4J
   Nodos: 18.5 Millones (Funcionarios | Empresas | Entidades)
   Aristas: 29.7 Millones (FIRMÓ | ORDENÓ | GANÓ | SOBRECOSTO)
        │
        ▼
  DETECCIÓN DE ANOMALÍAS
  Queries Cypher filtran topologías estadísticas sospechosas.
        │
        ▼
   DASHBOARD PÚBLICO
   Archivos JSON estáticos consumidos por UI en HTML/JS puro.
```

---

## 🚀 Instalación y Prueba Local

Si deseas correr el dashboard público localmente para visualizar los datos:

```bash
# 1. Clonar el repo
git clone https://github.com/usuario/CorupCol.git
cd CorupCol

# 2. Generar y optimizar los datos desde el reporte en crudo
python3 scripts/preparar_datos_publicos.py

# 3. Lanzar el servidor local
cd dashboard
python3 -m http.server 8080

# 4. Abre en tu navegador favorito
# http://localhost:8080
```

---

## 🤝 Contribuir

¡La corrupción ama la oscuridad, ayúdanos a encender la luz!
Aceptamos Pull Requests para:
- Implementar nuevas _queries_ Cypher para detectar fraccionamientos de contratos (múltiples contratos pequeños justo debajo del tope de licitación).
- Conexiones con nuevas fuentes de datos (RUES, SIGEP, Rama Judicial).
- Mejoras visuales en el grafo de D3.js.

Revisa los issues abiertos del repositorio para conocer el roadmap del proyecto.

---

## ⚖️ Descargo de Responsabilidad

Este software genera **alertas estadísticas anómalas**, no sentencias judiciales. Un volumen alto de contratos o adiciones en tiempo puede estar debidamente justificado por la ley en casos de fuerza mayor, exclusividad tecnológica o monopolios naturales. Los datos son consumidos tal y como los reportan las entidades en Datos Abiertos. Todo hallazgo requiere verificación periodística o de entes de control territorial/nacional.

**Licencia MIT.** Siéntete libre de clonarlo, auditar tu municipio y publicar la verdad.
