# Reporte Anticorrupción Colombia — Análisis Automatizado
**Generado:** 2026-03-05 | **Datos:** SECOP I/II — datos.gov.co | **Código:** github.com/[usuario]/CorupCol

---

## ¿Qué es este sistema?

Un sistema de inteligencia artificial que analiza automáticamente todos los contratos públicos registrados en el Sistema Electrónico de Contratación Pública (SECOP I y II) para detectar patrones estadísticos asociados a corrupción, usando un grafo de relaciones entre funcionarios, empresas, contratos y entidades del Estado colombiano.

**Escala del análisis:** 32.2 millones de nodos · 52.2 millones de relaciones · 17.8 millones de contratos · SECOP I (pre-2015) + SECOP II (2015-2026) · $7,056 billones COP analizados.

---

## Metodología

- **Fuente de datos:** SECOP I (~21M contratos pre-2015) y SECOP II (~8.7M contratos 2015-2026), descargados directamente de datos.gov.co mediante la API pública de Socrata. Los datos son oficiales del Gobierno de Colombia.
- **Procesamiento:** Los contratos se convierten en un grafo de relaciones (Neo4j) con ~19 millones de nodos y ~31 millones de conexiones entre funcionarios, empresas, contratos y entidades. El sistema detecta automáticamente patrones matemáticos que la revisión manual humana no puede escalar a este volumen.
- **Limitaciones inherentes:** El análisis detecta *anomalías estadísticas*, no corrupción probada. Un patrón sospechoso requiere investigación jurídica para confirmar si hay conducta ilícita. Algunas anomalías corresponden a entidades estatales con comportamiento legítimo.

---

## Los 5 hallazgos más críticos

### 1. 🔴 Autocontratación directa reiterada — Miguel Ángel Sánchez Medina
**Cédula:** 80798446 | **3 contratos detectados** | **Valor total:** ~$1,956 millones | **Fechas:** 2025-2026

El señor Sánchez Medina aparece en el SECOP como **funcionario que ordena el pago** y simultáneamente como **representante legal de la empresa que lo recibe** en al menos 3 contratos: `CO1.PCCNTR.7709631` ($1,212M, marzo 2025), y dos contratos adicionales de enero 2026 ($408M y $336M). La reiteración del patrón en distintas fechas descarta el error administrativo — es un patrón sistemático. Prohibido por el artículo 8 de la Ley 80 de 1993 y tipificado como delito en el artículo 410 del Código Penal colombiano.

*Cómo verificarlo:* Buscar `CO1.PCCNTR.7709631` en [community.secop.gov.co](https://community.secop.gov.co) y comparar "Ordenador del gasto" con "Representante legal" del contratista.

---

### 2. 🔴 Autocontratación directa — José Álvaro Bedoya Orozco
**Cédula:** 10189420 | **Contrato:** CO1.PCCNTR.7495551 | **Valor:** $880 millones | **Fecha:** 14 febrero 2025

Mismo patrón: el ordenador del gasto y el representante legal del contratista son la misma persona. **Contrato de febrero 2025, activo y verificable públicamente.**

*Cómo verificarlo:* Buscar `CO1.PCCNTR.7495551` en Colombia Compra Eficiente.

---

### 3. 🟠 Ordenador recurrente — Diana Patricia Arboleda Ramírez → Congregación Capuchina
**Cédula ordenadora:** 52262161 | **Contratos:** 112 | **Valor total:** $75,854 millones

La funcionaria autorizó 112 contratos distintos con la misma entidad religiosa —Congregación de Religiosos Terciarios Capuchinos de Nuestra Señora de los Dolores— a lo largo del tiempo. La Ley 80 exige selección objetiva del contratista en cada proceso; 112 contratos consecutivos con el mismo proveedor sin evidencia de competencia real configura un patrón de favorecimiento sistemático que debe ser investigado por la Procuraduría.

*Cómo verificarlo:* Buscar la cédula `52262161` como ordenador del gasto en el buscador avanzado del SECOP II.

---

### 4. 🟠 Ordenador recurrente — Ricardo Jerez Soto → Javier Osvaldo Ramírez Martínez
**Cédula ordenadora:** 79415117 | **Contratos:** 103 | **Valor total:** $17,360 millones

Un funcionario público que en 103 ocasiones elige a la misma persona natural como contratista estadísticamente no puede estar realizando procesos de selección objetiva e independientes. Este patrón requiere verificar si existe relación familiar o societaria entre ambas personas.

*Cómo verificarlo:* Cruzar cédulas en el SIGEP (sigep.gov.co) y el RUP de Colombia Compra Eficiente.

---

### 5. 🟡 Prórroga de 5 años exactos — Vehículo Secretaría Distrital de Gobierno
**Contrato:** CO1.PCCNTR.1832328 | **Valor:** $133 millones | **Prórroga:** 1,825 días (5 años exactos)

Un contrato de comodato vehicular que se prorroga exactamente 5 años más allá de su plazo original sugiere que el bien nunca fue devuelto o que el contrato fue usado para evadir un proceso de compra formal. La Contraloría Distrital de Bogotá debe verificar la ubicación actual del vehículo.

*Cómo verificarlo:* Buscar `CO1.PCCNTR.1832328` en Colombia Compra Eficiente y solicitar a la Secretaría Distrital el acta de devolución del vehículo.

---

## Cómo verificar cualquier hallazgo

| Recurso | URL | Para qué sirve |
|---------|-----|----------------|
| SECOP II | community.secop.gov.co | Buscar contratos por ID o NIT |
| SECOP I | contratos.gov.co | Contratos anteriores a 2015 |
| RUP | colombiacompra.gov.co/rup | Representantes legales de empresas |
| SIGEP | sigep.gov.co | Información de servidores públicos |
| Contraloría GR | contraloria.gov.co | Denuncias fiscales |
| Procuraduría | procuraduria.gov.co | Denuncias disciplinarias |
| Fiscalía | fiscalia.gov.co | Denuncias penales |

---

## Limitaciones del análisis

- **No prueba corrupción:** Detecta anomalías estadísticas que *pueden* indicar irregularidades. Cada caso requiere investigación jurídica independiente antes de publicar.
- **Datos incompletos en SECOP I:** Los contratos anteriores a 2015 tienen menos campos y nombres de contratistas a menudo no digitalizados.
- **Falsos positivos estructurales:** Entidades como FINDETER o la Agencia Logística de las FF.MM. legítimamente contratan con muchas entidades — el sistema los marca por su comportamiento estadístico, no por irregularidades reales.
- **Sin acceso a flujos de dinero:** Este sistema analiza los contratos, no la ejecución del gasto. Un contrato puede ser legítimo en papel pero corrupto en su ejecución real.
- **Odebrecht no aparece:** Sus contratos en Colombia se firmaron antes de SECOP II y bajo nombres de consorcios que no registran "Odebrecht" como proveedor directo.

---

## Fuentes y código

- **Datos fuente:** datos.gov.co — SECOP I (`rpmr-utcd`), SECOP II Contratos (`jbjy-vk9h`), SECOP II Procesos (`p6dx-8zbt`)
- **Código fuente:** github.com/[usuario]/CorupCol — Licencia MIT — reproducible por cualquier investigador
- **Metodología inspirada en:** Bruno César (Brasil) — [Ver artículo](https://www.dn.pt/economia/ia-contra-a-corrupo-programador-brasileiro-cria-algoritmo-que-expe-os-esquemas-invisveis-do-estado)

---

*"Los datos son públicos. La corrupción no debería serlo."*
