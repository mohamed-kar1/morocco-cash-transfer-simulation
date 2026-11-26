# Dictionnaire de données : `population.csv`

Tenu par : Personne 1. Dernière mise à jour : 2026-11-23.
Fichier produit par `src/population/build_population.py` (Phase 5) ; fixture conforme : `data/mock/population_mock.csv` (20 ménages inventés, pour tests uniquement).

Une ligne = un ménage. Encodage UTF-8, séparateur virgule, point décimal.
Les 10 colonnes et leur ordre sont ceux du contrat du Master Project Document (section des schémas partagés), vérifiés le 23 nov.

## Colonnes

| Colonne | Type | Unité / valeurs | Source ENCDM 2014 | Règle | Décision |
|---|---|---|---|---|---|
| `household_id` | texte | identifiant unique | `N_ménage` | tel quel | |
| `household_weight` | décimal > 0 | ménages représentés | `coef_ménage` | tel quel | D7 |
| `region` | texte | 12 régions (libellés `Région_12`) | `Région_12` | libellé, pas le code | |
| `urban_rural` | texte | `urbain` ou `rural` | `Milieu` (1 = urbain, 2 = rural) | recodage | |
| `household_size` | entier ≥ 1 | personnes | `Taille_ménage` (texte) | conversion en entier | |
| `children_count` | entier, 0 à `household_size` | personnes de moins de 15 ans | fichier Individus (âge) | comptage par ménage | D8 |
| `baseline_consumption` | décimal > 0 | MAD par mois, prix courants 2014 | `DAM` | `DAM / 12` | D3, D4 |
| `equivalence_factor` | décimal > 0 | sans unité | absent du fichier | `household_size` | D2 |
| `equiv_consumption` | décimal > 0 | MAD par mois et par personne | calculé | `baseline_consumption / equivalence_factor` | D2 |
| `eligible_baseline` | entier 0 ou 1 | 1 = éligible | `Pauvre`, `Vulnérable` | 1 si `Pauvre` ou `Vulnérable` (indicateur HCP) | D6 |

## Valeurs manquantes (nullability)

Aucune des 10 colonnes n'est nullable : toute ligne avec une valeur manquante est exclue ou corrigée dans la construction, et chaque exclusion est comptée dans le journal (lignes avant et après). Aucune valeur manquante n'a été constatée sur `DAM`, les poids, la région et le milieu à l'inspection du 23 nov.

## Catégories

- `urban_rural` : `urbain` (Milieu = 1), `rural` (Milieu = 2).
- `region` : Tanger-Tétouan-Al Hoceïma, Oriental, Fès-Meknès, Rabat-Salé-Kénitra, Béni Mellal-Khénifra, Casablanca-Settat, Marrakech-Safi, Drâa-Tafilalet, Souss-Massa, Guelmim-Oued Noun, Laâyoune-Sakia El Hamra, Dakhla-Oued Ed Dahab (codes 1 à 12 de `Région_12`).
- `eligible_baseline` : 0 ou 1.

## Traitement de la consommation (exigé par le document maître)

- Composantes : `DAM` total, groupe 9 inclus (D3) ; il contient des loyers fictifs (loyer imputé aux propriétaires) et des postes non consommatoires (impôts, transferts, remboursements de prêts).
- Période : annuelle dans la source, convertie en mensuel (÷ 12). Prix courants 2014, sans ajustement (D4).
- Échelle d'équivalence : taille du ménage (D2). Le document maître préfère l'adulte équivalent si défendable ; une échelle sourcée sera testée en sensibilité.

## Seuils de référence (pas des colonnes)

Seuil de pauvreté HCP 2014, par personne et par an : 4 667 MAD en urbain, 4 312 MAD en rural (D5). En mensuel (÷ 12) : environ 388,92 et 359,33 MAD. Bande de vulnérabilité : jusqu'à 1,5 fois le seuil.

## Règles de validation (Phase 5)

- `household_id` unique, sans valeur manquante.
- `household_weight`, `baseline_consumption`, `equivalence_factor`, `equiv_consumption` strictement positifs.
- `children_count` entre 0 et `household_size`.
- `urban_rural` dans {`urbain`, `rural`} ; `region` parmi les 12 libellés.
- `eligible_baseline` dans {0, 1}.
- Nombre de lignes attendu sur les vraies données : 15 970 ; somme de `household_weight` : 7 190 456.

## Particularités de la mock

- Valeurs inventées, aucune ne vient des vraies données.
- `eligible_baseline` y est calculé avec les seuils HCP (dépense par personne sous 1,5 fois le seuil du milieu). Sur les vraies données, on utilise directement les indicateurs `Pauvre` et `Vulnérable`.
- Elle contient des cas limites : ménage d'une personne, ménage de 12 personnes, sans enfant, trois petites régions, ménages juste au-dessus et en dessous des seuils.

## Fichier interne `person_weights.csv` (D14)

Hors contrat partagé : produit par `build_population.py` et lu par la partie B. Une ligne par ménage, même `household_id` que `population.csv`.

| Colonne | Type | Unité | Source | Règle |
|---|---|---|---|---|
| `household_id` | texte | identifiant unique | `N_ménage` | tel quel |
| `person_weight` | décimal | personnes représentées par ce ménage | `coef_indiv` (fichier Ménage) | tel quel ; positif ; somme 33 579 281 |

À utiliser pour les mesures par personne (taux de pauvreté par personne). `household_weight` sert aux mesures par ménage. Les deux ne sont pas interchangeables (D7).

Le seuil de pauvreté n'est pas une colonne : l'analyse le calcule à partir de `urban_rural` (D5, D14).
## `simulation_results.csv` tel que lu par la partie B (fixture fictive)

Définition de référence : Master Project Document et Personne 2. Ce qui suit est l'interprétation utilisée pour tester les métriques, convention exigée par l'analyse (D15), à communiquer à Personne 2.

Fixture : `data/mock/simulation_results_mock.csv`, générée par `src/analysis/mock_simulation.py` à partir de la population mock. Valeurs fictives : budget mensuel de 4 000 MAD, propension à consommer 0,8, chocs aléatoires. Ce ne sont pas des résultats.

Grain : une ligne = ménage x mois x scénario x réplication. Clé unique : `run_id`, `scenario_id`, `month`, `household_id`.

| Colonne | Type | Unité / valeurs | Interprétation utilisée |
|---|---|---|---|
| `run_id` | texte | R1, R2... | une réplication |
| `scenario_id` | texte | S0, S1, S2, S3 | scénario |
| `seed` | entier | | graine de la réplication |
| `month` | entier | 1 à 12 | mois simulé |
| `household_id` | texte | | même identifiant que `population.csv` |
| `household_weight` | décimal | ménages représentés | copie de `population.csv` |
| `economic_shock` | décimal | MAD par mois, négatif ou nul | identique dans les 4 scénarios d'une réplication |
| `transfer_amount` | décimal | MAD par mois, >= 0 | transfert versé ce mois-là |
| `disposable_resources` | décimal | MAD par mois | `baseline_consumption + economic_shock + transfer_amount` |
| `consumption_outcome` | décimal | MAD par mois | consommation après choc et transfert |
| `equiv_consumption_outcome` | décimal | MAD par mois et par personne | `consumption_outcome / equivalence_factor` |
| `eligible_baseline` | entier | 0 ou 1 | copie de `population.csv` |


## Sorties de la partie B (propriétaire : Personne 1)

Produites par `python -m src.analysis.export` (consommateur : rapport final et Personne 2). Les fichiers de la mock portent le suffixe `_mock` et ne se citent jamais. Une valeur vide dans `value` signifie « non défini » (dénominateur nul : aucun bénéficiaire, aucune dépense).

### `scenario_metrics.csv` (format long)

| Colonne | Type | Contenu |
|---|---|---|
| `run_id` | texte | Réplication ; `population` pour la situation de base |
| `scenario_id` | texte | `S0` à `S3` ; `baseline` pour la situation de base (population.csv) |
| `metric` | texte | Indicateur (voir tableau ci-dessous) |
| `value` | décimal | Valeur de l'indicateur |
| `weighting_basis` | texte | `ménage`, `personne`, `personne (approx.)` (mock), `non pondéré` ou `ménage (poids ménage x taille)` |
| `time_basis` | texte | `moyenne des 12 mois`, `DAM / 12 (valeur annuelle ramenée au mois)`, `12 mois cumulés`, etc. |
| `denominator` | décimal | Dénominateur du taux (somme des poids, effectif ou budget) |
| `notes` | texte | Unité du dénominateur et précisions |

### `group_impacts.csv`

Mêmes colonnes, avec `subgroup_dimension` et `subgroup_value` à la place de `time_basis` (la base de temps est rappelée dans `notes`). Dimensions : `urban_rural`, `region`, `household_size_group` (1 à 6, 7+), `has_children`, `eligible_baseline`. Règle des petits groupes (D12) : moins de 500 ménages non pondérés, signalé « effectif faible » dans `notes`, jamais supprimé. Les effectifs (`group_households_*`, `group_persons_weighted`) sont donnés une fois, pour `run_id = population`.

### Indicateurs

| Indicateur | Fichier | Unité | Définition |
|---|---|---|---|
| `poverty_headcount` | scenario_metrics, group_impacts | part (0 à 1) | Part pondérée des ménages (ou des personnes) dont la consommation équivalente par personne et par mois est strictement sous le seuil HCP du milieu (D5). |
| `poverty_gap` | scenario_metrics, group_impacts | part du seuil (0 à 1) | Écart moyen au seuil, en part du seuil, tous ménages confondus (0 pour les non-pauvres). |
| `gini` | scenario_metrics, group_impacts | indice (0 à 1) | Coefficient de Gini pondéré de la consommation équivalente par personne. |
| `mean_equiv_consumption` | scenario_metrics, group_impacts | MAD 2014 par personne et par mois | Consommation équivalente moyenne pondérée. |
| `coverage_eligible` | scenario_metrics | part (0 à 1) | Bénéficiaires éligibles / éligibles (eligible_baseline = 1) ; bénéficiaire = transfert > 0 au moins un mois (D16). |
| `exclusion_error` | scenario_metrics | part (0 à 1) | Ménages (ou personnes) pauvres au départ non bénéficiaires / pauvres au départ (D16). |
| `inclusion_error` | scenario_metrics | part (0 à 1) | Bénéficiaires non pauvres au départ / bénéficiaires (D16). Vide s'il n'y a aucun bénéficiaire. |
| `recipients_count` | scenario_metrics | ménages ou personnes représentés | Nombre pondéré de bénéficiaires (transfert > 0 au moins un mois). |
| `fiscal_cost_annual` | scenario_metrics | MAD par an | Transferts payés sur 12 mois, pondérés par household_weight (annuel = cumulé sur l'horizon). |
| `fiscal_cost_monthly_mean` | scenario_metrics | MAD par mois | Coût annuel pondéré divisé par 12. |
| `fiscal_cost_annual_sample` | scenario_metrics | MAD par an | Transferts payés sur 12 mois, somme brute sur les ménages de l'échantillon (non pondérée). |
| `budget_utilization` | scenario_metrics | part (0 à 1) | Dépenses / budget annuel commun, dans la base indiquée dans notes (D9, D15). Présent seulement si un budget est fourni. |
| `poverty_gap_reduction_mad` | scenario_metrics | MAD par an | Écart de pauvreté agrégé de S0 moins celui du scénario, x 12 mois, pondéré par household_weight x taille. |
| `poverty_gap_reduction_per_mad` | scenario_metrics | MAD d'écart réduits par MAD dépensé | poverty_gap_reduction_mad / fiscal_cost_annual. Vide si la dépense est nulle (D16, B6). |
| `group_households_unweighted` | group_impacts | ménages | Effectif non pondéré du groupe dans l'échantillon (sert à signaler les petits groupes, D12). |
| `group_households_weighted` | group_impacts | ménages représentés | Somme de household_weight dans le groupe. |
| `group_persons_weighted` | group_impacts | personnes représentées | Somme du poids personne (coef_indiv, D14) dans le groupe. |
| `<indicateur>_change_vs_S0` | scenario_metrics, group_impacts | unité de l'indicateur | Écart absolu avec S0 dans la même réplication (scénario moins S0). Absent pour S0. |

Autres fichiers : `metric_definitions.csv` (ce tableau) et `analysis_metadata.json` (entrées utilisées avec leur empreinte SHA-256, mode, budget, base de pondération des personnes, dates).
