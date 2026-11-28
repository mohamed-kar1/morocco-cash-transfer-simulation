# Inventaire des sources de données

Projet : Morocco Cash-Transfer Policy Evaluation Simulation
Responsable : Personne 1 (Population Generator)
Dernière mise à jour : 2026-11-23
Statut : ENCDM inspectée, RGPH comparé, `population.csv` construit ; à compléter avec la méthodologie

Légende des étiquettes :
- **[Documenté]** : écrit dans la documentation officielle du HCP.
- **[Observé]** : constaté en ouvrant les fichiers (voir la section Contrôles).
- **[Non vérifié]** : pas encore contrôlé ou non documenté.

---

## 1. ENCDM 2014 : source principale retenue à titre provisoire

| Champ | Valeur |
|---|---|
| Titre | Enquête Nationale sur la Consommation et les Dépenses des Ménages (ENCDM) 2014, fichier de microdonnées à grande diffusion (FMGD) |
| Institution | Haut-Commissariat au Plan (HCP), Maroc |
| Année de référence | 2014 ; collecte 2013/2014 [Documenté] |
| Unité d'observation | Ménage (fichier Ménage) et personne (fichier Individus) |
| Taille | 15 970 ménages, 75 691 personnes [Documenté, Observé] |
| Niveaux géographiques | National et régional selon la note technique ; milieu urbain/rural ; 12 régions dans le fichier [Documenté, Observé] |
| Plan d'échantillonnage | [Non vérifié] : la note technique ne décrit pas le plan (strates, grappes) |
| Poids | `coef_ménage` (ménages) et `coef_indiv` (personnes) ; la note appelle ce dernier `coef_individu_sum` [Documenté, Observé] |
| Monnaie et prix | Dirhams (MAD) courants, année 2014 [Documenté] |
| Variable de bien-être | `DAM` (dépense annuelle du ménage) et `DAP` (dépense annuelle par personne, égale à `DAM / taille`) [Documenté, Observé] |
| Format | SPSS (.sav) |
| Accès | Données ouvertes, site du HCP (page Micro données - Open Data). Aucune inscription constatée. Accès le 2026-11-22. Conditions de réutilisation : à confirmer sur la page du HCP |
| Dépôt GitHub | **Versionnée** dans `data/raw/encdm_2014/` (environ 37 Mo) : elle suffit à reproduire `population.csv`. Les fichiers dérivés `population.csv` (versionné) et `person_weights.csv` (interne, non versionné) sont décrits dans `data_dictionary.md` |
| Documentation | Note technique (métadonnées, 01/11/2019), nomenclature Bien et Service 2014, questionnaires ménage (fr, ar) et dépense (ar) |
| Citation suggérée par le HCP | Haut-commissariat au Plan (2019). Les données sur la consommation et les dépenses des ménages au Maroc. Fichier de microdonnées à grande diffusion (FMGD). Web. |
| Fichiers locaux | `Ménage_ENCDM_2014_en_format_SAV.sav`, `Individus__ENCDM_2014_en_format_SAV.sav` (ne pas committer, voir `.gitignore`) |

### Variables utiles au projet

| Besoin du contrat `population.csv` | Variable source | État |
|---|---|---|
| `household_id` | `N_ménage` | Disponible, unique [Observé] |
| `household_weight` | `coef_ménage` (voir règle D7) | Disponible, tous positifs [Observé] |
| `region` | `Région_12` | Disponible, 12 modalités [Observé] |
| `urban_rural` | `Milieu` (1 = Urbain, 2 = Rural) | Disponible [Observé] |
| `household_size` | `Taille_ménage` (texte avec espaces) | Converti en entier [Observé, 23 nov.] |
| `children_count` | Dérivé du fichier Individus (âge) | Construit : moins de 15 ans (D8) |
| `baseline_consumption` | `DAM / 12` (mensuel) | Construit : DAM total (D3) |
| `equivalence_factor` | Absent du fichier | Construit : taille du ménage (D2) |
| `equiv_consumption` | `baseline_consumption / equivalence_factor` | Construit |
| `eligible_baseline` | `Pauvre` ou `Vulnérable` (HCP) | Construit : 1 998 ménages éligibles (D5, D6) |

### Anomalies de documentation relevées
1. **Poids** : le texte de la note (Note 2) associe `coef_ménage` à DAP et `coef_individu_sum` à DAM. Les chiffres de contrôle publiés dans la même note sont reproduits par l'inverse : DAM moyenne = 76 317,23 avec `coef_ménage` (79 263,8 avec `coef_indiv`), DAP moyenne = 15 875,68 avec `coef_indiv` (19 413,1 avec `coef_ménage`). Règle retenue : D7.
2. **Pauvreté** : les variables `Pauvre`, `Vulnérable`, `Quintiles`, `Deciles` sont dans le fichier mais ne figurent pas dans la note technique. Le seuil officiel est publié à part par le HCP (Documenté, page « Méthodologie pauvreté & vulnérabilité ») : 4 667 MAD/personne/an en urbain, 4 312 en rural, en dirhams de 2014 ; les coupures observées dans les données le confirment (Observé). Valeurs relues dans le texte de la page le 25 nov.
3. **Âge** : la note indique « âge simple 15-98 ans » pour le fichier Individus, alors que le fichier contient des âges de 0 à 98.
4. **Page HCP** : la page de téléchargement indique « réalisée en 2006/2007 » pour l'ENCDM 2014, ce qui est une erreur évidente (la note et le fichier indiquent 2013/2014).
5. **Types** : `Taille_ménage` et `Age_CM` sont du texte avec espaces dans le fichier SAV.

---

## 2. RGPH 2014 (HCP) : contrôle de représentativité, non utilisé pour construire `population.csv`

| Champ | Valeur |
|---|---|
| Titre | Recensement Général de la Population et de l'Habitat 2014, microdonnées anonymisées |
| Institution | HCP |
| Taille | Échantillon de 10 % ; 730 099 ménages, 3 341 426 personnes, 85 variables [Documenté par le HCP] |
| Formats | SPSS, STATA, texte |
| Contenu | Démographie, éducation, emploi, logement. Aucune variable de consommation dans les fichiers Ménage et Individu [Observé, 23 nov.] |
| Fichiers utilisés | Fichier Ménage au format SPSS (53 Mo), lu par `compare_rgph` (variables `REG`, `MIL`, `TAILLE`, `MEN.TYPE`, `PDS`) |
| Fichiers non utilisés | Fichier Individu (307 Mo) : téléchargé, jamais utilisé, supprimé du poste le 2026-11-28 ; autres formats (STATA, texte) et questionnaires non conservés |
| Dépôt GitHub | **Non versionné** : volume (le fichier Individu dépasse la limite de 100 Mo de GitHub) et rôle secondaire. À télécharger sur le site du HCP et à placer dans `data/raw/rgph_2014/` pour relancer `compare_rgph` ; voir `data/raw/README.md` |
| Rôle | Contrôle de représentativité de l'ENCDM ; pas de calibration IPF (D1) |
| État | Inspecté le 23 nov. : comparaison agrégée avec l'ENCDM (`outputs/inspection/rgph_vs_encdm.md`) |

## 3. IPUMS International, Maroc : écarté

| Champ | Valeur |
|---|---|
| Titre | Maroc, recensement 2014, sous-ensemble harmonisé IPUMS (version 7.5) |
| Taille | 3 341 426 enregistrements de personnes [Documenté, catalogue Banque mondiale] |
| Contenu | Variables démographiques, éducation, emploi, logement ; aucune variable de consommation ou de revenu repérée dans la liste consultée |
| Accès | Inscription et licence IPUMS ; redistribution à des tiers interdite |
| État | Non téléchargé, non utilisé ; recensement identique au RGPH 2014 du HCP, donc inutile |

## 4. Documents d'appui

| Document | Usage | État |
|---|---|---|
| Nomenclature Bien et Service 2014 | Définir le périmètre de `DAM` (notamment le groupe 9) | Analysée le 23 nov. : groupe 9 = impôts, transferts, prêts ; loyers fictifs dans le groupe 3 (D3) |
| HCP, page « Méthodologie pauvreté & vulnérabilité » (https://www.hcp.ma/methodologie-pauvrete-vulnerabilite_r497.html) | Seuil de pauvreté officiel 2014 : 4 667 MAD (urbain), 4 312 MAD (rural) par personne et par an | Consultée le 23 nov. 2026, texte relu le 25 nov. ; reproduit 499 ménages pauvres et 1 998 éligibles sur les données (D5) |
| Troisième rapport du Maroc sur l'Agenda 2063 (HCP, octobre 2023) | Vérification croisée : taux de pauvreté national de 4,8 % en 2014 | Utilisé pour le contrôle ci-dessous |

---

## Contrôles effectués le 2026-11-22 sur l'ENCDM 2014

- `N_ménage` unique ; les 15 970 ménages du fichier Ménage sont tous présents dans le fichier Individus ; la taille du ménage égale le nombre de lignes du fichier Individus pour 100 % des ménages.
- `coef_ménage` > 0 pour tous les ménages ; somme = 7 190 456 ménages. Somme de `coef_indiv` = 33 579 281 personnes.
- `DAM` > 0 pour tous les ménages ; médiane non pondérée 58 098 MAD par an.
- Répartition : 10 380 ménages urbains, 5 590 ruraux.
- Indicateur HCP `Pauvre` : 499 ménages ; `Vulnérable` : 1 499 ménages ; aucun chevauchement.
- Taux de pauvreté avec `Pauvre` : 4,78 % pondéré par personne (`coef_indiv`) contre 3,0 % pondéré par ménage (`coef_ménage`). Le premier est cohérent avec les 4,8 % du rapport Agenda 2063 pour 2014. Par milieu (pondération personnes) : 1,64 % urbain, 9,48 % rural.
- `DAM_G9` (paiements fiscaux, transferts, prêts) existe dans le fichier : moyenne 2 640 MAD contre 75 068 pour `DAM` (non pondéré) [Observé, exécution du 23 nov.].
- Régions à faible effectif non pondéré (ménages) : Guelmim-Oued Noun 244, Dakhla-Oued Ed Dahab 305, Laâyoune-Sakia El Hamra 329, Drâa-Tafilalet 628.

## Contrôles du 2026-11-23 : RGPH et `population.csv`

- Comparaison ENCDM / RGPH (parts pondérées) : ménages représentés 7 190 456 contre 7 300 986 ; milieu, écart maximal 0,39 point ; région, écart maximal 0,08 point ; taille du ménage, écart maximal 3,32 points (ménages d'une personne : 3,89 % contre 7,20 %) [Observé]. Aucun filtre « ménage ordinaire » appliqué au RGPH (aucun type correspondant dans `MEN.TYPE`).
- `population.csv` construit par `src/population/build_population.py` : 15 970 lignes, somme de `household_weight` = 7 190 456, 499 ménages `Pauvre`, 1 499 `Vulnérable`, 1 998 éligibles, 12 régions ; `Pauvre` et `Vulnérable` codés 1 = oui ; taille du ménage égale au nombre d'individus pour tous les ménages ; libellés de région et d'urbain/rural identiques à la mock [Observé].

## Limites connues
- Les ménages d'une personne et de deux personnes sont sous-représentés dans l'ENCDM par rapport au RGPH (comparaison du 23 nov. ; définition des ménages à vérifier).
- Données de 2014, soit plus de dix ans avant la simulation.
- Le plan d'échantillonnage n'est pas documenté dans la note.
- Le seuil derrière `Pauvre` n'est pas dans la note technique ; il vient de la page HCP citée plus haut (voir D5).
- Les résultats par petite région devront être signalés comme instables (Note 5 de la note technique).