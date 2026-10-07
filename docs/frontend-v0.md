# Frontend V0 — Julia

## Objectif

Fournir une démonstration fiable de Julia pour le congrès, centrée sur la fiscalité béninoise et sur le principe
« No source, no legal claim ».

## Architecture

- React, Vite et TypeScript.
- CSS responsive sans dépendance à une bibliothèque de composants.
- Client HTTP validé à l’exécution avec Zod.
- Markdown rendu sans activer le HTML brut.
- Mode `mock` par défaut pour travailler sans backend ; son contenu indique explicitement qu’il s’agit d’une
  démonstration et ne simule aucune règle juridique.
- Mode `live` avec `VITE_API_MODE=live`, utilisant `POST /api/v1/answers`.

## Parcours livré

1. La landing page présente le positionnement, les garanties et le périmètre fiscal actif.
2. L’utilisateur ouvre Julia et pose une question en français.
3. Le frontend envoie la question avec les filtres `fiscal` et `BJ`.
4. Julia affiche soit une réponse et ses sources, soit un refus explicite en cas de sources insuffisantes.
5. Une source ouvre un panneau contenant document, article, page, version, statut, extrait et lien original.
6. Les passages OCR sont signalés et les erreurs réseau conservent la question saisie.

## États de réponse

- `answered` : réponse accompagnée de zéro ou plusieurs sources structurées. Le backend doit normalement fournir
  au moins une source pour toute affirmation juridique.
- `insufficient_sources` : le seuil de pertinence n’est pas atteint ; l’interface affiche un avertissement.
- `clarification_required` : la question nécessite une précision. Le texte de clarification est fourni dans
  `answer_markdown`.

## Statuts documentaires

Le frontend reprend les valeurs du manifeste du corpus :

- `en_vigueur` → « En vigueur » ;
- `archive` → « Archivé » ;
- `a_verifier` → « À vérifier ».

Ces valeurs ne doivent pas être remplacées par une estimation du modèle.

## Contrat backend

Le contrat canonique est [`api/frontend-contract.yaml`](api/frontend-contract.yaml). Les champs JSON restent en
`snake_case` côté HTTP ; le client les transforme en types TypeScript internes.

L’extrait `sources[].excerpt` doit provenir de la base documentaire. Il ne doit jamais être reformulé ou produit
par le LLM. `document_url` doit ouvrir le document original, idéalement à la page indiquée.

## Validation actuelle

- ouverture du chatbot depuis la landing page ;
- envoi des filtres attendus à FastAPI ;
- réponse sourcée et panneau de détail ;
- restitution fidèle du statut d’un document archivé ;
- refus en cas de sources insuffisantes ;
- conservation de la saisie après une erreur réseau ;
- validation et conversion du schéma HTTP ;
- mode de démonstration clairement identifié.

## Hors périmètre V0

- authentification et comptes ;
- historique synchronisé côté serveur ;
- favoris ;
- ajout de documents utilisateur ;
- administration du corpus ;
- streaming de la réponse ;
- domaines autres que la fiscalité béninoise.
