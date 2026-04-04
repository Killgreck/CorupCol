# Resumen Ejecutivo: Anomalías en Contratación Pública (SECOP I y II)

**Fecha de Análisis:** 2026-04-04
**Registros Analizados:** Más de 52 millones
**Valor Total Rastreable:** $7.056,9B COP

## ¿Qué es esto?
Este informe es el resultado del cruce masivo de toda la contratación pública estatal con modelos de detección de anomalías mediante grafos de conocimiento. No acusa de delitos, pero señala comportamientos estadísticamente atípicos que merecen escrutinio público y control fiscal.

## Metodología
- Se construyó una red interconectada (grafo) con todas las entidades, contratistas y representantes procesados a partir de los datos públicos del SECOP.
- Se aplicaron algoritmos para rastrear múltiples contratos hacia los mismos nodos finales.
- Se aislaron patrones que típicamente preceden actos de corrupción (carruseles, nepotismo, fraccionamiento).

## 5 Hallazgos más críticos

1. **Carrusel Inter-Agencia Extremo**: La entidad o contratista `Ministerio De Hacienda Y Credito Publico` firmó `23` contratos a través de `19` agencias distintas por un valor total de **$41,5B COP**. Este nivel de dispersión suele usarse para eludir controles jerárquicos.
   
2. **Nepotismo / Favoritismo Direccionado**: El funcionario `Diana Patricia Arboleda Ramirez` ha aprobado o adjudicado `112` contratos recurrentes a `Congregacion De Religiosos Terciarios Capuchinos De Nuestra Señora De Los Dolores` por **$0,1B COP**. 
   
3. **Prórrogas Excesivas (Sobrecostos de tiempo)**: El contrato `CO1.PCCNTR.1832328` otorgado a `Secretaria Distrital De Gobierno 1` tiene `1825` días de prórroga registrados, lo que desvirtúa la planeación original por un valor de **$0,0B COP**.

*(Revise los anexos CSV para el Top 50 de cada categoría).*

## ¿Cómo verificar esto (Para periodistas)?
1. **Carrusel**: Busque el NIT `899999090` en el SECOP II Institucional o en el portal Oceano de la Contraloría para comprobar el enjambre de contratos.
2. **Nepotismo**: Verifique en el SIGEP las fechas de posesión del ordenador del gasto `52262161` frente a las fechas de los contratos.
3. **Sobrecostos**: Ingrese el ID del proceso `CO1.PCCNTR.1832328` en el buscador de SECOP II y evalúe los documentos "Modificación" o "Otrosí".

## Limitaciones
- **NO todo es corrupción**: Algunos proveedores únicos de software o insumos médicos justificados parecen anomalías en volumen (por ej. empresas de servicios públicos o monopolios naturales).
- Existen casos de homonimia en nombres propios si no van acompañados del documento de identidad.

---
*Datos Abiertos de Colombia - Este es un proyecto open source inspirado en auditoría cívica con IA.*
