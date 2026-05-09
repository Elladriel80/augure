> [Read in English](README.md)

# dashboard

Dashboard read-only de la couche de règlement Phase 1 d'Augure. Affiche l'état live
de `AugPocToken` et `RoundRegistry` déployés sur Arbitrum Sepolia (testnet).

## Statut

Phase 1 — *active*. Jalon M5. Voir [`/contracts/README.fr.md`](../contracts/README.fr.md)
pour les pièces on-chain que ce dashboard lit.

## Ce qu'il affiche

- **Page token** (`/`) : nom, symbol, décimales, total supply, état pause, cap
  mensuel 10 % avec % consommé, liens vers les contracts sur Arbiscan.
- **Page rounds** (`/rounds`) : tous les rounds enregistrés, triés par date de
  proposition. Pastille de statut (Proposed / Challenged / Executed / Cancelled),
  fin de fenêtre de challenge, total à minter, nombre de bénéficiaires.
- **Détail d'un round** (`/round/[hash]`) : metadata complète avec compte à rebours
  live de la fenêtre de challenge (le cas échéant), lien IPFS vers le
  `valuation_report.md` pinné, ventilation par bénéficiaire.

## Ce qu'il ne fait PAS

- **Pas de wallet connect.** Read-only par design — le dashboard ne demande aucune
  signature, ne broadcast aucune transaction, ne détient aucune clé. Les opérations
  (`proposeRound`, `executeRound`, `cancelRound`) passent par les scripts Foundry
  dans [`/contracts/script/`](../contracts/script/), pas par cette UI.
- **Pas de backend, pas de base de données.** Chaque page se rend côté serveur en
  lisant directement la chain via un endpoint RPC public. L'hébergement est
  statique-friendly (Vercel, Netlify, Cloudflare Pages).

## Stack

- Next.js 15 (App Router) + React 19
- TypeScript strict
- viem 2.x (pas de wagmi — on n'a pas besoin de plumbing wallet)
- Tailwind CSS pour le styling
- Aucun framework CSS externe, aucun kit UI, aucun analytics

## Développement local

### Pré-requis

- Node.js 20+ ([télécharger](https://nodejs.org)).
- Optionnel mais recommandé : un endpoint RPC gratuit chez Alchemy, Infura ou Ankr
  pour Arbitrum Sepolia. L'endpoint public par défaut marche mais est rate-limité.

### Lancer

```bash
cd dashboard
cp .env.example .env.local
# Renseigner NEXT_PUBLIC_TOKEN_ADDRESS et NEXT_PUBLIC_REGISTRY_ADDRESS une fois le
# script de déploiement M4 exécuté sur Arbitrum Sepolia. Jusque-là le dashboard
# affiche un message "not yet deployed".
npm install
npm run dev
```

Ouvrir [http://localhost:3000](http://localhost:3000).

### Anvil (fork local)

Pour développer contre un fork local d'Arbitrum Sepolia :

```bash
# Dans un terminal — forker le testnet live
anvil --fork-url https://sepolia-rollup.arbitrum.io/rpc

# Dans un autre — pointer le dashboard dessus
NEXT_PUBLIC_CHAIN_ID=31337 \
NEXT_PUBLIC_RPC_URL=http://127.0.0.1:8545 \
NEXT_PUBLIC_TOKEN_ADDRESS=0x... \
NEXT_PUBLIC_REGISTRY_ADDRESS=0x... \
  npm run dev
```

## Déploiement sur Vercel

1. Connecter le repo GitHub à un nouveau projet Vercel, root directory =
   `dashboard/`.
2. Configurer les variables d'environnement dans **Settings → Environment Variables** :
   - `NEXT_PUBLIC_RPC_URL` (recommandé : un endpoint payant pour éviter le
     rate-limit)
   - `NEXT_PUBLIC_CHAIN_ID=421614`
   - `NEXT_PUBLIC_TOKEN_ADDRESS` et `NEXT_PUBLIC_REGISTRY_ADDRESS` (depuis le deploy
     M4)
   - `NEXT_PUBLIC_DEPLOY_BLOCK` (le block number de la tx de déploiement —
     accélère drastiquement les requêtes d'événements en sautant l'historique
     antérieur)
3. Deploy.

Le tier gratuit Vercel suffit — chaque page est rendue côté serveur, pas de
fonctions edge, pas de base de données.

## Pourquoi pas de cache server-render ?

Chaque page définit `export const dynamic = "force-dynamic"` pour que les
utilisateurs voient toujours l'état on-chain frais à chaque refresh. On évite
volontairement les couches ISR/cache de Next : les changements d'état sont rares
(un round par mois) mais quand ils arrivent on veut qu'ils soient visibles tout
de suite, pas après l'intervalle de revalidation. Le coût est une ou deux requêtes
RPC par page, ce qui passe largement sur un tier gratuit.

## Licence

Apache 2.0 — voir [/LICENSE](../LICENSE).
