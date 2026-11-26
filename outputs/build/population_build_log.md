# Journal de construction de `population.csv`

Agrégats uniquement. « Exclues » = lignes retirées par l'opération (0 si aucune).

| # | Opération | Lignes avant | Lignes après | Exclues | Remarque |
|---|---|---|---|---|---|
| 1 | Lecture du fichier Ménage (9 variables utiles) | 15 970 | 15 970 | 0 | Ménage_ENCDM_2014_en_format_SAV.sav |
| 2 | Lecture du fichier Individus (2 variables utiles) | 75 691 | 75 691 | 0 | Individus__ENCDM_2014_en_format_SAV.sav |
| 3 | Conversion de Taille_ménage (texte vers entier) | 15 970 | 15 970 | 0 | toute valeur non numérique arrête le script |
| 4 | Recodage de Région_12 en libellés | 15 970 | 15 970 | 0 | 12 régions |
| 5 | Recodage de Milieu (1 = urbain, 2 = rural) | 15 970 | 15 970 | 0 |  |
| 6 | Comptage des enfants de moins de 15 ans (fichier Individus) | 75 691 | 75 691 | 0 | 0 ménage(s) sans individu : enfants = 0 |
| 7 | Calcul des 10 colonnes du contrat (D2 à D8) | 15 970 | 15 970 | 0 | aucun ménage retiré |
| 8 | Validation du contrat et des chiffres de contrôle | 15 970 | 15 970 | 0 | lignes, poids, enfants, Pauvre, éligibles |
| 9 | Export de population.csv | 15 970 | 15 970 | 0 | data\processed\population.csv |
| 10 | Export de person_weights.csv (coef_indiv, fichier interne, D14) | 15 970 | 15 970 | 0 | data\processed\person_weights.csv |

## Totaux du fichier produit

- Lignes : 15 970
- Somme de household_weight : 7 190 456
- Ménages Pauvre (drapeau HCP) : 499
- Ménages éligibles (Pauvre ou Vulnérable) : 1 998
- Enfants de moins de 15 ans : 20 312
- Somme de coef_indiv (personnes représentées) : 33 579 281
- Ménages dont la taille != nombre d'individus : 0
