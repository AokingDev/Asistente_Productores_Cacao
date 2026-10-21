# Fuentes oficiales descargadas (`data/raw/`)

Documentos base de la base de conocimiento del RAG. **Los PDF no se suben a Git** porque en conjunto pesan ~70 MB
(el catálogo de cultivares supera por sí solo el límite de 20 MB del ZIP de entrega). Se descargan y verifican con:

```bash
python scripts/descargar_fuentes.py
```

Fecha de descarga y verificación: **21 de octubre de 2026**.

| Archivo local | Título | Institución / año | Págs. | Tamaño | Temas (metadato `tema`) | Enlace |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| `INIAP_guia_manejo_integrado_cacao.pdf` | Guía para facilitar el aprendizaje en el manejo integrado del cultivo de cacao (*Theobroma cacao* L.) | INIAP – EET Pichilingue, 2015 (edición abril 2017) | 162 | 18,1 MB | enfermedades, plagas, poda, manejo, fertilización, poscosecha | [repositorio.iniap.gob.ec](https://repositorio.iniap.gob.ec/server/api/core/bitstreams/ca109fb0-20aa-4946-82be-5deb55b83a2f/content) |
| `INIAP_manual76_cultivo_cacao_amazonia.pdf` | Manual No. 76 – Cartilla del cultivo de cacao (Amazonía Norte) | INIAP – EE Central de la Amazonía (s. f.) | 25 | 6,7 MB | suelo y clima, variedades, propagación, vivero, siembra, sombra, manejo, poscosecha | [canacacao.org](http://canacacao.org/wp-content/uploads/Manual-cultivo-Cacao-Ecuador.pdf) |
| `INIAP_catalogo_cultivares_cacao.pdf` | Catálogo de cultivares de cacao en Ecuador (Boletín Técnico No. 449) | INIAP, 2021 | 66 | 45,1 MB | clones, variedades, rendimiento, tolerancia a enfermedades | [repositorio.iniap.gob.ec](https://repositorio.iniap.gob.ec/server/api/core/bitstreams/f92da475-087c-49e9-89f7-1770a71a4ff4/content) |

## Referencias (APA 7.ª ed.)

- Merchán, M., Flores, E., & Quiroz, J. (2015). *Guía para facilitar el aprendizaje en el manejo integrado del cultivo de cacao (Theobroma cacao L.)*. Instituto Nacional de Investigaciones Agropecuarias. https://repositorio.iniap.gob.ec
- Instituto Nacional Autónomo de Investigaciones Agropecuarias. (s. f.). *Manual del cultivo de cacao* (Manual No. 76). Estación Experimental Central de la Amazonía. Recuperado el 21 de octubre de 2026, de http://canacacao.org/wp-content/uploads/Manual-cultivo-Cacao-Ecuador.pdf
- Quiroz-Vera, J., Mestanza, S., Parada-Vera, N., Morillo, E., Samaniego, I., & Garzón, I. (2021). *Catálogo de cultivares de cacao en Ecuador* (Boletín Técnico No. 449). Instituto Nacional de Investigaciones Agropecuarias.

## Observaciones de la catalogación

1. **El "Manual del Cultivo de Cacao en Ecuador" no es del MAG.** Al abrirlo, la portada indica *Manual No. 76 – INIAP,
   Estación Experimental Central de la Amazonía*; solo está alojado en el sitio de CANACACAO. Se renombró el archivo y
   debe corregirse la columna "Origen" en [`docs/04-fuentes.md`](../../docs/04-fuentes.md).
2. **Falta una guía del MAG** de manejo integrado de enfermedades, que el caso exige. Pendiente buscar en
   https://www.agricultura.gob.ec y añadirla aquí.
3. El enlace `.../bitstreams/<id>/download` del repositorio INIAP devuelve HTML (página DSpace); se usa el endpoint
   `/server/api/core/bitstreams/<id>/content`, que entrega el PDF directamente.
4. Los SHA-256 de cada archivo están en `scripts/descargar_fuentes.py`; si cambian, la fuente fue actualizada y se debe
   revisar su vigencia.

| Archivo | SHA-256 |
| :--- | :--- |
| INIAP_guia_manejo_integrado_cacao.pdf | `b9b9957668f37fec3ae2e27eb6af2f392bea3565f46508e3dd5a90c8f19313d7` |
| INIAP_manual76_cultivo_cacao_amazonia.pdf | `b7728f5b3026fd6a3d3d33a4eadf25790258d9b1eed30f1b053267d83b704819` |
| INIAP_catalogo_cultivares_cacao.pdf | `866cf19c0d06c1fdb6348246d01bcaa544a797e20c4d717403755ef6943f937c` |
