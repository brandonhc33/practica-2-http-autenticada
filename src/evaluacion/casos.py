"""Referencias propuestas para lectura documental de la copia local de 2016.

El estudiante debe revisarlas antes de generar resultados. No se envían al modelo.
"""

from src.prompts.contexto_ley_rep import obtener_fragmento_ley_rep

# Artículo, pregunta acotada y respuesta de referencia redactada para la evaluación.
REFERENCIAS = [
    (
        1,
        "¿Cuál es el objeto de la ley?",
        "Disminuir la generación de residuos y fomentar su reutilización, reciclaje y valorización mediante la responsabilidad extendida del productor y otros instrumentos, para proteger la salud y el medio ambiente.",
    ),
    (
        2,
        "¿Qué significa el principio de que el que contamina paga?",
        "El generador es responsable de sus residuos y debe internalizar los costos y las externalidades negativas asociados a su manejo.",
    ),
    (
        3,
        "¿Qué se entiende por almacenamiento?",
        "Acumulación de residuos en un lugar específico por un tiempo determinado.",
    ),
    (
        4,
        "¿Qué destino debe tener todo residuo potencialmente valorizable?",
        "Debe ser destinado a valorización, evitando su eliminación.",
    ),
    (
        5,
        "¿A quién se deben entregar los residuos sólidos domiciliarios y asimilables?",
        "A la municipalidad correspondiente o a un gestor autorizado para su manejo.",
    ),
    (
        6,
        "¿Cómo debe manejar los residuos un gestor y con qué autorizaciones?",
        "De manera ambientalmente racional, aplicando las mejores técnicas disponibles y prácticas ambientales, conforme a la normativa vigente y con las autorizaciones correspondientes.",
    ),
    (
        7,
        "¿Todos los gestores de residuos peligrosos deben contar con seguro según este artículo?",
        "El artículo exige seguro por daños a terceros y al medio ambiente a los gestores de residuos peligrosos que determine el Reglamento Sanitario sobre Manejo de Residuos Peligrosos.",
    ),
    (
        8,
        "¿Se permite importar residuos peligrosos para su eliminación?",
        "Se prohíbe la importación de residuos peligrosos para su eliminación.",
    ),
    (
        9,
        "¿De qué son responsables los productores en el régimen de responsabilidad extendida?",
        "De organizar y financiar la gestión de los residuos de los productos prioritarios que comercialicen en el país.",
    ),
    (
        10,
        "¿Cuáles son los seis productos prioritarios enumerados?",
        "Aceites lubricantes, aparatos eléctricos y electrónicos, baterías, envases y embalajes, neumáticos y pilas.",
    ),
    (
        11,
        "¿A qué período corresponde la información anual que puede requerir el Ministerio?",
        "Al año inmediatamente anterior al requerimiento.",
    ),
    (
        12,
        "¿Mediante qué instrumento se establecen las metas de recolección y valorización?",
        "Mediante decretos supremos dictados por el Ministerio.",
    ),
    (
        13,
        "¿Puede regularse el etiquetado como obligación asociada para asegurar las metas?",
        "Sí. Los decretos supremos pueden regular obligaciones de etiquetado para asegurar el cumplimiento de metas.",
    ),
    (
        14,
        "¿Qué debe establecer el reglamento mencionado al comienzo del artículo?",
        "El procedimiento para elaborar los decretos supremos que establezcan metas y otras obligaciones asociadas por producto prioritario.",
    ),
    (
        15,
        "¿A qué órgano se somete la propuesta de decreto que establece metas?",
        "Al pronunciamiento del Consejo de Ministros para la Sustentabilidad.",
    ),
    (
        16,
        "¿Cuál es el plazo para interponer el reclamo y desde cuándo se cuenta?",
        "Treinta días desde la publicación del decreto en el Diario Oficial.",
    ),
    (
        17,
        "¿Con qué frecuencia máxima deben revisarse las metas y demás obligaciones asociadas?",
        "Como máximo cada cinco años, según el procedimiento establecido en el reglamento.",
    ),
    (
        18,
        "¿A quién corresponde la interpretación administrativa de los decretos de metas?",
        "Al Ministerio.",
    ),
    (
        19,
        "¿Qué tipos de sistema de gestión permiten cumplir las obligaciones?",
        "Un sistema de gestión individual o colectivo.",
    ),
    (
        20,
        "¿Puede distribuir utilidades entre sus asociados la persona jurídica del sistema colectivo?",
        "No. Debe ser una persona jurídica que no distribuya utilidades entre sus asociados.",
    ),
]


def construir_casos() -> list[dict]:
    return [
        {
            "id": f"rep-{articulo:02d}",
            "consulta": pregunta,
            "referencia": referencia,
            "fragmento": obtener_fragmento_ley_rep(articulo),
        }
        for articulo, pregunta, referencia in REFERENCIAS
    ]
