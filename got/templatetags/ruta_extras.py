from django import template

register = template.Library()

@register.simple_tag
def ruta_status(ruta):
    """
    Devuelve un diccionario con:
      - 'label': El texto a mostrar en el botón.
      - 'style': Un string de CSS inline que define el color (suave y en gradiente según percentage_remaining),
                 junto con un tamaño uniforme: fuente de 0.7rem, padding de 0.4rem arriba/abajo y 0.6rem a los lados,
                 border-radius de 50px y un ancho mínimo de 120px.
    
    Lógica:
      1. Si la ruta tiene OT y su estado es 'x', se devuelve "En ejecución" con un azul suave.
      2. Si la ruta tiene OT:
           - Si percentage_remaining ≤ 0: "Retrasado" con un rojo intenso.
           - Si 0 < percentage_remaining < 10: "Por planear" con un gradiente de rojo a naranja,
             donde el color más bajo (para porcentaje 0) es menos “naranja” (más rojo) que el rojo de "Retrasado".
           - Si percentage_remaining ≥ 10: "Realizado" con un gradiente de amarillo a verde suave.
      3. Si la ruta no tiene OT, se devuelve el mismo gradiente de colores pero la etiqueta es siempre "Sin información".
    """
    base_style = "font-size: 0.65rem; padding: 0.3rem; border-radius: 50px; min-width: 100px; color: white; border: 1px #7D8B84 solid;"
    
    # Caso: En ejecución (si OT existe y su estado es 'x')
    if ruta.ot and ruta.ot.state == 'x':
        return {'label': 'En ejecución', 'style': f'background-color: hsl(210, 50%, 55%); {base_style}'}
    
    percentage = ruta.percentage_remaining
    
    # Función auxiliar para el gradiente en el rango 0–10 (por planear o sin información)
    def red_orange_style(perc):
        # Mapear perc de 0 a 10 a un hue de 10 a 30
        hue = 10 + (perc / 10) * 20
        # Lightness de 45% a 55%
        lightness = 45 + (perc / 10) * 10
        return f'background-color: hsl({hue}, 70%, {lightness}%); {base_style}'
    
    # Función auxiliar para el gradiente en el rango 10–100 (realizado o sin información)
    def yellow_green_style(perc):
        # Mapear de 10 a 100 a un hue de 60 a 120
        relative = min((perc - 10) / 90, 1)
        hue = 60 + relative * 60
        return f'background-color: hsl({hue}, 60%, 70%); {base_style} color: #191645;'
    
    # Si OT existe, se utilizan etiquetas "Por planear" o "Realizado", y si no, se etiqueta siempre "Sin información".
    if ruta.ot:
        if percentage <= 0:
            # "Retrasado": usamos un rojo intenso (más rojo que el inicio de por planear)
            return {'label': 'Retrasado', 'style': f'background-color: hsl(0, 80%, 40%); {base_style}'}
        elif percentage < 10:
            return {'label': 'Por planear', 'style': red_orange_style(percentage)}
        else:
            return {'label': 'Realizado', 'style': yellow_green_style(percentage)}
    else:
        # Sin OT: la etiqueta es siempre "Sin información", pero se usa la misma lógica de color.
        if percentage <= 0:
            return {'label': 'Sin información', 'style': f'background-color: hsl(0, 80%, 40%); {base_style}'}
        elif percentage < 10:
            return {'label': 'Sin información', 'style': red_orange_style(percentage)}
        else:
            return {'label': 'Sin información', 'style': yellow_green_style(percentage)}
