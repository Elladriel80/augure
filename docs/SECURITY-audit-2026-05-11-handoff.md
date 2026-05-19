# Security audit 2026-05-11 — action handoff

Ce document accompagne le PR `security/audit-2026-05-11`. Il liste **ce
qui a été corrigé en code** et **ce qui te reste à faire manuellement**
(rotations + paramètres GitHub).

---

## ✅ Corrigé dans le PR (rien à faire de ton côté)

| Audit ID | Fix |
|----------|-----|
| **P0-2** | Diagnostic historique : `git log --all` sur les `.env`, sur la clé Etherscan, sur le JWT Pinata et sur les webhooks Discord — **aucun secret trouvé dans l'historique**. Seules occurrences "discord.com/api/webhooks" sont des mentions textuelles dans les docstrings (URL générique sans token). Pas besoin de `git filter-repo` ni de force-push. |
| **P1-1** | `announce-release.yml` : inputs passés via `env:` et non interpolés dans `run:`. Whitelist `[A-Za-z0-9._/-]+` rejette tout tag malformé avant `$GITHUB_OUTPUT`. `weekly-recap.yml` était déjà OK (env vars), mais `build-weekly-recap.mjs` reçoit maintenant un `LOOKBACK_DAYS` clampé à `[1, 365]` avec fallback `7` sur NaN. |
| **P2-1** | `open_meteo.py:cache_path()` et `kalshi/client.py:snapshot_event()` : sanitisation par whitelist `[A-Za-z0-9._-]` + `Path.resolve()` + `relative_to()` qui lève si le chemin sort de la racine. Testé manuellement avec `..`, backslashes, drive letters, NUL byte. |
| **P2-2** | Les deux clients HTTP respectent maintenant `Retry-After` (cap à 30 s) et appliquent un budget cumulé (60 s Kalshi, 90 s Open-Meteo) qui les fait sortir tôt si l'API rate-limite trop longtemps. |
| **P2-3** | `predictor/requirements.lock` généré par `pip-compile --generate-hashes`. 297 lignes, toutes les transitives épinglées avec SHA-256. README mis à jour avec la commande `pip install -r requirements.lock --require-hashes` et la procédure de regen. |
| **P2-4** | `.github/dependabot.yml` (pip + npm + github-actions, hebdo lundi) et `.github/workflows/codeql.yml` (Python + JS/TS, security-extended) ajoutés. |
| **P2-5** | `node_modules/` confirmé absent de l'historique git (`git log --all -- dashboard/node_modules` vide). Rien à filter-repo. |
| **P3-1** | `USER_AGENT` mis à jour pour pointer vers l'identifiant projet courant (avec URL repo contactable). Plus de fuite d'identifiant historique dans les logs upstream Open-Meteo/Kalshi/NWS. |
| **P3-5** | `SECURITY.md` + `SECURITY.fr.md` à la racine, canal de disclosure via GitHub Private Vulnerability Reporting + politique 90 jours. |
| **P3-6** | Audit confirme que `allowed_mentions: { parse: [] }` est en place dans `post-discord.mjs`. Rien à faire. |
| **Bonus** | `.pre-commit-config.yaml` avec gitleaks + hygiène commune. `docs/SECURITY-rotation-procedure.md` documente comment tourner chaque secret. |

---

## 🔴 À faire AUJOURD'HUI (rotations)

L'audit recommande la rotation **inconditionnelle**, même si l'historique git est propre, parce que les `.env` sont restés sur disque sur une machine syncée GitHub Desktop. Le PR ne peut PAS tourner ces secrets à ta place — c'est manuel.

Procédure détaillée : [`docs/SECURITY-rotation-procedure.md`](SECURITY-rotation-procedure.md). Résumé exécutif ci-dessous.

- [ ] **Pinata** :
  - [ ] Activer 2FA sur le compte (le JWT actuel a `mfa_enabled: false`).
  - [ ] Générer une nouvelle scoped key avec permissions limitées
        (`pinFileToIPFS` + `pinList` uniquement, **pas** `unpin`).
  - [ ] Expiration à 90 jours.
  - [ ] Update `contracts/.env` local + repo secret `PINATA_JWT` si présent.
  - [ ] Révoquer l'ancien JWT depuis le dashboard Pinata.
- [ ] **Discord** : reset des 3 webhooks
      (`DISCORD_WEBHOOK_BUILD_LOG`, `DISCORD_WEBHOOK_PREDICTIONS`,
      `DISCORD_WEBHOOK_PNL_TRACKER`) **et** du repo secret
      `DISCORD_WEBHOOK_URL` côté CI.
- [ ] **Etherscan V2** : régénérer la clé (`<ancienne clé, révoquée le 2026-05-12>`) depuis [etherscan.io/myapikey](https://etherscan.io/myapikey). Optionnel : utiliser deux clés distinctes pour Etherscan et Arbiscan (P3-2).

---

## 🟠 À faire CETTE SEMAINE

### GitHub Security settings (5 min, gratuit)

`Settings → Code security and analysis` :
- [ ] **Secret scanning** : ON
- [ ] **Push protection** : ON (bloque les futurs commits avec secret reconnu)
- [ ] **Dependabot alerts** : ON
- [ ] **Dependabot security updates** : ON
- [ ] **CodeQL** : will run automatically once `.github/workflows/codeql.yml` lands sur main.

Référence : I-2 dans l'audit.

### Pre-commit local

```bash
pip install pre-commit
cd "C:\Users\Jean-Sébastien\Documents\Claude\Projects\Assurance décentralisée (1)\aratea"
pre-commit install
```

Bloque maintenant tout `git commit` qui inclurait un secret reconnu par gitleaks. Skippable une fois avec `--no-verify` si tu sais ce que tu fais.

### Déplacer les `.env` hors du repo (P1-2)

Optionnel mais recommandé : déplace `contracts/.env` et `predictor/.env` vers `~/.config/aratea/` (Linux/macOS) ou `%APPDATA%\aratea\` (Windows). Réduit la surface d'attaque locale (extensions VSCode, npm postinstall, etc.).

Si tu fais ça, il faudra adapter le chargement dans `contracts/script/*.s.sol` et les scripts Python qui font `dotenv.load_dotenv()` pour pointer vers le nouveau path.

---

## 🟡 À faire CE MOIS

- [ ] **Branch protection sur `main`** (I-3) : `Settings → Branches → Add rule for main`. Cocher *Require pull request before merging*, *Require status checks*, *Require signed commits*. Une fois activé, force-pushes et merges direct sont bloqués.
- [ ] **Vérifier `predictor/.env.example`** (P3-4) — confirmer que l'avertissement « Never commit this file with real values » est explicite. Ajouter si manquant.
- [ ] **Sequencing de la rotation Pinata** : caler un rappel calendar trimestriel pour rotation routinière.

---

## ⛔ Hors scope du PR (action utilisateur uniquement)

- **P1-3** : séparation des rôles Safe pour mainnet. Documenté dans le rotation runbook ; à câbler quand tu créeras le Safe.
- **I-1** : audit Solidity adversarial. Externe — Code4rena, Sherlock, ou peer review documentée avant mainnet.
- **I-4** : threat model des oracles externes. À traiter au moment où le predictor pilotera de la liquidité réelle.

---

## Vérification post-merge

Une fois ce PR mergé et les actions manuelles effectuées :

```bash
# Sanity check : les anciens secrets sont bien morts
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"rotation test"}' \
  "https://discord.com/api/webhooks/1503063500061413617/m9mVtGKA..."
# Doit retourner 404 ou 401 (webhook invalide) — sinon la rotation n'est pas faite.
```

```bash
# Sanity check : le pre-commit attrape bien un faux secret
cd aratea
echo "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789012345678/abcdef1234567890" > /tmp/fake.env
git add /tmp/fake.env  # hors repo mais bon
# pre-commit gitleaks doit pop
```
