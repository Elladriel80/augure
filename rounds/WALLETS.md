# WALLETS — contributors registry

*Public, versioned. Updated by signed PR. — Public, versionné. Mise à jour par PR signé.*

To be eligible for mint, a contributor must publicly link their GitHub handle to an Ethereum address in this file.

*Pour être éligible au mint, un apporteur doit lier publiquement son handle GitHub à une adresse Ethereum dans ce fichier.*

## Format

```
| GitHub handle | Ethereum address                              | Registration date | Notes |
|---------------|-----------------------------------------------|-------------------|-------|
| @<handle>     | 0x...                                         | YYYY-MM-DD        | ...   |
```

## Registration procedure / Procédure d'enregistrement

1. Fork this repo. *(Forker ce repo.)*
2. Add a row to the table below with your handle and address. *(Ajouter une ligne avec ton handle et ton adresse.)*
3. Sign with your Ethereum key a message containing your GitHub handle and the date. Paste the signature in the PR. *(Signer avec ta clé Ethereum un message contenant ton handle GitHub et la date. Coller la signature dans le PR.)*
4. Open the PR. A ratifier verifies the signature and merges. *(Ouvrir le PR. Un ratificateur vérifie la signature et merge.)*

## Registry

| GitHub handle | Ethereum address | Registration date | Notes |
|---|---|---|---|
| <to fill> | 0x... | 2026-MM-DD | Founder, retroactive valuation pending |

## Address change / Changement d'adresse

To change your address (e.g. compromise, multisig migration):
1. Open a PR updating your row.
2. Sign with **both old AND new** addresses, two linked signatures over a common message.
3. Ratification, merge.

Slashing applies to the entire history of addresses linked to the handle.

*Pour changer ton adresse (ex : compromission, migration multisig) :*
1. *Ouvrir un PR mettant à jour ta ligne.*
2. *Signer avec **l'ancienne ET la nouvelle** adresse, deux signatures liées par un message commun.*
3. *Ratification, merge.*

*Le slashing court sur l'historique entier des adresses liées au handle.*

## Withdrawal / Retrait

If a contributor wishes to leave: their tokens remain (acquired property), their entry stays in the registry for traceability, but their row is marked `STATUS: WITHDRAWN` and they are excluded from subsequent rounds.

*Si un apporteur souhaite quitter : ses tokens lui restent (propriété acquise), son entrée reste au registre pour traçabilité, mais sa ligne est marquée `STATUS: WITHDRAWN` et il n'est plus inclus dans les rounds suivants.*
