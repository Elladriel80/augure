# Politique de sécurité

> [Read in English](SECURITY.md)

## Signaler une vulnérabilité

Si vous pensez avoir trouvé une faille de sécurité dans ce dépôt
— smart contracts, predictor, dashboard ou tooling CI — **merci de ne
pas ouvrir d'issue GitHub publique**.

Contactez le mainteneur directement par email :

- **Contact :** `REDACTED-EMAIL`
- **Clé PGP :** *(pas encore publiée — demander hors-bande si vous
  avez besoin d'un transport chiffré)*

Merci d'inclure :

1. Une description de la vulnérabilité et du composant concerné.
2. Étapes de reproduction, ou proof-of-concept si disponible.
3. L'impact qu'un attaquant pourrait obtenir selon vous.
4. Un correctif suggéré, si vous en avez un.

Nous accusons réception sous **3 jours ouvrés** et fournissons une
évaluation initiale sous **10 jours ouvrés**. Les vulnérabilités
critiques touchant des fonds on-chain ou la sécurité des utilisateurs
sont prioritaires sur tout le reste.

## Politique de divulgation

Ce projet suit un modèle de **divulgation coordonnée** :

- Nous travaillerons avec vous pour confirmer, reproduire et trier
  l'issue.
- Nous demandons de ne **pas** divulguer publiquement les détails
  avant qu'un fix soit publié ou qu'un délai mutuellement convenu se
  soit écoulé (par défaut : **90 jours après le rapport initial**).
- Nous vous créditons dans les notes de version du fix sauf demande
  contraire.

## Périmètre

| Composant               | Couvert | Notes                                          |
|-------------------------|---------|------------------------------------------------|
| `contracts/`            | Oui     | Sources Solidity, scripts deploy, tests foundry. Voir [`contracts/docs/SECURITY.fr.md`](contracts/docs/SECURITY.fr.md) pour le threat model on-chain. |
| `predictor/`            | Oui     | Code Python qui fetche marchés et météo, génère prédictions, poste Discord. |
| `dashboard/`            | Oui     | Dashboard Next.js read-only (pas de wallet, pas de signature). |
| `.github/`              | Oui     | Workflows, scripts CI, config Dependabot. Les injections de script sont explicitement dans le scope. |
| Services tiers          | Non     | Open-Meteo, Kalshi, Pinata, Vercel, Discord — reporter chez le vendor. |
| Ingénierie sociale      | Non     | Cibler les comptes du mainteneur ou des contributeurs. |

## Hors scope

- Résultats qui supposent que l'attaquant contrôle déjà l'EOA, le
  compte Pinata ou le compte GitHub du mainteneur.
- Déni de service par épuisement légitime des quotas free-tier des
  API.
- Best-practice sans chemin d'exploitation concret. Ouvrir une issue
  normale ou une PR à la place.
- Travaux en cours sur `main` qui ne sont clairement pas déployés.

## Hardening déjà en place

- Analyse statique Slither en CI sur les contrats (`fail-on: medium`).
- Tests Forge unit + fuzz (10 000 runs) + invariants.
- Dependabot hebdomadaire sur `pip`, `npm`, `github-actions`.
- Analyse statique CodeQL sur Python et JavaScript/TypeScript.
- `.gitignore` couvre tous les fichiers de secrets connus ; procédure
  de rotation documentée dans
  [`docs/SECURITY-rotation-procedure.md`](docs/SECURITY-rotation-procedure.md)
  quand elle est présente.

## Statut mainnet

**Les contrats Phase 1 tournent uniquement sur le testnet Arbitrum
Sepolia.** Le déploiement mainnet est conditionné à au moins un audit
communautaire *et* à la mise en place d'un Safe multisig avec
signataires séparés par rôle. D'ici là, aucune valeur réelle n'est en
jeu on-chain.
