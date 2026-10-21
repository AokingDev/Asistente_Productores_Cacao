# Inventario de Fuentes y Levantamiento de Información (RAG)

## 1. Inventario de Fuentes Oficiales

La base de conocimiento de nuestro modelo RAG está construida estrictamente con documentos oficiales y validados para el cultivo de cacao en Ecuador.

| Documento | Origen Oficial | URL | Vigencia | Formato | Fragmentación Prevista (Chunking) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Guía para facilitar el aprendizaje en el manejo integrado del cultivo de cacao** | INIAP | [Enlace Repositorio](https://repositorio.iniap.gob.ec/bitstreams/ca109fb0-20aa-4946-82be-5deb55b83a2f/download) | Actual | PDF | Fragmentación por enfermedad/plaga (síntomas, daños y tipo de control). Tamaño de chunk mediano (aprox. 500 tokens) con 15% de overlap. |
| **Manual del Cultivo de Cacao en Ecuador** | MAG / SICA | [Enlace Repositorio](http://canacacao.org/wp-content/uploads/Manual-cultivo-Cacao-Ecuador.pdf) | Actual | PDF | Fragmentación por labor cultural (Poda, Riego, Fertilización, Cosecha). Tamaño de chunk grande (aprox. 800 tokens) para retener el contexto de los procesos. |
| **Catálogo de cultivares de cacao en Ecuador** | INIAP | [Enlace Repositorio](https://repositorio.iniap.gob.ec/bitstreams/f92da475-087c-49e9-89f7-1770a71a4ff4/download) | Actual | PDF | Fragmentación estructural (un chunk por cada clon/variedad) para evitar que la IA cruce características de rendimiento o tolerancia de un clon con otro. |

---

## 2. Levantamiento Real

*Resultados de la recopilación de dudas frecuentes de productores cacaoteros en campo, que el asistente deberá ser capaz de responder utilizando la base documental.*

1. **Identificación de Moniliasis:** ¿Cómo identifico si las manchas de mis mazorcas son por Moniliasis?
2. **Control de Escoba de Bruja:** Mis árboles tienen ramas engrosadas, verdes y deformes como escobas. ¿Qué método de control cultural debo aplicar?
3. **Pudrición Negra:** ¿Qué causa que las mazorcas se pongan negras y duras, y cómo lo prevengo?
4. **Mal del Machete:** Si veo hojas marchitas de color café rojizo que no se desprenden de la rama, ¿es Mal de Machete?
5. **Calendario de Podas:** ¿En qué época del año o mes es recomendable hacer la poda de mantenimiento para el cacao?
6. **Manejo de Residuos:** ¿Qué debo hacer exactamente con las mazorcas enfermas que tumbo al suelo durante la poda fitosanitaria?
7. **Control de Pulgones:** Tengo pulgones y hormigas en los cojinetes florales, ¿qué control químico y en qué dosis recomienda el INIAP?
8. **Chinche Amarillo (Monalonion):** ¿Qué síntomas presenta el ataque de la mosquita del cacao o chinche amarillo en los frutos pequeños?
9. **Desinfección:** ¿Cómo debo desinfectar mis herramientas para no propagar enfermedades de un árbol a otro?
10. **Nutrición:** ¿Qué tipo de fertilizante complementario necesita mi plantación si las hojas están amarillentas?
11. **Manejo de Sombra:** ¿Cómo debo manejar el porcentaje de sombra para evitar que aumente la población del chinche de la mazorca?
12. **Selección de Clones:** ¿Cuáles son los clones desarrollados por el INIAP que tienen mayor resistencia o tolerancia a la Moniliasis?
13. **Manejo de Malezas:** ¿Qué problemas me traen las malezas trepadoras en los árboles jóvenes y cómo las controlo?
14. **Poda de Formación:** Mi plantación tiene apenas un año, ¿cuántos ejes debo dejarle a la planta durante la poda de formación si es un clon?
15. **Clon EET 103:** Voy a renovar mi finca, ¿qué rendimiento y características de tolerancia a enfermedades tiene el clon EET 103?
