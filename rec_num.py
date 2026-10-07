def _generer_numero_recours():
    annee = timezone.now().year
    prefixe = f"REC-{annee}-"

    numeros = (
        Recours.objects
        .filter(numero_recours__startswith=prefixe)
        .values_list("numero_recours", flat=True)
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
    numero_recours = f"{prefixe}{prochain:04d}"

    while Recours.objects.filter(
        numero_recours=numero_recours
    ).exists():
        prochain += 1
        numero_recours = f"{prefixe}{prochain:04d}"

    return numero_recours

