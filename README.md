# Morocco Cash-Transfer Policy Evaluation Simulation

Simulation conditionnelle aux hypothèses : on compare quatre règles de distribution d'un même budget de transferts monétaires (S0 aucun transfert, S1 transfert égal, S2 selon la taille du ménage, S3 selon l'écart de pauvreté) sur une population de ménages marocains, avec des chocs mensuels sur 12 mois. Les résultats décrivent la simulation, pas l'effet réel d'un programme.

## Rôles
- **Personne 1** : Population Generator et Distributional Impact Analyst (`src/population/`, `src/analysis/`).
- **Personne 2** : Behavior Simulator, rapport et dashboard (`src/simulation/`, `src/reporting/`, `app/`).

Les schémas CSV partagés sont des contrats figés. Aucune modification sans accord des deux personnes.

## Structure
```
data/raw/          microdonnées brutes (ignorées par Git, jamais modifiées)
data/interim/      fichiers intermédiaires
data/processed/    sorties validées (population.csv, person_weights.csv, puis les sorties de la partie B)
data/mock/         fixtures conformes aux contrats
src/population/    inspect_data, compare_rgph, build_population (la validation est dans build_population ; pas d'IPF, voir D1)
src/analysis/      metrics, targeting, subgroups, export
src/simulation/    (Personne 2)
src/reporting/     (Personne 2)
app/               dashboard Streamlit (Personne 2)
tests/             tests unitaires et de contrat
docs/              data_sources.md, pending_decisions.md, methodology.md, data_dictionary.md
outputs/           rapports générés (inspection/ : inspection et comparaison RGPH ; build/ : journal de construction)
```

## Installation
Python 3.11 ou plus récent.
```
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Données
Les fichiers sources ne sont pas dans le dépôt. Voir `data/raw/README.md` pour savoir où les placer.

## Première étape : inspection de l'ENCDM 2014
```
python -m src.population.inspect_data
```
Le script lit les fichiers SAV de `data/raw/encdm_2014/`, exécute les contrôles et écrit un rapport (Markdown et JSON) dans `outputs/inspection/`. Options : `python -m src.population.inspect_data --help`.

## Construire `population.csv`
```
python -m src.population.build_population
```
Le script lit l'ENCDM 2014 (`data/raw/encdm_2014/`), construit les 10 colonnes du contrat (règles D2 à D8 dans `docs/pending_decisions.md`), vérifie les chiffres de contrôle (15 970 lignes, somme des poids 7 190 456, 499 `Pauvre`, 1 998 éligibles, 20 312 enfants de moins de 15 ans) et écrit :
- `data/processed/population.csv`,
- `outputs/build/population_build_log.md` (lignes avant et après chaque opération).

Le script s'arrête avec un message si un contrôle échoue. Le schéma du fichier est décrit dans `docs/data_dictionary.md`.

## Comparer l'ENCDM et le RGPH
```
python -m src.population.compare_rgph
```
Compare les parts pondérées par milieu, région et taille du ménage (fichier Ménage du RGPH dans `data/raw/rgph_2014/`) et écrit `outputs/inspection/rgph_vs_encdm.md`. Cette comparaison justifie le choix de source unique (D1).

## Calculer les indicateurs (partie B)
```
python -m src.analysis.export --mock
python -m src.analysis.export --simulation data/processed/simulation_results.csv --budget MONTANT
```
Le premier mode lit les fichiers fictifs de `data/mock/` et écrit des fichiers suffixés `_mock` (jamais citables comme résultats). Le second valide `simulation_results.csv` face à `population.csv`, puis écrit `scenario_metrics.csv`, `group_impacts.csv`, `metric_definitions.csv` et `analysis_metadata.json`. Les définitions sont dans `docs/methodology.md` (section 5) et le schéma dans `docs/data_dictionary.md`.

## Tests
```
pytest
```
Les tests sur les vraies données (construction, taux de pauvreté de départ) se déclenchent quand `data/processed/population.csv` et `data/processed/person_weights.csv` existent.

## Flux de travail
- Une branche par personne (par exemple `person1/population`), des fixtures mock conformes aux contrats tant que l'autre composant n'est pas prêt.
- Jalons : M1 sources et définitions, M2 schémas et mocks figés, M3 développement et tests, M4 échange de sorties et tests de contrat, M5 intégration, M6 expériences et sensibilité, M7 rapport et documentation.
- Ne pas committer de microdonnées restreintes. Respecter les licences des sources.
- Les décisions ouvertes sont suivies dans `docs/pending_decisions.md`.