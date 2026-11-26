# Méthodologie : population et indicateurs distributifs (Personne 1)

Projet : Morocco Cash-Transfer Policy Evaluation Simulation
Tenu par : Personne 1. Dernière mise à jour : 2026-11-26.
Documents liés : `data_sources.md` (fiches des sources), `data_dictionary.md` (schéma de `population.csv`), `pending_decisions.md` (registre D1 à D17).

Les résultats de la simulation décrivent un exercice conditionnel à des hypothèses, pas l'effet d'un programme réel.

## 1. Objectif

Produire un fichier de ménages, `data/processed/population.csv`, avec les 10 colonnes du contrat du Master Project Document, à partir de données officielles, avec une traçabilité de chaque champ dérivé. Ce fichier est l'entrée de la simulation (Personne 2) et des métriques (partie B).

## 2. Sources et faisabilité (A1 à A3)

### 2.1 Source retenue : ENCDM 2014 (HCP)

- Enquête nationale sur la consommation et les dépenses des ménages, collecte 2013/2014, année de référence 2014. Microdonnées à grande diffusion mises en ligne le 01/11/2019.
- 15 970 ménages et 75 691 personnes. Exploitable au niveau national, par milieu et par région (12 régions).
- Seule source disposant de la dépense des ménages (`DAM`), donc de la pauvreté et de l'éligibilité.
- Citation : Haut-commissariat au Plan (2019). *Les données sur la consommation et les dépenses des ménages au Maroc.* Fichier de microdonnées à grande diffusion (FMGD).

### 2.2 Sources écartées ou secondaires

| Source | Rôle | Motif |
|---|---|---|
| RGPH 2014 (HCP, fichier anonymisé à 10 %) | Contrôle des marges uniquement | 730 099 ménages, mais aucune variable de consommation ni de revenu (variables de logement, équipements, démographie) |
| IPUMS International, Maroc | Non utilisé | Même recensement 2014 que le RGPH, donc rien de plus ; non téléchargé |

Pour mémoire, le HCP combine lui-même le RGPH et l'ENCDM pour sa cartographie de la pauvreté, par un modèle statistique de la consommation par habitant estimé sur les variables communes aux deux sources ; ce n'est pas un IPF, et cette approche n'est pas reprise ici.

On ne joint pas d'enregistrements d'enquêtes différentes comme s'ils décrivaient les mêmes ménages.

### 2.3 IPF : checklist du guide et décision (D1)

| Question du guide | Constat |
|---|---|
| Graine adaptée ? | Oui : ENCDM, microdonnées au niveau ménage, avec région, milieu, taille et consommation |
| Marges autoritaires et alignées ? | RGPH 2014 : même année, mêmes régions et milieux. Le fichier est un échantillon à 10 % |
| Catégories harmonisables ? | Région et milieu : oui (libellés identiques après normalisation). Taille : comparée en classes 1 à 6 et 7 et plus ; la définition du ménage dans le RGPH n'est pas confirmée |
| Zéros structurels ? | Non évalués : l'IPF n'est pas mis en œuvre |
| Validation, convergence ? | Sans objet |

Comparaison des parts pondérées (`outputs/inspection/rgph_vs_encdm.md`) :

| Dimension | Écart maximal ENCDM moins RGPH |
|---|---|
| Milieu | 0,39 point |
| Région | 0,08 point |
| Taille du ménage | 1 personne : -3,32 points (3,89 % contre 7,20 %) ; 2 : -1,31 ; 4 : +1,32 ; 5 : +1,77 ; 6 : +1,30 ; 3 et 7 et plus : moins de 0,5 |

Ménages représentés : 7 190 456 (ENCDM) contre 7 300 986 (RGPH).

**Décision (D1, Personne 1)** : source unique, ENCDM, avec `coef_ménage` tel quel et sans IPF. Motif : région et milieu sont déjà alignés sur le recensement, et l'écart de taille n'est pas interprétable sans définition commune du ménage. Le calage des poids sur la taille est une variante de sensibilité (D13).

Réserve : `MEN.TYPE` du RGPH décrit la composition familiale (couple, ménage élargi, etc.) et non ordinaire ou collectif ; aucun filtre sur les ménages ordinaires n'a donc été appliqué, et la comparaison porte sur tous les ménages du fichier (4 986 sans type renseigné).

## 3. Construction de `population.csv` (A4 à A8)

Script : `src/population/build_population.py`. Les données brutes ne sont jamais modifiées. Le journal des lignes avant et après chaque opération est écrit dans `outputs/build/population_build_log.md` (aucune ligne exclue).

| Colonne | Règle | Décision |
|---|---|---|
| `household_id` | `N_ménage`, en texte | |
| `household_weight` | `coef_ménage` | D7 |
| `region`, `urban_rural` | `Région_12` en libellé ; `Milieu` : 1 urbain, 2 rural | |
| `household_size` | `Taille_ménage`, converti du texte en entier | |
| `children_count` | Nombre de personnes de moins de 15 ans dans le fichier Individus | D8 |
| `baseline_consumption` | `DAM / 12`, MAD courants 2014 | D3, D4 |
| `equivalence_factor` | Taille du ménage | D2 |
| `equiv_consumption` | `baseline_consumption / equivalence_factor` | D2 |
| `eligible_baseline` | 1 si `Pauvre` ou `Vulnérable` (indicateurs HCP) | D6 |

### 3.1 Poids (A6)

La note technique associe, dans son texte, `coef_ménage` à la dépense par personne et `coef_individu_sum` à la dépense par ménage. Ses propres chiffres de contrôle sont reproduits par l'inverse : `DAM` moyenne = 76 317,23 avec `coef_ménage`, `DAP` moyenne = 15 875,68 avec `coef_indiv`. Règle retenue : `coef_ménage` pour les mesures par ménage, `coef_indiv` pour la pauvreté par personne. Les deux poids ne sont pas interchangeables (le rapport `coef_indiv / (coef_ménage × taille)` va de 0,68 à 4,52). Les poids ne sont pas relabellisés : `coef_indiv` n'est pas dans `population.csv`, il est exporté à part dans `data/processed/person_weights.csv` (D14).

### 3.2 Consommation (A7)

- `DAM` : dépense annuelle du ménage pour tous les biens et services de la nomenclature, en dirhams courants 2014. Elle inclut le groupe 9 (paiements fiscaux, transferts en espèce et en nature, remboursements de prêts) et des loyers fictifs (loyer imputé aux propriétaires, groupe 3).
- Choix : `DAM` total (D3). Motif : la coupure de l'indicateur `Pauvre` est nette sur `DAM / taille`, donc le HCP classe les ménages sur le `DAM` total ; garder ce périmètre reste cohérent avec le seuil officiel.
- Sensibilité : `DAM - DAM_G9` donne 526 ménages sous le seuil au lieu de 499 ; 27 ménages (0,17 % des ménages, 5,4 % des pauvres) changent de statut, tous de non pauvre à pauvre.
- Aucune valeur manquante sur `DAM` ; aucun ajustement de prix (D4).
- Échelle d'équivalence : taille du ménage. Elle correspond à la dépense par personne utilisée par le HCP et ne tient pas compte des économies d'échelle. Le document maître préfère l'adulte équivalent « si défendable » ; une échelle sourcée sera testée en sensibilité (D13).

### 3.3 Seuil de pauvreté et éligibilité (A8)

Seuil officiel HCP, en dirhams de 2014 par personne et par an : **4 667 MAD en urbain, 4 312 MAD en rural** ; ligne alimentaire : 2 331 MAD. Vulnérable : entre 1 et 1,5 fois le seuil. Source : HCP, page « Méthodologie pauvreté & vulnérabilité » (https://www.hcp.ma/methodologie-pauvrete-vulnerabilite_r497.html), consultée le 23 novembre 2026, valeurs relues dans le texte de la page le 25 novembre 2026. Le HCP définit la vulnérabilité par la dépense par personne et par an, entre 4 667 et 7 001 MAD en urbain et entre 4 312 et 6 468 MAD en rural.

Contrôles sur `population.csv` : appliqués à `equiv_consumption × 12`, ces seuils donnent exactement 499 ménages pauvres et 1 998 ménages pauvres ou vulnérables, soit le décompte de `Pauvre` et de `Pauvre` + `Vulnérable` du HCP, sans écart. Taux de pauvreté pondéré par personne : 4,78 % (4,8 % publié par le HCP pour 2014) ; par ménage : 3,00 %.

Définitions du HCP utiles à la partie B (même page) : le taux de pauvreté est la proportion des **individus** (membres d'un ménage dont la dépense par tête est sous le seuil) ; l'indice volumétrique de la pauvreté mesure l'écart moyen entre le seuil et la dépense par tête des pauvres ; l'indice de sévérité met l'accent sur les plus pauvres ; l'inégalité est mesurée par le coefficient de Gini.

Éligibilité : fondée sur le bien-être de base, avant tout transfert, et fixe pendant les 12 mois (D6). `Pauvre` seul (499 ménages) reste une variante de sensibilité. Le seuil n'est pas une colonne de `population.csv` : l'analyse le calcule à partir de `urban_rural` (D14).

## 4. Contrôles et reproductibilité

| Commande | Rôle |
|---|---|
| `python -m src.population.inspect_data` | Inspection de l'ENCDM et cohérence avec la note technique |
| `python -m src.population.compare_rgph` | Comparaison des marges ENCDM et RGPH |
| `python -m src.population.build_population` | Construction, validation et export de `population.csv` et de `person_weights.csv` |
| `python -m src.analysis.export --mock` | Indicateurs de la partie B sur les fichiers fictifs (sorties suffixées `_mock`) |
| `python -m src.analysis.export --simulation ... --budget ...` | Indicateurs sur la vraie simulation de Personne 2 |
| `pytest` | 89 tests (population, mock, indicateurs, ciblage, sous-groupes, export) |

Contrôles bloquants du script de construction : 15 970 lignes, somme des poids 7 190 456, taille du ménage égale au nombre d'individus pour tous les ménages, 20 312 enfants de moins de 15 ans, 12 régions, 499 `Pauvre`, 1 998 éligibles.

## 5. Indicateurs et sorties de la partie B (B1 à B8)

### 5.1 Entrées et validation (B1)

`simulation_results.csv` (12 colonnes du contrat) est validé face à `population.csv` avant tout calcul : colonnes exactes, aucune valeur manquante, aucun doublon sur (`run_id`, `scenario_id`, `month`, `household_id`), 12 mois par ménage, mêmes `household_weight` et `eligible_baseline` que la population, transferts nuls en S0, et `equiv_consumption_outcome` = `consumption_outcome` / `equivalence_factor` (ce dernier contrôle détecte des montants annuels au lieu de mensuels). Une entorse arrête l'analyse avec un message clair (D15).

### 5.2 Indicateurs (B2, B3)

- **Bien-être** : consommation équivalente par personne et par mois, en MAD de 2014. Dans un scénario, moyenne des 12 mois de chaque ménage (D17).
- **Seuil** : seuil HCP du milieu divisé par 12 (4 667 et 4 312 par an). Un ménage est pauvre si son bien-être est strictement inférieur au seuil, comme dans la règle du HCP.
- **Taux de pauvreté** : part pondérée de pauvres. **Écart de pauvreté** : écart moyen au seuil en part du seuil (indice FGT1). **Gini** : coefficient pondéré par la courbe de Lorenz. **Consommation équivalente moyenne** : moyenne pondérée.
- **Bases de pondération** : « ménage » (`household_weight`) et « personne » (`coef_indiv`, fichier `person_weights.csv`, D14). Les deux sont toujours étiquetées dans `weighting_basis`.
- **Écarts avec S0** : différence absolue entre chaque scénario et S0 dans la même réplication.
- **Valeurs non définies** : un dénominateur nul donne une valeur vide, jamais une valeur infinie ; des valeurs manquantes, des poids négatifs ou des longueurs différentes arrêtent le calcul.

### 5.3 Ciblage, coût et coût-efficacité (B4 à B6)

- Bénéficiaire : ménage dont les transferts sur 12 mois sont strictement positifs. Référence « pauvre » : ménages `Pauvre` au départ, c'est-à-dire sous le seuil avant simulation (D16).
- **Couverture** = bénéficiaires éligibles / éligibles. **Erreur d'exclusion** = pauvres non bénéficiaires / pauvres. **Erreur d'inclusion** = bénéficiaires non pauvres / bénéficiaires. L'erreur d'inclusion n'est pas mesurée par rapport à l'éligibilité, car les bénéficiaires sont tous éligibles par construction.
- **Coût** : transferts sur 12 mois pondérés par `household_weight` (annuel = cumulé), moyenne mensuelle, et somme brute de l'échantillon.
- **Coût-efficacité** : réduction annuelle de l'écart de pauvreté agrégé (en MAD, pondéré par `household_weight` x taille) divisée par le coût annuel. Vide si la dépense est nulle.
- **Budget** : si le budget annuel commun est fourni, l'analyse rapporte son utilisation et s'arrête s'il est dépassé, avec une marge d'un demi-centime par transfert mensuel (arrondi des fichiers). Le budget doit être appliqué au coût pondéré : sinon les scénarios n'ont pas le même coût national et leurs coûts-efficacités ne sont pas comparables (D15).

### 5.4 Sous-groupes (B7)

Milieu, région, taille du ménage (1 à 6, puis 7+), présence d'enfants et éligibilité. Chaque groupe a ses indicateurs, ses écarts avec S0 et ses effectifs non pondérés et pondérés. Un groupe de moins de 500 ménages non pondérés est signalé « effectif faible » dans `notes`, jamais supprimé (D12).

### 5.5 Sorties (B8)

`scenario_metrics.csv` et `group_impacts.csv` (format long), `metric_definitions.csv` (définition et unité de chaque indicateur) et `analysis_metadata.json` (fichiers d'entrée avec empreinte SHA-256, mode, budget, base de pondération des personnes). Le schéma complet est dans `data_dictionary.md`. Les fichiers issus de la mock portent le suffixe `_mock` et ne se citent jamais comme résultats.

### 5.6 Vérifications

- Sur la population de départ, les taux de pauvreté par personne reproduisent ceux du HCP : 4,78 % au niveau national, 1,64 % en urbain, 9,48 % en rural ; par région, par exemple 14,64 % pour Drâa-Tafilalet. La consommation moyenne par personne (15 875,68 MAD par an) est celle de la note technique.
- Les indicateurs, le ciblage, le coût et les sous-groupes sont testés sur de petits exemples dont les résultats sont calculés à la main (Gini de [1, 2, 3, 4] = 0,25, par exemple).
- Le Gini de départ (0,395 par personne) doit être comparé à la publication du HCP avant d'être cité.

## 6. Limites

- **Année** : données de 2014, plus de dix ans avant la simulation ; la population décrite n'est pas celle d'aujourd'hui.
- **Échantillon** : 15 970 ménages représentent environ 7,2 millions de ménages ; les résultats sont des estimations.
- **Petits groupes** : Guelmim-Oued Noun (244 ménages interrogés), Dakhla-Oued Ed Dahab (305) et Laâyoune-Sakia El Hamra (329) sont sous le seuil de travail de 500 ; Drâa-Tafilalet (628) est juste au-dessus. Résultats à signaler comme instables (D12).
- **Ménages d'une personne** : 3,89 % des ménages dans l'ENCDM contre 7,20 % dans le RGPH ; la cause (définition du ménage, échantillonnage) n'est pas établie.
- **Consommation** : `DAM` contient des postes qui ne sont pas de la consommation (impôts, transferts, remboursements de prêts) et des loyers fictifs.
- **Seuil** : un seul seuil officiel (valeurs confirmées sur la page du HCP) ; les variables `Pauvre` et `Vulnérable` ne sont pas documentées dans la note technique, mais reproduites par ce seuil.
- **Plan d'échantillonnage** : non documenté dans la note technique.
- **Éligibilité fixe** : pas de changement de statut pendant les 12 mois.
- **Base de temps** : un ménage qui passe sous le seuil quelques mois, sans l'être en moyenne sur l'année, n'est pas compté pauvre (D17) ; variante « pauvre au moins un mois » prévue en sensibilité.
- **Coût-efficacité** : il dépend de la réponse de consommation aux transferts, définie par Personne 2 (D11) ; la mock a des règles inventées et ne donne aucun résultat citable.
- **Poids des personnes** : la base « personne » utilise `coef_indiv` ; `coef_indiv` n'est pas égal à `coef_ménage` x taille (rapport de 0,68 à 4,52).

## 7. Décisions encore ouvertes

D9 (budget), D10 (formules S2 et S3), D11 (chocs et réponse de consommation) : Personne 2. D12 (petits groupes), D13 (sensibilité), D14 (`poverty_line` et `coef_indiv`), D15 (format de `simulation_results.csv`) et D16 (référence du ciblage) et D17 (base de temps) sont décidées côté P1 sans changer le contrat partagé. Le nombre de réplications et les paramètres de simulation restent à Personne 2. D6 et la convention de D15 sont à communiquer à Personne 2 avant l'intégration (M2).
