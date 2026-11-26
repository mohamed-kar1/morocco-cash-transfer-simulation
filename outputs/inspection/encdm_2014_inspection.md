# Rapport d'inspection : ENCDM 2014

Statut : **OK**

Fichiers lus :
- Ménage : `Ménage_ENCDM_2014_en_format_SAV.sav`
- Individus : `Individus__ENCDM_2014_en_format_SAV.sav`

## Intégrité

| Contrôle | Résultat |
|---|---|
| Ménages | 15 970 |
| Personnes (fichier Individus) | 75 691 |
| Identifiant ménage unique | oui |
| Ménages sans individus / individus sans ménage | 0 / 0 |
| Taille du ménage = nombre de lignes Individus | 100.00 % des ménages |
| Taille du ménage (min, max) | 1, 26 |

## Poids

| Indicateur | Valeur |
|---|---|
| Somme de coef_ménage (ménages représentés) | 7 190 456 |
| Somme de coef_indiv (personnes représentées) | 33 579 281 |
| Somme de coef_ménage × taille | 34 071 538 |
| Rapport coef_indiv / (coef_ménage × taille) : min, moyenne, max | 0.677, 0.988, 4.521 |

Les deux poids ne sont pas interchangeables : coef_indiv n'est pas égal à coef_ménage × taille.

## Consommation

- DAM (MAD par an, non pondéré) : min 4 286, médiane 58 098, max 1 224 977.
- Écart maximal entre DAP et DAM/taille : 0.000000.

## Chiffres de contrôle de la note technique

| Contrôle | Note | Données | Reproduit |
|---|---|---|---|
| Nombre de ménages | 15 970 | 15 970 | oui |
| Somme de coef_ménage | 7 190 456 | 7 190 456 | oui |
| DAM moyenne, pondérée par coef_ménage | 76 317.23 | 76 317.23 | oui |
| DAP moyenne, pondérée par coef_indiv | 15 875.68 | 15 875.68 | oui |

Pondération inverse (non publiée dans la note) :
- DAM moyenne pondérée par coef_indiv : 79 263.80
- DAP moyenne pondérée par coef_ménage : 19 413.14

## Indicateurs HCP de pauvreté (non documentés dans la note technique)

| Indicateur | Valeur |
|---|---|
| Ménages `Pauvre` | 499 |
| Ménages `Vulnérable` | 1 499 |
| Ménages à la fois pauvres et vulnérables | 0 |
| Taux `Pauvre`, pondéré par personne (coef_indiv) | 4.78 % |
| Taux `Pauvre`, pondéré par ménage (coef_ménage) | 3.00 % |
| Taux `Vulnérable`, pondéré par personne | 12.47 % |

Coupure observée sur la dépense par personne (MAD par an). Ceci est une observation sur les données, pas un seuil officiel.

| Milieu | DAP max des pauvres | DAP min des non-pauvres |
|---|---|---|
| Urbain | 4 655 | 4 676 |
| Rural | 4 310 | 4 317 |

## Milieu de résidence

| Code | Modalité | Ménages (non pondéré) | Ménages représentés | Taux `Pauvre` (personnes) | Effectif faible |
|---|---|---|---|---|---|
| 1 | Urbain | 10 380 | 4 706 309 | 1.64 % |  |
| 2 | Rural | 5 590 | 2 484 147 | 9.48 % |  |

## Régions (seuil d'effectif faible provisoire : 500 ménages, voir D12)

| Code | Modalité | Ménages (non pondéré) | Ménages représentés | Taux `Pauvre` (personnes) | Effectif faible |
|---|---|---|---|---|---|
| 1 | Tanger-Tétouan-Al Hoceïma | 1 690 | 785 705 | 2.17 % |  |
| 2 | Oriental | 1 247 | 485 985 | 5.34 % |  |
| 3 | Fès-Meknès | 1 980 | 904 063 | 5.16 % |  |
| 4 | Rabat-Salé-Kénitra | 2 159 | 996 500 | 3.77 % |  |
| 5 | Béni Mellal-Khénifra | 1 372 | 512 154 | 9.25 % |  |
| 6 | Casablanca-Settat | 3 091 | 1 530 262 | 2.03 % |  |
| 7 | Marrakech-Safi | 1 754 | 914 934 | 5.39 % |  |
| 8 | Drâa-Tafilalet | 628 | 274 352 | 14.64 % |  |
| 9 | Souss-Massa | 1 171 | 591 990 | 5.08 % |  |
| 10 | Guelmim-Oued Noun | 244 | 88 662 | 6.45 % | oui |
| 11 | Laâyoune-Sakia El Hamra | 329 | 77 083 | 0.75 % | oui |
| 12 | Dakhla-Oued Ed Dahab | 305 | 28 766 | 0.32 % | oui |

## Âges et enfants (fichier Individus, non pondéré)

- Âge : min 0, max 98, manquants 0.
- Personnes de moins de 15 ans : 20 312 ; de moins de 18 ans : 24 515 (seuil de `children_count` en attente, voir D8).

## Avertissements
- Régions sous 500 ménages (non pondérés) : Guelmim-Oued Noun, Laâyoune-Sakia El Hamra, Dakhla-Oued Ed Dahab.
