# Registre des décisions en attente

Projet : Morocco Cash-Transfer Policy Evaluation Simulation
Tenu par : Personne 1
Dernière mise à jour : 2026-11-25

Règle : aucune décision ci-dessous n'est actée tant que son état n'est pas « Décidée ». Une « proposition provisoire » est une piste de travail, pas un choix de l'équipe. Chaque personne avance de façon indépendante : P1 fixe ses choix dès qu'ils sont étayés par une source ou une observation, et les aligne avec P2 au moment de figer les schémas (M2). « Décidée (P1) » = choix fait, révisable à l'alignement.

Propriétaire : P1 = Personne 1, P2 = Personne 2, P1+P2 = décision commune.

## Vue d'ensemble

| ID | Sujet | Propriétaire | État |
|---|---|---|---|
| D1 | Source de données et méthode (IPF ou source unique) | P1 | Décidée (P1) : ENCDM seule, poids conservés, pas d'IPF |
| D2 | Facteur d'équivalence | P1+P2 | Décidée (P1) : taille du ménage |
| D3 | Périmètre de `DAM` | P1 | Décidée (P1) : DAM total, variante sans groupe 9 |
| D4 | Période de référence et base de prix | P1+P2 | Décidée (P1) : DAM / 12, MAD courants 2014 |
| D5 | Seuil de pauvreté | P1+P2 | Décidée (P1) : seuils HCP par milieu |
| D6 | Règle d'éligibilité | P1+P2 | Décidée (P1) : Pauvre + Vulnérable, fixe |
| D7 | Règle des poids | P1 | Décidée (P1) |
| D8 | Seuil d'âge de `children_count` | P1 | Décidée (P1) : moins de 15 ans |
| D9 | Budget annuel commun | P2 (avec P1) | En attente |
| D10 | Formules S2 et S3, planchers, plafonds | P2 (avec P1) | En attente |
| D11 | Chocs et réponse de consommation | P2 | En attente |
| D12 | Règle des petits groupes | P1 | Décidée (P1) : seuil de 500 ménages non pondérés, groupes signalés et jamais supprimés |
| D13 | Réplications et sensibilité | P1+P2 | Décidée (P1) pour la population et les métriques ; nombre de réplications et paramètres de simulation : P2 |
| D14 | Colonnes `poverty_line` et `coef_indiv` dans `population.csv` | P1 | Décidée (P1) : contrat inchangé, `coef_indiv` dans un fichier interne, seuil calculé par l'analyse |
| D15 | Format de `simulation_results.csv` (unités, grain, définitions) | P1+P2 | Décidée (P1) : convention exigée par l'analyse, à communiquer à P2 |
| D16 | Référence du ciblage (bénéficiaires, couverture, erreurs d'inclusion et d'exclusion) | P1 | Décidée (P1) : référence = ménages `Pauvre` |
| D17 | Base de temps et pondération des indicateurs de la partie B | P1 | Décidée (P1) : moyenne des 12 mois ; coût-efficacité en poids ménage x taille |

---

## Décisions détaillées

### D1. Source de données et méthode de génération
- **Question** : quelle source de microdonnées, et IPF ou non ?
- **Constats** : seule l'ENCDM 2014 contient la consommation des ménages. L'IPUMS Maroc et le RGPH 2014 portent sur le même recensement et ne contiennent pas de consommation (RGPH confirmé sur la liste des variables du fichier le 23 nov. ; IPUMS non téléchargé, donc non vérifié).
- **Constats (comparaison du 23 nov., `outputs/inspection/rgph_vs_encdm.md`, parts pondérées)** : le RGPH (fichier à 10 %, 730 099 ménages) ne contient aucune variable de consommation. Ménages représentés : 7 190 456 (ENCDM) contre 7 300 986 (RGPH). Milieu : écart maximal 0,39 point. Région : écart maximal 0,08 point. Taille du ménage : seul écart supérieur à 2 points, avec 3,89 % de ménages d'une personne dans l'ENCDM contre 7,20 % dans le RGPH (-3,32 points) ; les ménages de 4 à 6 personnes sont sur-représentés de 1,3 à 1,8 point. Aucun filtre « ménage ordinaire » n'a pu être appliqué au RGPH (aucun type correspondant dans `MEN.TYPE`) : l'écart sur la taille 1 peut venir en partie de la définition des ménages.
- **Décision (23 nov., P1)** : ENCDM 2014 comme source unique, avec `coef_ménage` tel quel, sans IPF. Motif : région et milieu sont déjà alignés sur le RGPH ; l'écart de taille n'est pas interprétable sans définition commune des ménages. Limite à écrire dans `methodology.md` : les petits ménages sont sous-représentés dans l'ENCDM par rapport au RGPH.
- **Variante de sensibilité (D13)** : calage des poids sur la taille du ménage, avec comparaison du taux de pauvreté et du ciblage. Le seuil de 2 points du rapport est une valeur de travail.

### D2. Facteur d'équivalence
- **Question** : quelle échelle pour `equivalence_factor` ?
- **Options** : (a) taille du ménage, soit la dépense par personne, ce que fait déjà `DAP` ; (b) une échelle d'adulte équivalent à sourcer (par exemple OCDE modifiée).
- **Constat** : la coupure observée de l'indicateur `Pauvre` correspond à une dépense par personne (D5), donc l'option (a) reproduit la logique du HCP.
- **Contrainte** : le document maître préfère l'adulte équivalent « si défendable » ; ne pas citer d'échelle sans source vérifiée.
- **Décision (23 nov., P1)** : option (a), `equivalence_factor = taille du ménage`. Motif : `DAP = DAM / taille` est vérifié dans le fichier (écart nul) et le seuil HCP est par personne (D5). Une échelle d'adulte équivalent pourra être testée en sensibilité (D13), avec une source vérifiée.

### D3. Périmètre de `DAM`
- **Question** : `DAM` couvre « tous les biens et services de la nomenclature ». Il inclut le groupe 9 (paiements fiscaux, transferts, remboursements de crédits). Le garde-t-on comme « consommation » ?
- **Constats (nomenclature et note technique, 23 nov.)** : le groupe 9 regroupe les paiements fiscaux (91 : vignette, taxes, impôts sur le revenu), les transferts en espèce (92 : envois à la famille, Zakat, dons), les transferts en nature (93), les remboursements de prêts (94) et les transferts vers des membres absents (95). Le groupe 3 inclut des loyers fictifs (code 3111, loyer imputé aux propriétaires) : `DAM` n'est donc pas une dépense purement monétaire. La note fournit `DAM_G1` à `DAM_G9` : `DAM` hors groupe 9 se calcule par `DAM - DAM_G9`.
- **Décision (23 nov., P1)** : `baseline_consumption` = `DAM` total / 12. Motif : la coupure de `Pauvre` observée est nette sur `DAP = DAM / taille` (D5), donc le HCP classe les pauvres sur le `DAM` total, groupe 9 inclus ; garder le même périmètre reste cohérent avec le seuil officiel. Limite à documenter : `DAM` contient des postes qui ne sont pas de la consommation (impôts, transferts, remboursements) et des loyers fictifs.
- **Variante de sensibilité** : `DAM - DAM_G9`. Vérifié dans le fichier (23 nov., exécution locale) : `DAM_G9` existe, moyenne 2 640 MAD contre 75 068 pour `DAM` (non pondéré), médiane 400, part moyenne par ménage 2,5 %. Test de sensibilité (non pondéré) : avec les seuils HCP de D5, `DAM` total donne 499 ménages pauvres (identique au drapeau `Pauvre` du HCP) ; `DAM - DAM_G9` en donne 526. 27 ménages (0,17 % des ménages, 5,4 % des pauvres) changent de statut, tous dans le sens non pauvre vers pauvre. L'effet est limité mais pas nul : à mentionner dans la sensibilité.

### D4. Période de référence et base de prix
- **Constats** : dépenses annuelles en MAD courants 2014 ; la simulation tourne en pas mensuels.
- **Proposition provisoire** : `baseline_consumption = DAM / 12` (MAD par mois, prix courants 2014). Le budget annuel des scénarios devra être exprimé dans la même base, ou avec un ajustement de prix documenté.
- **Décision (23 nov., P1)** : `baseline_consumption = DAM / 12`, en MAD courants 2014 (documenté dans la note technique). Le budget de P2 (D9) doit être dans la même base.

### D5. Seuil de pauvreté
- **Constats** : la note technique ne documente ni `Pauvre` ni de seuil. Observation sur les données (non officielle) : la coupure de `Pauvre` se situe entre 4 655 et 4 676 MAD par personne et par an en urbain, et entre 4 310 et 4 317 MAD en rural.
- **Source officielle (consultée le 23 nov. 2026)** : HCP, page « Méthodologie pauvreté & vulnérabilité » (https://www.hcp.ma/methodologie-pauvrete-vulnerabilite_r497.html). Seuil de pauvreté monétaire, en dirhams de 2014 par personne et par an : **4 667 MAD en urbain, 4 312 MAD en rural**. Ligne alimentaire : 2 331 MAD. Vulnérabilité : entre 1 et 1,5 fois le seuil (urbain 4 667 à 7 001 ; rural 4 312 à 6 468). Taux 2014 : 4,8 % national, 1,6 % urbain, 9,5 % rural.
- **Contrôle** : les coupures observées dans les données (4 655 / 4 676 urbain, 4 310 / 4 317 rural) encadrent ces seuils ; appliqués à `DAM / taille`, ils donnent exactement 499 ménages pauvres, comme le drapeau `Pauvre` du HCP.
- **Décision (23 nov., P1)** : seuil différencié par milieu, converti en mensuel par ÷ 12 (environ 389 et 359 MAD). Base de prix : MAD courants 2014 (D4).
- **Confirmé (25 nov.)** : valeurs relues dans le texte de la page HCP (seuils 4 667 et 4 312 ; ligne alimentaire 2 331 ; vulnérabilité de 1 à 1,5 fois le seuil, soit 4 667 à 7 001 en urbain et 4 312 à 6 468 en rural). Appliqués à `equiv_consumption × 12` dans `population.csv`, ils redonnent exactement 499 pauvres et 1 998 pauvres ou vulnérables.

### D6. Règle d'éligibilité (`eligible_baseline`)
- **Constats** : `Pauvre` seul = 499 ménages (effectif faible pour S1 à S3) ; `Pauvre` + `Vulnérable` = 1 998 ménages.
- **Décision (23 nov., P1)** : `eligible_baseline = 1` si le ménage est `Pauvre` ou `Vulnérable` (indicateur HCP, cohérent avec les seuils de D5), soit 1 998 ménages non pondérés ; fixe pendant les 12 mois (valeur initiale du guide). Aucune valeur manquante sur `DAM`. `Pauvre` seul (499) reste une variante de sensibilité.

### D7. Règle des poids
- **Constats** : voir `data_sources.md`, anomalie 1.
- **Décision (23 nov., P1)** : `household_weight = coef_ménage` ; poids personne `coef_indiv` pour les indicateurs par personne (pauvreté par personne). Ne jamais interchanger les deux dénominateurs.
- **Résolu (25 nov., P1, voir D14)** : le contrat `simulation_results.csv` ne contient qu'un `household_weight`. Les mesures par personne utilisent `coef_indiv`, fourni par le fichier interne `person_weights.csv` et joint par `household_id`. Aucun changement du contrat partagé.

### D8. Seuil d'âge de `children_count`
- **Constats** : le fichier Individus contient l'âge ; 20 312 personnes de moins de 15 ans et 24 515 de moins de 18 ans (non pondéré).
- **Décision (23 nov., P1)** : enfant = moins de 15 ans (`children_count` = nombre de personnes de moins de 15 ans dans le ménage). Moins de 18 ans reste une variante de sensibilité. Utile pour S2 (taille) et pour la lecture du ciblage.

### D9. Budget annuel commun
- **À décider** : montant, calendrier de versement, règle en cas de dépassement (mise à l'échelle ou priorité). Le montant est une hypothèse de scénario à justifier, pas un fait.

### D10. Formules S2 et S3
- **À décider** : S2 (fonction de la taille, minimum, maximum) ; S3 (écart de pauvreté, plancher, plafond, traitement des ménages au-dessus du seuil). Dépend de D5.

### D11. Chocs et réponse de consommation
- **À décider (P2)** : lois des chocs, corrélations, propension à consommer. À étiqueter comme hypothèses avec analyse de sensibilité.

### D12. Règle des petits groupes
- **Constats** : Guelmim-Oued Noun 244, Dakhla-Oued Ed Dahab 305, Laâyoune-Sakia El Hamra 329, Drâa-Tafilalet 628 ménages (non pondérés).
- **Décision (25 nov., P1)** : un groupe est signalé « effectif faible » dans la colonne `notes` de `group_impacts.csv` s'il compte moins de 500 ménages non pondérés. Aucun groupe n'est supprimé, et les effectifs pondérés et non pondérés sont toujours donnés. Trois régions sont signalées (Guelmim-Oued Noun, Laâyoune-Sakia El Hamra, Dakhla-Oued Ed Dahab) ; Drâa-Tafilalet (628) n'est pas signalée mais sera commentée dans le rapport. Le seuil de 500 est une valeur de travail, testable en sensibilité.

### D13. Réplications et sensibilité
- **Décision (25 nov., P1)** : les métriques sont calculées par `run_id`, puis résumées sur l'ensemble des réplications (moyenne et intervalle), quel que soit leur nombre. Sensibilités prévues côté population et métriques : (a) éligibilité `Pauvre` seul (D6) ; (b) `DAM` sans groupe 9 (D3) ; (c) enfant = moins de 18 ans (D8) ; (d) calage des poids sur la taille du ménage (D1) ; (e) échelle d'adulte équivalent (D2), seulement avec une source vérifiée.
- **Reste à P2** : le nombre de réplications et les plages des paramètres de transfert, de chocs et de réponse de consommation (D9 à D11).

### D14. Colonnes supplémentaires dans `population.csv`
- **Constats** : S3 (écart de pauvreté) a besoin du seuil de chaque ménage ; les mesures par personne (D7) ont besoin de `coef_indiv`. Ni l'un ni l'autre n'est dans le contrat. Le contrat partagé est gelé : tout changement demande l'accord de P2.
- **Décision (25 nov., P1)** : le contrat `population.csv` ne change pas (10 colonnes). (1) `coef_indiv` est exporté dans un fichier interne, `data/processed/person_weights.csv` (`household_id`, `person_weight`), produit par `build_population.py` et joint par l'analyse ; sa somme (33 579 281) reproduit le rapport d'inspection. (2) `poverty_line` n'est pas une colonne : l'analyse la calcule à partir de `urban_rural` (D5 : 4 667 / 12 et 4 312 / 12 MAD par mois et par personne). P2 peut faire de même pour S3.
- **Information à P2** : rien à adopter. Si P2 préfère une colonne `poverty_line` ou `coef_indiv`, l'ajout reste possible plus tard sans effet sur le reste.

### D15. Format de `simulation_results.csv`
- **Constats** : le contrat donne les 12 colonnes, mais pas les unités ni les définitions.
- **Décision (25 nov., P1)** : convention exigée par l'analyse (B1). Une ligne par ménage, mois, scénario et réplication ; clé unique `run_id`, `scenario_id`, `month`, `household_id`. Montants (`economic_shock`, `transfer_amount`, `disposable_resources`, `consumption_outcome`) en MAD par mois ; `equiv_consumption_outcome` = `consumption_outcome` / `equivalence_factor` (par personne et par mois) ; chocs identiques entre scénarios d'une réplication. L'analyse valide le schéma, les clés, les doublons et les ordres de grandeur, et s'arrête avec un message clair si les unités diffèrent.
- **Budget commun (exigence de P1, lié à D9)** : il doit être appliqué au coût pondéré par `household_weight` (coût national), et non à la somme brute de l'échantillon. Sinon S1, S2 et S3 n'ont pas le même coût national et leurs coûts-efficacités ne sont pas comparables : sur la mock, un budget identique de 48 000 MAD sur l'échantillon donne 24,6, 24,8 et 28,7 millions de MAD pondérés. `targeting.py` contrôle le budget dans les deux bases (`budget_basis`).
- **À communiquer à P2** : cette convention est une exigence de P1 pour consommer le fichier. Si P2 produit autre chose, l'écart sera visible dès la validation.

### D16. Référence du ciblage
- **Constats** : l'éligibilité est `Pauvre` ou `Vulnérable` (D6) ; tous les bénéficiaires sont donc éligibles par construction. Une erreur d'inclusion mesurée par rapport à l'éligibilité serait toujours nulle.
- **Décision (25 nov., P1)** : ménage bénéficiaire = ménage avec `transfer_amount` > 0 au moins un mois de la réplication. Couverture = bénéficiaires / éligibles. Erreur d'exclusion = ménages `Pauvre` non bénéficiaires / ménages `Pauvre`. Erreur d'inclusion = bénéficiaires non `Pauvre` / bénéficiaires. Chaque taux est donné en base ménage (`household_weight`) et en base personne (`person_weight`). `Pauvre` est déduit de `equiv_consumption` × 12 sous le seuil du milieu (D5), qui redonne exactement les 499 ménages `Pauvre` du HCP.

### D17. Base de temps et pondération des indicateurs
- **Constats** : le maître demande d'expliquer si les résultats sont mensuels, de fin d'année, annualisés ou cumulés. Le seuil du HCP est annuel par personne ; la simulation est mensuelle.
- **Décision (26 nov., P1)** : le bien-être d'un ménage dans un scénario est la moyenne de ses 12 mois de consommation équivalente (MAD par personne et par mois), comparée au seuil mensuel (seuil annuel / 12). Les coûts sont cumulés sur 12 mois (annuel = cumulé). Le coût-efficacité utilise `household_weight` x taille pour l'écart de pauvreté, afin de rester dans le même univers de pondération que le coût.
- **Limite** : un ménage qui passe sous le seuil quelques mois sans l'être en moyenne n'est pas compté pauvre. Variante de sensibilité prévue : « pauvre au moins un mois » (D13).
- **Arrondi** : les fichiers arrondissent chaque transfert au centime ; le contrôle du budget tolère au plus un demi-centime par transfert mensuel (`targeting.py`).

---

## Journal des changements
- 2026-11-22 : création du registre ; D1 à D13 ouverts.
- 2026-11-23 : D2 à D8 décidées (P1) ; D3 : test de sensibilité sans groupe 9 (27 ménages changent de statut) ; D5 : source HCP et contrôle sur les données ; D14 ouverte.
- 2026-11-23 : D1 décidée (P1) après comparaison avec le RGPH : ENCDM seule, pas d'IPF.
- 2026-11-23 : `population.csv` construit par `src/population/build_population.py` : 15 970 lignes, somme des poids 7 190 456, 499 ménages `Pauvre`, 1 499 `Vulnérable`, 1 998 éligibles (D6), 12 régions. Aucune exclusion de ménage.
- 2026-11-25 : D12, D13, D14, D15 décidées (P1) ; D16 ajoutée et décidée. Contrat `population.csv` inchangé ; `person_weights.csv` (`coef_indiv`, somme 33 579 281) produit par `build_population.py`.
- 2026-11-28 : fichier RGPH Individu (jamais utilisé, 307 Mo) supprimé du poste ; RGPH non versionné sur GitHub (volume), ENCDM 2014 versionnée ; `data_sources.md` et `data/raw/README.md` mis à jour.
- 2026-11-26 : partie B écrite : `metrics.py`, `targeting.py`, `subgroups.py`, `export.py` avec leurs tests ; D17 décidée (P1).