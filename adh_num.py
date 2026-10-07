def _generer_numero_adhesion():
    annee = timezone.now().year
    prefixe = f"ADHES-{annee}-"

    numeros = (
        Adhesion.objects
        .filter(numero_adhesion__startswith=prefixe)
        .values_list("numero_adhesion", flat=True)
    )

    valeurs = []

    for numero in numeros:
        try:
            valeurs.append(
                int(numero.rsplit("-", 1)[1])
            )
        except (ValueError, IndexError):
            continue

    prochain = max(valeurs, default=0) + 1

    numero_adhesion = f"{prefixe}{prochain:04d}"

    while Adhesion.objects.filter(
        numero_adhesion=numero_adhesion
    ).exists():
        prochain += 1
        numero_adhesion = f"{prefixe}{prochain:04d}"

    return numero_adhesion

