# Contribuer à Augure

> [Read in English](CONTRIBUTING.md)

Augure récompense la valeur travail apportée au projet, sous toute forme : code, donnée, recherche, design, documentation, capital. Le système est **fact-only** : seul ce qui est commité dans Git compte.

## Étapes pour participer

1. **Lis** [`README.fr.md`](README.fr.md), [`rounds/RUBRIC.fr.md`](rounds/RUBRIC.fr.md), [`rounds/HOURLY_RATES.fr.md`](rounds/HOURLY_RATES.fr.md). Le modèle économique est non-conventionnel — assure-toi qu'il te convient avant d'investir du temps.
2. **Enregistre ton wallet** dans [`rounds/WALLETS.md`](rounds/WALLETS.md) (PR signé).
3. **Apporte de la valeur** dans le module pertinent :
   - **`predictor/`** — code, datasets, RFCs de recherche sur la prédiction.
   - **`contracts/`** — Solidity, specs, audits (Phase 2+).
   - **`rounds/`** — améliorations du rubric, du prompt, des scripts, de l'automatisation.
   - **`docs/`** — architecture, modèle token, RFCs sur le projet lui-même.
   - **Cash** — virement BTC à l'adresse multisig publiée. Subscription window mensuelle ; le cash est **soumis à ratification** comme tout autre apport et peut être refusé avec motivation écrite.
4. **Cooldown** : ta première contribution doit être mergée > 30 jours avant éligibilité au mint. Filtre les drive-by.

## Ce qui n'est PAS valorisé

- Promesses, intentions, brainstorms purs.
- PRs ouverts non-mergés, ou mergés puis revertés.
- Discord, DM, conversations : non-tracé dans Git, pas valorisé.
- Heures auto-déclarées ou submissions narratives : le système ne les accepte pas.
- Code auto-généré sans curation humaine documentée.
- Gaming visible (commits fragmentés, diffs gonflés, sock-puppet reviews).

## Bonnes pratiques

- **Ouvre une issue avant un gros PR**, évite les efforts qui ne mergeront pas.
- **Lie tes PRs à des issues** pour que l'impact soit visible à l'agent.
- **Écris des descriptions PR et commit messages substantiels.** C'est l'input principal de l'agent — descriptions creuses → valuation au plancher.
- **Tests, doc, code propre augmentent ton coefficient qualité**, jusqu'à ×1,3.
- **Dette technique, régressions, travail incomplet le diminuent**, jusqu'à ×0,5.

## Mécanisme de challenge

Si tu estimes que ta valuation dans un round est incorrecte, dépose un **challenge formel** pendant la fenêtre de 7 jours :
- Commente le PR du round avec le label `challenge`.
- Signe le commentaire avec ton wallet enregistré (message signé de la forme `challenge-round-YYYY-MM-<ton-handle>`).
- Précise exactement le point de valuation contesté et pourquoi.

Un challenge déposé déclenche un vote du panel Top-X holders. Le panel valide la valuation telle quelle ou la renvoie avec instructions écrites pour révision.

## Conduite

Standard : respect, honnêteté intellectuelle, transparence. Sanctionné (warning → exclusion → slashing par vote 67 %) :

- Plagiat ou copie de code propriétaire sans attribution / licence compatible.
- Soumission répétée d'artefacts intentionnellement faits pour gamer le rubric.
- Manipulation des challenges (sock puppets, intimidation).
- Conduite hostile envers d'autres contributeurs.

## Questions

Discord du projet : `<lien à venir>`. Forum : `<lien à venir>`.
