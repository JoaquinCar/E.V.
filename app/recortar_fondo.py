#!/usr/bin/env python3
"""
Recorta el fondo blanco de una imagen y la deja en PNG transparente,
lista para la barra de menú.

Por qué relleno desde los bordes y no un filtro de color: en la máscara de
Spider-Man los ojos son casi blancos. Un "todo lo blanco a transparente" los
agujerearía. El relleno solo se come el blanco **conectado al borde**, así que
respeta lo que está encerrado dentro del dibujo.

uso: recortar_fondo.py entrada.jpg salida.png [tamaño]
"""
import sys

from PIL import Image, ImageDraw, ImageFilter

# Verde imposible: la imagen trae magentas y cianes, así que la marca
# temporal tiene que ser un color que seguro no aparezca.
MARCA = (1, 254, 3)
TOLERANCIA = 32       # qué tan lejos del blanco sigue contando como fondo
MARGEN = 2            # píxeles de aire alrededor del recorte final


def recortar(entrada: str, salida: str, lado: int = 44) -> None:
    im = Image.open(entrada).convert('RGB')

    # Un borde blanco de 1px garantiza que el fondo esté conectado aunque el
    # dibujo toque la orilla.
    con_borde = Image.new('RGB', (im.width + 2, im.height + 2), (255, 255, 255))
    con_borde.paste(im, (1, 1))

    ImageDraw.floodfill(con_borde, (0, 0), MARCA, thresh=TOLERANCIA)

    # Lo marcado se vuelve transparente.
    rgba = con_borde.convert('RGBA')
    pix = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _ = pix[x, y]
            if (r, g, b) == MARCA:
                pix[x, y] = (0, 0, 0, 0)

    # Suavizar el borde: el relleno deja escalones duros.
    alfa = rgba.getchannel('A').filter(ImageFilter.GaussianBlur(0.6))
    rgba.putalpha(alfa)

    caja = rgba.getbbox()
    if caja:
        caja = (max(caja[0] - MARGEN, 0), max(caja[1] - MARGEN, 0),
                min(caja[2] + MARGEN, rgba.width), min(caja[3] + MARGEN, rgba.height))
        rgba = rgba.crop(caja)

    # Cuadrado, sin deformar: se centra sobre un lienzo transparente.
    lado_orig = max(rgba.size)
    lienzo = Image.new('RGBA', (lado_orig, lado_orig), (0, 0, 0, 0))
    lienzo.paste(rgba, ((lado_orig - rgba.width) // 2,
                        (lado_orig - rgba.height) // 2))

    lienzo.resize((lado, lado), Image.LANCZOS).save(salida)

    opacos = sum(1 for p in lienzo.getdata() if p[3] > 0)
    print(f'  {salida}  ·  {lado}x{lado}  ·  '
          f'{100 * opacos / (lado_orig ** 2):.0f}% con contenido')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    recortar(sys.argv[1], sys.argv[2],
             int(sys.argv[3]) if len(sys.argv) > 3 else 44)
