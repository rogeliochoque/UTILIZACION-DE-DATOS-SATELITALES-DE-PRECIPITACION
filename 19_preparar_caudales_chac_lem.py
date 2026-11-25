import os


def generar_archivo_amq_caudales(
    ruta_salida: str,
    id_estacion: int = 1,
    anio_inicio: int = 1980,
    anio_fin: int = 2020,
):
    """Genera el fichero de aforos/caudales observados con formato AMQ para CHAC."""
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

    # Aforos conocidos en m3/s: (Año, Mes): Caudal
    aforos_conocidos = {
        (2011, 6): 0.171,  # Junio 2011
        (2013, 10): 0.194,  # Octubre 2013
    }

    # Tipo de dato exactamente de 3 caracteres
    tipo_amq = "AMQ"
    # ID estación en 7 caracteres (columnas 4-10)
    id_est = str(id_estacion).strip()[:7].rjust(7)

    with open(ruta_salida, "w", encoding="ascii") as f:
        for anio in range(anio_inicio, anio_fin + 1):
            # Columnas 1-14: 'AMQ' (1-3) + ID (4-10) + Año (11-14)
            linea = f"{tipo_amq}{id_est}{anio:4d}"

            # 12 meses (columnas 15-74, 5 columnas por mes con 2 o 3 decimales)
            # Si no hay aforo, se coloca 0.000 para indicar dato no registrado
            suma_anual = 0.0
            cuenta_validos = 0

            for mes in range(1, 13):
                if (anio, mes) in aforos_conocidos:
                    q = aforos_conocidos[(anio, mes)]
                    linea += f"{q:5.3f}"[:5]  # Asegura exactamente 5 caracteres
                    suma_anual += q
                    cuenta_validos += 1
                else:
                    linea += " 0.00"  # 5 caracteres: espacio + 0.00

            # Columna final anual (columnas 75-80, 6 caracteres)
            if cuenta_validos > 0:
                q_med = suma_anual / cuenta_validos
                linea += f"{q_med:6.3f}"[:6]
            else:
                linea += "  0.00"

            linea += "\n"
            f.write(linea)

    print("=" * 65)
    print("FICHERO AMQ GENERADO CON ÉXITO")
    print(f"Ruta: {ruta_salida}")
    print(f"Código tipo: '{tipo_amq}' | Estación: '{id_est.strip()}'")
    print(f"Periodo    : {anio_inicio} - {anio_fin}")
    print("=" * 65)


if __name__ == "__main__":
    ARCHIVO_SALIDA = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios\CHAC\CAUDALES_1980_2020.LEM"

    generar_archivo_amq_caudales(
        ruta_salida=ARCHIVO_SALIDA,
        id_estacion=1,
        anio_inicio=1980,
        anio_fin=2020,
    )