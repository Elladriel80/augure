# TODO humain — Jean-Sébastien

> Ce fichier liste **uniquement** ce qui requiert ton intervention humaine et ne peut pas être fait par Claude (création de comptes externes, génération de portefeuilles, opérations de signature, validation de jalons). Tout le reste — code, tests, doc, CI — est traité côté Claude.
>
> Format : chaque action a un **statut**, un **moment où elle devient bloquante**, et une **estimation du temps** que ça te prendra.
>
> Ne fais rien ici sans que je te le rappelle au bon moment. Cette liste est juste pour qu'on n'oublie rien.

---

## Maintenant (M0 — setup initial)

### ☐ Ouvrir la pull request M0 sur GitHub

- **Pourquoi :** je ne peux pas ouvrir la PR moi-même (le CLI GitHub n'est pas installé sur ta machine), mais je vais préparer la branche `m0-contracts-setup` et la pousser sur le remote.
- **Ce que tu auras à faire :** ouvrir [https://github.com/Elladriel80/augure/pulls](https://github.com/Elladriel80/augure/pulls) → cliquer sur le bandeau jaune "Compare & pull request" → titre et description sont déjà préparés dans mon push, tu cliques juste "Create pull request".
- **Devient bloquant :** dès que je te dis que la branche est poussée (fin M0).
- **Temps estimé :** 30 secondes.

---

## Plus tard (M4 — déploiement testnet, dans environ 2-3 semaines)

### ☐ Créer un compte Pinata (stockage IPFS)

- **Pourquoi :** chaque round mensuel publié on-chain pointera vers son fichier JSON stocké sur IPFS. Pinata est le service qui garde ces fichiers accessibles publiquement.
- **Ce que tu auras à faire :** aller sur [pinata.cloud](https://pinata.cloud), créer un compte gratuit (1 GB inclus), récupérer une clé API, me la communiquer en privé.
- **Devient bloquant :** au moment où on publie le premier round on-chain (M4-M5).
- **Temps estimé :** 5-10 minutes.

### ☐ Créer le Safe multisig sur Arbitrum Sepolia

- **Pourquoi :** le Safe est le coffre-fort numérique qui détient le pouvoir de mint des tokens. Les actions sensibles (proposer un round, exécuter un mint) passeront par lui, jamais par une seule personne.
- **Ce que tu auras à faire :** aller sur [app.safe.global](https://app.safe.global), basculer le réseau sur Arbitrum Sepolia, créer un nouveau Safe avec 2 ou 3 signataires (toi + 1 ou 2 advisors de confiance), seuil 2/3 ou 2/2 selon ton choix. Je te guiderai pas-à-pas.
- **Pré-requis :** avoir un peu d'ETH testnet sur Arbitrum Sepolia (gratuit via faucet). Je t'enverrai le lien le moment venu.
- **Devient bloquant :** au moment du déploiement testnet (M4).
- **Temps estimé :** 15 minutes une fois MetaMask configuré.

### ☐ Me communiquer ton adresse EOA admin temporaire

- **Pourquoi :** l'adresse de ton portefeuille personnel (MetaMask sur Arbitrum Sepolia) qui détiendra temporairement les "clés admin" des contrats avant qu'on les transfère au Safe.
- **Ce que tu auras à faire :** ouvrir MetaMask, basculer sur Arbitrum Sepolia, copier l'adresse publique (`0x...`), me l'envoyer. **Aucune clé privée**, juste l'adresse publique.
- **Devient bloquant :** M4 (préparation du déploiement).
- **Temps estimé :** 30 secondes.

### ☐ Récupérer un peu d'ETH testnet sur Arbitrum Sepolia

- **Pourquoi :** payer les frais de transaction du déploiement initial (quelques centimes d'équivalent-dollars en ETH testnet, gratuit).
- **Ce que tu auras à faire :** utiliser un faucet comme [faucet.quicknode.com/arbitrum/sepolia](https://faucet.quicknode.com/arbitrum/sepolia) ou bridger depuis Sepolia ETH via [bridge.arbitrum.io](https://bridge.arbitrum.io).
- **Devient bloquant :** M4.
- **Temps estimé :** 5 minutes.

### ☐ Récupérer une clé API Arbiscan

- **Pourquoi :** vérifier publiquement le code source des contrats déployés (pour que la communauté puisse les inspecter directement sur le scanner blockchain).
- **Ce que tu auras à faire :** créer un compte gratuit sur [arbiscan.io](https://arbiscan.io) (le scanner blockchain d'Arbitrum), générer une clé API, me la communiquer.
- **Devient bloquant :** M4 (étape "verify" du déploiement).
- **Temps estimé :** 5 minutes.

---

## Encore plus tard (au moment d'envisager le mainnet)

### ☐ Audit communautaire des contrats

- **Pourquoi :** le prompt te disait que le mainnet est bloqué tant qu'au moins un audit communautaire n'a pas été fait. C'est une condition que TU as posée pour te protéger (et protéger les futurs holders) contre des bugs critiques.
- **Pistes :** Code4rena Arena-X (audit collaboratif payant mais accessible solo), Sherlock Watson, ou peer review documentée par 2-3 devs Solidity reconnus de la communauté.
- **Devient bloquant :** au moment où tu veux passer en mainnet (vraisemblablement plusieurs mois après M5).
- **Temps estimé :** plusieurs semaines de processus, coût variable selon l'option.

---

> Si tu vois quelque chose dans cette liste que tu veux supprimer, modifier ou prioriser autrement, dis-le moi.
