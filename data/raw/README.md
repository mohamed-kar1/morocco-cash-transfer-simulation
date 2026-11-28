# Données brutes

Les fichiers téléchargés du HCP (page « Micro données - Open Data ») ne sont jamais modifiés. Voir `docs/data_sources.md` pour les détails et les dates d'accès.

```
data/raw/
  encdm_2014/                 versionné dans Git (environ 37 Mo)
    Ménage_ENCDM_2014_en_format_SAV.sav
    Individus__ENCDM_2014_en_format_SAV.sav
    Nomenclature Bien & Service 2014.xlsx
    Note technique (métadonnées) sur l'Enquête Nationale ... .xlsx
  rgph_2014/                  NON versionné (ignoré par Git)
    Le fichier Ménage en format SPSS ... .sav     (environ 53 Mo, utilisé par compare_rgph)
```

## ENCDM 2014 : source unique de `population.csv`

Les quatre fichiers sont dans le dépôt. Ils suffisent à reproduire `population.csv` avec `python -m src.population.build_population`.

## RGPH 2014 : contrôle de représentativité seulement

- Il n'est pas dans le dépôt : volume important, rôle secondaire.
- Seul le fichier **Ménage** est utilisé, par `python -m src.population.compare_rgph`. Pour relancer cette comparaison, le télécharger sur le site du HCP (page Micro données - Open Data) et le placer dans `data/raw/rgph_2014/`.
- Le fichier **Individu** (307 Mo) n'est pas utilisé et n'est pas conservé. Il dépasserait de toute façon la limite de 100 Mo de GitHub.
- Le RGPH n'a aucune variable de consommation : il ne peut pas servir à construire `population.csv`.

## Non utilisé

IPUMS International (Maroc, 2014) : écarté, jamais téléchargé (licence IPUMS : redistribution interdite).