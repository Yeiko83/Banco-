# Carpeta de recursos (`assets/`) — TECINTEK S.A.S.

El sitio (`index.html`) referencia los archivos de esta carpeta por **nombre exacto**.
Mientras un archivo no exista, la página muestra automáticamente un *placeholder*
con degradado de los colores de marca (gracias a los `onerror` en el HTML), así que
el sitio se ve bien aunque falten imágenes. Reemplaza cada placeholder subiendo el
archivo con el nombre correspondiente **tal cual** aparece abajo.

## Identidad
| Archivo | Uso | Recomendado |
|---|---|---|
| `logo-tck.png` | Logo en header y footer | PNG con fondo transparente, ~200×200 px |
| `catalogo-tecintek.pdf` | Descarga "Catálogo PDF" | PDF, tamaño moderado |

## Hero y destacado
| Archivo | Uso | Recomendado |
|---|---|---|
| `tarjetas-mockup.jpg` | Imagen principal del hero (tilt 3D) | JPG vertical ~4:5, 800×1000 px |
| `volantes-mejores.jpg` | Imagen del bloque "Suministros" | JPG horizontal ~4:3, 1000×750 px |

## Galería (clic para ampliar en lightbox)
| Archivo | Etiqueta mostrada |
|---|---|
| `pieza-volante-1.jpg` | Publicidad · Volantes (imagen grande) |
| `carnets-lanyards.jpg` | Dotación · Carnets |
| `reglas-publicitarias.jpg` | Publicidad · Merchandising |
| `gorras-fila.jpg` | Dotación · Bordado |
| `pieza-volante-2.jpg` | Imprenta · Litografía |

## Catálogo (tarjetas de producto)
| Archivo | Producto |
|---|---|
| `volantes-mejores.jpg` | Volantes publicitarios |
| `tarjetas-mockup.jpg` | Tarjetas de presentación |
| `afiche-noche-talentos.jpg` | Afiches y pósters |
| `pendones-calle.jpg` | Pendones publicitarios |
| `pendon-urbana.jpg` | Pendón urbano gran formato |
| `abanico-imprenta.jpg` | Abanicos publicitarios |
| `banderines.jpg` | Banderines |
| `aviso-sushiwok.jpg` | Avisos y señalización comercial |
| `caja-luz-abastos.jpg` | Caja de luz / gigantografía |
| `plegables-mockup.jpg` | Plegables y brochures |
| `facturero-elcielo.jpg` | Facturero / talonario |
| `periodicos.jpg` | Impresión de periódicos y prensa |
| `senalizacion-grid.jpg` | Señalización institucional |
| `etiquetas-ropa.jpg` | Etiquetas para ropa |
| `camiseta-campana.jpg` | Camisetas para campañas |
| `polos-fila.jpg` | Polos institucionales |
| `mugs-colores.jpg` | Mugs y regalos corporativos |

> Los productos de las líneas **Telecomunicaciones (J6190)** y **Servicios de Comidas
> (I5629)**, además de algunos de comercio mayorista, usan placeholder con degradado a
> propósito (no requieren imagen). Puedes agregarles foto luego si lo deseas, añadiendo
> la ruta en el arreglo `PRODUCTS` dentro de `index.html`.

## Consejos
- Formato recomendado: **JPG** para fotos (ligero), **PNG** para el logo.
- Optimiza el peso (idealmente < 300 KB por imagen) para que el sitio cargue rápido.
- Mantén los nombres **en minúscula y con guiones**, exactamente como en las tablas.
