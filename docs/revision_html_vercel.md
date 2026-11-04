# Revisión del HTML para Vercel

Fecha: 4 de noviembre de 2026.
Web revisada: https://edaespanaencifras-vercel.vercel.app/
Archivo de entrega: `vercel/index.html`.

## Correcciones

- Selector «Periodo de los gráficos» con fechas explícitas, explicación de su alcance y confirmación de la selección. Las fechas reales coinciden con las etiquetas.
- Controles con estado seleccionado accesible, foco visible y ordenación territorial mediante botones operables con teclado. Unidades visibles y datos ausentes al final al ordenar.
- Corrección de desbordamientos en pantallas pequeñas y del espacio que ocupa la navegación al abrir una sección.
- Revisión de redacción, frases confusas y afirmaciones causales que los gráficos no permiten demostrar. Aclaración de la fecha de referencia de noviembre de 2023, del significado de «pp» y de las actualizaciones del informe.
- Chart.js 4.4.8 incluido en el propio HTML, conservando su licencia MIT. Las fuentes tipográficas mantienen una alternativa local.
- Se elimina la ocultación inicial del contenido por animaciones. Aviso si JavaScript está desactivado o si falla una sección.
- El generador conserva la sección europea y escribe el mismo resultado en `dashboard/index.html` y `vercel/index.html`. Eurostat se conserva como instantánea con metadatos y fecha de descarga explícitos; no hay actualización en directo.

## Verificación

- 37 enlaces originales del INE: HTTP 200, con títulos de tabla correspondientes y sin página de error detectada.
- 73 gráficos inicializados y cero errores de JavaScript en las interacciones comprobadas.
- Probados los cuatro periodos, los siete filtros del resumen, las nueve métricas territoriales, los seis indicadores de comparación y el selector de inflación europea.
- Probadas las diez columnas de ordenación territorial en ambos sentidos.
- Sin identificadores duplicados, enlaces internos a secciones inexistentes, etiquetas sin cerrar ni marcadores de plantilla pendientes.
- Sin textos dinámicos vacíos ni apariciones visibles de undefined, NaN o null.
- Sin desbordamiento horizontal del documento a 320, 390, 768 y 1440 píxeles. Las tablas y la navegación admiten desplazamiento dentro de sus contenedores.
- Comprobación sintáctica de JavaScript y regeneración completa mediante `python -m src.build_dashboard` correctas.

Las pruebas del navegador se realizaron cargando el HTML y sus scripts en Chrome mediante el protocolo de depuración. La navegación directa y la captura de pantalla del navegador de pruebas no estuvieron disponibles; la comprobación de tamaños se realizó mediante medidas del documento.

## Publicación

Los archivos están preparados localmente. No se ha publicado ni enviado ningún cambio a GitHub o Vercel. Para actualizar la web hay que desplegar de nuevo la carpeta `vercel` con el flujo habitual.

Esta revisión comprueba referencias, controles, presentación adaptable y coherencia de redacción. No sustituye una auditoría estadística independiente de cada serie o fórmula.
